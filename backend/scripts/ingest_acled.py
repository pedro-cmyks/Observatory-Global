"""
ACLED conflict-EVENT ingestion — the precise-event layer for narrative threads
(#232: threads have no connected conflict events; GDELT CAMEO events_v2 is
country-level + text-less = too coarse; ACLED is the gold-standard event dataset).

READY-TO-RUN but GATED on credentials. Set ACLED_API_KEY (+ ACLED_EMAIL for the
legacy path, or ACLED_USERNAME/ACLED_PASSWORD for the 2026 OAuth path) and it
fetches recent events → the `acled_conflicts_v2` schema (backend/app/db/migrations/
007_acled_conflicts.sql). Without them, ingestion is skipped cleanly (like the
optional stub at app/services/ingest_acled.py) — ACLED is NEVER a hard dependency.
The geo.py `/api/v2/conflict-markers` + `/api/v2/acled` endpoints already read this
table (ACLED-first, GDELT-fallback), so populating it is the only missing piece.

WHY EVENTS MATTER (Atlas binding thesis, see docs/research/event-sources/
acled-integration-plan.md): an ACLED event carries `source` URLs → the same
article Atlas may already have ingested as a signal → that signal's topic. So an
event binds PRECISELY to a thread via source_url → signal → topic, not just via a
coarse country+actor match. ACLED events ALSO carry lat/lon + typed actors, giving
a second, geospatial binding path. This ingest only LANDS events; binding is a
downstream step (kept out of here, mirroring how ingest_lemmy leaves discussion
attach to the unified engine).

═══════════════════════════════════════════════════════════════════════════════
ACCESS MODEL (researched 2026-07-01 — see the access-request + integration docs)
═══════════════════════════════════════════════════════════════════════════════
API access requires a myACLED account at the "Research" access level (free for
qualifying non-commercial / academic use; granted after registration + accepting
the Terms of Use & Attribution Policy + describing the use case). The free "Open"
tier does NOT include API access. Commercial use needs a paid corporate license.

Two auth flows are supported here; the scaffold auto-selects:

 (A) 2026 OAuth (preferred). POST https://acleddata.com/oauth/token
     body: username, password, grant_type=password, client_id=acled,
           scope=authenticated
     → { access_token (24h), refresh_token (14d), token_type: "Bearer" }
     Then GET the read endpoint with `Authorization: Bearer <access_token>`.
     Enable by setting ACLED_USERNAME + ACLED_PASSWORD.

 (B) Legacy key+email query auth (older accounts). GET the read endpoint with
     `key=<ACLED_API_KEY>&email=<ACLED_EMAIL>` as query params. ACLED is phasing
     this out; kept as a fallback for accounts that still have a raw key.

Read endpoint (2026 base): GET https://acleddata.com/api/acled/read
  Params used: event_date=<from>|<to>, event_date_where=BETWEEN,
               limit=<rows>, page=<n>, _format=json, fields=<csv subset>
  Row cap ~5000/call → paginate with &page=N until a short page is returned.
  Response: { "success": true, "count": N, "data": [ {event...}, ... ] }.

ATTRIBUTION (a condition of use, enforced downstream when surfaced): store the
per-event `source`, and any UI/export showing ACLED events must carry
"ACLED, accessed on [DATE]. www.acleddata.com." with the filters applied.

Kill-switch: ACLED_INGEST_ENABLED=false. Read-only-safe: if creds are absent it
returns [] and writes nothing. DO NOT run without a key.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import aiohttp
import asyncpg

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

ACLED_INGEST_ENABLED = os.getenv("ACLED_INGEST_ENABLED", "true").lower() not in (
    "false", "0", "no", "off",
)

# Credentials — none of these have defaults; absence = skip.
ACLED_API_KEY = os.getenv("ACLED_API_KEY")          # legacy path
ACLED_EMAIL = os.getenv("ACLED_EMAIL")              # legacy path
ACLED_USERNAME = os.getenv("ACLED_USERNAME")        # OAuth path (account email)
ACLED_PASSWORD = os.getenv("ACLED_PASSWORD")        # OAuth path

# 2026 endpoints (see module docstring). Overridable for staging/mirrors.
ACLED_OAUTH_URL = os.getenv("ACLED_OAUTH_URL", "https://acleddata.com/oauth/token")
ACLED_READ_URL = os.getenv("ACLED_READ_URL", "https://acleddata.com/api/acled/read")

# Tuning
DAYS_BACK = int(os.getenv("ACLED_DAYS_BACK", "3"))
PER_PAGE_LIMIT = int(os.getenv("ACLED_PAGE_LIMIT", "5000"))   # ACLED per-call cap
MAX_PAGES = int(os.getenv("ACLED_MAX_PAGES", "20"))           # safety ceiling
REQUEST_TIMEOUT = float(os.getenv("ACLED_TIMEOUT", "45"))
PER_PAGE_DELAY = float(os.getenv("ACLED_PAGE_DELAY", "1"))

USER_AGENT = os.getenv(
    "ACLED_USER_AGENT",
    "AtlasNarrativeIntelligence/1.0 (non-commercial research; +https://atlas-api-pedro.fly.dev)",
)

# The exact acled_conflicts_v2 columns fed by the INSERT, in order. The read
# request asks ACLED for exactly this subset via &fields= to keep payloads lean.
ACLED_FIELDS = [
    "event_id_cnty", "event_date", "year",
    "event_type", "sub_event_type",
    "actor1", "assoc_actor_1", "inter1",
    "actor2", "assoc_actor_2", "inter2", "interaction",
    "region", "country", "admin1", "admin2", "admin3", "location",
    "latitude", "longitude", "geo_precision",
    "source", "source_scale", "notes", "fatalities",
]


def acled_enabled() -> bool:
    return ACLED_INGEST_ENABLED


def _have_oauth_creds() -> bool:
    return bool(ACLED_USERNAME and ACLED_PASSWORD)


def _have_legacy_creds() -> bool:
    return bool(ACLED_API_KEY and ACLED_EMAIL)


def _to_int(value, default=None):
    """ACLED returns strings for everything; parse ints defensively."""
    if value is None or value == "":
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_event_date(value) -> "datetime.date":
    from datetime import date
    if not value:
        return datetime.now(timezone.utc).date()
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return datetime.now(timezone.utc).date()


async def _oauth_token(session: aiohttp.ClientSession) -> str | None:
    """2026 OAuth password grant → short-lived bearer access token."""
    body = {
        "username": ACLED_USERNAME,
        "password": ACLED_PASSWORD,
        "grant_type": "password",
        "client_id": "acled",
        "scope": "authenticated",
    }
    try:
        async with session.post(
            ACLED_OAUTH_URL,
            data=body,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as resp:
            if resp.status != 200:
                text = (await resp.text())[:200]
                logger.error("[ACLED] OAuth token HTTP %d: %s", resp.status, text)
                return None
            data = await resp.json(content_type=None)
            token = data.get("access_token")
            if not token:
                logger.error("[ACLED] OAuth response missing access_token: %s", data)
            return token
    except Exception as e:  # noqa: BLE001
        logger.error("[ACLED] OAuth token error: %s", str(e)[:160])
        return None


def _read_params(page: int) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS_BACK)
    params = {
        "event_date": f"{start:%Y-%m-%d}|{end:%Y-%m-%d}",
        "event_date_where": "BETWEEN",
        "limit": PER_PAGE_LIMIT,
        "page": page,
        "_format": "json",
        "fields": "|".join(ACLED_FIELDS),
    }
    # Legacy path carries creds as query params; OAuth path uses the header.
    if not _have_oauth_creds() and _have_legacy_creds():
        params["key"] = ACLED_API_KEY
        params["email"] = ACLED_EMAIL
    return params


async def fetch_recent_acled_events(days_back: int | None = None) -> list[dict]:
    """Fetch recent ACLED events (paginated). Empty list if no creds / on error."""
    if days_back is not None:
        globals()["DAYS_BACK"] = days_back  # allow caller override without a param cascade

    if not (_have_oauth_creds() or _have_legacy_creds()):
        logger.warning(
            "[ACLED] No credentials (set ACLED_USERNAME/PASSWORD or "
            "ACLED_API_KEY/EMAIL). Skipping ACLED ingestion."
        )
        return []

    all_events: list[dict] = []
    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if _have_oauth_creds():
            token = await _oauth_token(session)
            if not token:
                return []
            headers["Authorization"] = f"Bearer {token}"

        for page in range(1, MAX_PAGES + 1):
            try:
                async with session.get(
                    ACLED_READ_URL,
                    params=_read_params(page),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    if resp.status != 200:
                        text = (await resp.text())[:200]
                        logger.error(
                            "[ACLED] read HTTP %d (page %d): %s", resp.status, page, text
                        )
                        break
                    data = await resp.json(content_type=None)
            except Exception as e:  # noqa: BLE001
                logger.error("[ACLED] read error (page %d): %s", page, str(e)[:160])
                break

            if not data.get("success"):
                logger.error("[ACLED] unsuccessful response (page %d): %s", page, data)
                break
            events = data.get("data") or []
            all_events.extend(events)
            logger.info("[ACLED] page %d → %d events (running %d)",
                        page, len(events), len(all_events))
            # A short page (< limit) means we've reached the end.
            if len(events) < PER_PAGE_LIMIT:
                break
            await asyncio.sleep(PER_PAGE_DELAY)

    logger.info("[ACLED] fetched %d events total", len(all_events))
    return all_events


_INSERT_SQL = """
INSERT INTO acled_conflicts_v2 (
    event_id_cnty, event_date, year,
    event_type, sub_event_type,
    actor1, assoc_actor_1, inter1,
    actor2, assoc_actor_2, inter2, interaction,
    region, country, admin1, admin2, admin3, location,
    latitude, longitude, geo_precision,
    source, source_scale, notes, fatalities
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
    $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
) ON CONFLICT (event_id_cnty) DO NOTHING
"""


def _row_values(e: dict) -> tuple:
    """Map one raw ACLED event dict → the acled_conflicts_v2 column tuple."""
    return (
        str(e.get("event_id_cnty")),
        _parse_event_date(e.get("event_date")),
        _to_int(e.get("year")),
        e.get("event_type"),
        e.get("sub_event_type"),
        e.get("actor1"),
        e.get("assoc_actor_1"),
        _to_int(e.get("inter1")),
        e.get("actor2"),
        e.get("assoc_actor_2"),
        _to_int(e.get("inter2")),
        _to_int(e.get("interaction")),
        e.get("region"),
        e.get("country"),
        e.get("admin1"),
        e.get("admin2"),
        e.get("admin3"),
        e.get("location"),
        _to_float(e.get("latitude")),
        _to_float(e.get("longitude")),
        _to_int(e.get("geo_precision"), 1),
        e.get("source"),
        e.get("source_scale"),
        e.get("notes"),
        _to_int(e.get("fatalities"), 0),
    )


async def insert_acled_events(pool: asyncpg.Pool, events: list[dict]) -> int:
    if not events:
        return 0
    inserted = 0
    async with pool.acquire() as conn:
        for e in events:
            if not e.get("event_id_cnty"):
                continue
            try:
                result = await conn.execute(_INSERT_SQL, *_row_values(e))
                if result == "INSERT 0 1":
                    inserted += 1
            except Exception as ex:  # noqa: BLE001 - never let one row kill the run
                logger.warning(
                    "[ACLED] insert skip %s: %s", e.get("event_id_cnty"), str(ex)[:120]
                )
    return inserted


async def run_acled_ingestion() -> None:
    """Main entry: fetch recent events → upsert into acled_conflicts_v2."""
    if not acled_enabled():
        logger.info("[ACLED] disabled via ACLED_INGEST_ENABLED — skipping")
        return

    logger.info("[ACLED] ingestion starting (days_back=%d)…", DAYS_BACK)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        events = await fetch_recent_acled_events()
        inserted = await insert_acled_events(pool, events) if events else 0
        logger.info("[ACLED] inserted %d new conflict events", inserted)
        try:
            async with pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM acled_conflicts_v2")
                logger.info("[ACLED] total events in acled_conflicts_v2: %s", total)
        except Exception as e:  # noqa: BLE001 - count is informational only
            logger.debug("[ACLED] count query skipped: %s", str(e)[:120])
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_acled_ingestion())
