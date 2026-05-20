"""
Reddit public API ingestion — no auth required for public subreddits.
Captures social signal layer: narrative emergence before press coverage.
Runs every 4th GDELT cycle (~60 min). No env key needed.
Rate limit: 60 req/min public API — sleep 2s between subreddits, safe.
"""
import asyncio
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

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "ObservatorioGlobal/1.0 geo-intelligence-monitor (non-commercial research)"

# Subreddits: (name, default_country_or_None, source_family)
SUBREDDITS: list[tuple[str, str | None, str]] = [
    # Global geopolitics
    ("worldnews", None, "social"),
    ("geopolitics", None, "social"),
    ("GlobalNews", None, "social"),
    # Crisis-specific country subreddits
    ("colombia", "CO", "social"),
    ("Venezuela", "VE", "social"),
    ("ukraine", "UA", "social"),
    ("MiddleEast", None, "social"),
    ("Turkey", "TR", "social"),
    ("Nigeria", "NG", "social"),
    ("myanmar", "MM", "social"),
    ("haiti", "HT", "social"),
    # Conflict/security analysis
    ("CredibleDefense", None, "social"),
    ("SyrianCivilWar", "SY", "social"),
    ("PakistanPolitics", "PK", "social"),
]


def _parse_reddit_time(created_utc: float | None) -> datetime:
    if not created_utc:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(created_utc, tz=timezone.utc)


async def _fetch_subreddit(
    session: aiohttp.ClientSession,
    subreddit: str,
    default_country: str | None,
    since: datetime,
) -> list[dict]:
    signals = []
    try:
        async with session.get(
            f"{REDDIT_BASE}/r/{subreddit}/new.json",
            params={"limit": 50},
            timeout=aiohttp.ClientTimeout(total=20),
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            if resp.status == 429:
                logger.warning("[Reddit] rate limited on r/%s", subreddit)
                return signals
            if resp.status != 200:
                logger.warning("[Reddit] HTTP %d on r/%s", resp.status, subreddit)
                return signals
            data = await resp.json()

        posts = data.get("data", {}).get("children", [])
        for post in posts:
            p = post.get("data", {})
            created_utc = p.get("created_utc")
            pub_time = _parse_reddit_time(created_utc)
            if pub_time <= since:
                continue

            # Skip if removed or deleted
            if p.get("removed_by_category") or p.get("selftext") == "[removed]":
                continue

            title = (p.get("title") or "")[:500]
            selftext = (p.get("selftext") or "")[:300]
            permalink = p.get("permalink", "")
            url_str = f"{REDDIT_BASE}{permalink}" if permalink else ""

            if not url_str:
                continue

            # External link posts — use the linked URL as source_url if not self-post
            post_url = p.get("url", "")
            if post_url and not post_url.startswith(REDDIT_BASE) and not is_blocked(post_url):
                source_url = post_url
            else:
                source_url = url_str

            country_code = (
                extract_country(title, selftext)
                or default_country
                or "XX"
            )

            signals.append({
                "timestamp": pub_time,
                "country_code": country_code,
                "latitude": None,
                "longitude": None,
                "sentiment": 0.0,
                "source_url": source_url,
                "source_name": f"reddit/r/{subreddit}",
                "headline": title or None,
                "themes": [],
                "persons": [],
                "is_crisis": False,
                "crisis_score": 0.0,
                "crisis_themes": [],
                "severity": "low",
                "event_type": "other",
                "source_family": "social",
                "source_lang": "en",
                "geo_confidence": 0.5,
                "attribution_method": "reddit_public",
                "is_state_media": False,
                # Semantic class (migration 021) — Reddit is commentary, NOT corroboration
                "signal_class": "social_commentary",
            })

    except aiohttp.ClientError as e:
        logger.warning("[Reddit] network error r/%s: %s", subreddit, e)
    except Exception as e:
        logger.error("[Reddit] unexpected error r/%s: %s", subreddit, e)

    return signals


async def run_reddit_ingestion() -> None:
    """Fetch social signals from geopolitics subreddits. Called by ingest_loop.py."""
    since = datetime.now(timezone.utc) - timedelta(hours=2)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            for subreddit, default_country, _ in SUBREDDITS:
                signals = await _fetch_subreddit(session, subreddit, default_country, since)
                total_fetched += len(signals)

                if signals:
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
                                        source_family, source_lang, geo_confidence, attribution_method, is_state_media,
                                        signal_class
                                    )
                                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                                            $16,$17,$18,$19,$20,$21)
                                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
                                    """,
                                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                                    s["themes"], s["persons"],
                                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                                    s["severity"], s["event_type"],
                                    s["source_family"], s["source_lang"], s["geo_confidence"],
                                    s["attribution_method"], s["is_state_media"],
                                    s.get("signal_class", "social_commentary"),
                                )
                                if result == "INSERT 0 1":
                                    inserted += 1
                            except Exception as e:
                                logger.warning("[Reddit] insert error: %s", str(e)[:120])

                    total_inserted += inserted
                    logger.info(
                        "[Reddit] r/%s: %d fetched → %d inserted",
                        subreddit, len(signals), inserted,
                    )

                await asyncio.sleep(2)  # 2s between subreddits — 30 req/min max

    finally:
        await pool.close()

    logger.info(
        "[Reddit] ingestion complete — %d fetched, %d new signals",
        total_fetched, total_inserted,
    )
