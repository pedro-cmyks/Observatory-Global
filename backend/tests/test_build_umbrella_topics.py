import asyncio
import inspect

import numpy as np
import pytest

from scripts import build_umbrella_topics as _bu
from scripts.build_umbrella_topics import (
    UmbrellaGroupingUnavailable,
    _resolve_event_groups,
    _shared_actor_edges,
    _union_find_groups,
    _UMBRELLA_UPSERT_SQL,
    _LABEL_OR_FAMILY_CHANGED,
)

# Two topics whose centroids clear the 0.95 same-event cut → the deterministic
# semantic complete-linkage finds ONE group even with zero fold_groups around.
_SIMS = np.array([
    [1.00, 0.97, 0.10],
    [0.97, 1.00, 0.12],
    [0.10, 0.12, 1.00],
], dtype=np.float32)


async def _failing_judge():
    raise RuntimeError("same-event judge response was unparseable")


async def _empty_judge():
    return {}


async def _good_judge():
    return {0: [0, 1]}


def test_judge_failure_degrades_to_semantic_cut_without_fold_groups():
    # THE 2026-07-19 REGRESSION: the judge failed unparseable and the degraded
    # path was gated on non-empty label-fold groups — after THE RELABEL removed
    # near-duplicate labels, fold_groups={} and the build ABORTED, leaving the
    # umbrella layer stale. The deterministic semantic complete-linkage needs
    # no fold groups: a judge failure must degrade to it, full stop.
    groups, basis = asyncio.run(_resolve_event_groups(
        _failing_judge, _SIMS, threshold=0.95, degraded_ok=True))
    assert groups and sorted(next(iter(groups.values()))) == [0, 1]
    assert "llm-degraded" in basis


def test_empty_parseable_verdict_is_also_degraded_not_trusted():
    # Adversarial review 2026-07-14 (contract preserved through the refactor):
    # a parseable-but-empty grouping (hallucinated ids / all-below-confidence)
    # is a DEGRADED response, never a genuine "flatten everything" verdict.
    groups, basis = asyncio.run(_resolve_event_groups(
        _empty_judge, _SIMS, threshold=0.95, degraded_ok=True))
    assert groups
    assert "llm-degraded" in basis


def test_fallback_knob_off_restores_the_abort():
    with pytest.raises(UmbrellaGroupingUnavailable):
        asyncio.run(_resolve_event_groups(
            _failing_judge, _SIMS, threshold=0.95, degraded_ok=False))


def test_good_judge_verdict_passes_through():
    groups, basis = asyncio.run(_resolve_event_groups(
        _good_judge, _SIMS, threshold=0.95, degraded_ok=True))
    assert groups == {0: [0, 1]}
    assert basis == "llm-same-event-v1"


def test_abort_still_precedes_the_destructive_wipe_in_main():
    # The abort path (knob off / degraded impossible) must exit BEFORE the
    # parent_id wipe, and the degraded decision must NOT be conditioned on
    # label-fold state (the 07-19 bug class).
    src = inspect.getsource(_bu.main)
    wipe = src.index("SET parent_id = NULL")
    guard = src.index("sys.exit(3)")
    assert guard < wipe
    resolver_src = inspect.getsource(_bu._resolve_event_groups)
    # degrade is decided WITHOUT reading label-fold state (the 07-19 bug class)
    assert "fold_groups" not in resolver_src
    assert "fold_on" not in resolver_src


def test_degraded_fallback_env_flag_defaults_on():
    assert _bu._env_flag("ATLAS_TEST_ABSENT_FLAG_XYZ", default=True) is True
    import os
    os.environ["ATLAS_TEST_ABSENT_FLAG_XYZ"] = "off"
    try:
        assert _bu._env_flag("ATLAS_TEST_ABSENT_FLAG_XYZ", default=True) is False
    finally:
        del os.environ["ATLAS_TEST_ABSENT_FLAG_XYZ"]


def test_shared_distinctive_actor_reconnects_event_fragments():
    # Three US-Iran war fragments share distinctive actors (araghchi/khamenei/
    # hormuz); a fourth unrelated story shares only the ubiquitous 'trump'.
    actors = [
        {"araghchi", "khamenei", "trump"},   # US strikes Iran
        {"araghchi", "hormuz", "trump"},      # Hormuz blockade
        {"khamenei", "hormuz", "trump"},      # drone attack
        {"trump", "fifa", "messi"},           # unrelated World Cup/Trump story
    ]
    sims = np.array([
        [1.00, 0.88, 0.86, 0.40],
        [0.88, 1.00, 0.87, 0.42],
        [0.86, 0.87, 1.00, 0.41],
        [0.40, 0.42, 0.41, 1.00],
    ], dtype=np.float32)
    edges = _shared_actor_edges(actors, sims, max_actor_df=3, centroid_floor=0.82)
    groups = _union_find_groups(4, edges)
    assert len(groups) == 1
    (idxs,) = groups.values()
    assert set(idxs) == {0, 1, 2}


def test_ubiquitous_actor_does_not_connect_unrelated_topics():
    actors = [{"trump"}, {"trump"}, {"trump"}]
    sims = np.ones((3, 3), dtype=np.float32)
    edges = _shared_actor_edges(actors, sims, max_actor_df=1)  # df(trump)=3 > 1
    assert edges == []


def test_coincidental_rare_name_blocked_by_centroid_floor():
    actors = [{"raredude"}, {"raredude"}]
    sims = np.array([[1.0, 0.30], [0.30, 1.0]], dtype=np.float32)
    edges = _shared_actor_edges(actors, sims, max_actor_df=6, centroid_floor=0.82)
    assert edges == []


# --- #261 slice 1 (2026-07-19): CHUNKED same-event judge --------------------
# 830 labels in ONE prompt truncate the 4k-token response → unparseable → the
# whole run degrades and every LLM verdict is lost. Chunk the judge; a failed
# chunk degrades to its OWN sub-block complete-linkage; parsed chunks keep
# their verdicts; ALL-chunks-fail still raises (existing degradation ladder).

def _rows4():
    return [
        {"id": 10, "label": "Iran strike A", "category": "conflict", "crisis_relevant": True},
        {"id": 20, "label": "Iran strike B", "category": "conflict", "crisis_relevant": True},
        {"id": 30, "label": "Peru election dispute", "category": "elections", "crisis_relevant": False},
        {"id": 40, "label": "Peru recount protest", "category": "elections", "crisis_relevant": False},
    ]


# 10~20 and 30~40 semantically close; the two pairs unrelated.
_SIMS4 = np.array([
    [1.00, 0.97, 0.10, 0.12],
    [0.97, 1.00, 0.11, 0.13],
    [0.10, 0.11, 1.00, 0.96],
    [0.12, 0.13, 0.96, 1.00],
], dtype=np.float32)


def _fake_call_llm(responses_by_ids):
    """responses_by_ids: {frozenset(ids in prompt): raw response or Exception}."""
    calls = []

    async def fake(provider, *, system, user, client=None, **kw):
        ids = frozenset(int(line.split("\t")[0]) for line in user.splitlines()[1:])
        calls.append(ids)
        resp = responses_by_ids[ids]
        if isinstance(resp, Exception):
            raise resp
        return resp

    return fake, calls


def test_small_pool_is_one_judge_call(monkeypatch):
    fake, calls = _fake_call_llm({
        frozenset({10, 20, 30, 40}):
            '{"events":[{"name":"Iran","topic_ids":[10,20],"confidence":0.9}]}',
    })
    monkeypatch.setattr(_bu, "call_llm", fake)
    groups = asyncio.run(_bu._llm_event_multi(
        _rows4(), _SIMS4, min_confidence=0.7, threshold=0.95, chunk_size=120))
    assert len(calls) == 1
    assert groups == {0: [0, 1]}


def test_chunked_judge_merges_per_chunk_verdicts(monkeypatch):
    # chunk_size=2 with semantic ordering → chunks {10,20} and {30,40}
    fake, calls = _fake_call_llm({
        frozenset({10, 20}):
            '{"events":[{"name":"Iran","topic_ids":[10,20],"confidence":0.9}]}',
        frozenset({30, 40}):
            '{"events":[{"name":"Peru","topic_ids":[30,40],"confidence":0.8}]}',
    })
    monkeypatch.setattr(_bu, "call_llm", fake)
    groups = asyncio.run(_bu._llm_event_multi(
        _rows4(), _SIMS4, min_confidence=0.7, threshold=0.95, chunk_size=2))
    assert len(calls) == 2
    assert groups == {0: [0, 1], 2: [2, 3]}


def test_failed_chunk_degrades_to_subblock_linkage_others_survive(monkeypatch):
    fake, calls = _fake_call_llm({
        frozenset({10, 20}):
            '{"events":[{"name":"Iran","topic_ids":[10,20],"confidence":0.9}]}',
        frozenset({30, 40}): "NOT JSON — truncated garbage",
    })
    monkeypatch.setattr(_bu, "call_llm", fake)
    groups = asyncio.run(_bu._llm_event_multi(
        _rows4(), _SIMS4, min_confidence=0.7, threshold=0.95, chunk_size=2))
    # LLM verdict kept for the parsed chunk; the failed chunk's 0.96 pair is
    # recovered by ITS OWN complete-linkage (never lost, never cross-chained)
    assert groups == {0: [0, 1], 2: [2, 3]}


def test_all_chunks_failing_raises_for_the_ladder(monkeypatch):
    fake, _calls = _fake_call_llm({
        frozenset({10, 20}): "garbage",
        frozenset({30, 40}): RuntimeError("boom"),
    })
    monkeypatch.setattr(_bu, "call_llm", fake)
    with pytest.raises(RuntimeError):
        asyncio.run(_bu._llm_event_multi(
            _rows4(), _SIMS4, min_confidence=0.7, threshold=0.95, chunk_size=2))


def test_semantic_chunk_order_colocates_neighbors():
    from app.services.event_umbrella import semantic_chunk_order

    sims = [
        [1.0, 0.1, 0.9, 0.1],
        [0.1, 1.0, 0.1, 0.2],
        [0.9, 0.1, 1.0, 0.1],
        [0.1, 0.2, 0.1, 1.0],
    ]
    assert semantic_chunk_order(sims) == [0, 2, 1, 3]


# ---------------------------------------------------------------------------
# GB5 Class E (2026-07-30, docs/research/label-court/2026-07-29-gb5-blind-
# check.md): the umbrella upsert rewrote label/agg_n_signals on every rebuild
# without ever invalidating a court verdict earned on the PRIOR label or
# child set — dt-8105 served "Typhoon Bavi Landfall" with an `entailed` stamp
# earned by "Typhoon Noul Ravages Southern China". Schema-freeze / SQL-shape
# tests: no DB needed, just confirm the CASE-WHEN invalidation is present and
# wired to the right columns.
# ---------------------------------------------------------------------------

def test_umbrella_upsert_clears_all_four_court_columns_conditionally():
    sql = _UMBRELLA_UPSERT_SQL
    for col in ("label_status", "label_proposed", "label_checked_at", "label_court_model"):
        assert f"{col} = CASE WHEN" in sql, f"{col} must be conditionally reset"
        assert f"THEN NULL ELSE dynamic_topics.{col} END" in sql, \
            f"{col} must fall back to its OWN prior value when unchanged, never get clobbered"


def test_umbrella_upsert_stamps_label_updated_at_on_change():
    # the GB5-cited staleness detector (label_updated_at > label_checked_at)
    # returned 0/39 because this column was never touched by the upsert at
    # all — it must be set to now() exactly when the invalidation fires.
    sql = _UMBRELLA_UPSERT_SQL
    assert "label_updated_at = CASE WHEN" in sql
    assert "THEN now() ELSE dynamic_topics.label_updated_at END" in sql


def test_umbrella_upsert_invalidation_condition_covers_label_and_family_shape():
    # GB5 named BOTH triggers explicitly: "the label actually changed" AND
    # "equally when the child set changes" (dt-3433 kept a verdict through a
    # 10-child family collapsing to 2 unrelated children). No child-set
    # fingerprint column exists (no migration in this pass) — agg_n_signals
    # is the cheap, already-recomputed-every-rebuild proxy for "the family
    # changed shape".
    cond = _LABEL_OR_FAMILY_CHANGED
    assert "dynamic_topics.label IS DISTINCT FROM EXCLUDED.label" in cond
    assert "dynamic_topics.agg_n_signals IS DISTINCT FROM EXCLUDED.agg_n_signals" in cond
    assert " OR " in cond
    # every one of the five conditional columns must use the SAME condition
    # (a drifted duplicate would silently reintroduce the bug for one column)
    assert _UMBRELLA_UPSERT_SQL.count(cond) == 5


def test_umbrella_upsert_still_updates_the_ordinary_columns():
    # the fix must not regress the pre-existing rebuild-every-pass columns
    sql = _UMBRELLA_UPSERT_SQL
    for col in ("label=EXCLUDED.label", "centroid_vec=EXCLUDED.centroid_vec",
                "agg_n_signals=EXCLUDED.agg_n_signals", "umbrella_basis=EXCLUDED.umbrella_basis",
                "last_seen=EXCLUDED.last_seen", "updated_at=now()"):
        assert col in sql
    assert sql.strip().startswith("INSERT INTO dynamic_topics")
    assert "ON CONFLICT (identity_key) DO UPDATE SET" in sql
    assert sql.rstrip().endswith("RETURNING id")
