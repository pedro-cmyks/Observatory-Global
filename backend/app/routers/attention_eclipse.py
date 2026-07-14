"""Attention-eclipse / under-the-radar endpoint.

GET /api/v2/attention/eclipse[?hours=&min_langs=&min_countries=&limit=]

"While everyone watches the final, what ELSE consequential is slipping under the
radar?" Detects whether the window's COVERAGE is concentrated on one dominant event
(the eclipse) and, if so, surfaces the consequential-but-quiet stories being drowned
out. Read-only over signals_v2 + topic_members + topic_movement + dynamic_topics; no
new schema. Sibling of the parked /attention/silent-risks router.

Honesty: this is COVERAGE-volume concentration, a PROXY for attention (Atlas cannot
measure audience eyeballs — wiki/trends are decoupled from stories). On a diffuse day
the detector stays OFF and the surface is empty (no crying wolf). Every candidate is
reason-coded; sports/entertainment are LABELED, not dropped; the signal RANKS
candidates for an analyst, it does not certify an individual story.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import db
from app.services.attention_eclipse import assemble_eclipse

router = APIRouter()

# Per-topic coverage in the window: evidence-member volume + distinct languages /
# countries (breadth), joined to the DeepSeek-typed dynamic_topics fields and the
# latest Kalman movement. HAVING >= 3 drops singletons (pure noise).
_ECLIPSE_SQL = """
WITH win AS (
  SELECT tm.topic_id, tm.signal_id
  FROM topic_members tm
  WHERE tm.role = 'evidence'
    AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
),
agg AS (
  SELECT w.topic_id,
         COUNT(*) AS attention,
         COUNT(DISTINCT NULLIF(lower(s.source_lang), ''))
           FILTER (WHERE lower(s.source_lang) NOT IN ('xx','un','und','(null)')) AS langs,
         COUNT(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL) AS countries
  FROM win w JOIN signals_v2 s ON s.id = w.signal_id
  GROUP BY w.topic_id
  HAVING COUNT(*) >= 3
)
SELECT a.topic_id, a.attention, a.langs, a.countries,
       dt.label AS dyn_label, dt.category, dt.crisis_relevant,
       dt.mean_cohesion, dt.is_junk, dt.is_roundup,
       mv.velocity, mv.surprise
FROM agg a
LEFT JOIN dynamic_topics dt ON a.topic_id = 'dynamic-topic-' || dt.id::text
LEFT JOIN LATERAL (
  SELECT velocity, surprise FROM topic_movement
  WHERE topic_id = a.topic_id AND engine_version = 'movement-kalman-v1'
  ORDER BY window_end DESC LIMIT 1
) mv ON TRUE
"""


@router.get("/api/v2/attention/eclipse")
async def get_attention_eclipse(
    hours: int = Query(24, ge=1, le=168),
    min_langs: int = Query(3, ge=1, le=20),
    min_countries: int = Query(8, ge=1, le=100),
    eclipse_top1: float = Query(0.20, ge=0.02, le=0.90),  # 0.20 = honest prod gate; low values allow sensitive/demo runs
    limit: int = Query(8, ge=1, le=30),
) -> dict:
    if db.pool is None:
        return {"contract": "attention-eclipse-v0", "eclipse": False,
                "selected": [], "notes": ["database unavailable"]}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 45000")
        raw = await conn.fetch(_ECLIPSE_SQL, hours)

    rows = [{
        "topic_id": r["topic_id"],
        "label": r["dyn_label"] or r["topic_id"],
        "attention": r["attention"],
        "langs": r["langs"],
        "countries": r["countries"],
        "velocity": r["velocity"],
        "surprise": r["surprise"],
        "category": r["category"],
        "crisis_relevant": r["crisis_relevant"],
        "mean_cohesion": r["mean_cohesion"],
        "is_junk": r["is_junk"],
        "is_roundup": r["is_roundup"],
    } for r in raw]

    sel = assemble_eclipse(rows, eclipse_top1=eclipse_top1, min_langs=min_langs,
                           min_countries=min_countries, display_limit=limit)

    by_id = {row.topic_id: row for row in sel.ledger}
    selected = [{
        "topic_id": tid,
        "label": by_id[tid].label,
        "attention": by_id[tid].components["attention"],
        "attention_share": by_id[tid].attention_share,
        "consequence": by_id[tid].consequence,
        "language_breadth": by_id[tid].components["language_breadth"],
        "country_breadth": by_id[tid].components["country_breadth"],
        "velocity": by_id[tid].components["velocity"],
        "lane": by_id[tid].lane,
        "reason_codes": by_id[tid].reason_codes,
    } for tid in sel.selected_ids]

    notes: list[str] = []
    if not sel.eclipse:
        notes.append(
            f"no dominant event this window (top story = {sel.window.get('top1_share', 0)*100:.1f}% "
            f"of coverage, below the {eclipse_top1*100:.0f}% eclipse gate) — nothing under the radar"
        )
    notes.append("attention = coverage-volume share, a proxy for attention (not audience eyeballs)")

    return {
        "contract": "attention-eclipse-v0",
        "hours": hours,
        "eclipse": sel.eclipse,
        "dominant": sel.dominant,
        "window": sel.window,
        "selected": selected,
        "labeled_out": [
            {"topic_id": r.topic_id, "label": r.label, "status": r.status,
             "attention_share": r.attention_share, "lane": r.lane,
             "reason_codes": r.reason_codes}
            for r in sel.ledger
            if r.status in ("labeled_out", "dominant") and r.consequence >= 0.5
        ][:12],
        "method": sel.method,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
