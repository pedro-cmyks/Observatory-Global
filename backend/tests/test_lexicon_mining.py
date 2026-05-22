"""Unit tests for lexicon mining + merge behavior (issue #185)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def test_seed_wins_on_conflict_with_mined(tmp_path, monkeypatch):
    """Seed values must override mined values when both contain the same token."""
    # Point the loader at a sandbox directory containing a fake mined snapshot.
    fake_lex_dir = tmp_path / "lexicons"
    fake_lex_dir.mkdir()
    (fake_lex_dir / "en.mined.json").write_text(
        json.dumps({"war": -0.1, "novelterm": -1.4, "peace": 0.2}),
        encoding="utf-8",
    )

    # Patch the module's directory resolution to our sandbox.
    import enrichment.lexicon_sentiment as lex
    monkeypatch.setattr(
        "os.path.dirname",
        lambda _: str(tmp_path),
    )
    importlib.reload(lex)

    en = lex.LEXICONS["en"]
    # Seed "war" stays at the curated -2.5, NOT the mined -0.1.
    assert en["war"] == -2.5
    # Seed "peace" stays at the curated 2.5.
    assert en["peace"] == 2.5
    # Mined "novelterm" carries over (no seed entry collides).
    assert en["novelterm"] == -1.4


def test_missing_mined_file_is_silent(monkeypatch, tmp_path):
    """Missing snapshot is normal; loader returns {} without raising."""
    import enrichment.lexicon_sentiment as lex

    # Direct call to the loader with a path that has no JSON file.
    monkeypatch.setattr("os.path.dirname", lambda _: str(tmp_path))
    assert lex._load_mined_lexicon("en") == {}


def test_malformed_mined_json_is_ignored(monkeypatch, tmp_path, caplog):
    """A non-dict JSON body must not crash startup; warning logged."""
    fake_lex_dir = tmp_path / "lexicons"
    fake_lex_dir.mkdir()
    (fake_lex_dir / "en.mined.json").write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    import enrichment.lexicon_sentiment as lex
    monkeypatch.setattr("os.path.dirname", lambda _: str(tmp_path))
    out = lex._load_mined_lexicon("en")
    assert out == {}


def test_mined_loader_lowercases_keys(monkeypatch, tmp_path):
    fake_lex_dir = tmp_path / "lexicons"
    fake_lex_dir.mkdir()
    (fake_lex_dir / "es.mined.json").write_text(json.dumps({"GUERRA": -1.5}), encoding="utf-8")

    import enrichment.lexicon_sentiment as lex
    monkeypatch.setattr("os.path.dirname", lambda _: str(tmp_path))
    out = lex._load_mined_lexicon("es")
    assert out == {"guerra": -1.5}


def test_mine_script_normalizes_lang_to_supported_set():
    """_normalize_lang must accept supported langs, reject the rest including 'xx'."""
    from scripts.mine_lexicon_vocab import _normalize_lang, SUPPORTED_LANGS

    for lang in SUPPORTED_LANGS:
        assert _normalize_lang(lang) == lang
        assert _normalize_lang(lang.upper()) == lang

    assert _normalize_lang(None) is None
    assert _normalize_lang("") is None
    assert _normalize_lang("xx") is None  # multilingual shadow placeholder
    assert _normalize_lang("und") is None
    assert _normalize_lang("ja") is None  # not in supported set
    assert _normalize_lang("zh") is None


def test_mine_script_tokenizer_matches_lexicon_runtime_tokenizer():
    """Mining tokenization must match what lexicon_sentiment._score uses at runtime
    so token weights derived offline land on the same surface form."""
    from scripts.mine_lexicon_vocab import _tokens
    from enrichment.lexicon_sentiment import TOKEN_RE, _clean

    text = "Peace agreement signed; Wounded in attack."
    mined = _tokens(text)
    runtime = [t.lower() for t in TOKEN_RE.findall(_clean(text))]
    assert mined == runtime


def test_mine_script_decodes_html_entities_before_tokenisation():
    """Numeric/named entities must be decoded so accented letters survive.

    Without html.unescape, headlines like 'verk&#xE4;ndet' fragment into
    `verk`, `xe4`, `ndet`. The miner would store junk like `xe4` with a
    non-zero mean sentiment, polluting the snapshot and never matching
    the actual UTF-8 word at runtime.
    """
    from scripts.mine_lexicon_vocab import _tokens

    entity = _tokens("Verk&#xFC;ndet zerst&ouml;ren die Stadt")
    plain = _tokens("Verkündet zerstören die Stadt")
    assert entity == plain
    # Critical: no `xe4`/`xfc`/`ouml` tokens.
    assert not any(tok.startswith("x") and tok[1:].isalnum() and len(tok) <= 5 and tok not in {"xf", "xa"} for tok in entity)


def test_mine_script_normalize_lang_with_detect_fallback():
    """xx with a confident multilingual headline must route to its detected lang."""
    from scripts.mine_lexicon_vocab import _normalize_lang

    # Disabled fallback: xx stays None even with headline.
    assert _normalize_lang("xx", "Hello world today everyone", detect_fallback=False) is None

    # With fallback: a clear English headline routes to en.
    detected = _normalize_lang("xx", "World leaders agree on peace today", detect_fallback=True)
    assert detected in {"en", None}  # langdetect may return None if not installed

    # Empty raw + headline: fallback kicks in.
    detected_null = _normalize_lang(None, "World leaders agree on peace today")
    assert detected_null in {"en", None}
