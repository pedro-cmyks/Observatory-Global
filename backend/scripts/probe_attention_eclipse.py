"""Read-only PROBE for the attention-eclipse / under-the-radar signal.

Question (owner): during a World-Cup-final-scale attention eclipse, "while
everyone watches the final, what ELSE consequential is slipping under the radar?"

This probe measures, over the last N hours, whether Atlas can SEPARATE a
genuinely-eclipsed consequential story from ordinary quiet noise — using only
tables that exist today (signals_v2 + topic_members + topic_movement +
dynamic_topics). It is READ-ONLY: no writes, no schema change. It prints, it
does not decide.

Three parts, matching the three needs in the diagnosis:
  (a) ECLIPSE DETECTOR (window-level): is coverage concentrated on one event?
      top-1 coverage-volume share + HHI. Honest caveat: this is COVERAGE-volume
      concentration (the firehose bloating around the event), a PROXY for
      audience attention — Atlas cannot measure eyeballs (wiki/trends are
      decoupled from stories, top-N, stale). During a diffuse day the detector
      stays OFF and the signal should surface nothing (no crying wolf).
  (b) ATTENTION SHARE (per story): evidence-member volume / window total.
  (c) CONSEQUENCE PROXY (per story): REUSES daily_edition.global_breadth_signal
      (language + country breadth, NOT raw volume) + topic_movement velocity.

Under-radar ranking = among stories that clear a CONSEQUENCE FLOOR (multi-language
AND multi-country) and QUALITY GATES (not junk / not roundup / coherence floor),
the ones with the LOWEST attention share. The naive consequence/attention RATIO
is deliberately NOT used — it explodes on tiny denominators and surfaces local
trivia (measured: bull-goring-runner, a game review, at attention=5). The floor +
low-share ordering is the correct instrument.

Usage:
  cd backend && set -a && source /Users/pedro/AtlasLocalWorker/.env && set +a && \
  PYTHONPATH=$(pwd) <py> scripts/probe_attention_eclipse.py [--hours 24] [--sim-share 0.45]
"""
from __future__ import annotations

import argparse
import asyncio
import html
import os

import asyncpg

# Reuse the production consequence proxy verbatim — no parallel truth model.
try:
    from app.services.daily_edition import global_breadth_signal
except Exception:  # pragma: no cover - allow running outside PYTHONPATH
    def global_breadth_signal(lang: int, country: int) -> float:
        return round(0.5 * min(1.0, (lang or 0) / 5.0) + 0.5 * min(1.0, (country or 0) / 6.0), 6)


_WIN_SQL = """
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
SELECT a.*, dt.label AS dyn_label, dt.category, dt.crisis_relevant,
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

_ROUNDUP_LABEL_HINTS = (
    "front page", "naslovne", "portada", "roundup", "round-up", "briefing",
    "digest", "news from", "noticias", "schlagzeilen", "titulares",
)
# Bare-label lane typing (dynamic_topics.category is DeepSeek-typed; use it, not
# the keyword classify_stream_lane which mislabels e.g. 'armed-conflict-
# escalation' as sports — a measured false positive).
_SOFT_LANE_HINTS = (
    "world cup", "fifa", "football", "soccer", "olympic", "nba", "premier league",
    "box office", "netflix", "grammy", "oscars", "album", "concert",
)


def soft_lane(row: dict) -> str:
    cat = (row.get("category") or "").lower()
    if any(k in cat for k in ("sport", "entertainment", "culture", "celebrity")):
        return cat
    low = html.unescape(row.get("dyn_label") or row.get("topic_id") or "").lower()
    if any(k in low for k in _SOFT_LANE_HINTS):
        return "sports/entertainment(label)"
    return "general"


def consequence(row: dict) -> float:
    breadth = global_breadth_signal(row["langs"], row["countries"])
    mv = min(1.0, abs(row.get("velocity") or 0.0))
    sp = min(1.0, row.get("surprise") or 0.0)
    return round(0.6 * breadth + 0.25 * mv + 0.15 * sp, 3)


def gated_out(row: dict, cohesion_floor: float) -> str | None:
    if row.get("is_junk"):
        return "junk"
    if row.get("is_roundup"):
        return "roundup(flag)"
    low = html.unescape(row.get("dyn_label") or "").lower()
    if any(k in low for k in _ROUNDUP_LABEL_HINTS):
        return "roundup(label)"
    coh = row.get("mean_cohesion")
    if coh is not None and float(coh) < cohesion_floor:
        return f"low_cohesion({float(coh):.2f})"
    return None


def concentration(rows: list[dict]) -> tuple[float, float, float]:
    total = sum(r["attention"] for r in rows) or 1
    srt = sorted(rows, key=lambda x: -x["attention"])
    top1 = srt[0]["attention"] / total
    top3 = sum(r["attention"] for r in srt[:3]) / total
    hhi = sum((r["attention"] / total) ** 2 for r in rows)
    return top1, top3, hhi


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--sim-share", type=float, default=0.45,
                    help="simulated dominant-event share of total coverage (WC-final scenario)")
    ap.add_argument("--cohesion-floor", type=float, default=0.55)
    ap.add_argument("--min-langs", type=int, default=3)
    ap.add_argument("--min-countries", type=int, default=8)
    ap.add_argument("--eclipse-top1", type=float, default=0.20,
                    help="top-1 coverage share above which an eclipse is declared")
    args = ap.parse_args()

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET statement_timeout = 45000")
    rows = [dict(r) for r in await conn.fetch(_WIN_SQL, args.hours)]
    await conn.close()

    total = sum(r["attention"] for r in rows)
    for r in rows:
        r["share"] = r["attention"] / total
        r["cons"] = consequence(r)
        r["lane"] = soft_lane(r)
        r["gate"] = gated_out(r, args.cohesion_floor)
        r["name"] = html.unescape(r.get("dyn_label") or r["topic_id"])[:46]

    top1, top3, hhi = concentration(rows)
    eclipse_now = top1 >= args.eclipse_top1
    print(f"WINDOW = last {args.hours}h · topics(>=3 evidence) = {len(rows)} · total coverage = {total}")
    print(f"(a) ECLIPSE DETECTOR — REAL NOW: top1={top1*100:.1f}%  top3={top3*100:.1f}%  HHI={hhi:.4f}"
          f"  ->  {'ECLIPSE' if eclipse_now else 'DIFFUSE (no dominant event; signal stays quiet)'}")

    # Simulate a WC-final: inject a dominant sport event at --sim-share of the new total.
    dom_att = int(args.sim_share / (1 - args.sim_share) * total)
    sim = rows + [{"attention": dom_att}]
    s1, s3, shhi = concentration(sim)
    print(f"    SIMULATED WC-FINAL (dominant at {args.sim_share*100:.0f}% share): top1={s1*100:.1f}%"
          f"  HHI={shhi:.4f}  ->  {'ECLIPSE DETECTED' if s1 >= args.eclipse_top1 else 'diffuse'}")

    print("\nFIREHOSE — top 6 by coverage volume (what everyone is covering):")
    for r in sorted(rows, key=lambda x: -x["attention"])[:6]:
        print(f"  att={r['attention']:5d} share={r['share']*100:4.1f}%  L{r['langs']}/C{r['countries']}"
              f"  lane={r['lane']:14s} {r['name']}")

    cons_pool = [r for r in rows
                 if r["langs"] >= args.min_langs and r["countries"] >= args.min_countries]
    under = [r for r in cons_pool if not r["gate"] and r["lane"] == "general"]
    print(f"\n(c)+(b) UNDER-RADAR — consequential (L>={args.min_langs} & C>={args.min_countries}),"
          f" quality-gated, lane=general: {len(under)} of {len(cons_pool)} consequential")
    print("      lowest attention share first (the drowned-out consequential stories):")
    for r in sorted(under, key=lambda x: x["attention"])[:14]:
        print(f"  att={r['attention']:4d} share={r['share']*100:5.2f}% L{r['langs']:2d}/C{r['countries']:3d}"
              f" cons={r['cons']:.2f} vel={r.get('velocity') or 0:+.2f} {r['name']}")

    dropped = [r for r in cons_pool if r["gate"] or r["lane"] != "general"]
    print(f"\n      LABELED-OUT of the consequential set ({len(dropped)}) — classified, never silently hidden:")
    for r in sorted(dropped, key=lambda x: -x["attention"])[:8]:
        why = r["gate"] or f"lane:{r['lane']}"
        print(f"  att={r['attention']:5d} L{r['langs']}/C{r['countries']}  why={why:18s} {r['name']}")


if __name__ == "__main__":
    asyncio.run(main())
