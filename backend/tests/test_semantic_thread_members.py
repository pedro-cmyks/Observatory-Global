"""Pure-logic tests for semantic thread membership (no DB)."""

import asyncio
from pathlib import Path

import pytest

from app.services.research_semantic import (
    ANN_IVFFLAT_PROBES,
    ANN_QUERY_TIMEOUT_SECONDS,
    SemanticSignalLaneTimeout,
    THREAD_MEMBER_MIN_SIMILARITY,
    _prepare_ann_search,
    build_semantic_members,
    fetch_semantic_thread_members,
)


def _row(sid, sim, headline="Real headline about a clear subject here",
         lang="es", has_topic=False):
    return {
        "id": sid, "similarity": sim, "headline": headline,
        "country_code": "ES", "source_name": "El Pais", "source_url": "u",
        "timestamp": "2026-06-24T00:00:00", "sentiment": 0.1,
        "source_lang": lang, "has_topic": has_topic,
    }


def test_floor_excludes_low_similarity():
    rows = [_row(1, 0.95), _row(2, THREAD_MEMBER_MIN_SIMILARITY - 0.01)]
    out = build_semantic_members(rows)
    assert [m["signal_id"] for m in out] == [1]


def test_excludes_already_shown_lexicon_ids():
    rows = [_row(1, 0.9), _row(2, 0.9)]
    out = build_semantic_members(rows, exclude_ids={1})
    assert [m["signal_id"] for m in out] == [2]


def test_junk_headlines_dropped():
    rows = [_row(1, 0.9, headline="Doc Iniaztwk5508793.Shtml"),
            _row(2, 0.9, headline="too short"),
            _row(3, 0.9, headline="A genuine three word headline indeed")]
    out = build_semantic_members(rows)
    assert [m["signal_id"] for m in out] == [3]


def test_cross_syndication_dedup_by_headline():
    rows = [_row(1, 0.95, headline="Same Story Everywhere Today Reported"),
            _row(2, 0.90, headline="same story everywhere today reported")]
    out = build_semantic_members(rows)
    assert len(out) == 1
    assert out[0]["signal_id"] == 1  # higher-sim copy kept (input order)


def test_limit_respected():
    rows = [_row(i, 0.99, headline=f"Distinct headline number {i} about topic")
            for i in range(20)]
    out = build_semantic_members(rows, limit=5)
    assert len(out) == 5


def test_labels_provenance_and_gate_status():
    rows = [_row(1, 0.9, headline="First distinct subject headline here",
                 has_topic=False),
            _row(2, 0.9, headline="Second distinct subject headline here",
                 has_topic=True)]
    out = build_semantic_members(rows)
    assert all(m["retrieval"] == "semantic_member" for m in out)
    assert out[0]["gate_status"] == "below_gate"
    assert out[1]["gate_status"] == "assigned"


def test_source_lang_preserved_for_voice_surfacing():
    rows = [_row(1, 0.9, headline="Persian voice subject headline here", lang="fa"),
            _row(2, 0.9, headline="Unknown lang subject headline here", lang="")]
    out = build_semantic_members(rows)
    langs = {m["signal_id"]: m["source_lang"] for m in out}
    assert langs[1] == "fa"
    assert langs[2] == "xx"  # empty normalized to xx


def test_ann_search_uses_the_measured_under_load_probe_setting():
    """probes=20 was tuned for recall on an IDLE box (2026-07-13) and measured
    >100s under nightly load (2026-07-27/28) against a 6s budget — i.e. no
    answer at all whenever the DB was busy. 10 returned 2.1-2.9s loaded."""
    class Conn:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)

    conn = Conn()
    asyncio.run(_prepare_ann_search(conn))

    assert ANN_IVFFLAT_PROBES == 10
    assert conn.statements == ["SET ivfflat.probes = 10"]
    # the probe count only means something against a stated budget
    assert ANN_IVFFLAT_PROBES > 0 and ANN_QUERY_TIMEOUT_SECONDS == 6


def test_each_database_ann_lane_prepares_ivfflat_probes():
    source = (
        Path(__file__).parents[1] / "app/services/research_semantic.py"
    ).read_text()

    assert source.count("await _prepare_ann_search(conn)") >= 2


# ── Member lane: a timeout must never look like an empty membership ─────────


class _MemberConn:
    """asyncpg stand-in: serves a centroid, records the ANN query kwargs."""

    def __init__(self, centroid=None, rows=None, fetch_raises=None):
        self.centroid = centroid
        self.rows = rows or []
        self.fetch_raises = fetch_raises
        self.statements: list[str] = []
        self.fetch_kwargs: dict = {}

    async def fetchrow(self, query, *args, **kwargs):
        if self.centroid is None:
            return None
        return {"centroid_vec": self.centroid}

    async def fetch(self, query, *args, **kwargs):
        self.fetch_kwargs = kwargs
        if self.fetch_raises is not None:
            raise self.fetch_raises
        return self.rows

    async def execute(self, statement):
        self.statements.append(statement)


def test_member_ann_timeout_raises_a_named_degradation_not_an_empty_list():
    """Same ANN index, same load profile as the signal lane: probes=20 ran
    >100s under nightly load against an idle 1.5s. Unbounded, this lane
    would hang the thread detail; bounded-but-silent, a timeout would read
    as 'this thread has no semantic members' — the one thing it does not
    mean."""
    conn = _MemberConn(centroid=[0.1] * 8, fetch_raises=asyncio.TimeoutError())

    with pytest.raises(SemanticSignalLaneTimeout) as excinfo:
        asyncio.run(fetch_semantic_thread_members(conn, 42, hours=24))

    assert excinfo.value.degraded_reason == "ann_timeout"
    # still a TimeoutError, so themes.py / corroboration-style degrade paths
    # keep catching it without importing the named class
    assert isinstance(excinfo.value, TimeoutError)
    assert conn.statements == [f"SET ivfflat.probes = {ANN_IVFFLAT_PROBES}"]


def test_member_ann_query_is_bounded_by_the_shared_budget():
    conn = _MemberConn(centroid=[0.1] * 8, rows=[])

    out = asyncio.run(fetch_semantic_thread_members(conn, 42, hours=24))

    assert out == []
    assert conn.fetch_kwargs.get("timeout") == ANN_QUERY_TIMEOUT_SECONDS


def test_missing_centroid_stays_a_silent_measured_absence():
    """The honest empty keeps its contract: no centroid = nothing to search,
    an [] with no exception — only the timeout gets the named degradation."""
    conn = _MemberConn(centroid=None)

    out = asyncio.run(fetch_semantic_thread_members(conn, 42, hours=24))

    assert out == []
    assert conn.statements == []  # never reached the ANN prepare


def test_theme_detail_names_the_member_timeout_instead_of_swallowing_it():
    """themes.py wraps this lane in a bare `except Exception: []`. A timeout
    must exit through the TimeoutError branch and stamp a named warning —
    otherwise the raise above just becomes a quieter silent empty."""
    source = (Path(__file__).parents[1] / "app/routers/themes.py").read_text()

    timeout_branch = source.find("except TimeoutError")
    generic_branch = source.find("except Exception:", timeout_branch)
    assert timeout_branch != -1
    # TimeoutError must be caught BEFORE the generic swallow to ever fire
    assert generic_branch > timeout_branch
    assert "semantic_members_ann_timeout" in source
