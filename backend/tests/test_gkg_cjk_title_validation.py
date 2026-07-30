"""CJK PAGE_TITLE must survive the ingest title validation.

MEASURED (prod, 2026-07-30, 168h): headline IS NULL on 53.3% of CN, 45.5% of
TW and 38.5% of JP `gdelt_gkg_translated` rows, vs ~0% on the English GKG
lane and on RSS/NewsData. Replaying the exact validation over a live
translingual GKG file proved the mechanism: GDELT ships ``<PAGE_TITLE>`` for
99.8% of rows, but ``len(candidate.split()) >= 4`` is script-blind — a
complete Japanese/Chinese headline has 1-3 space-separated tokens, so the
title was discarded and the URL-slug fallback also failed (CJK press URLs
are numeric IDs). 89.9% of validation failures were CJK-dominant titles.

Full diagnosis: docs/research/recall-229/2026-07-30-gdelt-null-headline-diagnosis.md

The fix admits a title that is CJK-dominant (>50% of chars in the same four
unicode blocks as scripts/script_floor.py) AND >= 10 chars. Junk placeholder
classes stay rejected: they are ASCII ("Content 23748045") or pure doc-ids.
"""
from __future__ import annotations

from app.services.ingest_v2 import parse_gkg_row


def _row(title: str, url: str = "https://www.asahi.com/articles/ASV7S0TMNV7STIPE007M.html") -> list:
    row = ["20260730120000", "", "", "outlet", url] + [""] * 22
    row[10] = "1#Japan#JA##36.0#138.0#00#20"
    row[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
    return row


class TestCjkTitlesKept:
    def test_japanese_title_two_tokens_kept(self):
        # Real mainichi headline from the live-file replay: 2 "words" via
        # ideographic spaces, previously dropped -> NULL.
        title = "避難所が暑く、アスファルトの上で寝る被災者　現地入りの医師が見た「猛暑」の熊本地震"
        out = parse_gkg_row(_row(title), source_lang="xx")
        assert out is not None
        assert out["headline"] == title

    def test_japanese_title_single_token_kept(self):
        title = "【茨城新聞】島国ナウル、「ナオエロ」に改称"
        out = parse_gkg_row(_row(title), source_lang="xx")
        assert out is not None
        assert out["headline"] == title

    def test_chinese_title_no_spaces_kept(self):
        title = "日本30年來8次震度7劇震熊本占3次"
        out = parse_gkg_row(_row(title), source_lang="xx")
        assert out is not None
        assert out["headline"] == title

    def test_korean_title_short_of_four_words_kept(self):
        title = "국회 제02차 정무위원회 전체회의"
        out = parse_gkg_row(_row(title), source_lang="xx")
        assert out is not None
        assert out["headline"] == title


class TestJunkStillRejected:
    """The placeholder classes that motivated the >=4-word check are ASCII —
    never CJK-dominant — and must keep falling to the slug fallback / NULL."""

    def _headline_of(self, title: str):
        # Numeric-ID URL (the real JP pattern): no slug fallback available,
        # so a rejected title means headline is None.
        out = parse_gkg_row(_row(title, url="https://373news.com/news/national/detail/2026072401000541/"), source_lang="xx")
        return None if out is None else out["headline"]

    def test_ascii_placeholder_rejected(self):
        assert self._headline_of("Content 23748045") is None

    def test_date_id_scrape_rejected(self):
        assert self._headline_of("T20260728 376794") is None

    def test_pure_docid_rejected(self):
        assert self._headline_of("2026072812345678") is None

    def test_cjk_boilerplate_under_floor_rejected(self):
        # Nav-title boilerplate: CJK-dominant but < 10 chars.
        assert self._headline_of("ニュース一覧") is None

    def test_mostly_latin_short_title_rejected(self):
        # Latin path unchanged: 3 words, not CJK-dominant -> still dropped.
        assert self._headline_of("Porsche Cayenne Electric") is None


class TestLatinPathByteIdentical:
    def test_four_word_english_title_kept(self):
        title = "Quake shakes northern Japan coast"
        out = parse_gkg_row(_row(title), source_lang="en")
        assert out is not None
        assert out["headline"] == title
