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


def test_freak_movement_on_tiny_base_does_not_lead():
    # A 28-signal syndicated story whose changed_10h (53) exceeds its own
    # signal_count is noise/amplification — it must NOT out-rank a 766-signal
    # accelerating story for the front-page lead (movement is volume-damped).
    freak = _t("syndicated", sc=28, ch=53, conf=0.6)
    real = _t("real-mover", sc=766, ch=116, conf=0.6)
    assert [t["label"] for t in rank_threads([freak, real])][0] == "real-mover"


def test_lifestyle_thread_is_damped_below_a_comparable_real_thread():
    # 2026-06-29 §4(b): Vegas has the STRONGEST raw metrics - it would lead
    # without the damp (the live "Las Vegas Travel Guide ranks #1" pathology).
    # The editorial-lane damp drops it below real news, but it still appears
    # (input, not gate). Filler thread spreads the min-max normalisation.
    vegas = _t("Las Vegas Travel Guide", sc=300, ch=90, conf=0.97)
    iran = _t("Iran Attacks Bahrain and Kuwait", sc=250, ch=60, conf=0.90)
    filler = _t("Local council notes", sc=15, ch=1, conf=0.40)
    order = rank_threads([vegas, iran, filler])
    assert order[0]["label"] == "Iran Attacks Bahrain and Kuwait"
    labels = [t["label"] for t in order]
    assert "Las Vegas Travel Guide" in labels  # present, just no longer #1


def test_lane_damp_does_not_touch_real_news_ordering():
    from app.services.thread_ranking import lane_rank_multiplier
    assert lane_rank_multiplier({"label": "Iran Attacks Bahrain"}) == 1.0
    assert lane_rank_multiplier({"label": "Ukraine War Updates"}) == 1.0
    assert lane_rank_multiplier({"label": "World Cup 2026 Live Streams"}) < 1.0
    assert lane_rank_multiplier({"label": "Las Vegas Travel Guide"}) < 1.0


def _tb(label, *, sc, ch, conf, langs, countries):
    return {"label": label, "signal_count": sc, "changed_10h": ch,
            "avg_confidence": conf, "language_count": langs, "country_count": countries}


def test_global_breadth_lifts_a_multilingual_multicountry_story_over_a_local_volume_bin():
    # A genuinely global event (many languages + countries) outranks a bigger but
    # local, single-language thread — L2 now carries the L1 consequence signal.
    war = _tb("US-Iran war", sc=40, ch=10, conf=0.8, langs=5, countries=8)
    local = _tb("Local telco outage", sc=200, ch=8, conf=0.8, langs=1, countries=1)
    ranked = [t["label"] for t in rank_threads([local, war])]
    assert ranked[0] == "US-Iran war"


def test_thread_ranking_without_breadth_fields_still_ranks():
    a = {"label": "a", "signal_count": 100, "changed_10h": 20, "avg_confidence": 0.5}
    b = {"label": "b", "signal_count": 40, "changed_10h": 2, "avg_confidence": 0.5}
    ranked = [t["label"] for t in rank_threads([b, a])]
    assert ranked[0] == "a"


def test_correctly_typed_sport_is_damped_below_news_despite_global_breadth():
    # A World Cup match is genuinely multi-country/-language — the HIGHEST volume
    # and breadth here — but the semantic damp keeps it off the front page, so it
    # lands last behind the two real-news threads.
    football = {"label": "Suiza Elimina a Colombia", "signal_count": 60, "changed_10h": 20,
                "avg_confidence": 0.9, "language_count": 5, "country_count": 20,
                "crisis_relevant": False, "category": "Sports / World Cup"}
    war = {"label": "US-Iran war", "signal_count": 40, "changed_10h": 15,
           "avg_confidence": 0.8, "language_count": 2, "country_count": 6,
           "crisis_relevant": False, "category": "Armed conflict escalation"}
    election = {"label": "Election dispute", "signal_count": 30, "changed_10h": 10,
                "avg_confidence": 0.7, "language_count": 1, "country_count": 3,
                "crisis_relevant": False, "category": "Elections & Politics"}
    ranked = [t["label"] for t in rank_threads([football, war, election])]
    assert ranked[0] == "US-Iran war"  # real news leads, not the football
    # the sport is damped below the war despite carrying the highest breadth+volume
    assert ranked.index("Suiza Elimina a Colombia") > ranked.index("US-Iran war")
