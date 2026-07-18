"""Per-country noise floor for the narrative-lineage census (leak 5).

The 2026-07-18 gate review found same-LANGUAGE cosine floors that sit above
the global theta (Icelandic unrelated domestic units chain at >=0.862 purely
on language). The fix is a pure, measured per-country negative control:
same-dominant-country unit pairs >= week_gap weeks apart (per-day clusters,
so no member overlap by construction), p95 of their cosines = that country's
floor; a same-country edge must clear max(theta, floor + margin).

These tests freeze the pure parts only (no DB, no shards).
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.narrative_lineage_census import (
    SINGLE_COUNTRY_SHARE,
    compute_country_floors,
    dominant_country_share,
    effective_edge_threshold,
)
from scripts.load_narrative_lineage import build_method_string


def _unit(vec):
    v = np.asarray(vec, dtype=np.float32)
    return v / np.linalg.norm(v)


def _synthetic_units():
    """Two countries, 12 weeks, 2 units/week.

    'IS' units all point near ONE direction (a hot same-language background:
    unrelated stories still cosine-high). 'US' units alternate between two
    nearly-orthogonal directions (diverse background: cross-week sims low).
    """
    rng = np.random.default_rng(5)
    base_is = _unit([1.0, 0.2, 0.0, 0.0])
    base_us_a = _unit([0.0, 0.0, 1.0, 0.0])
    base_us_b = _unit([0.0, 0.0, 0.0, 1.0])
    dom, wk, vecs = [], [], []
    for k in range(12):
        for j in range(2):
            dom.append("IS")
            wk.append(k)
            vecs.append(_unit(base_is + rng.normal(0, 0.05, 4)))
        for j in range(2):
            dom.append("US")
            wk.append(k)
            base = base_us_a if (k + j) % 2 == 0 else base_us_b
            vecs.append(_unit(base + rng.normal(0, 0.05, 4)))
    return dom, np.asarray(wk), np.stack(vecs)


class TestComputeCountryFloors:
    def test_hot_language_background_yields_high_floor(self):
        dom, wk, U = _synthetic_units()
        floors = compute_country_floors(dom, wk, U, min_pairs=10)
        assert floors["IS"]["floor"] > 0.95  # unrelated but same-language-hot

    def test_diverse_background_yields_lower_floor_than_hot(self):
        dom, wk, U = _synthetic_units()
        floors = compute_country_floors(dom, wk, U, min_pairs=10)
        assert floors["US"]["floor"] < floors["IS"]["floor"]

    def test_min_pairs_gate_refuses_thin_countries(self):
        dom, wk, U = _synthetic_units()
        # 24 IS units over 12 weeks -> plenty of pairs; demand more than exist
        floors = compute_country_floors(dom, wk, U, min_pairs=10_000)
        assert floors == {}  # never guessed from thin data

    def test_week_gap_respected(self):
        # 2 units, adjacent weeks only -> gap>=3 finds ZERO control pairs
        dom = ["FR", "FR"]
        wk = np.asarray([0, 1])
        U = np.stack([_unit([1, 0, 0, 0]), _unit([1, 0.1, 0, 0])])
        assert compute_country_floors(dom, wk, U, min_pairs=1,
                                      week_gap=3) == {}
        # but with gap>=1 the pair IS a control pair
        got = compute_country_floors(dom, wk, U, min_pairs=1, week_gap=1)
        assert got["FR"]["n_pairs"] == 1

    def test_none_dominant_country_excluded(self):
        dom = [None, None, "DE", "DE"]
        wk = np.asarray([0, 5, 0, 5])
        U = np.stack([_unit([1, 0, 0, 0])] * 4)
        floors = compute_country_floors(dom, wk, U, min_pairs=1)
        assert set(floors) == {"DE"}

    def test_pure_and_deterministic(self):
        dom, wk, U = _synthetic_units()
        a = compute_country_floors(dom, wk, U, min_pairs=10)
        b = compute_country_floors(dom, wk, U, min_pairs=10)
        assert a == b


class TestEffectiveEdgeThreshold:
    FLOORS = {"IS": {"floor": 0.91, "n_pairs": 500, "n_units": 40},
              "US": {"floor": 0.40, "n_pairs": 900, "n_units": 80}}

    def test_same_country_hot_floor_raises_threshold(self):
        got = effective_edge_threshold(0.862, "IS", "IS", self.FLOORS, 0.02)
        assert got == pytest.approx(0.93)

    def test_same_country_cold_floor_keeps_theta(self):
        # US floor + margin sits below theta -> theta wins (max, not replace)
        got = effective_edge_threshold(0.862, "US", "US", self.FLOORS, 0.02)
        assert got == 0.862

    def test_cross_country_pair_keeps_theta(self):
        got = effective_edge_threshold(0.862, "IS", "US", self.FLOORS, 0.02)
        assert got == 0.862

    def test_unmeasured_country_keeps_theta(self):
        got = effective_edge_threshold(0.862, "VE", "VE", self.FLOORS, 0.02)
        assert got == 0.862

    def test_none_country_keeps_theta(self):
        got = effective_edge_threshold(0.862, None, None, self.FLOORS, 0.02)
        assert got == 0.862


class TestDominantCountryShare:
    def test_signal_weighted_dominant(self):
        cc, share = dominant_country_share(
            [["IC", "FR"], ["IC"], ["US"]], [90, 5, 5])
        assert cc == "IC"
        assert share == pytest.approx(0.95)

    def test_no_countries_is_none(self):
        assert dominant_country_share([[], []], [3, 4]) == (None, 0.0)

    def test_single_country_flag_threshold_is_08(self):
        # the census flags single_country at >= SINGLE_COUNTRY_SHARE
        assert SINGLE_COUNTRY_SHARE == 0.8


class TestMethodStringCarriesFloors:
    BASE = {"generated_at": "2026-07-18", "theta_topic_unit": 0.858,
            "theta_unit_unit": 0.862}

    def test_floors_appended_when_measured(self):
        m = dict(self.BASE, per_country_floor={
            "n_countries": 41, "percentile": 95.0, "margin": 0.02})
        s = build_method_string(m)
        assert "floors=41cc(p95+0.02)" in s
        assert "tu=0.858" in s and "uu=0.862" in s  # taus regex untouched

    def test_no_floors_block_keeps_legacy_string(self):
        s = build_method_string(self.BASE)
        assert "floors=" not in s
        assert s.startswith("census-v0 gen=2026-07-18")
