"""Universe view (contract universe-v0) — the SERVING half.

Spec: docs/specs/2026-07-02-universe-view.md. The whole living story
population as one navigable field.

THIS ENDPOINT DOES NOT BUILD ANYTHING (2026-07-27)
--------------------------------------------------
It used to. The build MEASURES 75.5s (2,603 nodes / 6,306 edges / 3.96 MB) —
longer than the Fly proxy holds a request open — so in production every cold
build was killed by the PROXY (HTTP 000 after ~70s; 502 at 32.7s / 61.1s;
0/5 success up to 92.5s). The in-process cache could therefore never fill, and
because nothing was ever stored there was not even a stale payload to fall
back on: `/api/v2/universe` sat at 0% availability and the UNIVERSE tab was
permanently dark.

Raising the STATEMENT timeout (20s -> 90s, commit ae877dee) could not fix that:
the ceiling was the request, not Postgres.

So the build left the request path, following the daily-edition pattern
(`build_daily_publication.py` -> `atlas_daily_editions`):

    backend/scripts/build_universe_field.py --execute   (M1, nightly, ~75s)
        -> universe_field_artifacts  (one compact JSONB row per window)
            -> this endpoint: one indexed read, always fast

Honest degradation, in order of truth:
  1. the stored artifact, with `generated_at` + `age_hours` + a `stale` marker
     the reader can see (a field older than the nightly cadence is served, but
     never silently presented as current),
  2. an honest empty payload naming its reason (`not_precomputed` before the
     first build has run here, `no_db`, or `db_error`) — never a hang, never a
     502, never a silent empty 200 that looks like "there are no stories".

The build logic itself lives in `app.services.universe_field` (fastapi-free, so
the M1 `mlvenv` builder can import it). The projection/edge helpers are
re-exported here because they are the frozen contract the universe tests pin.
"""
import asyncio
import logging

import asyncpg
from fastapi import APIRouter, Query, Response

from app.services.universe_field import (  # noqa: F401 — re-exported contract
    CATEGORY_PULL,
    NEIGHBORS_PER_NODE,
    STALE_AFTER_HOURS,
    TIMELINE_DAYS,
    _nearest_edges,
    _project_history,
    _project_universe,
    build_universe_payload,
    empty_payload,
    fetch_stored_universe,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# The artifact is rebuilt once a night. A short serving cache absorbs bursts of
# readers without adding staleness anyone could notice.
_CACHE_TTL_S = 60
# Dark ≠ down (council N4): when there is genuinely nothing to serve, the empty
# payload says when to come back.
RETRY_AFTER_S = 60

# The db-busy classes that mean "the database timed out / pushed back", as
# opposed to a code defect — surfaced honestly as reason='db_timeout'.
_DB_TIMEOUT_ERRORS = (
    asyncpg.exceptions.QueryCanceledError,
    asyncpg.exceptions.TooManyConnectionsError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    TimeoutError,
    asyncio.TimeoutError,
)


def _classify_failure(exc: BaseException) -> str:
    """'db_timeout' for statement-timeout/pool-pressure classes, else 'error'."""
    return "db_timeout" if isinstance(exc, _DB_TIMEOUT_ERRORS) else "error"


@router.get("/api/v2/universe")
async def get_universe(response: Response, days: int = Query(TIMELINE_DAYS, ge=7, le=90)):
    """The living story universe: bodies + full-space relations + time.

    A pure read of the precomputed artifact. It never builds, so it never hangs
    and never 502s; if the artifact is missing or the read fails, it says so.
    """
    try:
        payload = await fetch_stored_universe(days)
    except Exception as exc:
        reason = _classify_failure(exc)
        logger.error("universe artifact read failed (%s): %s", reason, exc)
        response.headers["Retry-After"] = str(RETRY_AFTER_S)
        return {
            **empty_payload(),
            "reason": reason,
            "retry_after_s": RETRY_AFTER_S,
        }

    if payload.get("reason"):
        # Nothing precomputed (yet) — an honest empty field with a reason, not
        # a spinner and not a lie. `not_precomputed` specifically means "the
        # nightly builder has not written an artifact here", which is a
        # different fact from "the database is unwell".
        response.headers["Retry-After"] = str(RETRY_AFTER_S)
        return {**payload, "retry_after_s": RETRY_AFTER_S}

    # A stale artifact is still the real field — serve it, but let caches (and
    # the reader, via meta.stale / meta.age_hours) see that it is old.
    response.headers["Cache-Control"] = f"public, max-age={_CACHE_TTL_S}"
    return payload
