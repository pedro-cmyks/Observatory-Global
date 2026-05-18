"""
NewsData.io ingestion — multilingual news API (60+ languages).
Fills the non-English coverage gap that GDELT underweights.
Runs every 4th GDELT cycle (~60 min). Env: NEWSDATA_API_KEY.
"""
import asyncio
import asyncpg
import aiohttp
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlparse

from app.services.ingest_rss import extract_country, is_blocked

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")

BASE_URL = "https://newsdata.io/api/1/latest"
NEWS_DATA_PAGE_SIZE = int(os.getenv("NEWSDATA_PAGE_SIZE", "10"))

# Language batches — avoid US/EN overrepresentation; focus on gaps.
# NewsData free plan allows at most 5 countries per request. Keep this at <=8 batches
# because the hourly cadence consumes batch_count * 24 requests/day (200 req/day cap).
LANGUAGE_BATCHES = [
    # Spanish + Portuguese LatAm
    {"language": "es,pt", "country": "co,mx,br,ar,ve"},
    {"language": "es,pt", "country": "pe,cl,ec,bo,cu"},
    # Arabic — MENA, not covered by GDELT GKG well
    {"language": "ar", "country": "eg,sa,iq,sy,ye"},
    # French West/Central Africa
    {"language": "fr", "country": "ml,bf,ne,sn,cd"},
    # Swahili / Amharic — East Africa
    {"language": "sw,am", "country": "ke,tz,ug,et,rw"},
    # Southeast Asia
    {"language": "id,ms,tl,vi,th", "country": "id,my,ph,vn,th"},
    # South Asia
    {"language": "hi,ur,bn", "country": "in,pk,bd,np,lk"},
]

LANGUAGE_CODES = {
    "arabic": "ar",
    "amharic": "am",
    "bengali": "bn",
    "french": "fr",
    "hindi": "hi",
    "indonesian": "id",
    "malay": "ms",
    "portuguese": "pt",
    "spanish": "es",
    "swahili": "sw",
    "tagalog": "tl",
    "thai": "th",
    "urdu": "ur",
    "vietnamese": "vi",
}


def _parse_pub_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


async def _fetch_batch(
    session: aiohttp.ClientSession,
    params: dict,
    since: datetime,
) -> list[dict]:
    signals = []
    try:
        async with session.get(
            BASE_URL,
            params={**params, "apikey": NEWSDATA_API_KEY, "size": NEWS_DATA_PAGE_SIZE},
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "ObservatorioGlobal/1.0"},
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.warning(
                    "[NewsData] HTTP %d for params %s: %s",
                    resp.status, params, body[:240],
                )
                return signals
            data = await resp.json()

        if data.get("status") != "success":
            logger.warning("[NewsData] API error: %s", data.get("message", "unknown"))
            return signals

        for article in data.get("results", []):
            pub_time = _parse_pub_date(article.get("pubDate"))
            if pub_time <= since:
                continue

            url_str = article.get("link", "")
            if not url_str or is_blocked(url_str):
                continue

            title = (article.get("title") or "")[:500]
            snippet = (article.get("description") or "")[:500]

            # NewsData can return ISO2 codes or full country names as a list. The DB
            # column is CHAR(2), so normalize before insert.
            raw_countries = article.get("country") or []
            raw_country = str(raw_countries[0]) if raw_countries else ""
            country_code = (
                raw_country.upper()
                if len(raw_country) == 2
                else extract_country(raw_country, "")
                or extract_country(title, snippet)
                or "XX"
            )

            raw_lang = str(article.get("language") or "und").lower()
            lang = LANGUAGE_CODES.get(raw_lang, raw_lang[:2] if len(raw_lang) >= 2 else "un")
            domain = urlparse(url_str).netloc.lower().removeprefix("www.")

            signals.append({
                "timestamp": pub_time,
                "country_code": country_code,
                "latitude": None,
                "longitude": None,
                "sentiment": 0.0,
                "source_url": url_str,
                "source_name": article.get("source_id") or domain,
                "headline": title or None,
                "themes": [],
                "persons": [],
                "is_crisis": False,
                "crisis_score": 0.0,
                "crisis_themes": [],
                "severity": "low",
                "event_type": "other",
                "source_family": "api",
                "source_lang": lang,
                "geo_confidence": 0.7,
                "attribution_method": "newsdata_api",
                "is_state_media": False,
            })

    except aiohttp.ClientError as e:
        logger.warning("[NewsData] network error: %s", e)
    except Exception as e:
        logger.error("[NewsData] unexpected error: %s", e)

    return signals


async def insert_newsdata_signals(pool: asyncpg.Pool, signals: list[dict]) -> int:
    if not signals:
        return 0
    inserted = 0
    async with pool.acquire() as conn:
        for s in signals:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO signals_v2 (
                        timestamp, country_code, latitude, longitude, sentiment,
                        source_url, source_name, headline, themes, persons,
                        is_crisis, crisis_score, crisis_themes, severity, event_type,
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                            $16,$17,$18,$19,$20)
                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
                    """,
                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                    s["themes"], s["persons"],
                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                    s["severity"], s["event_type"],
                    s["source_family"], s["source_lang"], s["geo_confidence"],
                    s["attribution_method"], s["is_state_media"],
                )
                if result == "INSERT 0 1":
                    inserted += 1
            except Exception as e:
                logger.warning("[NewsData] insert error: %s: %s", type(e).__name__, str(e)[:120])
    return inserted


async def run_newsdata_ingestion() -> None:
    """Fetch multilingual news from NewsData.io. Called by ingest_loop.py."""
    if not NEWSDATA_API_KEY:
        logger.warning("[NewsData] NEWSDATA_API_KEY not set — skipping")
        return

    # NewsData country/language buckets can be sparse; use a wider window and rely on
    # source_url dedupe so hourly runs backfill useful non-English coverage without repeats.
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            for batch_params in LANGUAGE_BATCHES:
                signals = await _fetch_batch(session, batch_params, since)
                total_fetched += len(signals)
                if signals:
                    n = await insert_newsdata_signals(pool, signals)
                    total_inserted += n
                    logger.info(
                        "[NewsData] batch %s: %d fetched → %d inserted",
                        batch_params.get("language"), len(signals), n,
                    )
                await asyncio.sleep(1)  # stay well within 200 req/day free limit
    finally:
        await pool.close()

    logger.info(
        "[NewsData] ingestion complete — %d fetched, %d new signals",
        total_fetched, total_inserted,
    )
