import inspect

import numpy as np

from scripts import build_umbrella_topics as _bu
from scripts.build_umbrella_topics import _shared_actor_edges, _union_find_groups


def test_llm_event_aborts_on_empty_grouping_before_the_wipe():
    # Adversarial review 2026-07-14: a degraded-but-parseable verdict (string ids,
    # all-below-confidence, hallucinated ids) can resolve to an empty grouping;
    # in llm-event mode that MUST abort before the destructive parent_id wipe, not
    # flatten the whole hierarchy. Guard lives in main() before the transaction.
    src = inspect.getsource(_bu.main)
    wipe = src.index("SET parent_id = NULL")
    guard = src.index("if not multi:")
    assert guard < wipe  # the empty-grouping abort precedes the destructive wipe
    assert "sys.exit(3)" in src[guard:wipe]


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
