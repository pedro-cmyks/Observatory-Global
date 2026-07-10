"""Tests for the archive-search pure ranking (archive-search-v0)."""
from app.routers.archive_search import rank_topics


def _t(id_, vec, **kw):
    base = {"id": id_, "label": f"t{id_}", "category": None,
            "crisis_relevant": None, "country_code": "CO",
            "period_start": "2026-06-01", "period_end": "2026-06-07",
            "n_stories": 5, "centroid_vec": vec, "top_sources": {}}
    base.update(kw)
    return base


def test_rank_topics_orders_by_cosine_and_applies_floor():
    q = [1.0, 0.0]
    rows = [_t(1, [1.0, 0.0]), _t(2, [0.7071, 0.7071]), _t(3, [0.0, 1.0])]
    out = rank_topics(q, rows, floor=0.5, limit=10)
    assert [r["id"] for r in out] == [1, 2]
    assert out[0]["similarity"] > out[1]["similarity"] >= 0.5


def test_rank_topics_respects_limit():
    q = [1.0, 0.0]
    rows = [_t(i, [1.0, 0.0]) for i in range(20)]
    assert len(rank_topics(q, rows, floor=0.0, limit=5)) == 5


def test_rank_topics_empty_is_honest():
    assert rank_topics([1.0, 0.0], [], floor=0.3, limit=10) == []


def test_rank_topics_zero_vector_never_divides_by_zero():
    out = rank_topics([0.0, 0.0], [_t(1, [0.0, 0.0])], floor=-1.0, limit=5)
    assert out and out[0]["similarity"] == 0.0
