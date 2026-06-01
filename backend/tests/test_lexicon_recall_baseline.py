from __future__ import annotations

from pathlib import Path

from scripts.lexicon_recall_baseline import build_report


def test_build_report_computes_overall_and_per_role_recall():
    gold = [
        {"signal_id": 1, "consensus_role": "primary_evidence"},
        {"signal_id": 2, "consensus_role": "primary_evidence"},
        {"signal_id": 3, "consensus_role": "noise"},
        {"signal_id": 4, "consensus_role": "noise"},
    ]
    assigned_ids = {1, 3}

    report = build_report(
        gold=gold, assigned_ids=assigned_ids, gold_path=Path("gold.jsonl")
    )

    assert report["schema_version"] == "atlas-lexicon-recall-baseline-v1"
    assert report["overall"]["gold_rows"] == 4
    assert report["overall"]["with_lexicon_candidate"] == 2
    assert report["overall"]["candidate_recall"] == 0.5
    assert report["primary_evidence"]["gold_rows"] == 2
    assert report["primary_evidence"]["with_lexicon_candidate"] == 1
    assert report["primary_evidence"]["candidate_recall"] == 0.5


def test_build_report_orders_roles_by_gold_volume_descending():
    gold = [
        {"signal_id": 1, "consensus_role": "noise"},
        {"signal_id": 2, "consensus_role": "noise"},
        {"signal_id": 3, "consensus_role": "noise"},
        {"signal_id": 4, "consensus_role": "context"},
    ]
    report = build_report(gold=gold, assigned_ids=set(), gold_path=Path("g.jsonl"))

    roles = [r["role"] for r in report["by_role"]]
    assert roles == ["noise", "context"]
    assert report["by_role"][0]["candidate_recall"] == 0.0


def test_build_report_handles_missing_primary_evidence_role():
    gold = [{"signal_id": 1, "consensus_role": "noise"}]
    report = build_report(gold=gold, assigned_ids={1}, gold_path=Path("g.jsonl"))

    assert report["primary_evidence"]["gold_rows"] == 0
    assert report["primary_evidence"]["candidate_recall"] is None
