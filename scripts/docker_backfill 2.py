#!/usr/bin/env python3
"""
GDELT Backfill via Python + docker exec psql
Avoids psycopg2 dependency by using subprocess to call docker exec
"""

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Increase CSV field size limit
csv.field_size_limit(10 * 1024 * 1024)

GDELT_URL = "http://data.gdeltproject.org/gdeltv2/{timestamp}.gkg.csv.zip"
CHECKPOINT_FILE = Path("checkpoints/backfill.json")

# FIPS to ISO mapping
FIPS_TO_ISO = {
    "US": "US", "UK": "GB", "CA": "CA", "AU": "AU", "NZ": "NZ",
    "FR": "FR", "GM": "DE", "IT": "IT", "SP": "ES", "PO": "PT",
    "NL": "NL", "BE": "BE", "SZ": "CH", "AS": "AU", "PL": "PL",
    "SW": "SE", "NO": "NO", "DA": "DK", "FI": "FI", "EI": "IE",
    "GR": "GR", "TU": "TR", "RS": "RU", "UP": "UA", "CH": "CN",
    "JA": "JP", "KS": "KR", "IN": "IN", "PK": "PK", "BG": "BD",
    "TH": "TH", "VM": "VN", "MY": "MY", "SN": "SG", "ID": "ID",
    "RP": "PH", "MX": "MX", "BR": "BR", "AR": "AR", "CI": "CL",
    "CO": "CO", "PE": "PE", "VE": "VE", "EG": "EG", "SF": "ZA",
    "NI": "NG", "KE": "KE", "IS": "IL", "SA": "SA", "AE": "AE",
    "IR": "IR", "IZ": "IQ", "AF": "AF"
}

def fips_to_iso(code):
    if not code:
        return None
    return FIPS_TO_ISO.get(code.upper(), code.upper())

def generate_timestamps(from_date, to_date):
    timestamps = []
    current = from_date.replace(minute=0, second=0, microsecond=0)
    while current <= to_date:
        for m in [0, 15, 30, 45]:
            ts = current.replace(minute=m)
            if from_date <= ts <= to_date:
                timestamps.append(ts.strftime("%Y%m%d%H%M%S"))
        current += timedelta(hours=1)
    return timestamps

def download_gkg(timestamp):
    url = GDELT_URL.format(timestamp=timestamp)
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        return None
    
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.endswith('.csv'):
                    return zf.read(name).decode('utf-8', errors='replace')
    except:
        pass
    return None

def parse_gkg_row(row):
    if len(row) < 27:
        return None
    
    try:
        ts = row[0][:14]
        timestamp = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
    except:
        return None
    
    source_name = row[3] if len(row) > 3 else ""
    source_url = row[4] if len(row) > 4 else ""
    
    # Parse locations
    locations = row[10] if len(row) > 10 else ""
    country_code = None
    lat = lon = None
    
    if locations:
        for loc in locations.split(';'):
            parts = loc.split('#')
            # V2ENHANCEDLOCATIONS format: Type#Name#Country#Region#CharOffset#Lat#Lon#FeatureID
            if len(parts) >= 7 and parts[2] and parts[5] and parts[6]:
                country_code = fips_to_iso(parts[2][:2])
                try:
                    lat = float(parts[5])
                    lon = float(parts[6])
                except:
                    continue
                # Validate coordinates
                if country_code and lat and lon and -90 <= lat <= 90 and -180 <= lon <= 180:
                    break
    
    if not country_code or lat is None or lon is None:
        return None
    
    # Sentiment
    sentiment = 0.0
    if len(row) > 15 and row[15]:
        try:
            sentiment = float(row[15].split(',')[0])
        except:
            pass
    
    # Themes (first 5)
    themes = []
    if len(row) > 8 and row[8]:
        for t in row[8].split(';')[:5]:
            name = t.split(',')[0] if ',' in t else t
            if name and len(name) > 2:
                themes.append(name.upper().replace("'", "''"))
    
    # Persons (first 5)
    persons = []
    if len(row) > 12 and row[12]:
        for p in row[12].split(';')[:5]:
            name = p.split(',')[0] if ',' in p else p
            if name and len(name) > 2:
                persons.append(name.lower().replace("'", "''"))
    
    return {
        'timestamp': timestamp,
        'country_code': country_code,
        'latitude': lat,
        'longitude': lon,
        'sentiment': sentiment,
        'source_url': source_url.replace("'", "''")[:500],
        'source_name': source_name.replace("'", "''")[:200],
        'themes': themes,
        'persons': persons
    }

def insert_batch(signals):
    if not signals:
        return 0
    
    # Build SQL
    values = []
    for s in signals:
        themes_arr = "'{" + ",".join(f'"{t}"' for t in s['themes']) + "}'"
        persons_arr = "'{" + ",".join(f'"{p}"' for p in s['persons']) + "}'"
        
        val = f"('{s['timestamp']}', '{s['country_code']}', {s['latitude']}, {s['longitude']}, " \
              f"{s['sentiment']}, '{s['source_url']}', '{s['source_name']}', {themes_arr}, {persons_arr})"
        values.append(val)
    
    sql = f"""
    INSERT INTO signals_v2 (timestamp, country_code, latitude, longitude, sentiment, source_url, source_name, themes, persons)
    VALUES {','.join(values)}
    ON CONFLICT DO NOTHING;
    """
    
    # Execute via docker exec
    result = subprocess.run(
        ["docker", "exec", "-i", "observatory-postgres", "psql", "-U", "observatory", "-d", "observatory", "-c", sql],
        capture_output=True,
        text=True
    )
    
    # Parse INSERT count - format is "INSERT 0 N"
    if "INSERT 0" in result.stdout:
        try:
            # Extract the number after "INSERT 0 "
            match = result.stdout.split("INSERT 0")[1].strip().split()[0]
            return int(match)
        except:
            pass
    return 0

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"last": None, "inserted": 0, "processed": 0}

def save_checkpoint(cp):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    cp["updated"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(cp, f)

def run(from_date, to_date, limit=0):
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=45, tzinfo=timezone.utc)
    
    all_ts = generate_timestamps(from_dt, to_dt)
    print(f"Backfill: {from_date} to {to_date} ({len(all_ts)} files)")
    
    cp = load_checkpoint()
    last = cp.get("last")
    
    start_idx = 0
    if last and last in all_ts:
        start_idx = all_ts.index(last) + 1
        print(f"Resuming from {last} (file {start_idx}/{len(all_ts)})")
    
    remaining = all_ts[start_idx:]
    if limit:
        remaining = remaining[:limit]
    
    for i, ts in enumerate(remaining):
        idx = start_idx + i + 1
        print(f"[{idx}/{len(all_ts)}] {ts}...", end=" ", flush=True)
        
        csv_data = download_gkg(ts)
        if not csv_data:
            print("(not found)")
            cp["last"] = ts
            cp["processed"] = cp.get("processed", 0) + 1
            save_checkpoint(cp)
            time.sleep(1)
            continue
        
        # Parse
        signals = []
        reader = csv.reader(io.StringIO(csv_data), delimiter='\t')
        for row in reader:
            try:
                sig = parse_gkg_row(row)
                if sig:
                    signals.append(sig)
            except:
                pass
        
        # Insert in batches of 100
        inserted = 0
        for batch_start in range(0, len(signals), 100):
            batch = signals[batch_start:batch_start+100]
            inserted += insert_batch(batch)
        
        cp["last"] = ts
        cp["processed"] = cp.get("processed", 0) + 1
        cp["inserted"] = cp.get("inserted", 0) + inserted
        save_checkpoint(cp)
        
        print(f"{len(signals)} parsed, {inserted} inserted")
        time.sleep(1)
    
    print(f"\nDone! Total inserted: {cp['inserted']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    
    if args.status:
        print(json.dumps(load_checkpoint(), indent=2))
    else:
        run(args.from_date, args.to_date, args.limit)
