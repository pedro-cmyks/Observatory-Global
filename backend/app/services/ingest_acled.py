"""
ACLED Conflict Data Ingestion Service.
Fetches recent armed conflict and protest events from the ACLED API.
Requires ACLED_API_KEY and ACLED_EMAIL in environment variables.
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")
ACLED_API_KEY = os.getenv("ACLED_API_KEY")
ACLED_EMAIL = os.getenv("ACLED_EMAIL")

ACLED_BASE_URL = "https://api.acleddata.com/acled/read"

async def fetch_recent_acled_events(days_back: int = 3) -> list[dict]:
    """Fetch recent events from ACLED API."""
    if not ACLED_API_KEY or not ACLED_EMAIL:
        logger.warning("[ACLED] API Key or Email not configured. Skipping ACLED ingestion.")
        return []

    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)
    
    date_str = f"{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}"

    params = {
        "key": ACLED_API_KEY,
        "email": ACLED_EMAIL,
        "event_date": date_str,
        "event_date_where": "BETWEEN",
        "limit": 5000,  # Max per request usually
        "format": "json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ACLED_BASE_URL, params=params, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"[ACLED] API request failed: {resp.status} - {text}")
                    return []
                
                data = await resp.json()
                if data.get("success") and "data" in data:
                    events = data["data"]
                    logger.info(f"[ACLED] Fetched {len(events)} events from API")
                    return events
                else:
                    logger.error(f"[ACLED] API returned unsuccessful response: {data}")
                    return []
    except Exception as e:
        logger.error(f"[ACLED] Error fetching data: {e}")
        return []

async def insert_acled_events(pool: asyncpg.Pool, events: list[dict]) -> int:
    """Insert ACLED events into database."""
    if not events:
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for e in events:
            try:
                # ACLED returns strings for everything, we need to parse numbers
                lat = float(e.get('latitude')) if e.get('latitude') else None
                lon = float(e.get('longitude')) if e.get('longitude') else None
                fatalities = int(e.get('fatalities', 0)) if str(e.get('fatalities', '0')).isdigit() else 0
                geo_prec = int(e.get('geo_precision', 1)) if str(e.get('geo_precision', '1')).isdigit() else 1
                
                # event_date comes as YYYY-MM-DD
                event_date = datetime.strptime(e.get('event_date'), '%Y-%m-%d').date() if e.get('event_date') else datetime.now(timezone.utc).date()

                await conn.execute("""
                    INSERT INTO acled_conflicts_v2 (
                        event_id_cnty, event_date, year,
                        event_type, sub_event_type,
                        actor1, assoc_actor_1, inter1,
                        actor2, assoc_actor_2, inter2, interaction,
                        region, country, admin1, admin2, admin3, location,
                        latitude, longitude, geo_precision,
                        source, source_scale, notes, fatalities
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                        $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
                    ) ON CONFLICT (event_id_cnty) DO NOTHING
                """,
                    str(e.get('event_id_cnty')),
                    event_date,
                    int(e.get('year')) if str(e.get('year')).isdigit() else None,
                    e.get('event_type'),
                    e.get('sub_event_type'),
                    e.get('actor1'),
                    e.get('assoc_actor_1'),
                    int(e.get('inter1')) if str(e.get('inter1')).isdigit() else None,
                    e.get('actor2'),
                    e.get('assoc_actor_2'),
                    int(e.get('inter2')) if str(e.get('inter2')).isdigit() else None,
                    int(e.get('interaction')) if str(e.get('interaction')).isdigit() else None,
                    e.get('region'),
                    e.get('country'),
                    e.get('admin1'),
                    e.get('admin2'),
                    e.get('admin3'),
                    e.get('location'),
                    lat,
                    lon,
                    geo_prec,
                    e.get('source'),
                    e.get('source_scale'),
                    e.get('notes'),
                    fatalities
                )
                inserted += 1
            except Exception as ex:
                logger.debug(f"[ACLED] Insert skip {e.get('event_id_cnty')}: {ex}")
                continue
    return inserted

async def run_acled_ingestion():
    """Main ACLED ingestion function."""
    logger.info(f"[{datetime.now()}] Starting ACLED ingestion...")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1)
    
    try:
        events = await fetch_recent_acled_events(days_back=3)
        if events:
            inserted = await insert_acled_events(pool, events)
            logger.info(f"[ACLED] Inserted {inserted} new conflict events")
            
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM acled_conflicts_v2")
            logger.info(f"[ACLED] Total events in database: {count}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(run_acled_ingestion())
