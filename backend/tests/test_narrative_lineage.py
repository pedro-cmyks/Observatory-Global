"""Narrative lineage (mig 084 + theme-lineage-v0) — loader + serving tests.

Freezes: loader parse/candidate policy + idempotence-by-construction (keyed
rows + ON CONFLICT upsert), the pure biography assembly (weekly eras, explicit
gaps, measured drift, candidate propagation, hot tier), and the honest-empty
contract. No DB, no network: I/O boundaries are faked.
"""
from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.services import narrative_lineage as nl
from scripts.load_narrative_lineage import (
    UPSERT_TOPIC_UNIT, UPSERT_UNIT_UNIT, build_method_string, is_candidate,
    load, parse_edges)


# ── fixtures ────────────────────────────────────────────────────────────────

METHOD = {
    "generated_at": "2026-07-18",
    "theta_topic_unit": 0.62,
    "theta_unit_unit": 0.55,
    "theta_measurement": {
        "topic_unit": {"bimodal": True},
        "unit_unit": {"bimodal": True},
    },
}

EDGES_DOC = {
    "method": METHOD,
    "topic_unit_edges": [
        {"topic_id": 1837, "unit_id": 2041, "sim": 0.714, "week": "2026-06-22"},
        {"topic_id": 1837, "unit_id": 2050, "sim": 0.625, "week": "2026-06-15"},
    ],
    "unit_unit_edges": [
        {"src_unit_id": 2001, "dst_unit_id": 2041, "sim": 0.83,
         "src_week": "2026-06-15", "dst_week": "2026-06-22", "kind": "adjacent"},
        {"src_unit_id": 2001, "dst_unit_id": 2050, "sim": 0.56,
         "src_week": "2026-06-15", "dst_week": "2026-06-15", "kind": "intra"},
    ],
}


def _unit(uid, day, label, n, vec, cc=("VE",), samples=None):
    return {"id": uid, "day": day, "label": label, "n_signals": n,
            "top_cc": list(cc), "vec": vec,
            "samples": samples if samples is not None
            else [f"sample headline for {label} {uid}"]}


# ── loader: parse + candidate policy ────────────────────────────────────────

class TestLoaderParse:
    def test_method_string_carries_measured_taus(self):
        s = build_method_string(METHOD)
        assert "tu=0.62" in s and "uu=0.55" in s and "gen=2026-07-18" in s

    def test_candidate_near_threshold_band(self):
        assert is_candidate(0.63, 0.62, True, near=0.02) is True   # in band
        assert is_candidate(0.66, 0.62, True, near=0.02) is False  # asserted

    def test_candidate_when_threshold_not_bimodal(self):
        # non-bimodal fallback threshold => EVERYTHING is a candidate
        assert is_candidate(0.99, 0.62, False) is True

    def test_parse_keys_are_upsert_identity(self):
        p = parse_edges(EDGES_DOC)
        assert set(p["topic_unit"]) == {(1837, 2041), (1837, 2050)}
        assert set(p["unit_unit"]) == {(2001, 2041), (2001, 2050)}

    def test_parse_twice_identical(self):
        # idempotence by construction: same doc -> same keyed rows
        assert parse_edges(EDGES_DOC) == parse_edges(EDGES_DOC)

    def test_candidate_flags_propagate_to_rows(self):
        p = parse_edges(EDGES_DOC)
        # 0.625 < 0.62+0.02 -> candidate; 0.714 asserted
        assert p["topic_unit"][(1837, 2050)][5] is True
        assert p["topic_unit"][(1837, 2041)][5] is False
        # uu: 0.56 < 0.55+0.02 -> candidate; 0.83 asserted
        assert p["unit_unit"][(2001, 2050)][7] is True
        assert p["unit_unit"][(2001, 2041)][7] is False


# ── loader: idempotent upsert against a fake conn ───────────────────────────

class FakeLoadConn:
    """Emulates the upsert identity: keyed store per statement kind."""

    def __init__(self):
        self.store: dict[tuple, tuple] = {}
        self.pruned = 0

    async def executemany(self, sql, rows):
        assert "ON CONFLICT" in sql  # idempotence is in the SQL, not hope
        kind = "tu" if "topic_unit" in sql.split("VALUES")[0] else "uu"
        for r in rows:
            self.store[(kind, r[0], r[1])] = r

    async def execute(self, sql, *args):
        return "DELETE 0"

    async def fetchval(self, sql):
        return len(self.store)


class TestLoaderIdempotence:
    def test_double_load_same_rows(self):
        conn = FakeLoadConn()
        parsed = parse_edges(EDGES_DOC)
        s1 = asyncio.run(load(conn, parsed))
        first = dict(conn.store)
        s2 = asyncio.run(load(conn, parsed))
        assert conn.store == first          # re-run converges, no growth
        assert s1["topic_unit"] == s2["topic_unit"] == 2
        assert len(conn.store) == 4

    def test_upsert_statements_target_partial_identity(self):
        assert "WHERE kind = 'topic_unit'" in UPSERT_TOPIC_UNIT
        assert "WHERE kind = 'unit_unit'" in UPSERT_UNIT_UNIT


# ── pure biography assembly ─────────────────────────────────────────────────

def _vec(direction):
    # tiny 3d stand-ins; the service normalizes, cosine is exact
    return {"a": [1.0, 0.0, 0.0], "b": [0.0, 1.0, 0.0],
            "ab": [1.0, 1.0, 0.0]}[direction]


TU = [{"unit_id": 11, "sim": 0.714, "candidate": False,
       "method": "census-v0 gen=2026-07-18 tu=0.62 uu=0.55"}]


class TestBuildLineagePayload:
    def _units(self):
        return [
            _unit(10, "2026-05-26", "Quake Casualties", 800, _vec("a")),
            _unit(11, "2026-06-16", "Reconstruction Debate", 200, _vec("ab"),
                  cc=("VE", "US")),
        ]

    def _uu(self, candidate=False):
        return [{"src_unit_id": 10, "unit_id": 11, "sim": 0.58,
                 "edge_kind": "gap-bridge", "candidate": candidate}]

    def _hot(self):
        return {"week": "2026-07-13", "label": "Quake Recovery",
                "n_signals": 96, "countries": ["VE"],
                "receipts": [{"headline": "hot receipt", "signal_id": 5,
                              "url": "u", "source": "s", "source_lang": "es",
                              "day": "2026-07-15"}]}

    def test_shape_and_weeks_ascending_with_explicit_gaps(self):
        out = nl.build_lineage_payload("dynamic-topic-1837", TU, self._uu(),
                                       self._units(), self._hot())
        assert out["contract"] == "theme-lineage-v0"
        assert out["lineage_id"] == "lin-10"
        weeks = [w["week"] for w in out["weeks"]]
        assert weeks == sorted(weeks)
        # May-25 era .. Jun-15 era => Jun-01/Jun-08 are explicit gaps
        gaps = [w["week"] for w in out["weeks"] if w.get("gap")]
        assert gaps == ["2026-06-01", "2026-06-08"]
        present = [w for w in out["weeks"] if not w.get("gap")]
        assert [w["tier"] for w in present] == ["archive", "archive", "hot"]

    def test_drift_null_first_then_measured_cosine(self):
        out = nl.build_lineage_payload("dynamic-topic-1837", TU, self._uu(),
                                       self._units(), self._hot())
        present = [w for w in out["weeks"] if not w.get("gap")]
        assert present[0]["drift_cos_prev"] is None
        # cos([1,0,0],[1,1,0]/√2) = 0.7071
        assert present[1]["drift_cos_prev"] == pytest.approx(0.7071, abs=1e-3)
        # hot node carries the stitch cosine, labeled by the stitch block
        assert present[2]["drift_cos_prev"] == pytest.approx(0.714)

    def test_candidate_join_flags_the_era_not_the_lineage(self):
        out = nl.build_lineage_payload("dynamic-topic-1837", TU,
                                       self._uu(candidate=True),
                                       self._units(), self._hot())
        present = [w for w in out["weeks"] if not w.get("gap")]
        assert present[0]["candidate"] is False   # root era
        assert present[1]["candidate"] is True    # joined via candidate bridge
        assert out["stitch"]["candidate"] is False  # the stitch itself held

    def test_stitch_block_parses_measured_thetas(self):
        out = nl.build_lineage_payload("dynamic-topic-1837", TU, self._uu(),
                                       self._units(), self._hot())
        st = out["stitch"]
        assert st["space"] == "openai/text-embedding-3-small"
        assert st["theta_topic_unit"] == pytest.approx(0.62)
        assert st["theta_unit_unit"] == pytest.approx(0.55)
        assert st["topic_sim"] == pytest.approx(0.714)
        assert st["member_coverage"] is None  # honest: not persisted

    def test_receipts_capped_at_three(self):
        units = [_unit(10, "2026-05-26", "Big Era", 500, _vec("a"),
                       samples=[f"h{i}" for i in range(9)])]
        out = nl.build_lineage_payload("dynamic-topic-1", TU, [], units, None)
        present = [w for w in out["weeks"] if not w.get("gap")]
        assert len(present[0]["receipts"]) == 3
        assert present[0]["receipts"][0] == {"headline": "h0",
                                             "day": "2026-05-26"}

    def test_meta_coverage_counts_present_over_span(self):
        out = nl.build_lineage_payload("dynamic-topic-1837", TU, self._uu(),
                                       self._units(), None)
        # 2 present eras over a 4-week span (2 gaps)
        assert out["meta"]["weeks_spanned"] == 4
        assert out["meta"]["weeks_present"] == 2
        assert out["meta"]["coverage_pct"] == pytest.approx(50.0)

    def test_no_edges_is_honest_empty(self):
        out = nl.build_lineage_payload("dynamic-topic-9", [], [], [], None)
        assert out["weeks"] == [] and out["stitch"] is None
        assert out["empty_reason"] == "no_lineage"


# ── serving: honest-empty + shape against a fake conn ───────────────────────

class FakeServeConn:
    def __init__(self, topic_row=None, tu_rows=(), uu_rows=(), unit_rows=(),
                 hot_rows=()):
        self.topic_row = topic_row
        self.tu_rows = list(tu_rows)
        self.uu_rows = list(uu_rows)
        self.unit_rows = list(unit_rows)
        self.hot_rows = list(hot_rows)

    async def fetchrow(self, sql, *args):
        return self.topic_row

    async def fetch(self, sql, *args):
        if "kind = 'topic_unit'" in sql:
            return self.tu_rows
        if "kind = 'unit_unit'" in sql:
            # BFS converges: only answer the first frontier
            seeds = set(args[0])
            return [r for r in self.uu_rows
                    if r["src_unit_id"] in seeds or r["unit_id"] in seeds]
        if "archive_story_units" in sql:
            return self.unit_rows
        if "topic_members" in sql:
            return self.hot_rows
        return []


class _Ts:
    def __init__(self, d):
        self._d = d

    def date(self):
        return self._d


class TestTopicLineageServing:
    def test_atlas_slug_is_honest_empty(self):
        out = asyncio.run(nl.topic_lineage(FakeServeConn(), "water-stress--pe"))
        assert out["empty_reason"] == "lineage_dynamic_topics_only"
        assert out["weeks"] == []

    def test_unknown_topic_honest_empty(self):
        out = asyncio.run(nl.topic_lineage(FakeServeConn(topic_row=None),
                                           "dynamic-topic-424242"))
        assert out["empty_reason"] == "topic_not_found"

    def test_no_stitch_honest_empty(self):
        conn = FakeServeConn(topic_row={"id": 7, "label": "X",
                                        "last_seen": _Ts(date(2026, 7, 16))})
        out = asyncio.run(nl.topic_lineage(conn, "dynamic-topic-7"))
        assert out["empty_reason"] == "no_lineage"
        assert out["contract"] == "theme-lineage-v0"

    def test_end_to_end_shape(self):
        conn = FakeServeConn(
            topic_row={"id": 1837, "label": "Quake Recovery",
                       "last_seen": _Ts(date(2026, 7, 16))},
            tu_rows=[{"unit_id": 11, "sim": 0.714, "candidate": False,
                      "method": "census-v0 gen=2026-07-18 tu=0.62 uu=0.55"}],
            uu_rows=[{"src_unit_id": 10, "unit_id": 11, "sim": 0.58,
                      "edge_kind": "adjacent", "candidate": False}],
            unit_rows=[
                {"id": 10, "day": "2026-06-09", "label": "Quake Casualties",
                 "samples": '["s1","s2"]', "n_signals": 800,
                 "top_cc": ["VE"], "vec": "[1.0, 0.0, 0.0]"},
                {"id": 11, "day": "2026-06-16", "label": "Reconstruction",
                 "samples": '["s3"]', "n_signals": 200,
                 "top_cc": ["VE"], "vec": "[1.0, 1.0, 0.0]"},
            ],
            hot_rows=[{"signal_id": 5, "headline": "hot h", "source_name": "s",
                       "source_url": "u", "country_code": "VE",
                       "source_lang": "es", "day": "2026-07-15"}])
        out = asyncio.run(nl.topic_lineage(conn, "dynamic-topic-1837"))
        assert out["empty_reason"] is None
        present = [w for w in out["weeks"] if not w.get("gap")]
        assert [w["tier"] for w in present] == ["archive", "archive", "hot"]
        # jsonb-as-str samples parsed; halfvec text parsed -> measured drift
        assert present[0]["receipts"][0]["headline"] == "s1"
        assert present[1]["drift_cos_prev"] == pytest.approx(0.7071, abs=1e-3)
        hot = present[-1]
        assert hot["week"] == "2026-07-13"  # Monday of Jul-16
        assert hot["receipts"][0]["signal_id"] == 5
        assert hot["countries"] == ["VE"]
