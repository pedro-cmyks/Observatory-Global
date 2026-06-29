"""
Lemmy ingestion — credential-free social signal layer (Unified Engine F1.2,
spec docs/specs/2026-06-29-atlas-unified-engine.md §7).

Lemmy is a federated link-aggregator (Reddit-shaped). Unlike Reddit, the public
JSON API is open and uncredentialled, and — the decisive property for Atlas —
**the instance IS a country/language**: feddit.it is Italian, jlai.lu French,
feddit.dk Danish. So each instance gives us a clean `source_origin_country` (the
WAVE-N domestic-voice model, now for forums) without any per-post geocoding.

ACCESS MODEL (verified 2026-06-29):
  GET https://<instance>/api/v3/post/list?type_=Local&sort=New&limit=N
  - `type_=Local` restricts to communities native to that instance (federated
    cross-posts are excluded) so the instance→country tag stays honest.
  - No auth. JSON: { "posts": [ { "post": {...}, "community": {...} } ] }.
  - `post.ap_id` is the canonical federated permalink — a stable per-post
    ON CONFLICT (source_url) dedup key.

Live-probed instances kept below; dead/migrated ones (feddit.de → off-Lemmy,
sopuli.fi) are dropped and skipped gracefully at runtime.

Lands every signal as source_family='social', signal_class='social_commentary',
verified=false by construction — it is DISCUSSION, never evidence. The discussion
membership (and mood via nlp_sentiment) is assigned downstream by
assign_discussion_topics.py / the unified engine, NOT here.

Runs from ingest_loop on the social cadence. Kill-switch: LEMMY_INGEST_ENABLED=false.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import aiohttp
import asyncpg

from app.services.ingest_rss import extract_country, is_blocked
from app.services.signal_text import clean_snippet

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

LEMMY_INGEST_ENABLED = os.getenv("LEMMY_INGEST_ENABLED", "true").lower() not in (
    "false", "0", "no", "off",
)

USER_AGENT = os.getenv(
    "LEMMY_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)

# (host, source_origin_country, source_lang). origin=None for the global/mixed
# instances (lemmy.world / lemmy.ml) — there the subject country comes from the
# headline geocode only, like Reddit's global subs.
LEMMY_INSTANCES: list[tuple[str, str | None, str]] = [
    ("lemmy.world", None, "en"),
    ("lemmy.ml", None, "en"),
    ("feddit.it", "IT", "it"),
    ("jlai.lu", "FR", "fr"),
    ("feddit.nl", "NL", "nl"),
    ("feddit.uk", "GB", "en"),
    ("lemmy.ca", "CA", "en"),
    ("lemmy.pt", "PT", "pt"),
    ("feddit.dk", "DK", "da"),
]

PER_INSTANCE_LIMIT = int(os.getenv("LEMMY_POST_LIMIT", "30"))
PER_INSTANCE_DELAY = float(os.getenv("LEMMY_DELAY", "2"))
WINDOW_HOURS = float(os.getenv("LEMMY_WINDOW_HOURS", "6"))


def lemmy_enabled() -> bool:
    return LEMMY_INGEST_ENABLED


def _parse_published(value: str | None) -> datetime | None:
    """Lemmy publishes ISO 8601 (e.g. '2026-06-29T18:00:00.123456Z' or
    '...+00:00'). Return tz-aware UTC, or None if unparseable."""
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        # tolerate a missing fractional/last-resort second-precision form
        try:
            dt = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _fetch_instance(
    session: aiohttp.ClientSession,
    host: str,
    origin_country: str | None,
    lang: str,
    since: datetime,
) -> list[dict]:
    """Fetch one instance's newest Local posts → social signal dicts."""
    url = (
        f"https://{host}/api/v3/post/list"
        f"?type_=Local&sort=New&limit={PER_INSTANCE_LIMIT}"
    )
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=20),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as resp:
            if resp.status != 200:
                logger.warning("[Lemmy] %s HTTP %d", host, resp.status)
                return []
            data = await resp.json(content_type=None)
    except aiohttp.ClientError as e:
        logger.warning("[Lemmy] network error %s: %s", host, e)
        return []
    except Exception as e:  # noqa: BLE001 - malformed JSON / migrated instance
        logger.warning("[Lemmy] parse/error %s: %s", host, str(e)[:120])
        return []

    signals: list[dict] = []
    for item in (data.get("posts") or []):
        post = item.get("post") or {}
        if post.get("removed") or post.get("deleted"):
            continue
        pub = _parse_published(post.get("published"))
        if pub is None or pub <= since:
            continue
        title = (post.get("name") or "").strip()
        if not title:
            continue
        # ap_id is the canonical federated permalink → stable dedup key. Fall back
        # to a constructed local permalink if a (rare) row lacks it.
        source_url = post.get("ap_id") or (
            f"https://{host}/post/{post.get('id')}" if post.get("id") else ""
        )
        if not source_url or is_blocked(source_url):
            continue
        community = (item.get("community") or {}).get("name") or "lemmy"
        country_code = extract_country(title, "") or origin_country or "XX"
        signals.append({
            "timestamp": pub,
            "country_code": country_code,
            "latitude": None,
            "longitude": None,
            "sentiment": 0.0,
            "source_url": source_url[:1000],
            "source_name": f"lemmy/{community}@{host}",
            "headline": title[:500],
            "themes": [],
            "persons": [],
            "is_crisis": False,
            "crisis_score": 0.0,
            "crisis_themes": [],
            "severity": "low",
            "event_type": "other",
            "source_family": "social",
            "source_lang": lang,
            "geo_confidence": 0.6 if origin_country else 0.5,
            "attribution_method": "lemmy_api",
            "is_state_media": False,
            # Lemmy is public discussion, NOT corroboration.
            "signal_class": "social_commentary",
            "snippet": clean_snippet(title),
            # the instance home country — the WAVE-N domestic-voice tag for forums.
            "source_origin_country": origin_country,
        })
    return signals


_INSERT_SQL = """
INSERT INTO signals_v2 (
    timestamp, country_code, latitude, longitude, sentiment,
    source_url, source_name, headline, themes, persons,
    is_crisis, crisis_score, crisis_themes, severity, event_type,
    source_family, source_lang, geo_confidence, attribution_method, is_state_media,
    signal_class, snippet, source_origin_country
)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
        $16,$17,$18,$19,$20,$21,$22,$23)
ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
"""


async def _insert(pool: asyncpg.Pool, signals: list[dict]) -> int:
    inserted = 0
    async with pool.acquire() as conn:
        for s in signals:
            try:
                result = await conn.execute(
                    _INSERT_SQL,
                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                    s["themes"], s["persons"],
                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                    s["severity"], s["event_type"],
                    s["source_family"], s["source_lang"], s["geo_confidence"],
                    s["attribution_method"], s["is_state_media"],
                    s["signal_class"], s["snippet"], s["source_origin_country"],
                )
                if result == "INSERT 0 1":
                    inserted += 1
            except Exception as e:  # noqa: BLE001 - never let one row kill the run
                logger.warning("[Lemmy] insert error: %s", str(e)[:120])
    return inserted


async def run_lemmy_ingestion() -> None:
    """Fetch newest Local posts from country/lang Lemmy instances → social signals."""
    if not lemmy_enabled():
        logger.info("[Lemmy] disabled via LEMMY_INGEST_ENABLED — skipping")
        return

    since = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_fetched = total_inserted = 0
    try:
        async with aiohttp.ClientSession() as session:
            for idx, (host, origin, lang) in enumerate(LEMMY_INSTANCES):
                signals = await _fetch_instance(session, host, origin, lang, since)
                total_fetched += len(signals)
                if signals:
                    inserted = await _insert(pool, signals)
                    total_inserted += inserted
                    logger.info(
                        "[Lemmy] %s: %d fetched → %d inserted", host, len(signals), inserted
                    )
                if idx < len(LEMMY_INSTANCES) - 1:
                    await asyncio.sleep(PER_INSTANCE_DELAY)
    finally:
        await pool.close()
    logger.info(
        "[Lemmy] ingestion complete — %d fetched, %d new signals",
        total_fetched, total_inserted,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_lemmy_ingestion())
