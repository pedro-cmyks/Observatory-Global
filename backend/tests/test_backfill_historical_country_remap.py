"""Freeze the archive-table remap plan logic (FIPS-disaster stock heal).

Locks the invariants that make the historical backfill safe: topological
pair ordering (chains never double-hop), collision detection against live
residents, the merge path, ledger idempotency, and the write-boundary
correction+merge in historical_sync.
"""

import pytest

from app.services.country_corrections import load_remap
from scripts.backfill_historical_country_remap import (
    ordered_pairs,
    plan_daily,
    plan_evidence,
    row_sig,
)
from scripts.historical_sync import apply_country_corrections


# ── ordered_pairs ────────────────────────────────────────────────────────────

def test_ordered_pairs_covers_full_remap_and_respects_chains():
    remap = load_remap()
    order = ordered_pairs(remap)
    assert len(order) == len(remap)
    assert set(order) == set(remap.items())
    idx = {pair: i for i, pair in enumerate(order)}
    # BP→SB→PM→PA→PY: each target space must be evacuated first
    assert idx[("PA", "PY")] < idx[("PM", "PA")]
    assert idx[("PM", "PA")] < idx[("SB", "PM")]
    assert idx[("SB", "PM")] < idx[("BP", "SB")]
    # MG→MN→MC→MO
    assert idx[("MC", "MO")] < idx[("MN", "MC")]
    assert idx[("MN", "MC")] < idx[("MG", "MN")]
    # GK→GG→GE, AY→AQ→AS, TP→ST→LC, RM→MH→MS, VQ→VI→VG, TT→TL→TK,
    # RN→MF→YT, EK→GQ→GU
    for late, mid in [("GK", "GG"), ("AY", "AQ"), ("TP", "ST"), ("RM", "MH"),
                      ("VQ", "VI"), ("TT", "TL"), ("RN", "MF"), ("EK", "GQ")]:
        assert idx[(mid, remap[mid])] < idx[(late, mid)]


def test_ordered_pairs_raises_on_cycle():
    with pytest.raises(ValueError, match="cycle"):
        ordered_pairs({"A": "B", "B": "A"})


# ── plan_daily ───────────────────────────────────────────────────────────────

def _row(cc, topic="t", day="2026-05-10", family="gdelt", n=10, **over):
    row = {
        "day": day, "topic_slug": topic, "country_code": cc,
        "source_family": family, "signal_class": "news",
        "model_version": "atlas-hist-v1",
        "signal_count": n, "avg_sentiment": None, "sentiment_coverage": 0.0,
        "topic_coverage": 0.0, "entity_coverage": 0.0,
        "local_voice_ratio": None, "source_diversity": None,
        "evidence_sample_count": 0,
    }
    row.update(over)
    return row


def test_plan_simple_move():
    ops = plan_daily([_row("LS")], set(), load_remap())
    assert len(ops) == 1
    assert ops[0]["op"] == "move"
    assert (ops[0]["old"], ops[0]["new"]) == ("LS", "LB")
    assert ops[0]["pk"]["country_code"] == "LS"


def test_plan_chain_never_double_hops_or_false_merges():
    # A Panama row (stored PM) and a Paraguay row (stored PA) at the SAME
    # (day, topic, family, class): PA must leave for PY before PM arrives,
    # producing two moves and NO merge.
    rows = [_row("PM", n=5), _row("PA", n=7)]
    ops = plan_daily(rows, set(), load_remap())
    assert [op["op"] for op in ops] == ["move", "move"]
    moves = {(op["old"], op["new"]) for op in ops}
    assert moves == {("PA", "PY"), ("PM", "PA")}
    # order: PA evacuates first
    assert (ops[0]["old"], ops[0]["new"]) == ("PA", "PY")


def test_plan_collision_merges_into_existing_genuine_row():
    genuine_lb = _row("LB", n=4, sentiment_coverage=0.5,
                      evidence_sample_count=1)
    misfiled_ls = _row("LS", n=36, sentiment_coverage=0.25,
                       evidence_sample_count=3)
    ops = plan_daily([genuine_lb, misfiled_ls], set(), load_remap())
    assert len(ops) == 1
    op = ops[0]
    assert op["op"] == "merge"
    assert (op["old"], op["new"]) == ("LS", "LB")
    assert op["source_row"]["signal_count"] == 36
    assert op["target_before"]["signal_count"] == 4
    assert op["target_after"]["signal_count"] == 40
    assert op["target_after"]["sentiment_coverage"] == pytest.approx(
        (0.5 * 4 + 0.25 * 36) / 40)
    assert op["target_after"]["evidence_sample_count"] == 4


def test_plan_chain_landing_then_merge_with_unplanned_resident():
    # An ex-PM row lands at PA-space where a ledger-excluded resident (from a
    # previous run) already sits → merge, not a PK crash; and the excluded
    # resident itself is never re-planned (no PA→PY double hop).
    resident = _row("PA", n=9)  # already healed in a previous run
    excluded = {row_sig(resident)}
    pm_row = _row("PM", n=5)
    ops = plan_daily([resident, pm_row], excluded, load_remap())
    assert len(ops) == 1
    op = ops[0]
    assert op["op"] == "merge"
    assert (op["old"], op["new"]) == ("PM", "PA")
    assert op["target_after"]["signal_count"] == 14


def test_plan_rows_with_distinct_pk_dimensions_never_collide():
    rows = [_row("LS", topic="a"), _row("LS", topic="b"),
            _row("LS", day="2026-05-11", topic="a"),
            _row("LS", family="unknown", topic="a")]
    ops = plan_daily(rows, set(), load_remap())
    assert len(ops) == 4
    assert all(op["op"] == "move" for op in ops)


def test_plan_second_run_is_empty_after_ledger_exclusion():
    # post-run state: ex-LS row now at LB (LB not a key → never a candidate),
    # ex-PM row now at PA (a key → must be ledger-excluded)
    healed_pa = _row("PA", n=5)
    ops = plan_daily([_row("LB"), healed_pa], {row_sig(healed_pa)},
                     load_remap())
    assert ops == []


# ── plan_evidence ────────────────────────────────────────────────────────────

def test_plan_evidence_moves_and_liechtenstein_split():
    rows = [
        {"sample_id": "a", "country_code": "LS",
         "headline": "Beirut port explosion anniversary"},
        {"sample_id": "b", "country_code": "LS",
         "headline": "Vaduz castle reopens"},
        {"sample_id": "c", "country_code": "KV", "headline": "Pristina vote"},
        {"sample_id": "d", "country_code": "US", "headline": "not a key"},
    ]
    ops = plan_evidence(rows, set())
    got = {(op["sample_id"], op["old"], op["new"]) for op in ops}
    assert got == {("a", "LS", "LB"), ("b", "LS", "LI"), ("c", "KV", "XK")}


def test_plan_evidence_excludes_ledgered_ids():
    rows = [{"sample_id": "a", "country_code": "PA", "headline": None}]
    assert plan_evidence(rows, {"a"}) == []
    ops = plan_evidence(rows, set())
    assert [(op["old"], op["new"]) for op in ops] == [("PA", "PY")]


# ── historical_sync write boundary ───────────────────────────────────────────

def _artifact_row(cc, family="gdelt", n=10, **over):
    row = {
        "day": "2026-05-10", "topic_slug": "t", "country_code": cc,
        "source_family": family, "signal_class": "news",
        "model_version": "atlas-hist-v1", "signal_count": n,
        "avg_sentiment": None, "sentiment_coverage": 0.0,
        "topic_coverage": 0.0, "entity_coverage": 0.0,
        "local_voice_ratio": None, "source_diversity": None,
        "evidence_sample_count": 0,
    }
    row.update(over)
    return row


def test_sync_corrects_gdelt_lane_rows_at_write():
    out = apply_country_corrections(
        [_artifact_row("LS"), _artifact_row("RB", family="unknown")])
    assert [r["country_code"] for r in out] == ["LB", "RS"]


def test_sync_leaves_real_outlet_families_untouched():
    out = apply_country_corrections(
        [_artifact_row("PA", family="independent"),
         _artifact_row("MN", family="press")])
    assert [r["country_code"] for r in out] == ["PA", "MN"]


def test_sync_merges_artifact_rows_colliding_after_correction():
    # a misfiled LS aggregate + a genuine override-path LB aggregate in the
    # same artifact must not race for one upsert PK
    out = apply_country_corrections(
        [_artifact_row("LS", n=30, sentiment_coverage=0.1),
         _artifact_row("LB", n=10, sentiment_coverage=0.5)])
    assert len(out) == 1
    assert out[0]["country_code"] == "LB"
    assert out[0]["signal_count"] == 40
    assert out[0]["sentiment_coverage"] == pytest.approx(
        (0.1 * 30 + 0.5 * 10) / 40)


def test_sync_does_not_merge_across_pk_dimensions():
    out = apply_country_corrections(
        [_artifact_row("LS", n=30),
         _artifact_row("LB", n=10, signal_class="press")])
    assert len(out) == 2
