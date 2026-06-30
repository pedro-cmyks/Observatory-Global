"""Taxonomy revision — Codex 3rd-vote backfill (#204).

The overnight broad pass (phase_d_goldset) runs 3 annotators, but the Codex
annotator (ChatGPT-subscription, rate-metered) exhausts its quota mid-run,
leaving a window of 2-vote items (DeepSeek + OpenAI only). This script fills ONLY
those gaps: it loads the accumulated goldset, finds records missing a Codex label,
batches just those headlines to Codex under the v2 taxonomy, and merges the votes
back — recomputing gold (majority), agree_n, n_votes. Idempotent (re-runnable;
only touches missing-codex rows) and quota-safe (stops cleanly when Codex reports
its usage limit, persisting whatever it filled).

Run AFTER Codex quota resets (full window) for max coverage in one pass:
  python -m backend.scripts.ensemble.phase_d_codex_backfill [--chunk 30] [--max-chunks N]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from backend.scripts.ensemble.model_clients import call_codex, extract_json
from backend.scripts.ensemble.phase_d_goldset import _parse, _prompt

CAND = "docs/research/taxonomy-revision/candidate-v2.json"
OUT = "docs/research/taxonomy-revision/goldset.json"
ANNS = ("deepseek", "openai", "codex")


def _recompute(rec: dict) -> None:
    """Recompute gold/agree_n/n_votes from the 3 annotator fields in place."""
    votes = [rec.get(a) for a in ANNS if rec.get(a)]
    if not votes:
        return
    c = Counter(votes)
    gold, top = c.most_common(1)[0]
    rec["gold"], rec["agree_n"], rec["n_votes"] = gold, top, len(votes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=30)
    ap.add_argument("--max-chunks", type=int, default=0, help="0 = no cap (until quota)")
    args = ap.parse_args()

    with open(CAND) as f:
        cand = json.load(f)
    valid = {c["slug"] for c in cand["categories"]} | {"OUT_OF_SCOPE"}
    with open(OUT) as f:
        data = json.load(f)
    records = data["records"]

    # the gaps: records the runner labeled with <3 votes (codex missing)
    gaps = [r for r in records if not r.get("codex")]
    print(f"goldset n={len(records)} | codex-missing (2-vote) gaps: {len(gaps)}")
    if not gaps:
        print("nothing to backfill — base already uniformly 3-vote.")
        return 0

    # codex labels per headline (batched); a chunk maps n->record via local index
    chunks = [gaps[i:i + args.chunk] for i in range(0, len(gaps), args.chunk)]
    filled, quota_hit = 0, False
    for ci, ch in enumerate(chunks):
        if args.max_chunks and ci >= args.max_chunks:
            print(f"stopping at --max-chunks={args.max_chunks}")
            break
        # phase_d _prompt expects items with an "n" key (1-based within the chunk)
        local = [{"n": j + 1, "headline": r["headline"]} for j, r in enumerate(ch)]
        try:
            labels = _parse(call_codex(_prompt(cand, local)), valid)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)[:90]
            print(f"  chunk{ci} codex FAIL {msg}", file=sys.stderr)
            if "usage limit" in msg.lower():
                quota_hit = True
                print("  codex quota exhausted — persisting partial backfill and stopping.")
                break
            continue
        for j, r in enumerate(ch):
            sl = labels.get(j + 1)
            if sl:
                r["codex"] = sl
                _recompute(r)
                filled += 1
        print(f"  chunk {ci+1}/{len(chunks)} done ({filled} filled so far)")

    # recompute base-level stats + persist
    tot_unan = sum(1 for r in records if r.get("agree_n") == r.get("n_votes") == len(ANNS))
    tot_oos = sum(1 for r in records if r.get("gold") == "OUT_OF_SCOPE")
    tot_emb = sum(1 for r in records if r.get("embedded"))
    data.update({"n": len(records), "unanimous": tot_unan, "oos_gold": tot_oos,
                 "embedded": tot_emb})
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    remaining = sum(1 for r in records if not r.get("codex"))
    print(f"\nbackfilled {filled} codex votes. remaining 2-vote: {remaining}.")
    print(f"base: n={len(records)} unanimous(3/3)={tot_unan} oos={tot_oos} embedded={tot_emb}")
    if quota_hit and remaining:
        print("re-run after the next codex quota reset to finish the remainder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
