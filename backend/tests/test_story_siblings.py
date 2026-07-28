"""Pure tests for the story-lens sibling ranker (no DB, synthetic vectors)."""
import numpy as np

from app.services.story_siblings import rank_siblings


def _unit(v):
    a = np.asarray(v, dtype=np.float64)
    return a / np.linalg.norm(a)


def _matrix():
    # 6 unit vectors in 4-dim: seed cluster {0,1,2} tight, {3} mid, {4,5} far pair
    rows = [
        _unit([1.0, 0.05, 0.0, 0.0]),   # 0 seed
        _unit([1.0, 0.10, 0.0, 0.0]),   # 1 near seed (hermano)
        _unit([1.0, 0.12, 0.01, 0.0]),  # 2 near seed AND near 1 (dedup fold candidate)
        _unit([0.5, 0.8, 0.0, 0.0]),    # 3 mid distance
        _unit([0.0, 0.0, 1.0, 0.05]),   # 4 far
        _unit([0.0, 0.0, 1.0, 0.10]),   # 5 far, near 4
    ]
    return np.vstack(rows)


KEYS = [f"dynamic-topic-{i}" for i in range(6)]
LABELS = [f"Topic {i}" for i in range(6)]
CATS = [None] * 6


def test_seed_excluded_and_nearest_first():
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS)
    ids = [s.topic_key for s in sibs]
    assert "dynamic-topic-0" not in ids
    assert ids[0] in ("dynamic-topic-1", "dynamic-topic-2")
    weights = [s.weight for s in sibs]
    assert weights == sorted(weights, reverse=True)


def test_same_event_fold():
    # 1 and 2 are near-duplicates (cos > 0.999) -> one is folded under the other
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS)
    ids = [s.topic_key for s in sibs]
    assert not ("dynamic-topic-1" in ids and "dynamic-topic-2" in ids)
    rep = next(s for s in sibs if s.topic_key in ("dynamic-topic-1", "dynamic-topic-2"))
    assert set(rep.folded) & {"dynamic-topic-1", "dynamic-topic-2"}


def test_cap_respected():
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS, cap=1)
    assert len(sibs) == 1


def test_every_sibling_carries_a_receipt():
    for s in rank_siblings(0, _matrix(), KEYS, LABELS, CATS):
        assert s.reasons, "ranking without a receipt is forbidden (spec §6)"
        assert s.reasons[0]["basis"] == "whitened_cos"
        assert s.kinship in ("hermano", "primo")


def test_honest_empty_guards():
    m = _matrix()
    assert rank_siblings(99, m, KEYS, LABELS, CATS) == []
    assert rank_siblings(0, m[:1], KEYS[:1], LABELS[:1], CATS[:1]) == []


def test_misaligned_or_unnormalized_inputs_raise():
    import pytest
    m = _matrix()
    with pytest.raises(ValueError):
        rank_siblings(0, m, KEYS[:5], LABELS[:5], CATS[:5])
    with pytest.raises(ValueError):
        rank_siblings(0, m * 3.0, KEYS, LABELS, CATS)
