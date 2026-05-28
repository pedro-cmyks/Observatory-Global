#!/usr/bin/env python3
"""Build the scope-typed multi-vendor consensus training corpus.

Merges the per-model LLM annotation files (output of `llm_annotator.py`)
into one row per signal carrying, for every signal:
  - the per-model votes (decision / scope / evidence_role),
  - the LLM majority consensus (decision, scope, evidence_role) with the
    agreement count,
  - the human gold labels (replicated in every annotation row as `gold_*`),
  - a binary `is_evidence` target for the Phase B scope gate
    (consensus correct -> 1, consensus incorrect -> 0, else null).

This is roadmap Phase A step 2 ("persist consensus labels with scope +
evidence_role"). It is the bridge artifact the Phase B embedding probe and
any later learned classifier train on. Zero API cost — pure local merge.

Schema version: atlas-consensus-corpus-v1
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "atlas-consensus-corpus-v1"

# A signal needs at least this many LLM votes agreeing on the modal decision
# to be treated as a consensus label (7 annotators -> simple majority is 4).
DEFAULT_MAJORITY = 4

# Feature/context fields copied verbatim from the annotation rows.
CONTEXT_FIELDS = (
    "headline",
    "source_lang",
    "country_code",
    "source_family",
    "source_name",
    "assigned_topic_slug",
    "assigned_topic_label",
    "sample_bucket",
)
GOLD_FIELDS = (
    "gold_decision",
    "gold_scope",
    "gold_evidence_role",
    "gold_error_type",
    "gold_topic_slug",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _mode_with_count(values: list[str]) -> tuple[str | None, int]:
    """Return (modal_value, count). Ties resolved by Counter insertion order
    (Python's Counter.most_common is stable for equal counts)."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None, 0
    val, count = Counter(clean).most_common(1)[0]
    return val, count


def build_corpus(input_dir: Path, majority: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files = sorted(glob.glob(str(input_dir / "*stratified-256*.jsonl")))
    if not files:
        raise SystemExit(f"no annotation files matched in {input_dir}")

    # model_provenance -> {signal_id -> row}
    per_model: dict[str, dict[int, dict[str, Any]]] = {}
    for f in files:
        rows = _read_jsonl(Path(f))
        prov = rows[0]["annotator_provenance"]
        # `resume` runs can append duplicate signal_ids; last write wins.
        by_id = {int(r["signal_id"]): r for r in rows}
        per_model[prov] = by_id

    models = sorted(per_model)
    common = set.intersection(*(set(m.keys()) for m in per_model.values()))

    corpus: list[dict[str, Any]] = []
    for sid in sorted(common):
        # Any model's row carries the shared context + human gold.
        ref = per_model[models[0]][sid]

        votes: dict[str, dict[str, Any]] = {}
        decisions: list[str] = []
        scopes: list[str] = []
        roles: list[str] = []
        for prov in models:
            r = per_model[prov][sid]
            d = r.get("annotator_decision")
            votes[prov] = {
                "decision": d,
                "scope": r.get("annotator_scope"),
                "evidence_role": r.get("annotator_evidence_role"),
                "confidence": r.get("annotator_confidence"),
            }
            if d is not None:
                decisions.append(d)
            if r.get("annotator_scope") is not None:
                scopes.append(r["annotator_scope"])
            if r.get("annotator_evidence_role") is not None:
                roles.append(r["annotator_evidence_role"])

        decision_counts = dict(Counter(decisions))
        mode_decision, mode_count = _mode_with_count(decisions)
        consensus_decision = mode_decision if mode_count >= majority else None
        consensus_scope, _ = _mode_with_count(scopes)
        consensus_role, _ = _mode_with_count(roles)

        if consensus_decision == "correct":
            is_evidence: int | None = 1
        elif consensus_decision == "incorrect":
            is_evidence = 0
        else:  # partial / unclear / no_majority -> excluded from binary target
            is_evidence = None

        row: dict[str, Any] = {"signal_id": sid}
        for k in CONTEXT_FIELDS:
            row[k] = ref.get(k)
        # Atlas v2's own assignment confidence + matched-term count — free
        # baseline features for the Phase B probe (does Atlas's own score
        # already separate evidence from context?).
        row["atlas_confidence"] = ref.get("confidence")
        ev = ref.get("evidence") or {}
        matched = ev.get("matched_terms") if isinstance(ev, dict) else None
        row["atlas_matched_terms"] = len(matched) if isinstance(matched, list) else None
        for k in GOLD_FIELDS:
            row[f"human_{k[5:]}"] = ref.get(k)  # gold_decision -> human_decision
        row.update(
            {
                "llm_votes": votes,
                "llm_decision_counts": decision_counts,
                "llm_consensus_decision": consensus_decision,
                "llm_consensus_agreement": mode_count,
                "llm_n_voters": len(decisions),
                "llm_consensus_scope": consensus_scope,
                "llm_consensus_evidence_role": consensus_role,
                "is_evidence": is_evidence,
                "schema_version": SCHEMA_VERSION,
            }
        )
        corpus.append(row)

    # ---- summary ----
    agree_hist = Counter(r["llm_consensus_agreement"] for r in corpus)
    consensus_decisions = Counter(
        r["llm_consensus_decision"] or "no_majority" for r in corpus
    )
    is_ev = Counter(
        "evidence" if r["is_evidence"] == 1 else "not_evidence" if r["is_evidence"] == 0 else "ambiguous"
        for r in corpus
    )
    # Human gold is NOT present in the stratified-256 annotator input
    # (`gold_*` fields are null placeholders — the LLM panel judged
    # independently). Pedro's human labels live separately in the reviewed
    # batch files and only partially overlap this sample, so human-vs-consensus
    # is reported elsewhere, not here.
    human_decided = sum(
        1 for r in corpus if r.get("human_decision") in {"correct", "incorrect"}
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "models": models,
        "n_models": len(models),
        "majority_threshold": majority,
        "n_signals_common": len(corpus),
        "consensus_agreement_histogram": dict(sorted(agree_hist.items())),
        "consensus_decision_counts": dict(consensus_decisions),
        "is_evidence_balance": dict(is_ev),
        "n_rows_with_human_gold": human_decided,
    }
    return corpus, summary


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build multi-vendor consensus training corpus.")
    base = Path("docs/research/atlas-paper/phase-1-validation")
    p.add_argument("--input-dir", type=Path, default=base / "labels/llm-annotator")
    p.add_argument("--out", type=Path, default=base / "labels/consensus/2026-05-28-7llm-consensus-corpus.jsonl")
    p.add_argument("--summary", type=Path, default=base / "labels/consensus/2026-05-28-7llm-consensus-corpus.summary.json")
    p.add_argument("--majority", type=int, default=DEFAULT_MAJORITY)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    corpus, summary = build_corpus(args.input_dir, args.majority)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for r in corpus:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nwrote {len(corpus)} rows -> {args.out}")


if __name__ == "__main__":
    main()
