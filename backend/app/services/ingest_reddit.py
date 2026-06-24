"""
Reddit ingestion — credential-free via public Atom RSS feeds.

Captures the social signal layer: narrative emergence + public discussion
before/around press coverage.

ACCESS MODEL (re-verified 2026-06-24):
  - The Reddit *Data API* (oauth.reddit.com / *.json) now requires OAuth AND,
    since Reddit's Nov-2025 "Responsible Builder" policy, pre-approval before a
    new app can even be created (~2-4 week wait). The unauthenticated *.json
    endpoint 403s from every IP.
  - BUT the per-subreddit Atom feed `https://www.reddit.com/r/<sub>/.rss` is a
    built-in, credential-free surface and still returns 200 with a real browser
    User-Agent. That is what we use here — no client id/secret, no approval.
  - The feed IS rate-limited per IP (429 with no body) and escalates to 403
    under burst load. The decisive mitigation is FEWER REQUESTS: Reddit serves
    a combined multi-subreddit feed `/r/a+b+c/.rss` in ONE request, and every
    entry still carries its own `<category term="<sub>">`, so per-subreddit
    country attribution is recoverable. We fetch the watchlist in a handful of
    combined chunks (≈4 requests/cycle, not 14) with generous spacing.

Empirical check on 2026-06-24: `/r/worldnews/.rss` → 200, 44 KB, 25 entries,
no auth; `/r/worldnews+geopolitics+ukraine/.rss` → 200, 25 entries tagged by
sub; `/r/<sub>/new.json` → 403. Hence combined RSS, not the JSON API. A live
run inserted the first Reddit rows ever into signals_v2.

Runs every 4th GDELT cycle (~60 min) via ingest_loop. Enabled by default;
set REDDIT_INGEST_ENABLED=false to disable.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import aiohttp
import asyncpg
import feedparser

from app.services.ingest_rss import extract_country, is_blocked, parse_entry_time
from app.services.signal_text import clean_snippet

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

# Kill-switch only — no credentials are needed for the RSS surface.
REDDIT_INGEST_ENABLED = os.getenv("REDDIT_INGEST_ENABLED", "true").lower() not in (
    "false", "0", "no", "off",
)

# Reddit serves the RSS feed only to browser-like User-Agents; a generic
# "bot/1.0" UA is rejected the same way the JSON API is.
USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)
RSS_BASE = "https://www.reddit.com"

# Polite pacing — the RSS surface 429s under burst load and ESCALATES to 403 if
# you keep poking during the penalty window (verified 2026-06-24). So we never
# retry a 429: skip the chunk and let the hourly cadence + rotation recover it.
# Chunks are rotated by hour so a different one leads each cycle (the first
# request of a run is the one most likely to beat the limiter).
CHUNK_SIZE = int(os.getenv("REDDIT_RSS_CHUNK", "4"))
PER_CHUNK_DELAY = float(os.getenv("REDDIT_RSS_DELAY", "15"))

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

# Case-insensitive lookups keyed by subreddit name (the feed's <category term>
# may differ in case from our canonical list).
_CANON_BY_SUB = {name.lower(): name for name, _, _ in SUBREDDITS}
_COUNTRY_BY_SUB = {name.lower(): country for name, country, _ in SUBREDDITS}


def reddit_enabled() -> bool:
    """RSS needs no credentials; only the explicit kill-switch can disable it."""
    return REDDIT_INGEST_ENABLED


def _entry_subreddit(entry) -> str | None:
    """Recover which subreddit an entry came from via its <category term>."""
    for tag in (entry.get("tags") or []):
        term = tag.get("term")
        if term:
            return term
    return None


async def _fetch_feed_bytes(
    session: aiohttp.ClientSession, url: str, label: str
) -> bytes | None:
    """GET the Atom feed with a browser UA. On 429/error: skip (no retry — see
    the pacing note above; retrying escalates the per-IP penalty to a 403)."""
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=25),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml,application/xml,text/xml",
            },
        ) as resp:
            if resp.status == 200:
                return await resp.read()
            if resp.status == 429:
                logger.warning("[Reddit] r/%s rate limited (429) — skipping this cycle", label)
            else:
                logger.warning("[Reddit] r/%s HTTP %d", label, resp.status)
            return None
    except aiohttp.ClientError as e:
        logger.warning("[Reddit] network error r/%s: %s", label, e)
        return None
    except Exception as e:
        logger.error("[Reddit] unexpected error r/%s: %s", label, e)
        return None


async def _fetch_chunk(
    session: aiohttp.ClientSession,
    subreddits: list[str],
    since: datetime,
) -> list[dict]:
    """Fetch a COMBINED multi-subreddit Atom feed (one request) → social signals.

    Each entry's <category term> tells us its origin subreddit, which we map back
    to the configured default country and a per-sub source_name.
    """
    signals: list[dict] = []
    label = "+".join(subreddits)
    content = await _fetch_feed_bytes(session, f"{RSS_BASE}/r/{label}/.rss", label)
    if not content:
        return signals

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        logger.warning("[Reddit] parse error r/%s: %s", label, feed.bozo_exception)
        return signals

    for entry in feed.entries:
        pub_time = parse_entry_time(entry)
        if pub_time <= since:
            continue

        title = (entry.get("title") or "")[:500]
        # entry.link is the reddit comments permalink — unique per post, so it
        # is a safe ON CONFLICT (source_url) dedup key and keeps the reddit
        # thread as its own social signal rather than collapsing into a press URL.
        source_url = entry.get("link", "")
        if not source_url or is_blocked(source_url):
            continue

        sub_term = _entry_subreddit(entry)
        sub_key = (sub_term or "").lower()
        sub_name = _CANON_BY_SUB.get(sub_key, sub_term or label)
        default_country = _COUNTRY_BY_SUB.get(sub_key)
        country_code = extract_country(title, "") or default_country or "XX"

        signals.append({
            "timestamp": pub_time,
            "country_code": country_code,
            "latitude": None,
            "longitude": None,
            "sentiment": 0.0,
            "source_url": source_url,
            "source_name": f"reddit/r/{sub_name}",
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
            "attribution_method": "reddit_rss",
            "is_state_media": False,
            # Reddit is commentary/discussion, NOT corroboration.
            "signal_class": "social_commentary",
            "snippet": clean_snippet(title),
        })

    return signals


async def run_reddit_ingestion() -> None:
    """Fetch social signals from geopolitics subreddit RSS feeds. No credentials."""
    if not reddit_enabled():
        logger.info("[Reddit] disabled via REDDIT_INGEST_ENABLED — skipping")
        return

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=2)
    names = [name for name, _, _ in SUBREDDITS]
    chunks = [names[i:i + CHUNK_SIZE] for i in range(0, len(names), CHUNK_SIZE)]
    # Rotate which chunk leads by hour — the first request of a run is the most
    # likely to beat the per-IP limiter, so spread that advantage across chunks.
    if chunks:
        off = now.hour % len(chunks)
        chunks = chunks[off:] + chunks[:off]
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            for idx, chunk in enumerate(chunks):
                signals = await _fetch_chunk(session, chunk, since)
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
                    logger.info("[Reddit] chunk r/%s: %d fetched → %d inserted",
                                "+".join(chunk), len(signals), inserted)
                # Space requests — the RSS surface 429s under burst load.
                if idx < len(chunks) - 1:
                    await asyncio.sleep(PER_CHUNK_DELAY)
    finally:
        await pool.close()

    logger.info("[Reddit] ingestion complete — %d fetched, %d new signals", total_fetched, total_inserted)
