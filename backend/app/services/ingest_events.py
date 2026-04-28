"""
GDELT Events Ingestion Service for V2 Schema.
Fetches the latest GDELT Events export (export.CSV.zip) and inserts into events_v2.
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import zipfile
import io
import pandas as pd
from datetime import datetime, timezone

from app.services.country_codes import fips_to_iso

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

async def fetch_latest_events_url() -> str | None:
    """Get the URL of the latest GDELT Events export file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(GDELT_LAST_UPDATE_URL) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch GDELT update list: {resp.status}")
                return None
            text = await resp.text()
            for line in text.strip().split('\n'):
                # We want the export.CSV.zip (not mentions, not gkg)
                if 'export.csv.zip' in line.lower():
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
    return None

async def download_and_parse_events(url: str) -> list[dict]:
    """Download and parse GDELT Events file."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to download {url}")
                    return []
                content = await resp.read()

        results = []
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                # GDELT Events has no header, use tab separator
                # Need to specify types or use low_memory=False
                df = pd.read_csv(f, sep='\t', header=None, low_memory=False)
                
                # We need columns:
                # 0: GlobalEventID
                # 57: DATEADDED (YYYYMMDDHHMMSS)
                # 5: Actor1Code, 6: Actor1Name, 7: Actor1CountryCode
                # 15: Actor2Code, 16: Actor2Name, 17: Actor2CountryCode
                # 26: IsRootEvent, 27: EventCode, 28: EventBaseCode, 29: EventRootCode
                # 30: QuadClass, 31: GoldsteinScale
                # 32: NumMentions, 33: NumSources, 34: NumArticles, 35: AvgTone
                # 51: ActionGeo_FullName, 52: ActionGeo_CountryCode (FIPS)
                # 54: ActionGeo_Lat, 55: ActionGeo_Long
                # 58: SOURCEURL
                
                if len(df.columns) < 59:
                    logger.error("Events CSV has fewer columns than expected")
                    return []

                # Convert DATEADDED
                def parse_date(d):
                    try:
                        s = str(int(d))
                        return datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    except:
                        return datetime.now(timezone.utc)

                for _, row in df.iterrows():
                    # Map FIPS to ISO for geographic countries
                    fips_action_country = str(row[52]).strip() if pd.notna(row[52]) else None
                    action_country = fips_to_iso(fips_action_country) if fips_action_country else None

                    # Actor countries are typically 3-letter codes in GDELT, we store as-is
                    actor1_country = str(row[7]).strip() if pd.notna(row[7]) else None
                    actor2_country = str(row[17]).strip() if pd.notna(row[17]) else None

                    # Goldstein scale
                    goldstein = float(row[31]) if pd.notna(row[31]) else None
                    avg_tone = float(row[35]) if pd.notna(row[35]) else None
                    
                    # Lat / Lon
                    lat = float(row[54]) if pd.notna(row[54]) else None
                    lon = float(row[55]) if pd.notna(row[55]) else None

                    results.append({
                        "global_event_id": int(row[0]),
                        "timestamp": parse_date(row[57]),
                        "actor1_code": str(row[5]).strip() if pd.notna(row[5]) else None,
                        "actor1_name": str(row[6]).strip() if pd.notna(row[6]) else None,
                        "actor1_country_code": actor1_country,
                        "actor2_code": str(row[15]).strip() if pd.notna(row[15]) else None,
                        "actor2_name": str(row[16]).strip() if pd.notna(row[16]) else None,
                        "actor2_country_code": actor2_country,
                        "is_root_event": bool(int(row[26])) if pd.notna(row[26]) else False,
                        "event_code": str(row[27]).strip() if pd.notna(row[27]) else "000",
                        "event_root_code": str(row[29]).strip() if pd.notna(row[29]) else None,
                        "quad_class": int(row[30]) if pd.notna(row[30]) else None,
                        "goldstein_scale": goldstein,
                        "action_country_code": action_country,
                        "action_location_name": str(row[51]).strip() if pd.notna(row[51]) else None,
                        "latitude": lat,
                        "longitude": lon,
                        "num_mentions": int(row[32]) if pd.notna(row[32]) else 0,
                        "num_sources": int(row[33]) if pd.notna(row[33]) else 0,
                        "num_articles": int(row[34]) if pd.notna(row[34]) else 0,
                        "avg_tone": avg_tone,
                        "source_url": str(row[58]).strip() if pd.notna(row[58]) else None,
                    })

        logger.info(f"[Events] Parsed {len(results)} events")
        return results

    except Exception as e:
        logger.error(f"[Events] Error parsing: {e}")
        return []

async def insert_events(pool: asyncpg.Pool, events: list[dict]) -> int:
    """Insert parsed events into events_v2 table."""
    if not events:
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for e in events:
            try:
                await conn.execute("""
                    INSERT INTO events_v2 (
                        global_event_id, timestamp,
                        actor1_code, actor1_name, actor1_country_code,
                        actor2_code, actor2_name, actor2_country_code,
                        is_root_event, event_code, event_root_code,
                        quad_class, goldstein_scale,
                        action_country_code, action_location_name,
                        latitude, longitude,
                        num_mentions, num_sources, num_articles,
                        avg_tone, source_url
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                        $14, $15, $16, $17, $18, $19, $20, $21, $22
                    ) ON CONFLICT (global_event_id) DO NOTHING
                """,
                    e['global_event_id'], e['timestamp'],
                    e['actor1_code'], e['actor1_name'], e['actor1_country_code'],
                    e['actor2_code'], e['actor2_name'], e['actor2_country_code'],
                    e['is_root_event'], e['event_code'], e['event_root_code'],
                    e['quad_class'], e['goldstein_scale'],
                    e['action_country_code'], e['action_location_name'],
                    e['latitude'], e['longitude'],
                    e['num_mentions'], e['num_sources'], e['num_articles'],
                    e['avg_tone'], e['source_url']
                )
                inserted += 1
            except Exception as ex:
                logger.debug(f"[Events] Insert skip: {ex}")
                continue
    return inserted

async def run_events_ingestion():
    """Main GDELT Events ingestion function."""
    logger.info(f"[{datetime.now()}] Starting GDELT Events ingestion...")

    pool = await asyncpg.create_pool(DATABASE_URL)
    
    try:
        url = await fetch_latest_events_url()
        if url:
            logger.info(f"[Events] Downloading: {url}")
            events = await download_and_parse_events(url)
            inserted = await insert_events(pool, events)
            logger.info(f"[Events] Inserted {inserted} new events")
            
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM events_v2")
            logger.info(f"[Events] Total events in database: {count}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(run_events_ingestion())
