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
    # German is not in v1; Latin script still routes to EN.
    score, _, lang = score_headline("Peace agreement reached today", source_lang="de")
    assert lang == "en"
    assert score > 0


# ── Confidence cap ───────────────────────────────────────────────────────────
def test_confidence_never_exceeds_lexicon_ceiling():
    # Stacking many strong words; confidence must still cap at 0.5.
    text = "war attack killed dead wounded crisis violence riot tension threat"
    _, conf, _ = score_headline(text, source_lang="en")
    assert conf <= CONFIDENCE_CEILING + 1e-6


def test_neutral_text_scores_zero_with_zero_confidence():
    score, conf, _ = score_headline("The conference will be held next Monday in the city center building.", source_lang="en")
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
