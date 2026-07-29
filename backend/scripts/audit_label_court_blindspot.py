"""LABEL-COURT BLIND-SPOT AUDIT (read-only harness, 2026-07-29).

Context: finder-v2 (docs/research/recall-229/2026-07-29-sibling-finder-v2-
measurement.md) found active topics whose labels contradict their own evidence
(dt-3188 'Wildfire in Halkidiki' = Chania workshop explosion; dt-1226
'Crimea-Congo Hemorrhagic Fever' = Spanish femicide). The label court
(label_court.py, DeepSeek temp-0 -> dynamic_topics.label_status) exists to
catch exactly this. This harness measures WHETHER IT DOES: sample active
topics stratified by label_status, dump each label + up to 10 member headlines
(the SAME receipt lane the court reads), for an independent hand-judgment into
describes / partially / contradicts. The confusion matrix court-verdict x
hand-judgment is computed downstream in the artifact.

Strictly read-only: SELECT only, no LLM calls, no writes to any table.

Pre-registered (BEFORE any sample was drawn — see the artifact for the full
registration):
  - strata: entailed 30 / partial 15 / failed 15 (entailed oversampled — the
    blind-spot question lives in the court's PASS stamp);
  - umbrellas EXCLUDED (family-membership bar is a different court question;
    the entailed stratum has 0 umbrellas anyway);
  - deterministic sample: ORDER BY md5(id || seed);
  - receipts: label_court's own _RECEIPTS_SQL shape, LIMIT 10, HTML-decoded.

Run (repo root, M1 env):
  DATABASE_URL=... backend/.venv/bin/python backend/scripts/audit_label_court_blindspot.py \
      --out docs/research/label-court/2026-07-29-court-blindspot-samples.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys
from pathlib import Path

import asyncpg

# Same receipt lane the court reads (label_court._RECEIPTS_SQL), LIMIT param.
_RECEIPTS_SQL = """
    SELECT s.headline, s.country_code
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1 AND tm.role = 'evidence'
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code
    ORDER BY max(s.timestamp) DESC
    LIMIT $2
"""
_RECEIPTS_FALLBACK_SQL = """
    SELECT s.headline, s.country_code
    FROM dynamic_topic_members dtm
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) AS sid
    JOIN signals_v2 s ON s.id = sid
    WHERE dtm.dynamic_topic_id = $1
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code
    ORDER BY max(s.timestamp) DESC
    LIMIT $2
"""

_SAMPLE_SQL = """
    SELECT id, label, label_status, label_checked_at, agg_n_signals
    FROM dynamic_topics
    WHERE state = 'active' AND label IS NOT NULL
      AND NOT is_umbrella AND label_status = $1
    ORDER BY md5(id::text || $2)
    LIMIT $3
"""

STRATA = (("entailed", 30), ("partial", 15), ("failed", 15))
# Named witness set from the finder-v2 measurement — always included, tagged.
WITNESSES = (3188, 1226, 2944)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only label-court blind-spot sampler.")
    ap.add_argument("--out", required=True, help="samples JSONL path")
    ap.add_argument("--seed", default="blindspot-2026-07-29", help="sample seed")
    ap.add_argument("--receipts", type=int, default=10)
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr)
        sys.exit(2)

    conn = await asyncpg.connect(db)
    out: list[dict] = []
    try:
        seen: set[int] = set()
        for status, n in STRATA:
            rows = await conn.fetch(_SAMPLE_SQL, status, args.seed, n)
            for r in rows:
                seen.add(int(r["id"]))
                out.append(dict(r) | {"witness": False})
        # Force-include witnesses (non-umbrella actives; skip if already drawn)
        wrows = await conn.fetch(
            "SELECT id, label, label_status, label_checked_at, agg_n_signals "
            "FROM dynamic_topics WHERE id = ANY($1::int[]) "
            "AND state='active' AND NOT is_umbrella", list(WITNESSES))
        for r in wrows:
            if int(r["id"]) not in seen:
                out.append(dict(r) | {"witness": True})

        for rec in out:
            dyn_id = int(rec["id"])
            topic_id = f"dynamic-topic-{dyn_id}"
            rows = await conn.fetch(_RECEIPTS_SQL, topic_id, args.receipts)
            lane = "topic_members"
            if not rows:
                rows = await conn.fetch(_RECEIPTS_FALLBACK_SQL, dyn_id, args.receipts)
                lane = "emergent_sample"
            rec["receipt_lane"] = lane
            rec["receipts"] = [
                {"headline": html.unescape(r["headline"] or ""),
                 "country_code": r["country_code"]} for r in rows]
            rec["label_checked_at"] = (
                rec["label_checked_at"].isoformat() if rec["label_checked_at"] else None)
    finally:
        await conn.close()

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    by_status: dict[str, int] = {}
    for rec in out:
        by_status[rec["label_status"]] = by_status.get(rec["label_status"], 0) + 1
    thin = sum(1 for rec in out if len(rec["receipts"]) < 2)
    print(f"wrote {len(out)} samples -> {path}  strata={by_status}  thin(<2 receipts)={thin}")


if __name__ == "__main__":
    asyncio.run(main())
