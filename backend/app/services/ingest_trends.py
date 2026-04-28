"""
Google Trends Ingestion Service for V2 Schema.
Fetches trending searches from Google Trends via pytrends
and inserts into trends_v2 table.

Runs every 30 minutes (lighter than GDELT GKG).
"""
import asyncio
import asyncpg
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")

# Countries to track — mapped to pytrends identifiers
COUNTRY_TRENDS_MAP = {
    "US": "united_states",
    "GB": "united_kingdom",
    "IN": "india",
    "BR": "brazil",
    "CO": "colombia",
    "MX": "mexico",
    "AR": "argentina",
    "FR": "france",
    "DE": "germany",
    "IT": "italy",
    "JP": "japan",
    "KR": "south_korea",
    "AU": "australia",
    "CA": "canada",
    "ES": "spain",
}


async def fetch_trending_for_country(country_code: str, pytrends_name: str) -> list[dict]:
    """Fetch trending searches for one country using pytrends."""
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        trending_df = pytrends.trending_searches(pn=pytrends_name)

        results = []
        for idx, row in trending_df.iterrows():
            if idx >= 20:  # Top 20
                break
            results.append({
                "country_code": country_code,
                "keyword": str(row[0]).strip(),
                "rank": idx + 1,
                "approximate_volume": 0,  # pytrends trending_searches doesn't return volume
            })

        logger.info(f"[Trends] {country_code}: fetched {len(results)} trending searches")
        return results

    except Exception as e:
        logger.warning(f"[Trends] {country_code} ({pytrends_name}) failed: {e}")
        return []


async def insert_trends(pool: asyncpg.Pool, trends: list[dict]) -> int:
    """Insert trending searches into trends_v2 table."""
    if not trends:
        return 0

    inserted = 0
    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        for t in trends:
            try:
                await conn.execute("""
                    INSERT INTO trends_v2 (timestamp, country_code, keyword, rank, approximate_volume)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                """,
                    now,
                    t['country_code'],
                    t['keyword'],
                    t['rank'],
                    t['approximate_volume']
                )
                inserted += 1
            except Exception as e:
                logger.debug(f"[Trends] Insert skip: {e}")
                continue

    return inserted


async def run_trends_ingestion():
    """Main trends ingestion function."""
    logger.info(f"[{datetime.now()}] Starting Google Trends ingestion...")

    pool = await asyncpg.create_pool(DATABASE_URL)

    try:
        all_trends = []
        for country_code, pytrends_name in COUNTRY_TRENDS_MAP.items():
            trends = await fetch_trending_for_country(country_code, pytrends_name)
            all_trends.extend(trends)
            # Small delay between countries to avoid rate limiting
            await asyncio.sleep(2)

        if all_trends:
            inserted = await insert_trends(pool, all_trends)
            logger.info(f"[Trends] Inserted {inserted} trending searches across {len(COUNTRY_TRENDS_MAP)} countries")
        else:
            logger.warning("[Trends] No trending data fetched")

        # Stats
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM trends_v2")
            logger.info(f"[Trends] Total records in trends_v2: {count}")

    finally:
        await pool.close()

    logger.info(f"[{datetime.now()}] Google Trends ingestion complete!")


if __name__ == "__main__":
    asyncio.run(run_trends_ingestion())
