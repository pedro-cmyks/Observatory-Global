"""Pure-logic tests for semantic thread membership (no DB)."""

import asyncio
from pathlib import Path

from app.services.research_semantic import (
    ANN_IVFFLAT_PROBES,
    THREAD_MEMBER_MIN_SIMILARITY,
    _prepare_ann_search,
    build_semantic_members,
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


def test_ann_search_uses_the_measured_recall_probe_floor():
    class Conn:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)

    conn = Conn()
    asyncio.run(_prepare_ann_search(conn))

    assert ANN_IVFFLAT_PROBES == 20
    assert conn.statements == ["SET ivfflat.probes = 20"]


def test_each_database_ann_lane_prepares_ivfflat_probes():
    source = (
        Path(__file__).parents[1] / "app/services/research_semantic.py"
    ).read_text()

    assert source.count("await _prepare_ann_search(conn)") >= 2
