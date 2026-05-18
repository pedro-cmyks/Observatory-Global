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

# Language batches — avoid US/EN overrepresentation; focus on gaps
LANGUAGE_BATCHES = [
    # Spanish + Portuguese LatAm
    {"language": "es,pt", "country": "co,mx,br,ar,ve,pe,cl,ec,bo,cu"},
    # Arabic — MENA, not covered by GDELT GKG well
    {"language": "ar", "country": "eg,sa,iq,sy,ye,jo,lb,ma,tn,ae,qa"},
    # French West Africa + Levant
    {"language": "fr", "country": "ml,bf,ne,sn,cd,cm,ci,dz,tn,ma"},
    # Swahili / Amharic — East Africa
    {"language": "sw,am", "country": "ke,tz,ug,et,rw"},
    # Southeast Asia
    {"language": "id,ms,tl,vi,th", "country": "id,my,ph,vn,th,kh,mm"},
    # South Asia
    {"language": "hi,ur,bn", "country": "in,pk,bd,np,lk"},
]


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
            params={**params, "apikey": NEWSDATA_API_KEY, "size": 50},
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "ObservatorioGlobal/1.0"},
        ) as resp:
            if resp.status != 200:
                logger.warning("[NewsData] HTTP %d for params %s", resp.status, params)
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

            # NewsData returns country as a list; take first or infer from text
            raw_countries = article.get("country") or []
            country_code = (
                raw_countries[0].upper()
                if raw_countries
                else extract_country(title, snippet)
            ) or "XX"

            lang = (article.get("language") or "und")[:10]
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

    since = datetime.now(timezone.utc) - timedelta(hours=2)
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
