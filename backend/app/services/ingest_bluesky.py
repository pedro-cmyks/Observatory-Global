"""
Bluesky ingestion — credential-free social signal layer (Unified Engine F1.1,
spec docs/specs/2026-06-29-atlas-unified-engine.md §7).

Bluesky's firehose is exposed by **Jetstream**, a public JSON-over-WebSocket
feed — no auth, no `atproto` library, no binary CBOR decoding. We subscribe to
`app.bsky.feed.post` creates, drain a BOUNDED window each run (the firehose is
thousands/sec, so we cap by time AND count), and land substantive top-level
posts as social signals.

ACCESS MODEL (verified 2026-06-29):
  wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post
  event = { kind:'commit', did, commit:{ operation, collection, rkey,
            record:{ text, langs, createdAt, reply? } } }

Bluesky has no instance→country (it is one global network), so unlike Lemmy
there is no `source_origin_country`; the country is the NER geocode of the text
(`extract_country`) and `source_lang` is the post's declared language — the
spec's "country via lang + NER" (§7). Lands source_family='social',
signal_class='social_commentary', verified=false — discussion, never evidence.

Runs from ingest_loop on the social cadence. Kill-switch: BLUESKY_INGEST_ENABLED=false.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import aiohttp
import asyncpg

from app.services.ingest_rss import extract_country, is_blocked
from app.services.signal_text import clean_snippet

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

BLUESKY_INGEST_ENABLED = os.getenv("BLUESKY_INGEST_ENABLED", "true").lower() not in (
    "false", "0", "no", "off",
)

JETSTREAM_URL = os.getenv(
    "BLUESKY_JETSTREAM_URL",
    "wss://jetstream2.us-east.bsky.network/subscribe"
    "?wantedCollections=app.bsky.feed.post",
)

# Bound the drain: the firehose is thousands/sec, so stop at whichever limit hits
# first. These keep one run cheap and the social insert volume sane.
COLLECT_SECONDS = float(os.getenv("BLUESKY_COLLECT_SECONDS", "25"))
MAX_POSTS = int(os.getenv("BLUESKY_MAX_POSTS", "300"))
# Substance floor: short posts are chatter, won't embed (cron needs >=20), and
# add noise without signal. 60 favours real statements over one-liners.
MIN_TEXT_LEN = int(os.getenv("BLUESKY_MIN_TEXT_LEN", "60"))


def bluesky_enabled() -> bool:
    return BLUESKY_INGEST_ENABLED


def _parse_created(value: str | None) -> datetime:
    """record.createdAt is client-supplied ISO 8601; tolerate junk by falling
    back to now (the post just arrived on the live firehose)."""
    now = datetime.now(timezone.utc)
    if not value:
        return now
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return now
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    # client clocks lie; never trust a future timestamp
    return dt if dt <= now else now


def _event_to_signal(ev: dict) -> dict | None:
    """Map a Jetstream commit event → a social signal dict, or None to drop."""
    if ev.get("kind") != "commit":
        return None
    commit = ev.get("commit") or {}
    if commit.get("operation") != "create" or commit.get("collection") != "app.bsky.feed.post":
        return None
    record = commit.get("record") or {}
    if record.get("reply"):
        return None  # top-level posts only — replies are conversational noise
    text = (record.get("text") or "").strip()
    if len(text) < MIN_TEXT_LEN:
        return None
    langs = record.get("langs") or []
    if not langs:
        return None  # undetermined-language posts are mostly spam/non-text
    did, rkey = ev.get("did"), commit.get("rkey")
    if not did or not rkey:
        return None
    source_url = f"https://bsky.app/profile/{did}/post/{rkey}"
    if is_blocked(source_url):
        return None

    # Bluesky langs are BCP-47 (e.g. 'pt-BR', 'zh-Hans'); signals_v2.source_lang
    # is CHAR(2), so reduce to the 2-letter base. Drop if it isn't a clean code.
    lang = str(langs[0]).split("-")[0][:2].lower()
    if len(lang) != 2 or not lang.isalpha():
        return None
    country_code = extract_country(text, "") or "XX"
    return {
        "timestamp": _parse_created(record.get("createdAt")),
        "country_code": country_code,
        "latitude": None,
        "longitude": None,
        "sentiment": 0.0,
        "source_url": source_url,
        "source_name": "bluesky",
        "headline": text[:500],
        "themes": [],
        "persons": [],
        "is_crisis": False,
        "crisis_score": 0.0,
        "crisis_themes": [],
        "severity": "low",
        "event_type": "other",
        "source_family": "social",
        "source_lang": lang,
        "geo_confidence": 0.5,
        "attribution_method": "bluesky_jetstream",
        "is_state_media": False,
        # Bluesky is public discussion, NOT corroboration.
        "signal_class": "social_commentary",
        "snippet": clean_snippet(text),
        # global network — no instance home country (country is the NER geocode).
        "source_origin_country": None,
    }


async def _drain_jetstream() -> list[dict]:
    """Connect, collect substantive posts until the time OR count cap, return them."""
    signals: list[dict] = []
    seen_urls: set[str] = set()
    deadline = time.monotonic() + COLLECT_SECONDS
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                JETSTREAM_URL,
                timeout=aiohttp.ClientTimeout(total=20),
                heartbeat=15,
                max_msg_size=4 * 1024 * 1024,
            ) as ws:
                while time.monotonic() < deadline and len(signals) < MAX_POSTS:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
                    except asyncio.TimeoutError:
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                        continue
                    try:
                        ev = msg.json()
                    except Exception:  # noqa: BLE001 - skip a malformed frame
                        continue
                    sig = _event_to_signal(ev)
                    if sig and sig["source_url"] not in seen_urls:
                        seen_urls.add(sig["source_url"])
                        signals.append(sig)
    except aiohttp.ClientError as e:
        logger.warning("[Bluesky] jetstream connection error: %s", e)
    except Exception as e:  # noqa: BLE001 - never let the firehose kill the cycle
        logger.warning("[Bluesky] drain error: %s", str(e)[:160])
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
            except Exception as e:  # noqa: BLE001 - one bad row never kills the run
                logger.warning("[Bluesky] insert error: %s", str(e)[:120])
    return inserted


async def run_bluesky_ingestion() -> None:
    """Drain a bounded window of the Bluesky Jetstream firehose → social signals."""
    if not bluesky_enabled():
        logger.info("[Bluesky] disabled via BLUESKY_INGEST_ENABLED — skipping")
        return
    signals = await _drain_jetstream()
    if not signals:
        logger.info("[Bluesky] ingestion complete — 0 posts collected")
        return
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        inserted = await _insert(pool, signals)
    finally:
        await pool.close()
    langs = {s["source_lang"] for s in signals}
    logger.info(
        "[Bluesky] ingestion complete — %d collected, %d new signals, %d langs",
        len(signals), inserted, len(langs),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bluesky_ingestion())
