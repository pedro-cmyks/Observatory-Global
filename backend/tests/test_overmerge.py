"""Over-merge detector — pure multimodality math + decision logic (no DB).

The merge sprint (court 47.9%->24.3%) left ~220 OVER-MERGE blob-topics: a topic
whose members are a FUSION of 2+ distinct stories, wearing a vague umbrella label
("Mixed Local News", "Multiple Deadly Incidents Across Peru and Ukraine") that the
label court cannot catch (a vague label trivially entails a diverse set), that the
content-junk classifier cannot catch (each member is a real news item), and that
the M2 radial floor cannot catch (the centroid falls BETWEEN the sub-clusters, so
few members read "below floor").

The distinguishing signal is MEMBERSHIP MULTIMODALITY: if a topic's member
embeddings split into 2+ well-separated sub-clusters of SUBSTANTIAL size, it is a
fusion of distinct stories. This module freezes:

  - 2-means (numpy, deterministic seed) over the member matrix,
  - separation (cosine gap between sub-centroids), intra-cluster spread,
  - the silhouette-style gap_ratio = separation / spread,
  - balance = min(|A|,|B|)/(|A|+|B|),
  - the keep/demote decision, and the shared-actor veto that spares a legit
    mega-story (Ukraine War: frontline + diplomacy + sanctions + refugees is ONE
    story whose sub-aspects share actors — it must NOT be demoted),
  - the split-judge prompt/parse (precision-first: unavailable => KEEP).

Precision-first everywhere: when unsure, KEEP.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.overmerge import (
    BORDERLINE,
    DEMOTE,
    KEEP,
    OverMergeParams,
    SplitStats,
    apply_judge_verdict,
    country_dominant_overlap,
    decide,
    is_over_merge,
    parse_split_judge_response,
    partition,
    set_overlap,
    split_judge_user,
    split_stats,
    two_means,
)


# ---------------------------------------------------------------- helpers
def _axis(i: int, d: int) -> np.ndarray:
    v = np.zeros(d, dtype=np.float64)
    v[i] = 1.0
    return v


def _blob(center: np.ndarray, n: int, sigma: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return center[None, :] + rng.normal(0.0, sigma, size=(n, center.shape[0]))


def _bimodal(d: int = 128, n_a: int = 40, n_b: int = 40,
             sigma: float = 0.02, seed: int = 1) -> np.ndarray:
    """Two tight clusters around ORTHOGONAL unit vectors — a clear fusion."""
    a = _blob(_axis(0, d), n_a, sigma, seed)
    b = _blob(_axis(1, d), n_b, sigma, seed + 1)
    return np.vstack([a, b])


def _unimodal(d: int = 128, n: int = 90, sigma: float = 0.16,
              seed: int = 5) -> np.ndarray:
    """One isotropic blob — a real single story with internal spread."""
    return _blob(_axis(0, d), n, sigma, seed)


# ---------------------------------------------------------------- two_means
def test_two_means_is_deterministic_under_seed():
    mat = _bimodal(seed=3)
    l1, _ = two_means(mat, seed=42)
    l2, _ = two_means(mat, seed=42)
    assert np.array_equal(l1, l2)


def test_two_means_recovers_a_clear_bimodal_partition():
    """The 80 rows are two orthogonal blobs of 40; 2-means must separate them
    (each true blob lands in one label, up to label swap)."""
    mat = _bimodal(n_a=40, n_b=40, seed=7)
    labels, cent = two_means(mat, seed=42)
    assert cent.shape == (2, mat.shape[1])
    first40 = labels[:40]
    last40 = labels[40:]
    # each true blob is internally homogeneous...
    assert len(set(first40.tolist())) == 1
    assert len(set(last40.tolist())) == 1
    # ...and the two blobs got DIFFERENT labels
    assert first40[0] != last40[0]


def test_two_means_all_identical_rows_is_not_a_split():
    """Degenerate input (every row identical) must not fabricate two clusters."""
    mat = np.tile(_axis(0, 32), (20, 1))
    labels, _ = two_means(mat, seed=42)
    # one cluster is empty -> split_stats reads balance 0 (below)
    assert (labels == 0).all() or (labels == 1).all()


# ---------------------------------------------------------------- split_stats
def test_split_stats_bimodal_has_wide_gap_and_high_balance():
    stats = split_stats(_bimodal(n_a=40, n_b=40, seed=11), seed=42)
    assert stats is not None
    assert stats.n == 80
    assert {stats.size_a, stats.size_b} == {40}
    assert stats.balance == pytest.approx(0.5, abs=1e-9)
    assert stats.separation > 0.5          # near-orthogonal sub-centroids
    assert stats.gap_ratio > 3.0           # separation >> intra spread
    assert stats.mean_silhouette > 0.6     # clean two-cluster structure


def test_split_stats_unimodal_has_narrow_gap():
    stats = split_stats(_unimodal(seed=5), seed=42)
    assert stats is not None
    # 2-means WILL split it, but the gap is small relative to the spread
    assert stats.gap_ratio < 1.5
    assert stats.mean_silhouette < 0.5


def test_split_stats_orders_bimodal_above_unimodal():
    """The core contract: whatever the exact numbers, a fusion's gap_ratio and
    silhouette dominate a single blob's."""
    bi = split_stats(_bimodal(seed=13), seed=42)
    uni = split_stats(_unimodal(seed=13), seed=42)
    assert bi.gap_ratio > uni.gap_ratio
    assert bi.mean_silhouette > uni.mean_silhouette


def test_split_stats_too_few_rows_is_honest_none():
    assert split_stats(np.zeros((1, 16)), seed=42) is None
    assert split_stats(np.zeros((0, 16)), seed=42) is None


def test_partition_labels_and_stats_are_consistent():
    """The script needs sub-cluster labels that MATCH the reported stats — one
    2-means run yields both (labels sizes == the stats' size_a/size_b)."""
    mat = _bimodal(n_a=40, n_b=40, seed=23)
    labels, stats = partition(mat, seed=42)
    assert labels is not None and stats is not None
    assert int((labels == 0).sum()) == stats.size_a
    assert int((labels == 1).sum()) == stats.size_b
    # and it agrees with split_stats (the public stats-only entry)
    assert split_stats(mat, seed=42).gap_ratio == pytest.approx(stats.gap_ratio)


def test_partition_too_few_rows_is_none_none():
    assert partition(np.zeros((1, 16)), seed=42) == (None, None)


def test_split_stats_degenerate_single_cluster_reports_zero_balance():
    """All-identical rows: no real second cluster -> balance 0 (keep)."""
    stats = split_stats(np.tile(_axis(0, 32), (30, 1)), seed=42)
    assert stats is not None
    assert stats.balance == 0.0


# ---------------------------------------------------------------- is_over_merge
def test_is_over_merge_true_on_balanced_bimodal():
    stats = split_stats(_bimodal(n_a=40, n_b=40, seed=17), seed=42)
    assert is_over_merge(stats, OverMergeParams()) is True


def test_is_over_merge_false_on_unimodal():
    stats = split_stats(_unimodal(seed=17), seed=42)
    assert is_over_merge(stats, OverMergeParams()) is False


def test_is_over_merge_false_below_min_members():
    """A tiny topic can't be a fusion of two SUBSTANTIAL stories — honest skip."""
    stats = split_stats(_bimodal(n_a=5, n_b=5, seed=19), seed=42)  # n=10
    assert stats.n == 10
    assert is_over_merge(stats, OverMergeParams(min_members=12)) is False


def test_is_over_merge_false_when_second_cluster_is_a_sliver():
    """2-means peeling a few strays off a real story (the M2-floor case) has a
    wide gap but tiny balance -> NOT an over-merge."""
    stats = SplitStats(n=60, size_a=57, size_b=3, separation=0.9,
                       intra_spread=0.05, gap_ratio=18.0,
                       mean_silhouette=0.4, balance=3 / 60)
    assert stats.balance < OverMergeParams().tau_bal
    assert is_over_merge(stats, OverMergeParams()) is False


def test_is_over_merge_none_stats_is_false():
    assert is_over_merge(None, OverMergeParams()) is False


# ---------------------------------------------------------------- set_overlap
def test_set_overlap_disjoint_is_zero():
    assert set_overlap({"UA", "RU"}, {"PE", "MX"}) == 0.0


def test_set_overlap_identical_is_one():
    assert set_overlap({"UA", "RU"}, {"RU", "UA"}) == 1.0


def test_set_overlap_partial_is_jaccard():
    # {UA,RU} vs {UA,PL}: intersection 1, union 3
    assert set_overlap({"UA", "RU"}, {"UA", "PL"}) == pytest.approx(1 / 3)


def test_set_overlap_empty_sides_are_zero_not_crash():
    assert set_overlap(set(), set()) == 0.0
    assert set_overlap({"UA"}, set()) == 0.0


# ---------------------------------------------- country_dominant_overlap
# The Measure-step precision fix. The naive combined-set Jaccard is PERSON-
# SWAMPED: two halves of a SINGLE-country story share the one country token but
# each item names different people, so the many distinct person tokens dilute the
# intersection below the veto threshold -> the story reads "distinct actors" and
# is wrongly demoted (verified: the FP demotes were ~all single-country). Splitting
# the two signals and taking the MAX un-swamps the country signal.
def test_country_dominant_overlap_single_country_is_one_despite_disjoint_persons():
    """Both sub-clusters are all-US with DISJOINT persons — the swamped combined
    Jaccard was ~1/7 (below veto); country-dominant reads 1.0 (veto fires)."""
    a = {"c:US", "p:abbott", "p:cruz", "p:paxton"}
    b = {"c:US", "p:biden", "p:harris", "p:mayorkas"}
    # the OLD swamped behaviour (what caused the false positives):
    assert set_overlap(a, b) < 0.2
    # the FIX: the shared country is not diluted by the distinct persons
    assert country_dominant_overlap(a, b) == 1.0


def test_country_dominant_overlap_cross_country_fusion_stays_zero():
    """Peru on one side, Ukraine on the other, no shared person -> genuine fusion,
    overlap 0 (the demote proceeds)."""
    a = {"c:PE", "p:boluarte"}
    b = {"c:UA", "p:zelensky"}
    assert country_dominant_overlap(a, b) == 0.0


def test_country_dominant_overlap_person_rescue_when_country_missing():
    """A rare cross-/no-country ONE story (e.g. a summit, or NULL country codes)
    is rescued by shared persons -> the MAX picks up the person signal."""
    a = {"p:zelensky", "p:putin"}
    b = {"p:zelensky", "p:putin"}
    assert country_dominant_overlap(a, b) == 1.0


def test_country_dominant_overlap_partial_country_share():
    # A={US,MX}, B={US}: country Jaccard 1/2 = 0.5 (>= tau_overlap default) -> veto
    a = {"c:US", "c:MX", "p:x"}
    b = {"c:US", "p:y"}
    assert country_dominant_overlap(a, b) == pytest.approx(0.5)


def test_country_dominant_overlap_empty_is_zero():
    assert country_dominant_overlap(set(), set()) == 0.0
    assert country_dominant_overlap({"p:x"}, set()) == 0.0


def test_country_dominant_overlap_one_common_wire_person_does_not_veto():
    """A genuine fusion whose halves both name one common wire-service person
    (Trump in a Gaza item AND a trade item) must NOT be vetoed: one shared person
    among many keeps the person Jaccard low, and the countries differ."""
    a = {"c:IL", "p:trump", "p:netanyahu", "p:gallant"}
    b = {"c:CN", "p:trump", "p:xi", "p:wang"}
    # 1 shared person / 5 union = 0.2, and countries differ -> below the 0.5 veto
    assert country_dominant_overlap(a, b) < OverMergeParams().tau_overlap


# ---------------------------------------------------------------- decide
def _bimodal_stats(gap_ratio: float = 3.0, balance: float = 0.5,
                   n: int = 60) -> SplitStats:
    return SplitStats(n=n, size_a=int(n * (1 - balance)), size_b=int(n * balance),
                      separation=0.8, intra_spread=0.8 / max(gap_ratio, 1e-9),
                      gap_ratio=gap_ratio, mean_silhouette=0.7, balance=balance)


def test_decide_demotes_a_balanced_wide_gap_with_distinct_actors():
    verdict, reason = decide(_bimodal_stats(gap_ratio=5.0), entity_overlap=0.0,
                             params=OverMergeParams())
    assert verdict == DEMOTE
    assert "distinct actors" in reason or "wide gap" in reason


def test_decide_shared_actors_veto_keeps_a_mega_story():
    """Ukraine-War class: wide internal gap, balanced, BUT the sub-clusters share
    actors (UA/RU) -> one story, KEEP. This is the critical false-positive guard."""
    verdict, reason = decide(_bimodal_stats(gap_ratio=5.0), entity_overlap=0.8,
                             params=OverMergeParams())
    assert verdict == KEEP
    assert "shared actors" in reason


def test_decide_borderline_band_routes_to_judge():
    p = OverMergeParams()
    mid = (p.tau_sep_low + p.tau_sep) / 2.0
    verdict, _ = decide(_bimodal_stats(gap_ratio=mid), entity_overlap=0.0, params=p)
    assert verdict == BORDERLINE


def test_decide_unimodal_keeps_without_touching_actors():
    p = OverMergeParams()
    verdict, reason = decide(_bimodal_stats(gap_ratio=p.tau_sep_low - 0.3),
                             entity_overlap=None, params=p)
    assert verdict == KEEP
    assert "unimodal" in reason


def test_decide_unbalanced_keeps():
    p = OverMergeParams()
    stats = SplitStats(n=60, size_a=57, size_b=3, separation=0.9, intra_spread=0.05,
                       gap_ratio=18.0, mean_silhouette=0.4, balance=3 / 60)
    verdict, reason = decide(stats, entity_overlap=0.0, params=p)
    assert verdict == KEEP
    assert "unbalanced" in reason


def test_decide_below_min_members_keeps_precision_first():
    p = OverMergeParams(min_members=12)
    stats = SplitStats(n=8, size_a=4, size_b=4, separation=0.9, intra_spread=0.05,
                       gap_ratio=18.0, mean_silhouette=0.9, balance=0.5)
    verdict, reason = decide(stats, entity_overlap=0.0, params=p)
    assert verdict == KEEP
    assert "min_members" in reason


def test_decide_none_stats_keeps():
    verdict, _ = decide(None, entity_overlap=0.0, params=OverMergeParams())
    assert verdict == KEEP


# ---------------------------------------------------------------- split judge
def test_split_judge_user_lists_both_sides():
    prompt = split_judge_user("Mixed Local News",
                              ["Flood hits Jakarta", "Drone strike on Kyiv"],
                              ["Housing bill passes in Lima", "Peru market crash"])
    assert "Mixed Local News" in prompt
    assert "Flood hits Jakarta" in prompt
    assert "Housing bill passes in Lima" in prompt


def test_parse_split_judge_one_story_keeps():
    # True == "one story" == KEEP
    assert parse_split_judge_response('{"verdict":"one_story"}') is True


def test_parse_split_judge_two_stories_demotes():
    # False == "two stories" == demote candidate
    assert parse_split_judge_response('{"verdict":"two_stories"}') is False


def test_parse_split_judge_tolerates_prose_wrapping():
    raw = 'Here is my answer:\n{"verdict": "two_stories"}\nThanks.'
    assert parse_split_judge_response(raw) is False


def test_parse_split_judge_unavailable_is_none_precision_first():
    assert parse_split_judge_response("") is None
    assert parse_split_judge_response("not json at all") is None
    assert parse_split_judge_response('{"verdict":"maybe"}') is None


# ----------------------------------------------------- apply_judge_verdict
# The judge gates BOTH bands (borderline AND structural-demote): a flagged
# candidate becomes a real demote only on a positive "two_stories" confirmation.
def test_apply_judge_verdict_two_stories_demotes():
    v, note = apply_judge_verdict(False)
    assert v == DEMOTE and "two stories" in note


def test_apply_judge_verdict_one_story_keeps():
    v, note = apply_judge_verdict(True)
    assert v == KEEP and "one story" in note


def test_apply_judge_verdict_unavailable_keeps_precision_first():
    """A structural demote whose judge call fails is KEPT — never demote a real
    story on the ABSENCE of a positive confirmation (this is what rescues the
    cross-country-same-story residual when the judge is up, and stays safe when
    it is down)."""
    v, note = apply_judge_verdict(None)
    assert v == KEEP and "unavailable" in note
