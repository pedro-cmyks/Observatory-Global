"""Corroborate-v2 pre-registered gate (spec 2026-08-11-corroborate-v2-design.md).

--freeze : sample up to 20 claims that TODAY produce status='corroborated' via
           corroborate_claim against live prod; save claim + counts to the
           fixture. Run BEFORE any corroborate-v2 behavior change.
--check  : replay the frozen claims with current code; PASS iff the total
           corroborating count across the sample drops <=15% vs frozen
           (G-NO-REGRESION). Per-claim deltas reported either way.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE = Path(__file__).resolve().parents[2] / (
    "docs/research/corroborate-v2/2026-08-11-regression-sample.json")

# The population the gate protects: dossier receipts come from SERVED
# threads, so the sample is one recent evidence headline per top ACTIVE
# dynamic topic (by lifetime volume, non-junk, court-entailed). These claims
# have in-corpus coverage by construction, so 'corroborated' arrives through
# the Atlas lanes even when DOC 2.0 flakes. (A first-per-country draw over
# raw signals froze only 3 corroborated claims out of 40 — niche local
# stories with no corroborating coverage anywhere. Honest, but a base of 3
# cannot carry a 15% bar.)
_TOP_TOPICS_SQL = """
    SELECT id, label
    FROM dynamic_topics
    WHERE state = 'active'
      AND COALESCE(is_junk, false) = false
      AND COALESCE(is_umbrella, false) = false
      AND label_status = 'entailed'
    ORDER BY agg_n_signals DESC, id
    LIMIT 40
"""

_TOPIC_RECEIPT_SQL = """
    SELECT s.headline, s.country_code, s.source_lang
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1
      AND tm.role = 'evidence'
      AND s.headline IS NOT NULL
      AND length(s.headline) BETWEEN 40 AND 200
    ORDER BY tm.assigned_at DESC
    LIMIT 1
"""


async def _run(mode: str) -> int:
    import asyncpg
    from app.services.corroboration import corroborate_claim, extract_claim_terms
    from app.services.research_semantic import embed_query

    # Same lane wiring as the router — without embed_fn the atlas_hot
    # semantic lane (the strongest in-corpus corroborator) never runs and
    # the freeze under-measures by construction.
    def _embed_fn(text):
        return asyncio.to_thread(embed_query, text)

    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        if mode == "freeze":
            topics = await conn.fetch(_TOP_TOPICS_SQL)
            rows = []
            for t in topics:
                r = await conn.fetchrow(
                    _TOPIC_RECEIPT_SQL, f"dynamic-topic-{t['id']}")
                if r:
                    rows.append(r)
            frozen = []
            for r in rows:
                # The claim tokenizer is Latin-only today; a Greek/Hindi
                # headline yields an empty query in every lane. The gate
                # samples the population the organ can actually measure —
                # a known limitation, not the regression surface.
                if len(extract_claim_terms(r["headline"])["terms"]) < 4:
                    continue
                res = await corroborate_claim(
                    headline=r["headline"], country=r["country_code"],
                    conn=conn, embed_fn=_embed_fn)
                v = res.get("verdict") or {}
                if v.get("status") == "corroborated":
                    frozen.append({
                        "headline": r["headline"],
                        "country": r["country_code"],
                        "source_lang": r["source_lang"],
                        "corroborating": v.get("corroborating", 0),
                    })
                    print(f"  [{len(frozen):>2}] {v.get('corroborating'):>3}  "
                          f"{r['headline'][:70]}")
                if len(frozen) >= 20:
                    break
            FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE.write_text(json.dumps(
                {"frozen_at": "2026-08-11", "claims": frozen}, indent=2))
            print(f"frozen {len(frozen)} corroborated claims -> {FIXTURE}")
            return 0 if len(frozen) >= 15 else 1

        # PAIRED check (instrument v2, pre-registered in the gate artifact
        # BEFORE this run): run-1 measured freeze-time-vs-check-time and the
        # 22.8% "drop" was dominated by DOC 2.0 availability variance between
        # the two moments (Udaipur 15->0 and Infantino 7->0 both replayed at
        # their frozen counts minutes later). This design fetches each frozen
        # claim ONCE and scores the SAME match pool under the frozen v1 rules
        # and the v2 rules — the only difference left is the rules. The 15%
        # bar is UNCHANGED.
        from app.services.corroboration import (
            SAME_EVENT_TERM_RECALL, SAME_EVENT_SIMILARITY,
            CORROBORATE_TERM_RECALL, extract_claim_terms as _ect,
            figure_relation, term_recall,
        )
        import re as _re

        _V1_FIGURE_RE = _re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?")

        def _v1_figure(text):
            """Frozen v1 extract_figure (pre-d16464a3): naive comma-strip."""
            if not text:
                return None
            m = _V1_FIGURE_RE.search(text)
            if not m:
                return None
            try:
                return float(m.group(0).replace(",", ""))
            except ValueError:
                return None

        def _v1_relation(claim_terms, claim_figure, headline, similarity):
            """Frozen v1 classify_relation (pre-ca3f4156): no anchor guard,
            no locale, no aging (aging lived nowhere in v1)."""
            recall = term_recall(claim_terms, headline)
            same_event = recall >= SAME_EVENT_TERM_RECALL or (
                similarity is not None and similarity >= SAME_EVENT_SIMILARITY)
            fig_rel = figure_relation(claim_figure, _v1_figure(headline))
            if same_event and fig_rel == "contradicts":
                return "contradicts"
            if fig_rel == "corroborates" and same_event:
                return "corroborates"
            if recall >= CORROBORATE_TERM_RECALL or (
                    similarity is not None
                    and similarity >= SAME_EVENT_SIMILARITY):
                return "corroborates"
            return "context"

        data = json.loads(FIXTURE.read_text())
        old_total = new_total = 0
        rule_kills = {"template": 0, "aged": 0, "other": 0, "gained": 0}
        for c in data["claims"]:
            res = await corroborate_claim(
                headline=c["headline"], country=c["country"], conn=conn,
                embed_fn=_embed_fn)
            pool = (res["corroborating"] + res["contradicting"]
                    + res["context"] + res.get("template_matches", []))
            terms = _ect(c["headline"])["terms"]
            claim_fig = _v1_figure(c["headline"])
            old_n = sum(
                1 for m in pool
                if _v1_relation(terms, claim_fig, m.get("snippet"),
                                m.get("similarity")) == "corroborates")
            new_n = (res.get("verdict") or {}).get("corroborating", 0)
            old_total += old_n
            new_total += new_n
            for m in pool:
                v1 = _v1_relation(terms, claim_fig, m.get("snippet"),
                                  m.get("similarity"))
                if v1 == "corroborates" and m["relation"] == "template_match":
                    rule_kills["template"] += 1
                elif v1 == "corroborates" and m.get("aged") \
                        and m["relation"] == "corroborates":
                    rule_kills["aged"] += 1
                elif v1 == "corroborates" and not m.get("aged") \
                        and m["relation"] != "corroborates":
                    rule_kills["other"] += 1
                elif v1 != "corroborates" and m["relation"] == "corroborates" \
                        and not m.get("aged"):
                    rule_kills["gained"] += 1
            print(f"  v1={old_n:>3} v2={new_n:>3} (frozen {c['corroborating']:>3})"
                  f"  {c['headline'][:64]}")
        drop = 0.0 if old_total == 0 else (old_total - new_total) / old_total
        print(f"\nrule attribution: {rule_kills}")
        print(f"G-NO-REGRESION (paired): v1={old_total} v2={new_total} "
              f"drop={drop:.1%} (bar <=15%)")
        print("PASS" if drop <= 0.15 else "FAIL")
        return 0 if drop <= 0.15 else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.exit(asyncio.run(_run("freeze" if a.freeze else "check")))
