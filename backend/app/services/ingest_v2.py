"""
GDELT Ingestion for V2 Schema
Fetches latest GDELT data and inserts into signals_v2 table
"""
import asyncio
import aiohttp
import asyncpg
import zipfile
import io
import csv
from datetime import datetime, timezone
from typing import Optional
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory")

# GDELT GKG (Global Knowledge Graph) URL
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

async def fetch_latest_gdelt_url() -> Optional[str]:
    """Get the URL of the latest GDELT GKG file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(GDELT_LAST_UPDATE_URL) as resp:
            if resp.status != 200:
                print(f"Failed to fetch GDELT update list: {resp.status}")
                return None
            text = await resp.text()
            for line in text.strip().split('\n'):
                if 'gkg' in line.lower() and line.endswith('.csv.zip'):
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
    return None

async def download_and_parse_gkg(url: str) -> list[dict]:
    """Download and parse GDELT GKG file."""
    signals = []
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Failed to download {url}: {resp.status}")
                return signals
            
            data = await resp.read()
            
    # Unzip and parse
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for filename in zf.namelist():
            if filename.endswith('.csv'):
                with zf.open(filename) as f:
                    reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8', errors='replace'), delimiter='\t')
                    for row in reader:
                        try:
                            signal = parse_gkg_row(row)
                            if signal:
                                signals.append(signal)
                        except Exception as e:
                            continue
    
    return signals

def parse_gkg_row(row: list) -> Optional[dict]:
    """Parse a single GKG row into a signal dict."""
    if len(row) < 27:
        return None
    
    # Extract fields (GKG 2.0 format)
    try:
        date_str = row[0]  # YYYYMMDDHHMMSS
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
                country_code = parts[2][:2] if parts[2] else None
                try:
                    lat = float(parts[4]) if parts[4] else None
                    lon = float(parts[5]) if parts[5] else None
                except:
                    pass
                if country_code and lat and lon:
                    break
    
    if not country_code:
        return None
    
    # Themes (V2ENHANCEDTHEMES - field 8)
    themes_raw = row[8] if len(row) > 8 else ""
    themes = []
    if themes_raw:
        for theme in themes_raw.split(';'):
            theme_name = theme.split(',')[0] if ',' in theme else theme
            if theme_name and len(theme_name) > 2:
                themes.append(theme_name.upper())
    themes = list(set(themes))[:10]
    
    # Persons (V2ENHANCEDPERSONS - field 12)
    persons_raw = row[12] if len(row) > 12 else ""
    persons = []
    if persons_raw:
        for person in persons_raw.split(';'):
            person_name = person.split(',')[0] if ',' in person else person
            if person_name and len(person_name) > 2:
                persons.append(person_name.lower())
    persons = list(set(persons))[:10]
    
    # Tone (V2TONE - field 15)
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
        'persons': persons
    }

async def insert_signals(pool: asyncpg.Pool, signals: list[dict]) -> int:
    """Insert signals into database."""
    if not signals:
        return 0
    
    inserted = 0
    async with pool.acquire() as conn:
        for signal in signals:
            try:
                await conn.execute("""
                    INSERT INTO signals_v2 (timestamp, country_code, latitude, longitude, sentiment, source_url, source_name, themes, persons)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT DO NOTHING
                """, 
                    signal['timestamp'],
                    signal['country_code'],
                    signal['latitude'],
                    signal['longitude'],
                    signal['sentiment'],
                    signal['source_url'],
                    signal['source_name'],
                    signal['themes'],
                    signal['persons']
                )
                inserted += 1
            except Exception as e:
                continue
    
    return inserted

async def update_countries(pool: asyncpg.Pool):
    """Update countries_v2 with any new countries from signals."""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO countries_v2 (code, name, latitude, longitude)
            SELECT DISTINCT ON (country_code)
                country_code,
                country_code,
                AVG(latitude),
                AVG(longitude)
            FROM signals_v2
            WHERE country_code IS NOT NULL
            AND latitude IS NOT NULL
            GROUP BY country_code
            ON CONFLICT (code) DO UPDATE SET
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
        """)

async def refresh_aggregates(pool: asyncpg.Pool):
    """Refresh the materialized view."""
    async with pool.acquire() as conn:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2")

async def run_ingestion():
    """Main ingestion function."""
    print(f"[{datetime.now()}] Starting GDELT ingestion...")
    
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    try:
        # Fetch latest GDELT URL
        url = await fetch_latest_gdelt_url()
        if not url:
            print("Could not find GDELT update URL")
            return
        
        print(f"Downloading: {url}")
        
        # Download and parse
        signals = await download_and_parse_gkg(url)
        print(f"Parsed {len(signals)} signals")
        
        # Insert
        inserted = await insert_signals(pool, signals)
        print(f"Inserted {inserted} new signals")
        
        # Update countries
        await update_countries(pool)
        print("Updated countries")
        
        # Refresh aggregates
        await refresh_aggregates(pool)
        print("Refreshed aggregates")
        
        # Stats
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM signals_v2")
            print(f"Total signals in database: {count}")
        
    finally:
        await pool.close()
    
    print(f"[{datetime.now()}] Ingestion complete!")

if __name__ == "__main__":
    asyncio.run(run_ingestion())
