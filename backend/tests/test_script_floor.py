"""Script-aware headline length floor (2026-07-30, threading-floor diagnosis).

`docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md` §1/§6.3
found the R1 scoped-snapshot pull's `length(headline) >= 20` is Latin-
calibrated: real, complete CJK headlines routinely sit at 10-19 characters,
so the flat floor throttles the JP/KR/TW/CN funnel disproportionately vs
every Latin-script witness (measured follow-up:
`docs/research/recall-229/2026-07-30-cjk-length-floor-measurement.md`).

These tests pin the pure module (`backend/scripts/script_floor.py`) that
implements the fix: real ja/zh/ko examples pulled from prod during the
measurement (some genuine headlines, some non-CJK junk that must NOT be
rescued), the CJK-dominance boundary, and the Python/SQL mirror agreement.
No DB/network — pure string/regex logic only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.scripts import script_floor as sf  # noqa: E402


# ------------------------------------------------------------- cjk_ratio


def test_cjk_ratio_none_and_empty_are_zero():
    assert sf.cjk_ratio(None) == 0.0
    assert sf.cjk_ratio("") == 0.0
    assert sf.cjk_ratio("   ") == 0.0


def test_cjk_ratio_pure_latin_is_zero():
    assert sf.cjk_ratio("Best Air Bathtubs") == 0.0
    assert sf.cjk_ratio("Content 23748045") == 0.0


def test_cjk_ratio_pure_cjk_is_one():
    # "Japan" in Japanese kanji — 2 chars, both Han.
    assert sf.cjk_ratio("日本") == 1.0


def test_cjk_ratio_mixed_is_between():
    # 1 kanji among 6 chars.
    r = sf.cjk_ratio("Tokyo 東")
    assert 0.0 < r < 1.0


# ------------------------------------------------------- is_cjk_dominant


def test_real_japanese_headline_is_cjk_dominant():
    # Real prod headline (JP subject, 168h sample), 19 chars, a complete
    # sentence: "Japan had 8 magnitude-7+ quakes in 30 years, 3 in Kumamoto."
    h = "日本30年來8次震度7劇震 熊本占3次"
    assert len(h) == 19
    assert sf.is_cjk_dominant(h)


def test_real_korean_headline_is_cjk_dominant():
    # Real prod headline (KR subject, 168h sample), 18 chars, a complete
    # sentence about a National Assembly committee session.
    h = "국회 제02차 정무위원회 전체회의"
    assert len(h) == 18
    assert sf.is_cjk_dominant(h)


def test_non_cjk_junk_headline_is_not_cjk_dominant():
    # Real prod junk (scraper placeholder), also short — must NOT be
    # classified CJK-dominant, so it keeps failing the Latin floor.
    for junk in ("Content 23748045", "T20260728 376794", "Rid Atpress 617007",
                 "072026 1927143", "1000"):
        assert not sf.is_cjk_dominant(junk), junk


def test_english_headline_about_asia_is_not_cjk_dominant():
    assert not sf.is_cjk_dominant("Tokyo Stock Exchange rallies on GDP data")


def test_boundary_exactly_half_is_not_dominant():
    # "day" (3 Latin) + one CJK char = 1/4 = 0.25, not dominant either way;
    # construct an exact 0.5 split to pin the STRICT ">" cut.
    half = "AB" + "日本"  # 2 Latin + 2 CJK = ratio exactly 0.5
    assert sf.cjk_ratio(half) == 0.5
    assert not sf.is_cjk_dominant(half)  # strict >, not >=


def test_boundary_just_over_half_is_dominant():
    just_over = "A" + "日本"  # 1 Latin + 2 CJK = ratio 2/3
    assert sf.cjk_ratio(just_over) > 0.5
    assert sf.is_cjk_dominant(just_over)


# --------------------------------------------------- effective_headline_floor


def test_floor_is_10_for_cjk_dominant():
    assert sf.effective_headline_floor("日本30年來8次震度7劇震 熊本占3次") == 10


def test_floor_is_20_for_latin():
    assert sf.effective_headline_floor("Best Air Bathtubs") == 20


def test_floor_is_20_for_non_cjk_junk():
    assert sf.effective_headline_floor("Content 23748045") == 20


def test_floor_is_20_for_none_or_empty():
    assert sf.effective_headline_floor(None) == 20
    assert sf.effective_headline_floor("") == 20


def test_rescued_headlines_clear_the_new_floor_but_not_the_old():
    # The exact rescue case the diagnosis calls out: 19 real CJK chars,
    # fails length>=20, passes length>=10.
    h = "日本30年來8次震度7劇震 熊本占3次"
    assert len(h) < 20
    assert len(h) >= sf.effective_headline_floor(h)
    assert len(h) < sf.LATIN_FLOOR


def test_still_too_short_even_for_the_cjk_floor():
    # A 2-char CJK fragment stays excluded under either floor — the fix
    # rescues short-but-complete headlines, not fragments.
    h = "日本"
    assert sf.is_cjk_dominant(h)
    assert len(h) < sf.effective_headline_floor(h)


# ------------------------------------------------------------- the SQL gate


def test_gate_default_off(monkeypatch):
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    assert sf.cjk_len_floor_enabled() is False


def test_gate_garbage_is_off(monkeypatch):
    monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", "banana")
    assert sf.cjk_len_floor_enabled() is False


def test_gate_on_values(monkeypatch):
    for v in ("1", "true", "True", "on", "ON", "yes"):
        monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", v)
        assert sf.cjk_len_floor_enabled() is True, v


def test_predicate_off_is_byte_identical_flat_floor(monkeypatch):
    monkeypatch.delenv("ATLAS_CJK_LEN_FLOOR", raising=False)
    assert sf.headline_length_predicate("s.headline") == "length(s.headline) >= 20"
    assert sf.headline_length_predicate("headline") == "length(headline) >= 20"


def test_predicate_on_is_the_case_expression(monkeypatch):
    monkeypatch.setenv("ATLAS_CJK_LEN_FLOOR", "on")
    pred = sf.headline_length_predicate("s.headline")
    assert pred == sf.headline_floor_sql("s.headline")
    assert "CASE WHEN" in pred
    assert "s.headline" in pred
    assert "10" in pred and "20" in pred


def test_sql_class_mirrors_the_python_regex_ranges():
    # The four unicode blocks embedded in the SQL bracket expression must be
    # the identical codepoint ranges the Python regex matches — this is the
    # "MUST stay in lockstep" comment in script_floor.py, pinned as a test so
    # a future edit to one side trips the other.
    sql = sf.headline_floor_sql("headline")
    for boundary_char in ("぀", "ヿ", "㐀", "䶿", "一",
                          "鿿", "가", "힣"):
        assert boundary_char in sql, repr(boundary_char)
        assert sf._CJK_CHAR_RE.match(boundary_char), repr(boundary_char)
