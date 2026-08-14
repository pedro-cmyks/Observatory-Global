"""Behavioural tests for the story-siblings handler's FAMILY rows (Z3).

The measurement (docs/research/recall-229/2026-08-14-duplicate-live-stories.md)
found that `_TOPICS_SQL`'s `AND NOT is_umbrella` removed R2 umbrellas from the
candidate universe outright: dt-242 and dt-12927 (the umbrella over the same
Colombian earthquake) could never be each other's siblings even though their
whitened cosine, 0.6489, EXCEEDED dt-242's then-#1 hermano at 0.6360.

These tests drive the real handler over a fake asyncpg pool — the router file
had only source-regex coverage before, which cannot tell you whether the
umbrella actually comes back, where it ranks, or what it says about itself.

The field is a miniature of the live one: an earthquake cluster (a leaf anchor,
a leaf sibling, and an umbrella that outranks that sibling) plus a completely
separate control cluster used to prove no regression for stories that have no
umbrella anywhere near them.
"""
import asyncio

import numpy as np
import pytest

from app import db
from app.routers import story

DIM = 768


def _vec(*components: tuple[int, float]) -> list[float]:
    v = np.zeros(DIM, dtype=np.float64)
    for i, w in components:
        v[i] = w
    return [float(x) for x in (v / np.linalg.norm(v))]


# --- the miniature field ------------------------------------------------------
# 242    : the leaf anchor (Pedro's witness)
# 12927  : the R2 umbrella over the same event — CLOSER to 242 than 523 is,
#          mirroring the measured 0.6489 > 0.6360
# 523    : an ordinary leaf sibling
# 999/1000: an unrelated cluster, orthogonal to all of the above (the control)
TOPIC_ROWS = [
    {"id": 242, "label": "7.4-Magnitude Earthquake Kills Dozens in Colombia",
     "category": "Earthquake or volcanic disaster", "label_status": "entailed",
     "is_umbrella": False, "centroid_vec": _vec((0, 1.0))},
    {"id": 12927, "label": "Colombia Declares Disaster After Deadly Earthquake",
     "category": "Earthquake or volcanic disaster", "label_status": "entailed",
     "is_umbrella": True, "centroid_vec": _vec((0, 1.0), (1, 0.35))},
    {"id": 523, "label": "Venezuela Earthquake Death Toll",
     "category": "Earthquake or volcanic disaster", "label_status": "entailed",
     "is_umbrella": False, "centroid_vec": _vec((0, 1.0), (2, 0.80))},
    {"id": 999, "label": "Control Story",
     "category": "Labour strike", "label_status": "entailed",
     "is_umbrella": False, "centroid_vec": _vec((4, 1.0))},
    {"id": 1000, "label": "Control Story Neighbour",
     "category": "Labour strike", "label_status": "entailed",
     "is_umbrella": False, "centroid_vec": _vec((4, 1.0), (5, 0.05))},
]

# dt-12927's 8 children, three of which share no category with the rest — the
# measured contamination (two earthquakes + Ebola rows) that makes `family_
# category` honestly null.
FAMILY_ROWS = [{"parent_id": 12927, "n_children": 8, "n_cats": 2,
                "a_cat": "Earthquake or volcanic disaster"}]

COUNTRY_ROWS = [
    {"topic_id": "dynamic-topic-242", "country_code": "CO", "n": 19},
    {"topic_id": "dynamic-topic-12927", "country_code": "DE", "n": 24},
]


class _FakeConn:
    def __init__(self, topics=None, families=None, family_error=False,
                 country_error=False):
        self.topics = TOPIC_ROWS if topics is None else topics
        self.families = FAMILY_ROWS if families is None else families
        self.family_error = family_error
        self.country_error = country_error
        self.fetched = []

    async def execute(self, *_a, **_k):
        return "SET"

    async def fetch(self, sql, *args):
        self.fetched.append(sql)
        if "FROM dynamic_topics" in sql and "centroid_vec IS NOT NULL" in sql:
            return list(self.topics)
        if "parent_id = ANY" in sql:
            if self.family_error:
                raise RuntimeError("family lookup blew up")
            ids = set(args[0])
            return [r for r in self.families if r["parent_id"] in ids]
        if "signals_v2" in sql:
            if self.country_error:
                raise RuntimeError("country lane blew up")
            want = set(args[0])
            return [r for r in COUNTRY_ROWS if r["topic_id"] in want]
        return []

    async def fetchrow(self, sql, *args):
        if "is_umbrella" in sql and "state = 'active'" in sql and "parent_id" not in sql:
            row = next((t for t in self.topics
                        if t["id"] == args[0] and t["is_umbrella"]), None)
            return None if row is None else {"label": row["label"],
                                             "label_status": row["label_status"]}
        if "parent_id = $1" in sql:
            # largest active walkable child — dt-523 stands in for dt-12927
            return {"id": 523} if args[0] == 12927 else None
        return None


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self):
                return pool._conn

            async def __aexit__(self, *_a):
                return False

        return _Ctx()


@pytest.fixture(autouse=True)
def _wired(monkeypatch):
    """Pool + whitening + redis stubbed; the topics cache cleared so no test
    inherits another's matrix."""
    story._TOPICS_CACHE.clear()
    monkeypatch.setattr(story, "_redis_client", lambda: None)
    monkeypatch.setattr(story, "load_whitening", lambda: object())
    # Identity whitening: keeps the fixture's cosines readable while still
    # handing rank_siblings the unit-norm rows its contract demands.
    monkeypatch.setattr(
        story, "apply_whitening",
        lambda arr, _w: np.asarray(arr, dtype=np.float32)
        / np.linalg.norm(arr, axis=1, keepdims=True),
    )
    yield
    story._TOPICS_CACHE.clear()


def _call(thread_id, conn=None):
    conn = conn or _FakeConn()
    db.pool = _FakePool(conn)
    try:
        return asyncio.run(story.get_story_siblings(thread_id)), conn
    finally:
        db.pool = None


# --------------------------------------------------------------- the witness
def test_umbrella_is_returned_as_a_sibling_at_all():
    payload, _ = _call("dynamic-topic-242")
    ids = [s["id"] for s in payload["siblings"]]
    assert "dynamic-topic-12927" in ids, (
        "the umbrella over the anchor's own event must be reachable — "
        "`NOT is_umbrella` made this structurally impossible"
    )


def test_umbrella_ranks_where_the_math_puts_it():
    # 12927 is closer to the anchor than 523; it must lead, not be appended.
    payload, _ = _call("dynamic-topic-242")
    ids = [s["id"] for s in payload["siblings"]]
    assert ids[0] == "dynamic-topic-12927"
    assert ids.index("dynamic-topic-12927") < ids.index("dynamic-topic-523")


def test_family_row_is_marked_as_a_family_not_a_peer_story():
    payload, _ = _call("dynamic-topic-242")
    fam = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-12927")
    leaf = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-523")
    assert fam["kind"] == "family"
    assert fam["child_count"] == 8
    assert leaf["kind"] == "story"
    assert leaf["child_count"] is None


def test_family_category_only_when_the_children_agree():
    # The fixture's 8 children span 2 categories (the measured contamination),
    # so "shared category" is honestly absent rather than the modal guess.
    payload, _ = _call("dynamic-topic-242")
    fam = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-12927")
    assert fam["family_category"] is None

    agreed = _FakeConn(families=[{"parent_id": 12927, "n_children": 8, "n_cats": 1,
                                  "a_cat": "Earthquake or volcanic disaster"}])
    payload2, _ = _call("dynamic-topic-242", agreed)
    fam2 = next(s for s in payload2["siblings"] if s["id"] == "dynamic-topic-12927")
    assert fam2["family_category"] == "Earthquake or volcanic disaster"


def test_family_edge_carries_the_aggregate_anchor_caveat():
    payload, _ = _call("dynamic-topic-242")
    fam = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-12927")
    leaf = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-523")
    bases = [r["basis"] for r in fam["reasons"]]
    assert bases[0] == "whitened_cos", "the headline receipt stays the measured cosine"
    assert "aggregate_anchor" in bases
    caveat = next(r for r in fam["reasons"] if r["basis"] == "aggregate_anchor")
    assert "8 stories" in caveat["value"]
    # a leaf match is NOT weakened by a caveat it doesn't carry
    assert "aggregate_anchor" not in [r["basis"] for r in leaf["reasons"]]


# --------------------------------------------------------------- the control
def test_leaf_only_neighbourhood_is_byte_identical_with_and_without_umbrellas():
    # The regression guard: a story with no umbrella near it must not move
    # because umbrellas joined the field.
    with_umbrella, _ = _call("dynamic-topic-999")
    leaf_only = [t for t in TOPIC_ROWS if not t["is_umbrella"]]
    without_umbrella, _ = _call("dynamic-topic-999", _FakeConn(topics=leaf_only))
    assert with_umbrella["siblings"] == without_umbrella["siblings"]
    assert [s["id"] for s in with_umbrella["siblings"]] == ["dynamic-topic-1000"]
    assert all(s["kind"] == "story" for s in with_umbrella["siblings"])


# ------------------------------------------------- umbrella asked about directly
def test_umbrella_anchor_still_resolves_via_its_stand_in_child():
    payload, _ = _call("dynamic-topic-12927")
    assert "umbrella_resolved_via_child" in payload["notes"]
    assert payload["anchor"]["label"] == "Colombia Declares Disaster After Deadly Earthquake"


def test_umbrella_anchor_is_never_its_own_sibling():
    payload, _ = _call("dynamic-topic-12927")
    ids = [s["id"] for s in payload["siblings"]]
    assert "dynamic-topic-12927" not in ids, "an anchor cannot be kin to itself"
    assert "dynamic-topic-523" not in ids, "the stand-in child is not a sibling either"


def test_umbrella_anchor_marks_itself_a_family():
    payload, _ = _call("dynamic-topic-12927")
    assert payload["anchor"]["kind"] == "family"
    assert payload["anchor"]["child_count"] == 8


def test_leaf_anchor_is_marked_a_story():
    payload, _ = _call("dynamic-topic-242")
    assert payload["anchor"]["kind"] == "story"
    assert payload["anchor"]["child_count"] is None


# --------------------------------------------------------------- honest degrade
def test_family_lookup_failure_degrades_the_count_not_the_kind():
    payload, _ = _call("dynamic-topic-242", _FakeConn(family_error=True))
    fam = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-12927")
    assert fam["kind"] == "family", "an unknown count must never demote a container"
    assert fam["child_count"] is None
    assert "aggregate_anchor" in [r["basis"] for r in fam["reasons"]]
    # the OTHER lane is untouched: country receipts still landed
    assert "country_receipts_degraded" not in payload["notes"]
    assert payload["anchor"]["countries"] == ["CO"]


def test_country_lane_failure_still_marks_families():
    payload, _ = _call("dynamic-topic-242", _FakeConn(country_error=True))
    assert "country_receipts_degraded" in payload["notes"]
    fam = next(s for s in payload["siblings"] if s["id"] == "dynamic-topic-12927")
    assert fam["kind"] == "family"
