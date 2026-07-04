#!/usr/bin/env python3
"""Gold-growth consensus merge (2026-07-04 hard-topic pass).

Takes the two annotator vote files (DeepSeek + gpt-4o-mini) over the
hard-topic decision-band candidates, keeps rows where BOTH vendors agree
decisively (correct/correct -> is_evidence=1, incorrect/incorrect -> 0;
anything with partial/unclear or a split is DROPPED — 2-vendor unanimity
is the price of only having two voters vs the original corpus's 3-vendor
majority), and emits rows in the atlas-consensus-corpus-v1 shape so
train_scope_gate can consume [original 5k + growth] transparently.

Provenance: schema_version atlas-consensus-corpus-v1-goldgrowth-0704 so
the added rows are always distinguishable from the frozen 5k artifact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_votes(path: Path) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out[int(r["signal_id"])] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", type=Path, default=Path("/tmp/goldgrowth/candidates.jsonl"))
    ap.add_argument("--votes-a", type=Path, default=Path("/tmp/goldgrowth/votes-deepseek.jsonl"))
    ap.add_argument("--votes-b", type=Path, default=Path("/tmp/goldgrowth/votes-gpt4omini.jsonl"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    cands = [json.loads(l) for l in args.candidates.read_text(encoding="utf-8").splitlines() if l.strip()]
    va = load_votes(args.votes_a)
    vb = load_votes(args.votes_b)

    kept, dropped_split, dropped_soft, missing = [], 0, 0, 0
    pos_by_topic: dict[str, list[int]] = {}
    for c in cands:
        sid = int(c["signal_id"])
        a, b = va.get(sid), vb.get(sid)
        if not a or not b:
            missing += 1
            continue
        da = a.get("annotator_decision")
        db = b.get("annotator_decision")
        if da not in ("correct", "incorrect") or db not in ("correct", "incorrect"):
            dropped_soft += 1  # partial/unclear from either vendor
            continue
        if da != db:
            dropped_split += 1
            continue
        is_evidence = 1 if da == "correct" else 0
        slug = c["assigned_topic_slug"]
        pos_by_topic.setdefault(slug, [0, 0])
        pos_by_topic[slug][0] += is_evidence
        pos_by_topic[slug][1] += 1
        kept.append({
            "signal_id": c["signal_id"],
            "headline": c["headline"],
            "source_lang": c.get("source_lang"),
            "country_code": c.get("country_code"),
            "source_family": c.get("source_family", "gdelt"),
            "source_name": c.get("source_name"),
            "assigned_topic_slug": slug,
            "assigned_topic_label": c["assigned_topic_label"],
            "sample_bucket": "goldgrowth_hard_band_0704",
            "atlas_confidence": c.get("atlas_confidence"),
            "atlas_matched_terms": c.get("atlas_matched_terms"),
            "human_decision": None, "human_scope": None,
            "human_evidence_role": None, "human_error_type": None,
            "human_topic_slug": None,
            "llm_votes": {
                a.get("annotator_provenance", "deepseek"): {"decision": da},
                b.get("annotator_provenance", "gpt4omini"): {"decision": db},
            },
            "llm_decision_counts": {da: 2},
            "llm_consensus_decision": da,
            "llm_consensus_agreement": 2,
            "llm_n_voters": 2,
            "llm_consensus_scope": a.get("annotator_scope"),
            "llm_consensus_evidence_role": a.get("annotator_evidence_role"),
            "is_evidence": is_evidence,
            "schema_version": "atlas-consensus-corpus-v1-goldgrowth-0704",
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"candidates {len(cands)} | kept {len(kept)} "
          f"(unanimous) | split {dropped_split} | soft {dropped_soft} | missing {missing}")
    print(f"{'topic':34} {'new_pos':>7} {'new_n':>6}")
    for slug, (p, n) in sorted(pos_by_topic.items()):
        print(f"{slug:34} {p:7d} {n:6d}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
