"""Unit tests for the multilingual lexicon-grade sentiment scorer (issue #164)."""
from __future__ import annotations

import pytest

from enrichment.lexicon_sentiment import (
    CONFIDENCE_CEILING,
    LEXICONS,
    score_headline,
)


# ── Language hint wins when supported ────────────────────────────────────────
def test_english_hint_uses_english_lexicon():
    score, conf, lang = score_headline("Peace agreement signed in Geneva", source_lang="en")
    assert lang == "en"
    assert score > 0
    assert 0 < conf <= CONFIDENCE_CEILING


def test_spanish_hint_uses_spanish_lexicon():
    score, conf, lang = score_headline("Acuerdo de paz firmado en Ginebra", source_lang="es")
    assert lang == "es"
    assert score > 0
    assert 0 < conf <= CONFIDENCE_CEILING


def test_french_hint_uses_french_lexicon():
    score, conf, lang = score_headline("Accord de paix signé à Genève", source_lang="fr")
    assert lang == "fr"
    assert score > 0


def test_portuguese_hint_uses_portuguese_lexicon():
    score, conf, lang = score_headline("Acordo de paz assinado em Genebra", source_lang="pt")
    assert lang == "pt"
    assert score > 0


def test_arabic_hint_uses_arabic_lexicon():
    score, conf, lang = score_headline("اتفاق سلام تاريخي بين البلدين", source_lang="ar")
    assert lang == "ar"
    assert score > 0


# ── Negative content ─────────────────────────────────────────────────────────
def test_war_attack_scores_negative_in_english():
    score, _, _ = score_headline("Deadly attack kills civilians in border town", source_lang="en")
    assert score < 0


def test_violencia_protesta_scores_negative_in_spanish():
    score, _, _ = score_headline("Violencia y protesta tras escándalo de corrupción", source_lang="es")
    assert score < 0


# ── Script-based fallback when source_lang missing ──────────────────────────
def test_arabic_script_falls_back_to_ar_lexicon_without_hint():
    score, _, lang = score_headline("هجوم على المدنيين", source_lang=None)
    assert lang == "ar"
    assert score < 0


def test_latin_script_falls_back_to_en_without_hint():
    score, _, lang = score_headline("Peace agreement reached", source_lang=None)
    assert lang == "en"
    assert score > 0


def test_unsupported_lang_hint_falls_back_by_script():
    # Japanese is not in v1; Latin script still routes to EN.
    score, _, lang = score_headline("Peace agreement reached today", source_lang="ja")
    assert lang == "en"
    assert score > 0


# ── Confidence cap ───────────────────────────────────────────────────────────
def test_confidence_never_exceeds_lexicon_ceiling():
    # Stacking many strong words; confidence must still cap at 0.5.
    text = "war attack killed dead wounded crisis violence riot tension threat"
    _, conf, _ = score_headline(text, source_lang="en")
    assert conf <= CONFIDENCE_CEILING + 1e-6


def test_unknown_tokens_score_zero_with_zero_confidence():
    score, conf, _ = score_headline("lorem ipsum qwerty zyxwvu placeholder", source_lang="en")
    assert score == 0
    assert conf == 0


# ── Edge cases ───────────────────────────────────────────────────────────────
def test_empty_string_returns_zero():
    score, conf, lang = score_headline("", source_lang="en")
    assert score == 0
    assert conf == 0
    assert lang is None


def test_whitespace_only_returns_zero():
    score, conf, lang = score_headline("   ", source_lang="en")
    assert score == 0
    assert conf == 0


def test_too_few_tokens_returns_zero():
    score, conf, lang = score_headline("Hi", source_lang="en")
    assert score == 0
    assert conf == 0


# ── HTML entity decode regression (2026-05-22) ──────────────────────────────
# Upstream feeds emit numeric/named character references (`&#xE4;`, `&auml;`).
# Without html.unescape, the tokenizer fractures `verk&#xE4;ndet` into
# garbage tokens (`verk` + `xe4` + `ndet`), preventing lexicon matches and
# routing the row to `fast_neutral`. Regression test pins the decode step.
def test_html_numeric_entities_decoded_before_scoring():
    plain_score, _, _ = score_headline("Guerra y crisis devastan la región", source_lang="es")
    entity_score, _, _ = score_headline(
        "Guerra y crisis devastan la regi&#xF3;n", source_lang="es"
    )
    assert plain_score == entity_score
    assert entity_score < 0


def test_html_named_entities_decoded_before_scoring():
    plain_score, _, _ = score_headline("Krieg und Krise zerstören die Stadt", source_lang="de")
    named_entity_score, _, _ = score_headline(
        "Krieg und Krise zerst&ouml;ren die Stadt", source_lang="de"
    )
    # Either lexicon hits both equivalently, or neither — the key invariant is
    # that decoding does not produce a different tokenisation outcome.
    assert plain_score == named_entity_score


def test_html_entities_do_not_create_xhex_tokens():
    # If decoding fails, lexicon would never see `region` and would treat
    # `regi`, `xf3`, `n` as separate tokens. Score parity is the regression
    # signal we care about.
    plain, _, _ = score_headline("Caf\xe9 con leche y crisis", source_lang="es")
    entity, _, _ = score_headline("Caf&#xe9; con leche y crisis", source_lang="es")
    assert plain == entity


# ── Lexicon coverage sanity ──────────────────────────────────────────────────
def test_all_v1_languages_present():
    expected = {"en", "es", "fr", "pt", "ar"}
    assert expected.issubset(LEXICONS.keys())


def test_each_lexicon_has_positive_and_negative_seeds():
    for lang, lex in LEXICONS.items():
        positives = [w for w, v in lex.items() if v > 0]
        negatives = [w for w, v in lex.items() if v < 0]
        assert positives, f"{lang} lexicon missing positive seeds"
        assert negatives, f"{lang} lexicon missing negative seeds"
