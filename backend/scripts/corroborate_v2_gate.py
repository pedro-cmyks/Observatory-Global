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

        data = json.loads(FIXTURE.read_text())
        base = sum(c["corroborating"] for c in data["claims"])
        now_total = 0
        for c in data["claims"]:
            res = await corroborate_claim(
                headline=c["headline"], country=c["country"], conn=conn,
                embed_fn=_embed_fn)
            v = res.get("verdict") or {}
            n = v.get("corroborating", 0)
            now_total += n
            print(f"  {n:>3} (was {c['corroborating']:>3})  {c['headline'][:70]}")
        drop = 0.0 if base == 0 else (base - now_total) / base
        print(f"\nG-NO-REGRESION: frozen={base} now={now_total} "
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
