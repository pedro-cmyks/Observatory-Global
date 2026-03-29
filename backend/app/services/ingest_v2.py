"""
GDELT Ingestion for V2 Schema
Fetches latest GDELT data and inserts into signals_v2 table
V3: Now includes crisis classification
V3.1: Converts FIPS country codes to ISO 3166-1 alpha-2
V3.2: Fixed CSV field size limit for GDELT GKG large fields
"""
import csv
import sys

# CRITICAL: Increase CSV field size limit for GDELT GKG files
# GDELT V2Themes/V2Persons columns can exceed 200KB
# Must be set BEFORE any csv.reader() calls
csv.field_size_limit(10 * 1024 * 1024)  # 10MB

import asyncio
import aiohttp
import asyncpg
import zipfile
import io
import logging
from datetime import datetime, timezone
from typing import Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.crisis_themes import (
    is_crisis_theme,
    get_crisis_themes,
    calculate_crisis_score,
    calculate_severity,
    get_event_type
)
from app.services.country_codes import fips_to_iso

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")

# GDELT GKG (Global Knowledge Graph) URL
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
GDELT_TRANS_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate-translation.txt"

async def fetch_latest_gdelt_url(update_url: str = GDELT_LAST_UPDATE_URL) -> Optional[str]:
    """Get the URL of the latest GDELT GKG file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(update_url) as resp:
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
    """Download and parse GDELT GKG file with resilient error handling."""
    signals = []
    skipped = 0
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error(f"Failed to download {url}: {resp.status}")
                return signals
            
            data = await resp.read()
            
    # Unzip and parse
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    with zf.open(filename) as f:
                        reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8', errors='replace'), delimiter='\t')
                        for line_num, row in enumerate(reader, start=1):
                            try:
                                signal = parse_gkg_row(row)
                                if signal:
                                    signals.append(signal)
                            except Exception as e:
                                skipped += 1
                                if skipped <= 5:  # Log first 5 errors only
                                    logger.warning(f"Skipped line {line_num} in {filename}: {type(e).__name__}: {str(e)[:100]}")
                                continue  # CRITICAL: Continue, don't crash
    except Exception as e:
        logger.error(f"Failed to process zip file from {url}: {e}")
    
    if skipped > 0:
        logger.info(f"Processed {url}: {len(signals)} signals, {skipped} skipped")
    
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
    
    headline = None
    if source_url:
        import urllib.parse
        try:
            path = urllib.parse.urlparse(source_url).path
            slug = path.strip('/').split('/')[-1]
            if slug and len(slug) >= 5 and ('-' in slug or '_' in slug):
                slug = slug.replace('.html', '').replace('.htm', '').replace('.php', '')
                headline = slug.replace('-', ' ').replace('_', ' ').title()
        except:
            pass
    
    # Locations (V2ENHANCEDLOCATIONS - field 10)
    locations = row[10] if len(row) > 10 else ""
    country_code = None
    lat = None
    lon = None
    
    if locations:
        for loc in locations.split(';'):
            parts = loc.split('#')
            if len(parts) >= 6:
                # Extract FIPS code and convert to ISO
                country_code_fips = parts[2][:2] if parts[2] else None
                country_code = fips_to_iso(country_code_fips)  # Convert FIPS→ISO
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
    
    # Crisis classification
    crisis_themes = get_crisis_themes(themes)
    is_crisis = len(crisis_themes) > 0
    crisis_score = calculate_crisis_score(themes) if is_crisis else 0.0
    severity = calculate_severity(themes) if is_crisis else 'low'
    event_type = get_event_type(themes) if is_crisis else 'other'
    
    return {
        'timestamp': timestamp,
        'country_code': country_code.upper(),
        'latitude': lat,
        'longitude': lon,
        'sentiment': sentiment,
        'source_url': source_url,
        'source_name': source_name,
        'headline': headline,
        'themes': themes,
        'persons': persons,
        # Crisis classification fields
        'is_crisis': is_crisis,
        'crisis_score': crisis_score,
        'crisis_themes': crisis_themes,
        'severity': severity,
        'event_type': event_type
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
                    INSERT INTO signals_v2 (
                        timestamp, country_code, latitude, longitude, sentiment, 
                        source_url, source_name, headline, themes, persons,
                        is_crisis, crisis_score, crisis_themes, severity, event_type
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT DO NOTHING
                """, 
                    signal['timestamp'],
                    signal['country_code'],
                    signal['latitude'],
                    signal['longitude'],
                    signal['sentiment'],
                    signal['source_url'],
                    signal['source_name'],
                    signal['headline'],
                    signal['themes'],
                    signal['persons'],
                    signal['is_crisis'],
                    signal['crisis_score'],
                    signal['crisis_themes'],
                    signal['severity'],
                    signal['event_type']
                )
                inserted += 1
            except Exception as e:
                continue
    
    return inserted

async def update_countries(pool: asyncpg.Pool):
    """
    Add new countries from signals, but NEVER overwrite existing coordinates.
    Manual coordinates in countries_v2 are authoritative.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO countries_v2 (code, name, latitude, longitude)
            SELECT DISTINCT
                country_code,
                country_code,
                NULL::numeric,
                NULL::numeric
            FROM signals_v2
            WHERE country_code IS NOT NULL
            AND country_code NOT IN (SELECT code FROM countries_v2)
            ON CONFLICT (code) DO NOTHING
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
        url = await fetch_latest_gdelt_url(GDELT_LAST_UPDATE_URL)
        if url:
            print(f"Downloading: {url}")
            signals = await download_and_parse_gkg(url)
            print(f"Parsed {len(signals)} eng signals")
            inserted = await insert_signals(pool, signals)
            print(f"Inserted {inserted} new eng signals")
        
        # Fetch Translingual GDELT URL
        trans_url = await fetch_latest_gdelt_url(GDELT_TRANS_UPDATE_URL)
        if trans_url:
            print(f"Downloading Translingual: {trans_url}")
            trans_signals = await download_and_parse_gkg(trans_url)
            print(f"Parsed {len(trans_signals)} translingual signals")
            inserted_trans = await insert_signals(pool, trans_signals)
            print(f"Inserted {inserted_trans} new translingual signals")
        
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
