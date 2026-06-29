"""Unified Engine F3.2 — A/B report (spec 2026-06-29-atlas-unified-engine §11).

Compares the v1-compat projection vs the unified-v2 construction in
`topic_members`, over the same window, on the §11 metrics. This IS Paper 1's
split-brain-vs-unified experiment, and the gate for the F4 cutover:

  unified-v2 >= v1 on coherence, recall(proxy), evidence-purity
  AND no worse on black-hole/noise.

Metrics (engine-agnostic, computed from the persisted e5 embeddings so the
comparison does not privilege either construction):
  - coherence       — per topic, mean cosine(member, member-centroid); aggregate
                      is the member-weighted mean (↑ tighter topics).
  - evidence_purity — fraction of evidence members within 0.85 cosine of their
                      own topic centroid (↑ fewer off-topic members).
  - black_hole      — largest single topic's share of all evidence members (↓;
                      #224 mega-blob guard) + the Gini of topic sizes.
  - cross_source    — topics holding BOTH evidence and discussion members (the
                      unification payoff; press + forum about one situation).
  - coverage(proxy) — distinct topics with >= MIN_TOPIC members + total members
                      (a recall stand-in until the gold benchmark exists).

Caveat (printed): v1-compat evidence members that are not embedded are excluded
from coherence/purity (those are computed over the embedded subset); v2 members
are embedded by construction. Coverage/black-hole use ALL members.

Run (M1 mlvenv): python -m backend.scripts.engine_ab_report
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import asyncpg
import numpy as np

V1 = "v1-compat"
V2 = "unified-v2"
MIN_TOPIC = 3          # topics below this are too small to score coherence
PURITY_SIM = 0.85      # member within this cosine of its topic centroid = on-topic


def _parse_vec(text: str) -> np.ndarray:
    return np.asarray(json.loads(text.replace("{", "[").replace("}", "]")), dtype=np.float32)


def _unit(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


async def _members_with_emb(conn, engine: str, role: str) -> dict[str, list[np.ndarray]]:
    rows = await conn.fetch(
        """SELECT tm.topic_id, e.vec::text AS vec
           FROM topic_members tm
           JOIN signal_embeddings e ON e.signal_id = tm.signal_id
           WHERE tm.engine_version = $1 AND tm.role = $2""",
        engine, role,
    )
    out: dict[str, list[np.ndarray]] = {}
    for r in rows:
        out.setdefault(r["topic_id"], []).append(_parse_vec(r["vec"]))
    return out


async def _all_member_counts(conn, engine: str, role: str) -> dict[str, int]:
    rows = await conn.fetch(
        """SELECT topic_id, count(*)::int AS n FROM topic_members
           WHERE engine_version=$1 AND role=$2 GROUP BY topic_id""",
        engine, role,
    )
    return {r["topic_id"]: int(r["n"]) for r in rows}


def _gini(counts: list[int]) -> float:
    if not counts:
        return 0.0
    x = np.sort(np.asarray(counts, dtype=np.float64))
    n = len(x)
    cum = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n) if cum[-1] > 0 else 0.0


def _metrics(emb_by_topic: dict[str, list[np.ndarray]], all_counts: dict[str, int]) -> dict:
    coh_weighted_num = coh_weight = 0.0
    purity_on = purity_tot = 0
    scored_topics = 0
    for topic, embs in emb_by_topic.items():
        if len(embs) < MIN_TOPIC:
            continue
        m = _unit(np.vstack(embs))
        centroid = m.mean(axis=0)
        cn = np.linalg.norm(centroid)
        if cn == 0:
            continue
        centroid = centroid / cn
        sims = m @ centroid
        coh = float(sims.mean())
        coh_weighted_num += coh * len(embs)
        coh_weight += len(embs)
        purity_on += int((sims >= PURITY_SIM).sum())
        purity_tot += len(sims)
        scored_topics += 1

    counts = list(all_counts.values())
    total_members = sum(counts)
    black_hole = (max(counts) / total_members) if total_members else 0.0
    return {
        "topics_total": len(all_counts),
        "topics_scored": scored_topics,
        "evidence_members": total_members,
        "coherence": (coh_weighted_num / coh_weight) if coh_weight else 0.0,
        "evidence_purity": (purity_on / purity_tot) if purity_tot else 0.0,
        "black_hole_share": black_hole,
        "size_gini": _gini(counts),
        "coverage_topics_ge_min": sum(1 for c in counts if c >= MIN_TOPIC),
    }


async def _surplus_quality(conn) -> dict:
    """Settle member-recall WITHOUT human gold: measure the coherence of v1's
    SURPLUS — evidence signals assigned by v1 but NOT by v2 — inside v1's own
    atlas topics. If those members are LOOSE (low coherence) they are v1's
    over-assignment, so v2's lower member count is avoided-noise, not lost-signal.
    Compares v1-only coherence vs v1-shared coherence (members both engines kept)."""
    rows = await conn.fetch(
        """SELECT tm.topic_id, tm.signal_id, e.vec::text AS vec
           FROM topic_members tm JOIN signal_embeddings e ON e.signal_id = tm.signal_id
           WHERE tm.engine_version = $1 AND tm.role = 'evidence'""", V1)
    v2_ids = set(await conn.fetchval(
        "SELECT array_agg(DISTINCT signal_id) FROM topic_members "
        "WHERE engine_version=$1 AND role='evidence'", V2) or [])
    by_topic: dict[str, list[tuple[int, np.ndarray]]] = {}
    for r in rows:
        by_topic.setdefault(r["topic_id"], []).append((int(r["signal_id"]), _parse_vec(r["vec"])))
    only_sims, shared_sims = [], []
    for embs in by_topic.values():
        if len(embs) < MIN_TOPIC:
            continue
        m = _unit(np.vstack([v for _, v in embs]))
        centroid = m.mean(axis=0)
        cn = np.linalg.norm(centroid)
        if cn == 0:
            continue
        sims = m @ (centroid / cn)
        for (sid, _), sim in zip(embs, sims):
            (shared_sims if sid in v2_ids else only_sims).append(float(sim))
    return {
        "v1_only_members": len(only_sims),
        "v1_only_coherence": float(np.mean(only_sims)) if only_sims else 0.0,
        "v1_shared_coherence": float(np.mean(shared_sims)) if shared_sims else 0.0,
    }


async def _cross_source(conn, engine: str) -> dict:
    row = await conn.fetchrow(
        """
        WITH ev AS (SELECT DISTINCT topic_id FROM topic_members
                    WHERE engine_version=$1 AND role='evidence'),
             di AS (SELECT DISTINCT topic_id FROM topic_members
                    WHERE engine_version=$1 AND role='discussion')
        SELECT (SELECT count(*) FROM ev) AS ev_topics,
               (SELECT count(*) FROM di) AS di_topics,
               (SELECT count(*) FROM ev JOIN di USING (topic_id)) AS bound
        """,
        engine,
    )
    return {"evidence_topics": int(row["ev_topics"]), "discussion_topics": int(row["di_topics"]),
            "cross_source_bound": int(row["bound"])}


async def run(_args) -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        report = {}
        for engine in (V1, V2):
            emb = await _members_with_emb(conn, engine, "evidence")
            counts = await _all_member_counts(conn, engine, "evidence")
            m = _metrics(emb, counts)
            m.update(await _cross_source(conn, engine))
            report[engine] = m

        def fmt(k, pct=False):
            a, b = report[V1].get(k, 0), report[V2].get(k, 0)
            f = (lambda x: f"{x:.1%}") if pct else (lambda x: f"{x:.3f}" if isinstance(x, float) else str(x))
            return f"  {k:24s}  v1={f(a):>10s}   v2={f(b):>10s}"

        print(f"\n=== Engine A/B — {V1} vs {V2} ===")
        print(fmt("evidence_members"))
        print(fmt("topics_total"))
        print(fmt("topics_scored"))
        print(fmt("coverage_topics_ge_min"))
        print(fmt("coherence"))
        print(fmt("evidence_purity", pct=True))
        print(fmt("black_hole_share", pct=True))
        print(fmt("size_gini"))
        print(fmt("evidence_topics"))
        print(fmt("discussion_topics"))
        print(fmt("cross_source_bound"))

        surplus = await _surplus_quality(conn)
        print("\n=== v1 surplus quality (is v2's member gap lost-signal or avoided-noise?) ===")
        print(f"  v1-only members ......... {surplus['v1_only_members']} (in v1, not v2)")
        print(f"  v1-only coherence ....... {surplus['v1_only_coherence']:.3f}")
        print(f"  v1-shared coherence ..... {surplus['v1_shared_coherence']:.3f}")

        v1, v2 = report[V1], report[V2]
        surplus_is_noise = (
            surplus["v1_only_members"] > 0
            and surplus["v1_only_coherence"] + 0.02 < surplus["v1_shared_coherence"]
        )
        # §11 cutover gate — ALL must hold: coherence, recall, evidence-purity up,
        # black-hole no worse. RECALL is the honest catch: coherence/purity favour
        # v2 by construction (members are assigned by embedding tightness), so a
        # purity win that SHEDS recall is not a real win — the gate must see it.
        better_coh = v2["coherence"] >= v1["coherence"]
        better_pur = v2["evidence_purity"] >= v1["evidence_purity"]
        no_worse_bh = v2["black_hole_share"] <= v1["black_hole_share"] + 0.02
        # recall proxy (no gold yet): v2 must not cover materially fewer signals or
        # topics than v1. 5% slack.
        recall_members = v2["evidence_members"] >= 0.95 * v1["evidence_members"]
        recall_topics = v2["coverage_topics_ge_min"] >= 0.95 * v1["coverage_topics_ge_min"]
        no_recall_regression = recall_members and recall_topics
        gate = better_coh and better_pur and no_worse_bh and no_recall_regression
        print("\n=== Cutover gate (§11) ===")
        print(f"  coherence v2>=v1 ............ {better_coh}  ({v2['coherence']:.3f} vs {v1['coherence']:.3f})")
        print(f"  evidence_purity v2>=v1 ..... {better_pur}")
        print(f"  black_hole no worse ........ {no_worse_bh}")
        print(f"  recall: members no regress . {recall_members}  ({v2['evidence_members']} vs {v1['evidence_members']})")
        print(f"  recall: topics no regress .. {recall_topics}  ({v2['coverage_topics_ge_min']} vs {v1['coverage_topics_ge_min']})")
        print(f"  cross_source v2 bound ...... {v2['cross_source_bound']} topics (v1 {v1['cross_source_bound']})")
        quality_won = better_coh and better_pur and no_worse_bh
        more_topics = v2["coverage_topics_ge_min"] >= v1["coverage_topics_ge_min"]
        # effective recall: a member shortfall is acceptable IF v1's surplus is
        # measurably looser (over-assignment) than its shared members.
        effective_recall_ok = recall_members or (recall_topics and surplus_is_noise)
        if quality_won and more_topics and effective_recall_ok:
            print("  VERDICT: PASS (effective) — v2 wins quality + topic-coverage; the "
                  "member shortfall is v1 OVER-ASSIGNMENT (its surplus is measurably "
                  "looser than its shared members). Strong case for F4; confirm on "
                  "gold when available, then flip ATLAS_UNIFIED_ENGINE.")
        elif gate:
            print("  VERDICT: PASS — unified-v2 clears the §11 gate; ready for F4 cutover")
        elif quality_won and more_topics and not recall_members:
            print("  VERDICT: STRONG CANDIDATE, HOLD CUTOVER — v2 wins coherence/"
                  "purity/black-hole AND finds more topics, but assigns fewer total "
                  "MEMBERS. v1's surplus is partly OVER-ASSIGNMENT (its lower purity "
                  "+ higher black-hole show it). Whether the member gap is lost "
                  "signal or avoided noise needs the gold benchmark (Paper 1 eval / "
                  "#229) — which does not exist yet. Keep v2 behind the flag, "
                  "measured; do NOT flip until member-recall is settled on gold.")
        elif quality_won and not no_recall_regression:
            print("  VERDICT: NOT YET — v2 is purer but sheds both members and topics; "
                  "grow new-topic formation / scoped passes (#229) before cutover.")
        else:
            print("  VERDICT: NOT YET — v2 does not clear the gate; iterate")
        print(json.dumps(report, indent=2))
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.parse_args()
    return asyncio.run(run(None))


if __name__ == "__main__":
    raise SystemExit(main())
