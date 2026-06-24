"""
Reddit ingestion — OAuth app-only (read-only). Captures the social signal layer:
narrative emergence + public discussion before/around press coverage.

Reddit blocks the unauthenticated public JSON endpoint (HTTP 403) from BOTH
datacenter and residential IPs since 2023, so OAuth is mandatory. Create a
"script"/"web app" at https://www.reddit.com/prefs/apps and set:
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
    REDDIT_USER_AGENT  (optional; Reddit wants a unique descriptive UA)
App-only client_credentials grant → read public subreddits. No user login.
Quota: ~100 QPM / OAuth app. Graceful no-op when creds are absent.

Runs every 4th GDELT cycle (~60 min) via ingest_loop.
"""
import asyncio
import time
import asyncpg
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from app.services.ingest_rss import extract_country, is_blocked
from app.services.signal_text import clean_snippet

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "ObservatorioGlobal/1.0 (narrative-intelligence research; contact: atlas)",
)
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE = "https://oauth.reddit.com"

# Subreddits: (name, default_country_or_None, source_family)
SUBREDDITS: list[tuple[str, str | None, str]] = [
    ("worldnews", None, "social"),
    ("geopolitics", None, "social"),
    ("GlobalNews", None, "social"),
    ("colombia", "CO", "social"),
    ("Venezuela", "VE", "social"),
    ("ukraine", "UA", "social"),
    ("MiddleEast", None, "social"),
    ("Turkey", "TR", "social"),
    ("Nigeria", "NG", "social"),
    ("myanmar", "MM", "social"),
    ("haiti", "HT", "social"),
    ("CredibleDefense", None, "social"),
    ("SyrianCivilWar", "SY", "social"),
    ("PakistanPolitics", "PK", "social"),
]

# Cached app-only token (process-lifetime; refreshed before expiry).
_token: dict = {"value": None, "expires_at": 0.0}


def reddit_enabled() -> bool:
    return bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)


async def _get_token(session: aiohttp.ClientSession) -> str | None:
    """App-only OAuth token (client_credentials). Cached until ~1 min before expiry."""
    now = time.time()
    if _token["value"] and now < _token["expires_at"] - 60:
        return _token["value"]
    try:
        auth = aiohttp.BasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        async with session.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=auth,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.warning("[Reddit] token HTTP %d: %s", resp.status, body[:160])
                return None
            data = await resp.json()
        _token["value"] = data.get("access_token")
        _token["expires_at"] = now + float(data.get("expires_in", 3600))
        return _token["value"]
    except Exception as e:
        logger.warning("[Reddit] token error: %s", e)
        return None


def _parse_reddit_time(created_utc: float | None) -> datetime:
    if not created_utc:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(created_utc, tz=timezone.utc)


async def _fetch_subreddit(
    session: aiohttp.ClientSession,
    token: str,
    subreddit: str,
    default_country: str | None,
    since: datetime,
) -> list[dict]:
    signals: list[dict] = []
    try:
        async with session.get(
            f"{OAUTH_BASE}/r/{subreddit}/new",
            params={"limit": 50},
            timeout=aiohttp.ClientTimeout(total=20),
            headers={"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"},
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
            pub_time = _parse_reddit_time(p.get("created_utc"))
            if pub_time <= since:
                continue
            if p.get("removed_by_category") or p.get("selftext") == "[removed]":
                continue

            title = (p.get("title") or "")[:500]
            selftext = (p.get("selftext") or "")[:300]
            permalink = p.get("permalink", "")
            url_str = f"https://www.reddit.com{permalink}" if permalink else ""
            if not url_str:
                continue

            post_url = p.get("url", "")
            if post_url and not post_url.startswith("https://www.reddit.com") and not is_blocked(post_url):
                source_url = post_url
            else:
                source_url = url_str

            country_code = extract_country(title, selftext) or default_country or "XX"

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
                "attribution_method": "reddit_oauth",
                "is_state_media": False,
                # Reddit is commentary/discussion, NOT corroboration.
                "signal_class": "social_commentary",
                "snippet": clean_snippet(selftext),
            })

    except aiohttp.ClientError as e:
        logger.warning("[Reddit] network error r/%s: %s", subreddit, e)
    except Exception as e:
        logger.error("[Reddit] unexpected error r/%s: %s", subreddit, e)

    return signals


async def run_reddit_ingestion() -> None:
    """Fetch social signals from geopolitics subreddits via OAuth. Called by ingest_loop."""
    if not reddit_enabled():
        logger.warning("[Reddit] REDDIT_CLIENT_ID/SECRET not set — skipping (OAuth required)")
        return

    since = datetime.now(timezone.utc) - timedelta(hours=2)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            token = await _get_token(session)
            if not token:
                logger.warning("[Reddit] no OAuth token — skipping")
                return
            for subreddit, default_country, _ in SUBREDDITS:
                signals = await _fetch_subreddit(session, token, subreddit, default_country, since)
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
                                        signal_class, snippet
                                    )
                                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                                            $16,$17,$18,$19,$20,$21,$22)
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
                                    s.get("snippet"),
                                )
                                if result == "INSERT 0 1":
                                    inserted += 1
                            except Exception as e:
                                logger.warning("[Reddit] insert error: %s", str(e)[:120])
                    total_inserted += inserted
                    logger.info("[Reddit] r/%s: %d fetched → %d inserted", subreddit, len(signals), inserted)
                await asyncio.sleep(1)  # OAuth allows ~100 QPM; 1s/subreddit is safe
    finally:
        await pool.close()

    logger.info("[Reddit] ingestion complete — %d fetched, %d new signals", total_fetched, total_inserted)
