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
from statistics import median

from fastapi import APIRouter, Query

from app import db
from app.services.attention_eclipse import (
    assemble_eclipse, country_dominance, entropy_collapse, field_entropy, MIN_CC_SIGNALS,
)

router = APIRouter()

# Per-topic coverage in the window: evidence-member volume + distinct languages /
# countries (breadth), joined to the DeepSeek-typed dynamic_topics fields and the
# latest Kalman movement. HAVING >= 3 drops singletons (pure noise).
_ECLIPSE_SQL = """
WITH win AS (
  SELECT tm.topic_id, tm.signal_id
  FROM topic_members tm
  WHERE tm.role = 'evidence'
    AND tm.engine_version = 'v1-compat'
    AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
),
agg AS (
  SELECT w.topic_id,
         COUNT(*) AS attention,
         COUNT(DISTINCT NULLIF(lower(s.source_lang), ''))
           FILTER (WHERE lower(s.source_lang) NOT IN ('xx','un','und','(null)')) AS langs,
         COUNT(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL) AS countries,
         (array_agg(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL)) AS country_codes
  FROM win w JOIN signals_v2 s ON s.id = w.signal_id
  GROUP BY w.topic_id
  HAVING COUNT(*) >= 3
)
SELECT a.topic_id, a.attention, a.langs, a.countries, a.country_codes,
       dt.label AS dyn_label, dt.category, dt.crisis_relevant,
       dt.mean_cohesion, dt.is_junk, dt.is_roundup, dt.identity_key,
       mv.velocity, mv.surprise
FROM agg a
LEFT JOIN dynamic_topics dt ON a.topic_id = 'dynamic-topic-' || dt.id::text
LEFT JOIN LATERAL (
  SELECT velocity, surprise FROM topic_movement
  WHERE topic_id = a.topic_id AND engine_version = 'movement-kalman-v1'
  ORDER BY window_end DESC LIMIT 1
) mv ON TRUE
"""

# Per-country #1 story (by evidence volume), among countries with enough signal.
_CC_DOMINANCE_SQL = """
WITH win AS (
  SELECT tm.topic_id, tm.signal_id FROM topic_members tm
  WHERE tm.role='evidence'
    AND tm.engine_version = 'v1-compat'
    AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
),
per AS (
  SELECT w.topic_id, s.country_code, COUNT(*) AS c
  FROM win w JOIN signals_v2 s ON s.id = w.signal_id
  WHERE s.country_code IS NOT NULL
  GROUP BY w.topic_id, s.country_code
),
cc_tot AS (SELECT country_code, SUM(c) AS tot FROM per GROUP BY country_code),
cc_top AS (
  SELECT DISTINCT ON (country_code) country_code, topic_id
  FROM per ORDER BY country_code, c DESC, topic_id
)
SELECT
  (SELECT COUNT(*) FROM cc_top t JOIN cc_tot g USING (country_code)
     WHERE g.tot >= $2 AND t.topic_id = $3) AS led,
  (SELECT COUNT(*) FROM cc_tot WHERE tot >= $2) AS qualifying
"""

# Daily field entropy over the trailing 7 full days (baseline for entropy-collapse).
_ENTROPY_BASELINE_SQL = """
-- 'day' boundaries use the DB session TZ (assumed UTC on Fly/Supabase).
WITH d AS (
  SELECT date_trunc('day', tm.assigned_at) AS day, tm.topic_id, COUNT(*) AS c
  FROM topic_members tm
  WHERE tm.role='evidence'
    AND tm.engine_version = 'v1-compat'
    AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at >= date_trunc('day', NOW()) - INTERVAL '7 days'
    AND tm.assigned_at <  date_trunc('day', NOW())
  GROUP BY 1, 2 HAVING COUNT(*) >= 3
),
tot AS (SELECT day, SUM(c) AS t FROM d GROUP BY day)
SELECT d.day, -SUM((c::float / t) * ln(c::float / t)) AS h
FROM d JOIN tot USING (day) GROUP BY d.day
"""


@router.get("/api/v2/attention/eclipse")
async def get_attention_eclipse(
    hours: int = Query(24, ge=1, le=168),
    min_langs: int = Query(3, ge=1, le=20),
    min_countries: int = Query(8, ge=1, le=100),
    eclipse_top1: float = Query(0.20, ge=0.02, le=0.90),
    limit: int = Query(8, ge=1, le=30),
) -> dict:
    if db.pool is None:
        return {"contract": "attention-eclipse-v1", "hours": hours, "eclipse": False,
                "tier": "none", "intensity": 0.0,
                "axes": {"country_dominance": None, "entropy_collapse": None,
                         "top1_share": 0.0, "hhi": 0.0},
                "dominant": {}, "window": {}, "selected": [], "labeled_out": [],
                "method": {}, "notes": ["database unavailable"],
                "generated_at": datetime.now(timezone.utc).isoformat()}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 45000")
        raw = await conn.fetch(_ECLIPSE_SQL, hours)

        rows = [{
            "topic_id": r["topic_id"], "label": r["dyn_label"] or r["topic_id"],
            "attention": r["attention"], "langs": r["langs"], "countries": r["countries"],
            "country_codes": list(r["country_codes"] or []),
            "velocity": r["velocity"], "surprise": r["surprise"],
            "category": r["category"], "crisis_relevant": r["crisis_relevant"],
            "mean_cohesion": r["mean_cohesion"], "is_junk": r["is_junk"],
            "is_roundup": r["is_roundup"], "identity_key": r["identity_key"],
        } for r in raw]

        cc_dominance: float | None = None
        if rows:
            dom_id = max(rows, key=lambda r: r["attention"])["topic_id"]
            drow = await conn.fetchrow(_CC_DOMINANCE_SQL, hours, MIN_CC_SIGNALS, dom_id)
            if drow:
                cc_dominance = country_dominance(int(drow["led"] or 0), int(drow["qualifying"] or 0))

        # entropy_collapse compares the field vs a per-CALENDAR-DAY baseline, so it is
        # only meaningful at the ambient 24h window; skip (honest None) for other spans.
        collapse: float | None = None
        if hours == 24:
            base_rows = await conn.fetch(_ENTROPY_BASELINE_SQL)
            baselines = [float(b["h"]) for b in base_rows if b["h"] is not None]
            if len(baselines) >= 3:
                h_now = field_entropy([r["attention"] for r in rows])
                collapse = entropy_collapse(h_now, median(baselines))

    sel = assemble_eclipse(rows, eclipse_top1=eclipse_top1, min_langs=min_langs,
                           min_countries=min_countries, display_limit=limit,
                           country_dominance=cc_dominance, entropy_collapse=collapse,
                           field_size=len(rows),
                           total_coverage=sum(r["attention"] for r in rows))

    by_id = {row.topic_id: row for row in sel.ledger}
    dom_cc = {r["topic_id"]: r["country_codes"] for r in rows}
    selected = [{
        "topic_id": tid, "label": by_id[tid].label,
        "attention": by_id[tid].components["attention"],
        "attention_share": by_id[tid].attention_share,
        "consequence": by_id[tid].consequence,
        "language_breadth": by_id[tid].components["language_breadth"],
        "country_breadth": by_id[tid].components["country_breadth"],
        "countries": dom_cc.get(tid, []),
        "velocity": by_id[tid].components["velocity"], "lane": by_id[tid].lane,
        "reason_codes": by_id[tid].reason_codes,
    } for tid in sel.selected_ids]

    notes: list[str] = []
    if sel.tier != "total":
        notes.append(
            f"tier={sel.tier} (top story = {sel.window.get('top1_share', 0)*100:.1f}% of coverage; "
            f"country_dominance={sel.axes.get('country_dominance')}, "
            f"entropy_collapse={sel.axes.get('entropy_collapse')})"
        )
    notes.append("attention = coverage-volume share, a proxy for attention (not audience eyeballs)")

    return {
        "contract": "attention-eclipse-v1", "hours": hours,
        "eclipse": sel.eclipse, "tier": sel.tier, "intensity": sel.intensity,
        "axes": sel.axes, "dominant": sel.dominant, "window": sel.window,
        "selected": selected,
        "labeled_out": [
            {"topic_id": r.topic_id, "label": r.label, "status": r.status,
             "attention_share": r.attention_share, "lane": r.lane,
             "reason_codes": r.reason_codes}
            for r in sel.ledger if r.status in ("labeled_out", "dominant") and r.consequence >= 0.5
        ][:12],
        "method": sel.method, "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
