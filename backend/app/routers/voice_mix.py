"""Voice Mix endpoint (#160/#230) — live corpus diversity as a product surface.

Answers "whose voice is in Atlas right now?" with a number. Same formula as the
offline audit (`scripts/voice_mix_audit.py`), shared via
`app.services.voice_mix`. Optional ?country=CC scopes to one subject country so
CountryBrief can show its local voice mix.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import db
from app.services import voice_mix

router = APIRouter()


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

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")
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
    return report
