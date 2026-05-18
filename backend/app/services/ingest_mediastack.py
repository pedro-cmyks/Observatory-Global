"""
MediaStack ingestion — Spanish/Portuguese news supplement.
Targets LatAm + Iberian coverage not well-represented in GDELT.
Runs every 8th GDELT cycle (~2 hours). Env: MEDIASTACK_API_KEY.
Free tier: 500 req/month → max ~1 req/3 hours, conservative fetch.
"""
import asyncpg
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from app.services.ingest_rss import extract_country, is_blocked

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)
MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY", "")

BASE_URL = "https://api.mediastack.com/v1/news"

# Single fetch per run — conserves the 500 req/month quota
FETCH_PARAMS = {
    "languages": "es,pt",
    "countries": "co,mx,br,ar,ve,pe,cl,ec,bo,cu,do,ni,hn,sv,gt,py,uy",
    "limit": 100,
    "sort": "published_desc",
}


def _parse_pub_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    # Format: "2026-05-17T12:34:00+00:00" or "2026-05-17T12:34:00Z"
    try:
        raw = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


async def run_mediastack_ingestion() -> None:
    """Fetch Spanish/Portuguese news from MediaStack. Called by ingest_loop.py."""
    if not MEDIASTACK_API_KEY:
        logger.warning("[MediaStack] MEDIASTACK_API_KEY not set — skipping")
        return

    since = datetime.now(timezone.utc) - timedelta(hours=4)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    signals: list[dict] = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BASE_URL,
                params={**FETCH_PARAMS, "access_key": MEDIASTACK_API_KEY},
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "ObservatorioGlobal/1.0"},
            ) as resp:
                if resp.status != 200:
                    logger.warning("[MediaStack] HTTP %d", resp.status)
                    return
                data = await resp.json()

        for article in data.get("data", []):
            pub_time = _parse_pub_date(article.get("published_at"))
            if pub_time <= since:
                continue

            url_str = article.get("url", "")
            if not url_str or is_blocked(url_str):
                continue

            title = (article.get("title") or "")[:500]
            snippet = (article.get("description") or "")[:500]

            country_raw = (article.get("country") or "").upper()
            country_code = country_raw or extract_country(title, snippet) or "XX"
            lang = (article.get("language") or "und")[:10]
            domain = urlparse(url_str).netloc.lower().removeprefix("www.")

            signals.append({
                "timestamp": pub_time,
                "country_code": country_code,
                "latitude": None,
                "longitude": None,
                "sentiment": 0.0,
                "source_url": url_str,
                "source_name": article.get("source") or domain,
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
                "geo_confidence": 0.65,
                "attribution_method": "mediastack_api",
                "is_state_media": False,
            })

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
                    logger.warning("[MediaStack] insert error: %s", str(e)[:120])

        logger.info(
            "[MediaStack] ingestion complete — %d fetched, %d new signals",
            len(signals), inserted,
        )
    finally:
        await pool.close()
