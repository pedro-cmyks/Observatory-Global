#!/usr/bin/env python3
"""
Simple GDELT Backfill Script - Standalone version
Uses only standard library + psycopg2 for maximum reliability.

Usage:
    python3 scripts/simple_backfill.py --from 2025-12-30 --to 2026-01-13 --limit 10
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Increase CSV field size limit for GDELT
csv.field_size_limit(10 * 1024 * 1024)

# Database configuration (Docker PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://observatory:changeme@localhost:5432/observatory"
)

# GDELT Archive URL pattern
GDELT_URL = "http://data.gdeltproject.org/gdeltv2/{timestamp}.gkg.csv.zip"

# Checkpoint file
CHECKPOINT_FILE = Path("checkpoints/simple_backfill.json")

# FIPS to ISO country code mapping (subset for common countries)
FIPS_TO_ISO = {
    "US": "US", "UK": "GB", "CA": "CA", "AU": "AU", "NZ": "NZ",
    "FR": "FR", "GM": "DE", "IT": "IT", "SP": "ES", "PO": "PT",
    "NL": "NL", "BE": "BE", "SZ": "CH", "AU": "AT", "PL": "PL",
    "SW": "SE", "NO": "NO", "DA": "DK", "FI": "FI", "EI": "IE",
    "GR": "GR", "TU": "TR", "RS": "RU", "UP": "UA", "CH": "CN",
    "JA": "JP", "KS": "KR", "KN": "KP", "IN": "IN", "PK": "PK",
    "BG": "BD", "BM": "MM", "TH": "TH", "VM": "VN", "MY": "MY",
    "SN": "SG", "ID": "ID", "RP": "PH", "AS": "AU", "MX": "MX",
    "BR": "BR", "AR": "AR", "CI": "CL", "CO": "CO", "PE": "PE",
    "VE": "VE", "EG": "EG", "SF": "ZA", "NI": "NG", "KE": "KE",
    "IS": "IL", "SA": "SA", "AE": "AE", "IR": "IR", "IZ": "IQ",
    "AF": "AF", "BL": "BO", "EC": "EC", "PM": "PA", "NU": "NI",
    "GT": "GT", "HO": "HN", "ES": "SV", "CU": "CU", "DR": "DO",
    "HA": "HT", "JM": "JM", "CS": "CZ", "HU": "HU", "RO": "RO",
    "BU": "BG", "EN": "EE", "LG": "LV", "LH": "LT", "LO": "SK",
    "SI": "SI", "HR": "HR", "BK": "BA", "MW": "MK", "AL": "AL",
    "SR": "RS", "MN": "ME", "KV": "XK", "BY": "BY", "MD": "MD",
    "GG": "GE", "AM": "AM", "AJ": "AZ", "KZ": "KZ", "UZ": "UZ",
    "TI": "TJ", "KG": "KG", "TX": "TM"
}


def fips_to_iso(fips_code):
    """Convert FIPS country code to ISO 3166-1 alpha-2."""
    if not fips_code:
        return None
    return FIPS_TO_ISO.get(fips_code.upper(), fips_code.upper())


def generate_timestamps(from_date, to_date):
    """Generate all GDELT 15-minute timestamps between two dates."""
    timestamps = []
    current = from_date.replace(minute=0, second=0, microsecond=0)
    
    while current <= to_date:
        for minute in [0, 15, 30, 45]:
            ts = current.replace(minute=minute)
            if from_date <= ts <= to_date:
                timestamps.append(ts.strftime("%Y%m%d%H%M%S"))
        current += timedelta(hours=1)
    
    return timestamps


def download_gkg(timestamp):
    """Download and extract a GDELT GKG file."""
    url = GDELT_URL.format(timestamp=timestamp)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            if response.status != 200:
                return None
            data = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"  HTTP error {e.code} for {timestamp}")
        return None
    except Exception as e:
        print(f"  Error downloading {timestamp}: {e}")
        return None
    
    # Extract CSV from zip
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.endswith('.csv'):
                    return zf.read(name).decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  Error extracting {timestamp}: {e}")
        return None
    
    return None


def parse_gkg_row(row):
    """Parse a single GKG row into a signal dict."""
    if len(row) < 27:
        return None
    
    # Timestamp
    try:
        date_str = row[0]
        timestamp = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except:
        timestamp = datetime.now(timezone.utc)
    
    source_url = row[4] if len(row) > 4 else None
    source_name = row[3] if len(row) > 3 else None
    
    # Locations (V2ENHANCEDLOCATIONS - field 10)
    locations = row[10] if len(row) > 10 else ""
    country_code = None
    lat = None
    lon = None
    
    if locations:
        for loc in locations.split(';'):
            parts = loc.split('#')
            if len(parts) >= 6:
                cc_fips = parts[2][:2] if parts[2] else None
                country_code = fips_to_iso(cc_fips)
                try:
                    lat = float(parts[4]) if parts[4] else None
                    lon = float(parts[5]) if parts[5] else None
                except:
                    pass
                if country_code and lat and lon:
                    break
    
    if not country_code:
        return None
    
    # Themes
    themes_raw = row[8] if len(row) > 8 else ""
    themes = []
    if themes_raw:
        for theme in themes_raw.split(';')[:10]:
            theme_name = theme.split(',')[0] if ',' in theme else theme
            if theme_name and len(theme_name) > 2:
                themes.append(theme_name.upper())
    themes = list(set(themes))[:10]
    
    # Persons
    persons_raw = row[12] if len(row) > 12 else ""
    persons = []
    if persons_raw:
        for person in persons_raw.split(';')[:10]:
            person_name = person.split(',')[0] if ',' in person else person
            if person_name and len(person_name) > 2:
                persons.append(person_name.lower())
    persons = list(set(persons))[:10]
    
    # Sentiment (tone)
    tone_raw = row[15] if len(row) > 15 else ""
    sentiment = 0.0
    if tone_raw:
        try:
            tone_parts = tone_raw.split(',')
            sentiment = float(tone_parts[0]) if tone_parts else 0.0
        except:
            pass
    
    return {
        'timestamp': timestamp,
        'country_code': country_code.upper(),
        'latitude': lat,
        'longitude': lon,
        'sentiment': sentiment,
        'source_url': source_url,
        'source_name': source_name,
        'themes': themes,
        'persons': persons,
    }


def parse_csv(csv_content):
    """Parse GKG CSV content into signals."""
    signals = []
    reader = csv.reader(io.StringIO(csv_content), delimiter='\t')
    for row in reader:
        try:
            signal = parse_gkg_row(row)
            if signal:
                signals.append(signal)
        except:
            continue
    return signals


def insert_signals(conn, signals):
    """Insert signals into PostgreSQL."""
    if not signals:
        return 0
    
    inserted = 0
    cur = conn.cursor()
    
    for s in signals:
        try:
            cur.execute("""
                INSERT INTO signals_v2 (
                    timestamp, country_code, latitude, longitude, sentiment,
                    source_url, source_name, themes, persons
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                s['timestamp'],
                s['country_code'],
                s['latitude'],
                s['longitude'],
                s['sentiment'],
                s['source_url'],
                s['source_name'],
                s['themes'],
                s['persons'],
            ))
            inserted += 1
        except Exception as e:
            pass
    
    conn.commit()
    cur.close()
    return inserted


def load_checkpoint():
    """Load checkpoint from file."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"last_timestamp": None, "total_inserted": 0, "files_processed": 0}


def save_checkpoint(checkpoint):
    """Save checkpoint to file."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    checkpoint["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


def run_backfill(from_date, to_date, rate=1.0, limit=None):
    """Run the backfill."""
    import psycopg2
    
    # Parse dates
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(
        hour=23, minute=45, tzinfo=timezone.utc
    )
    
    # Generate timestamps
    all_timestamps = generate_timestamps(from_dt, to_dt)
    print(f"Backfill range: {from_date} to {to_date} ({len(all_timestamps)} files)")
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    last_ts = checkpoint.get("last_timestamp")
    
    # Find resume point
    start_idx = 0
    if last_ts and last_ts in all_timestamps:
        start_idx = all_timestamps.index(last_ts) + 1
        print(f"Resuming from {last_ts} (file {start_idx}/{len(all_timestamps)})")
    
    remaining = all_timestamps[start_idx:]
    if limit:
        remaining = remaining[:limit]
    
    if not remaining:
        print("Nothing to process")
        return
    
    print(f"Processing {len(remaining)} files...")
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    
    try:
        for i, ts in enumerate(remaining):
            print(f"[{start_idx + i + 1}/{len(all_timestamps)}] {ts}...", end=" ")
            
            # Download
            csv_content = download_gkg(ts)
            if not csv_content:
                print("(not found)")
                checkpoint["last_timestamp"] = ts
                checkpoint["files_processed"] = checkpoint.get("files_processed", 0) + 1
                save_checkpoint(checkpoint)
                time.sleep(rate)
                continue
            
            # Parse
            signals = parse_csv(csv_content)
            
            # Insert
            inserted = insert_signals(conn, signals)
            checkpoint["total_inserted"] = checkpoint.get("total_inserted", 0) + inserted
            checkpoint["last_timestamp"] = ts
            checkpoint["files_processed"] = checkpoint.get("files_processed", 0) + 1
            save_checkpoint(checkpoint)
            
            print(f"{len(signals)} parsed, {inserted} inserted")
            
            time.sleep(rate)
        
        print(f"\nBackfill complete! Total inserted: {checkpoint['total_inserted']}")
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Simple GDELT Backfill")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--rate", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--limit", type=int, help="Max files to process (for testing)")
    parser.add_argument("--status", action="store_true", help="Show checkpoint status")
    
    args = parser.parse_args()
    
    if args.status:
        cp = load_checkpoint()
        print(json.dumps(cp, indent=2))
        return
    
    run_backfill(args.from_date, args.to_date, args.rate, args.limit)


if __name__ == "__main__":
    main()
