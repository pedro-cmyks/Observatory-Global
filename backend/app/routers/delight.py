"""GET /api/v2/delight — the loading-delight rotation feed (loading-delight-v0).

Math-first "Atlas facts" distilled from aggregates that are already cheap:
country_hourly_v2 / country_heat_v2 matviews, the Kalman topic_movement table,
and the coverage-gap query the briefing already runs. No LLM anywhere.

Non-fatal by design: every fact query is individually guarded — a failed fact
is dropped, never a 500; an empty feed is a valid payload (the frontend ships
bundled evergreen facts as fallback). Redis-cached 15 min.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app import db
from app.main_v2 import app
from app.core.iso_country_names import resolve_country_name
from app.services import delight_facts

router = APIRouter()
logger = logging.getLogger(__name__)

CACHE_KEY = "delight_feed:v2:24"
CACHE_TTL = 900


@router.get("/api/v2/delight")
async def get_delight_feed():
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    facts: list[dict] = []
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")

        # Languages (one bounded 24h GROUP BY — the heaviest scan here, so it
        # runs in its own guard and the pulse fact never dies with it).
        known: dict[str, int] = {}
        try:
            lang_rows = await conn.fetch("""
                SELECT COALESCE(NULLIF(TRIM(source_lang), ''), 'xx') AS lang,
                       COUNT(*)::bigint AS n
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                GROUP BY 1
            """)
            known = {r["lang"]: int(r["n"]) for r in lang_rows if r["lang"] != "xx"}
            total_known = sum(known.values())
            f = delight_facts.language_fact(total_known, known.get("en", 0), len(known))
            if f:
                facts.append(f)
        except Exception:
            logger.warning("delight: language fact failed", exc_info=True)

        # Pulse (matview agg, cheap).
        try:
            pulse = await conn.fetchrow("""
                SELECT COALESCE(SUM(signal_count), 0)::bigint AS n,
                       COUNT(DISTINCT country_code)::int      AS countries
                FROM country_hourly_v2
                WHERE hour > NOW() - INTERVAL '24 hours'
            """)
            f = delight_facts.pulse_fact(int(pulse["n"]), int(pulse["countries"]), len(known))
            if f:
                facts.append(f)
        except Exception:
            logger.warning("delight: pulse fact failed", exc_info=True)

        # Fastest-rising story — the shared Kalman movement field (#219).
        try:
            mover = await conn.fetchrow("""
                SELECT dt.label
                FROM (
                    SELECT DISTINCT ON (topic_id) topic_id, velocity, trend
                    FROM topic_movement
                    WHERE engine_version = 'movement-kalman-v1'
                    ORDER BY topic_id, window_end DESC
                ) tm
                JOIN dynamic_topics dt
                  ON 'dynamic-topic-' || dt.id = tm.topic_id
                WHERE dt.state = 'active' AND NOT dt.is_umbrella
                  AND tm.trend = 'surging'
                ORDER BY tm.velocity DESC NULLS LAST
                LIMIT 1
            """)
            f = delight_facts.mover_fact(mover["label"] if mover else None)
            if f:
                facts.append(f)
        except Exception:
            logger.warning("delight: mover fact failed", exc_info=True)

        # Coverage gap — same shape as the briefing gap box (#225/#172).
        try:
            gap = await conn.fetchrow("""
                SELECT t.label, COUNT(*)::int AS raw_signals
                FROM signal_topic_assignments a
                JOIN atlas_topics t ON t.id = a.topic_id
                WHERE a.assigned_at > NOW() - INTERVAL '24 hours'
                GROUP BY t.label
                HAVING COUNT(*) >= 20
                   AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
                ORDER BY raw_signals DESC
                LIMIT 1
            """)
            if gap:
                f = delight_facts.gap_fact(gap["label"], int(gap["raw_signals"]))
                if f:
                    facts.append(f)
        except Exception:
            logger.warning("delight: gap fact failed", exc_info=True)

        # Under the radar: top-10 composite heat, below-median volume.
        try:
            heat_rows = await conn.fetch("""
                WITH med AS (
                    SELECT percentile_disc(0.5) WITHIN GROUP (ORDER BY volume_now)::bigint AS v
                    FROM country_heat_v2
                    WHERE hours_window = 24 AND atlas_heat IS NOT NULL
                )
                SELECT h.country_code, h.volume_now::bigint AS volume,
                       (SELECT v FROM med) AS median_volume
                FROM country_heat_v2 h
                WHERE h.hours_window = 24 AND h.atlas_heat IS NOT NULL
                ORDER BY h.atlas_heat DESC
                LIMIT 10
            """)
            for r in heat_rows:
                if int(r["volume"]) < int(r["median_volume"]):
                    f = delight_facts.quiet_fact(
                        resolve_country_name(r["country_code"]), int(r["volume"])
                    )
                    if f:
                        facts.append(f)
                    break
        except Exception:
            logger.warning("delight: quiet fact failed", exc_info=True)

    payload = {
        "contract": "loading-delight-v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facts": facts,
    }
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(CACHE_KEY, CACHE_TTL, json.dumps(payload))
        except Exception:
            pass
    return payload
