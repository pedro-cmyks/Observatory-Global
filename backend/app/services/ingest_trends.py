"""
Google Trends Ingestion Service for V2 Schema.
Uses the public Google Trends RSS feed (trends.google.com/trending/rss?geo=XX)
instead of pytrends — reliable from cloud/datacenter IPs.

Runs every 30 minutes (every 2nd GDELT cycle).
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")

# ISO country codes supported by Google Trends RSS
TREND_COUNTRIES = [
    "US", "GB", "IN", "BR", "MX", "AR", "CO", "FR", "DE", "IT",
    "JP", "KR", "AU", "CA", "ES", "ZA", "NG", "EG", "TR", "RU",
    "UA", "PL", "NL", "SE", "NO", "CH", "SG", "TH", "ID", "PH",
]

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AtlasNarrativeEngine/2.0; +https://observatory-global.vercel.app)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# Google Trends RSS namespace
GT_NS = "https://trends.google.com/trending/rss"


def _parse_volume(traffic_str: str) -> int:
    """Parse '200K+' or '1M+' into an integer."""
    if not traffic_str:
        return 0
    s = traffic_str.upper().replace("+", "").replace(",", "").strip()
    try:
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        return int(s)
    except Exception:
        return 0


async def fetch_trending_for_country(session: aiohttp.ClientSession, country_code: str) -> list[dict]:
    """Fetch top trending searches for one country via RSS."""
    url = RSS_URL.format(geo=country_code)
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                logger.warning(f"[Trends] {country_code}: HTTP {resp.status}")
                return []
            content = await resp.text()

        root = ET.fromstring(content)
        results = []
        for i, item in enumerate(root.findall(".//item")):
            if i >= 20:
                break
            title = (item.findtext("title") or "").strip()
            traffic_raw = item.findtext(f"{{{GT_NS}}}approx_traffic") or "0"
            volume = _parse_volume(traffic_raw)
            if title:
                results.append({
                    "country_code": country_code,
                    "keyword": title,
                    "rank": i + 1,
                    "approximate_volume": volume,
                })

        logger.info(f"[Trends] {country_code}: {len(results)} trending searches")
        return results

    except Exception as e:
        logger.warning(f"[Trends] {country_code} failed: {type(e).__name__}: {e}")
        return []


async def insert_trends(pool: asyncpg.Pool, trends: list[dict]) -> int:
    """Upsert trending searches into trends_v2."""
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
                    ON CONFLICT ON CONSTRAINT trends_v2_country_code_keyword_hour_bucket_key DO UPDATE
                        SET rank = EXCLUDED.rank,
                            approximate_volume = GREATEST(trends_v2.approximate_volume, EXCLUDED.approximate_volume)
                """,
                    now,
                    t["country_code"],
                    t["keyword"],
                    t["rank"],
                    t["approximate_volume"],
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"[Trends] Insert failed for {t.get('country_code')}/{t.get('keyword')}: {e}")
                continue

    return inserted


async def run_trends_ingestion():
    """Main trends ingestion function — fetches all countries in parallel batches."""
    logger.info(f"[{datetime.now()}] Starting Google Trends ingestion (RSS)...")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1)

    try:
        all_trends: list[dict] = []

        # Fetch countries in batches of 5 to avoid hammering the RSS endpoint
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(TREND_COUNTRIES), 5):
                batch = TREND_COUNTRIES[i:i + 5]
                tasks = [fetch_trending_for_country(session, cc) for cc in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        all_trends.extend(res)
                # Small pause between batches
                await asyncio.sleep(1)

        if all_trends:
            inserted = await insert_trends(pool, all_trends)
            logger.info(f"[Trends] Inserted {inserted} records across {len(TREND_COUNTRIES)} countries")
        else:
            logger.warning("[Trends] No data fetched from any country")

        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM trends_v2")
            logger.info(f"[Trends] trends_v2 total rows: {count}")

    finally:
        await pool.close()

    logger.info(f"[{datetime.now()}] Google Trends ingestion complete!")


if __name__ == "__main__":
    asyncio.run(run_trends_ingestion())
