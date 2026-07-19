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
