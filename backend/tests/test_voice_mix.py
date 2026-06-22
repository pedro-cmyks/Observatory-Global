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


def test_compute_exposes_voices_by_origin():
    r = voice_mix.compute({"en": 100}, {"US": 80, "GB": 20, "(null)": 5}, 105, 0, 5)
    vbo = {v["cc"]: v for v in r["voices_by_origin"]}
    assert vbo["US"]["pct"] == 0.8       # share of attributable origins
    assert "(null)" not in vbo            # unattributed excluded


def test_primary_langs_map():
    assert voice_mix.primary_langs("IR") == ("fa",)
    assert voice_mix.primary_langs("EG") == ("ar",)   # Arabic world
    assert voice_mix.primary_langs("xx") == ()        # unknown -> empty


def test_relation_flags_foreign_dominated_subject():
    # Iran-like: 5000 signals about it, only 50 voiced by Iran -> 99% foreign.
    r = voice_mix.relation(
        scope_total=5000, endogenous=50,
        foreign_origins=[("GB", 2000), ("US", 1500)],
        foreign_langs=[("en", 4800)],
    )
    assert r["self_voice_ratio"] == 0.01
    assert r["foreign_voice_ratio"] == 0.99
    assert r["dominant_outsider"]["origin"] == "GB"
    assert r["dominant_outsider"]["pct_of_foreign"] == round(2000 / 4950, 4)


def test_relation_endogenous_country():
    # A self-covered subject -> high self_voice_ratio, no dominant outsider drama.
    r = voice_mix.relation(1000, 900, [("US", 100)], [("en", 100)])
    assert r["self_voice_ratio"] == 0.9
    assert r["foreign_voice"] == 100
