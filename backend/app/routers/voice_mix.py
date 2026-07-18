"""Voice Mix endpoint (#160/#230) — live corpus diversity as a product surface.

Answers "whose voice is in Atlas right now?" with a number. Same formula as the
offline audit (`scripts/voice_mix_audit.py`), shared via
`app.services.voice_mix`. Optional ?country=CC scopes to one subject country so
CountryBrief can show its local voice mix.

Degradation contract (2026-07-18, the intermittent-503 fix): the aggregation
scans signals_v2 and under M1 batch-window DB contention a statement can blow
past its timeout — previously that bubbled into the global db_busy handler as
a 503. Now every query block is bounded (statement_timeout 2500ms; the 3-query
base block worst-case ≈7.5s < the old single 8s budget) and timeouts are
caught HERE: the base block degrades to an honest 200
`{"degraded": true, "reason": "db_busy"}` shape (clients already guard on the
fields they read — Landing falls back to its dated baseline, CountryBrief
skips the panel), and the country relation block degrades independently so a
slow relation query never takes down the base report (the delight-facts
per-query-guard lesson).
"""
import logging
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Query

from app import db
from app.services import voice_mix

router = APIRouter()
logger = logging.getLogger(__name__)

# Per-STATEMENT budget. The base block runs 3 aggregate queries, the relation
# block 3 more — bounding each at 2.5s keeps any block's worst case under the
# previous single 8s budget instead of letting them stack toward ~16s+.
STATEMENT_TIMEOUT_MS = 2500

# The db-busy classes the app-level handler maps to 503 — caught locally so
# this endpoint can serve its honest degraded shape instead.
_DB_BUSY_ERRORS = (
    asyncpg.exceptions.QueryCanceledError,
    asyncpg.exceptions.TooManyConnectionsError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    TimeoutError,
)


def degraded_payload(hours: int, cc: str | None, reason: str) -> dict:
    """Honest degraded voice-mix shape. Carries NO stats fields at all — a
    degraded response must never be mistaken for a measured zero (Landing
    guards on `distinct_origin_countries`, CountryBrief on `relation`)."""
    return {
        "contract": "voice-mix-v0",
        "degraded": True,
        "reason": reason,
        "detail": "voice-mix aggregation timed out under database load — retry shortly",
        "window_hours": hours,
        "country": cc,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v2/voice-mix")
async def get_voice_mix(
    hours: int = Query(168, ge=1, le=720),
    country: str | None = Query(None, min_length=2, max_length=2),
):
    cc = country.upper() if country else None
    where = "timestamp > NOW() - ($1::int * INTERVAL '1 hour')"
    params: list = [hours]
    if cc:
        where += " AND country_code = $2"
        params.append(cc)

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
            lang_rows = await conn.fetch(
                f"SELECT COALESCE(NULLIF(TRIM(source_lang),''),'(null)') AS lang, "
                f"COUNT(*) AS n FROM signals_v2 WHERE {where} GROUP BY 1", *params)
            origin_rows = await conn.fetch(
                f"SELECT COALESCE(NULLIF(TRIM(source_origin_country),''),'(null)') AS o, "
                f"COUNT(*) AS n FROM signals_v2 WHERE {where} GROUP BY 1", *params)
            extra = await conn.fetchrow(
                f"SELECT COUNT(*) AS total, "
                f"COUNT(*) FILTER (WHERE is_state_media) AS state_media, "
                f"COUNT(DISTINCT source_name) AS distinct_sources "
                f"FROM signals_v2 WHERE {where}", *params)
    except _DB_BUSY_ERRORS as exc:
        logger.warning("voice-mix base aggregation degraded (%s): %s",
                       type(exc).__name__, str(exc)[:120])
        return degraded_payload(hours, cc, "db_busy")

    lang_counts = {r["lang"]: int(r["n"]) for r in lang_rows}
    origin_counts = {r["o"]: int(r["n"]) for r in origin_rows}
    report = voice_mix.compute(
        lang_counts, origin_counts,
        int(extra["total"]), int(extra["state_media"]),
        int(extra["distinct_sources"]),
    )
    report["window_hours"] = hours
    report["country"] = cc
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["contract"] = "voice-mix-v0"

    # The speaker↔subject relation: only meaningful when a subject country is
    # scoped. "Of all coverage ABOUT this country, how much is voiced BY it?"
    # Guarded independently — a timeout here degrades ONLY the relation, the
    # base report above still serves.
    if cc:
        langs = list(voice_mix.primary_langs(cc))
        p = len(params)
        try:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
                agg = await conn.fetchrow(
                    f"SELECT "
                    f"  COUNT(*) FILTER (WHERE source_origin_country IS NOT NULL) AS origin_known, "
                    f"  COUNT(*) FILTER (WHERE source_origin_country = ${p+1}) AS domestic, "
                    f"  COUNT(*) FILTER (WHERE source_origin_country IS NOT NULL "
                    f"      AND source_origin_country <> ${p+1} "
                    f"      AND source_lang = ANY(${p+2}::text[])) AS soft_power "
                    f"FROM signals_v2 WHERE {where}",
                    *params, cc, langs)
                f_origins = await conn.fetch(
                    f"SELECT source_origin_country AS cc, COUNT(*) AS n FROM signals_v2 "
                    f"WHERE {where} AND source_origin_country IS NOT NULL "
                    f"AND source_origin_country <> ${p+1} "
                    f"GROUP BY 1 ORDER BY n DESC LIMIT 6", *params, cc)
                f_langs = await conn.fetch(
                    f"SELECT source_lang AS lang, COUNT(*) AS n FROM signals_v2 "
                    f"WHERE {where} AND source_lang NOT IN ('xx','un','und') "
                    f"AND TRIM(source_lang) <> '' "
                    f"AND NOT (source_lang = ANY(${p+1}::text[])) "
                    f"GROUP BY 1 ORDER BY n DESC LIMIT 6", *params, langs)
            report["relation"] = voice_mix.relation(
                int(extra["total"]), int(agg["origin_known"] or 0),
                int(agg["domestic"] or 0), int(agg["soft_power"] or 0),
                [(r["cc"], int(r["n"])) for r in f_origins],
                [(r["lang"], int(r["n"])) for r in f_langs],
            )
        except _DB_BUSY_ERRORS as exc:
            logger.warning("voice-mix relation lane degraded (%s): %s",
                           type(exc).__name__, str(exc)[:120])
            report["relation_degraded"] = True
        report["primary_languages"] = langs
    return report
