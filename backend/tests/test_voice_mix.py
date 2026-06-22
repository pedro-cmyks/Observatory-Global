"""Voice Mix diversity metric (#160/#230).

The whole diversification program is judged by this number, so its behavior
must be pinned: a monoculture scores near 0, a balanced multilingual corpus
scores high, and unknown-language buckets never inflate the result.
"""
from app.services import voice_mix


def _origins():
    return {"US": 100, "GB": 50, "(null)": 200}


def test_monoculture_scores_near_zero():
    # All English, language-known. english_balance=0, entropy=0, cjk=0.
    r = voice_mix.compute({"en": 1000, "xx": 5000}, _origins(), 6000, 0, 10)
    assert r["english_share_of_known"] == 1.0
    assert r["cjk"]["total"] == 0
    assert r["diversity_score"] < 1.0


def test_diverse_corpus_scores_high():
    langs = {"en": 200, "zh": 200, "ja": 200, "ko": 200, "es": 200, "ar": 200}
    r = voice_mix.compute(langs, _origins(), 1200, 0, 50)
    assert r["cjk"]["total"] == 600
    assert r["cjk"]["share_of_known"] == 0.5          # well past 5% target
    assert r["components"]["cjk_coverage"] == 1.0
    assert r["non_english_share_of_known"] > 0.8
    assert r["diversity_score"] > 70


def test_diversity_score_strictly_rises_with_balance():
    mono = voice_mix.compute({"en": 1000}, _origins(), 1000, 0, 5)
    mixed = voice_mix.compute(
        {"en": 500, "zh": 200, "es": 150, "ru": 150}, _origins(), 1000, 0, 5)
    assert mixed["diversity_score"] > mono["diversity_score"]


def test_unknown_buckets_excluded_from_known_slice():
    # 'xx' and '(null)' must not count as a language nor dilute English share.
    r = voice_mix.compute(
        {"en": 100, "xx": 900, "(null)": 50}, _origins(), 1050, 0, 5)
    assert r["language_known"] == 100
    assert r["distinct_known_languages"] == 1
    assert r["english_share_of_known"] == 1.0


def test_cjk_coverage_caps_at_target():
    # Exactly the 5% target → coverage component saturates at 1.0.
    r = voice_mix.compute({"en": 950, "zh": 50}, _origins(), 1000, 0, 5)
    assert r["cjk"]["share_of_known"] == 0.05
    assert r["components"]["cjk_coverage"] == 1.0
