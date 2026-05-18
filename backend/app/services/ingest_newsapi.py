"""
NewsAPI.org ingestion — targeted crisis country queries.
Developer plan: 100 req/day. Use for high-priority country/topic combos.
Runs every 8th GDELT cycle (~2 hours). Env: NEWSAPI_KEY.
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
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

BASE_URL = "https://newsapi.org/v2/everything"

# Targeted queries for coverage gaps — prioritize crisis countries + non-English.
# Current cadence: 8 queries × 12 runs/day = 96 req/day. Keep this small until #156
# adds a persistent daily quota budget.
QUERIES = [
    {"q": "Colombia conflict", "language": "en", "pageSize": 20},
    {"q": "Venezuela crisis", "language": "en", "pageSize": 20},
    {"q": "Myanmar junta", "language": "en", "pageSize": 20},
    {"q": "Sudan war", "language": "en", "pageSize": 20},
    {"q": "Gaza humanitarian", "language": "en", "pageSize": 20},
    {"q": "Haiti gang", "language": "en", "pageSize": 20},
    {"q": "Sahel conflict", "language": "en", "pageSize": 20},
    {"q": "Congo M23", "language": "en", "pageSize": 20},
]


def _parse_pub_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        raw = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


async def run_newsapi_ingestion() -> None:
    """Fetch targeted crisis news from NewsAPI.org. Called by ingest_loop.py."""
    if not NEWSAPI_KEY:
        logger.warning("[NewsAPI] NEWSAPI_KEY not set — skipping")
        return

    # NewsAPI crisis queries are sparse on the free plan. Use a wider window and rely on
    # source_url dedupe so scheduled runs add new evidence without repeating old rows.
    since = datetime.now(timezone.utc) - timedelta(days=7)
    from_str = since.strftime("%Y-%m-%dT%H:%M:%S")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            for query_params in QUERIES:
                try:
                    async with session.get(
                        BASE_URL,
                        params={
                            **query_params,
                            "from": from_str,
                            "searchIn": "title,description",
                            "sortBy": "publishedAt",
                            "apiKey": NEWSAPI_KEY,
                        },
                        timeout=aiohttp.ClientTimeout(total=30),
                        headers={"User-Agent": "ObservatorioGlobal/1.0"},
                    ) as resp:
                        if resp.status == 426:
                            # 426 = developer plan hitting paid-only feature
                            logger.warning("[NewsAPI] plan limit hit, query: %s", query_params.get("q"))
                            continue
                        if resp.status != 200:
                            logger.warning("[NewsAPI] HTTP %d", resp.status)
                            continue
                        data = await resp.json()

                    if data.get("status") != "ok":
                        logger.warning("[NewsAPI] error: %s", data.get("message", ""))
                        continue

                    signals = []
                    lang = query_params.get("language", "und")

                    for article in data.get("articles", []):
                        pub_time = _parse_pub_date(article.get("publishedAt"))
                        if pub_time <= since:
                            continue

                        url_str = article.get("url", "")
                        if not url_str or is_blocked(url_str) or url_str == "https://removed.com":
                            continue

                        title = (article.get("title") or "")[:500]
                        snippet = (article.get("description") or "")[:500]
                        country_code = extract_country(title, snippet) or "XX"
                        domain = urlparse(url_str).netloc.lower().removeprefix("www.")

                        signals.append({
                            "timestamp": pub_time,
                            "country_code": country_code,
                            "latitude": None,
                            "longitude": None,
                            "sentiment": 0.0,
                            "source_url": url_str,
                            "source_name": article.get("source", {}).get("name") or domain,
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
                            "attribution_method": "newsapi_org",
                            "is_state_media": False,
                        })

                    total_fetched += len(signals)
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
                                logger.warning("[NewsAPI] insert error: %s", str(e)[:120])

                    total_inserted += inserted
                    logger.info(
                        "[NewsAPI] query '%s': %d fetched → %d inserted",
                        query_params.get("q"), len(signals), inserted,
                    )

                except Exception as e:
                    logger.error("[NewsAPI] query error '%s': %s", query_params.get("q"), e)

    finally:
        await pool.close()

    logger.info(
        "[NewsAPI] ingestion complete — %d fetched, %d new signals",
        total_fetched, total_inserted,
    )
