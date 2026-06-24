"""Unified narrative-thread ranking (Pedro, 2026-06-24).

The living/aggregate split was a source label dressed as quality: dynamic
clusters always ranked first, atlas topics filled below. But an atlas topic
that keeps growing is a live thread too — it shouldn't be demoted by origin.
rank_threads() scores ALL threads the same way, by movement + volume +
coherence, with no source bias:

- volume is log-damped so a 3,000-signal category can't bury a 50-signal story
  by raw count alone,
- movement (10h delta relative to size) lets a heating thread rise,
- coherence (avg_confidence) breaks ties toward real stories over loose bins.
"""
from __future__ import annotations

from app.services.thread_ranking import rank_threads


def _t(label, *, sc, ch, conf, source="dynamic"):
    return {"label": label, "signal_count": sc, "changed_10h": ch,
            "avg_confidence": conf, "source": source}


def test_empty():
    assert rank_threads([]) == []


def test_movement_breaks_a_volume_tie():
    hot = _t("hot", sc=100, ch=60, conf=0.5)
    cold = _t("cold", sc=100, ch=5, conf=0.5)
    assert [t["label"] for t in rank_threads([cold, hot])] == ["hot", "cold"]


def test_hot_small_story_can_outrank_stale_big_bin():
    # Pedro's case: a raw category must not dominate by volume alone.
    story = _t("US-Iran strikes", sc=50, ch=40, conf=0.9)
    bin_ = _t("Military Conflict", sc=3000, ch=20, conf=0.3)
    assert [t["label"] for t in rank_threads([bin_, story])][0] == "US-Iran strikes"


def test_confidence_breaks_a_near_tie():
    coherent = _t("coherent", sc=100, ch=20, conf=0.9)
    loose = _t("loose", sc=100, ch=20, conf=0.2)
    assert [t["label"] for t in rank_threads([loose, coherent])] == ["coherent", "loose"]


def test_source_field_does_not_bias_ranking():
    # identical metrics, different source → order must be stable, not source-led
    a = _t("a", sc=100, ch=20, conf=0.5, source="atlas")
    d = _t("d", sc=100, ch=20, conf=0.5, source="dynamic")
    ranked = [t["label"] for t in rank_threads([a, d])]
    assert set(ranked) == {"a", "d"}
    # swapping input order must not flip them (deterministic, source-agnostic)
    ranked2 = [t["label"] for t in rank_threads([d, a])]
    assert ranked == ranked2


def test_big_volume_still_helps_when_movement_and_coherence_equal():
    big = _t("big", sc=2000, ch=40, conf=0.5)
    small = _t("small", sc=40, ch=1, conf=0.5)
    # big has both more volume and more absolute movement → ranks first
    assert [t["label"] for t in rank_threads([small, big])][0] == "big"
