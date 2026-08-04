"""Backfill of NULL translingual headlines: validation parity + safe rewrite.

The backfill script duplicates parse_gkg_row's fixed title validation
(ff55d6b0) in lockstep. These tests pin the parity on the SAME fixture titles
as test_gkg_cjk_title_validation.py, and prove the archive-partition rewrite
preserves every untouched line byte-identically, keeps row_count, recomputes
the manifest's uncompressed-line sha256 exactly as archive_export.py does,
backs the originals up, and is idempotent.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from backfill_null_headlines import (  # noqa: E402
    accept_title,
    parse_gkg_titles,
    rewrite_partition,
)


class TestAcceptTitleParityWithParser:
    """Same keep/drop outcomes as parse_gkg_row's validation."""

    def test_japanese_two_token_title_kept(self):
        t = "避難所が暑く、アスファルトの上で寝る被災者　現地入りの医師が見た「猛暑」の熊本地震"
        assert accept_title(t) == t

    def test_japanese_single_token_title_kept(self):
        t = "【茨城新聞】島国ナウル、「ナオエロ」に改称"
        assert accept_title(t) == t

    def test_chinese_no_spaces_kept(self):
        t = "日本30年來8次震度7劇震熊本占3次"
        assert accept_title(t) == t

    def test_korean_short_of_four_words_kept(self):
        t = "국회 제02차 정무위원회 전체회의"
        assert accept_title(t) == t

    def test_four_word_english_kept(self):
        t = "Quake shakes northern Japan coast"
        assert accept_title(t) == t

    def test_entities_decoded_before_validation(self):
        assert accept_title("hurac&#xE1;n golpea la costa norte") == \
            "huracán golpea la costa norte"

    def test_ascii_placeholder_rejected(self):
        assert accept_title("Content 23748045") is None

    def test_date_id_scrape_rejected(self):
        assert accept_title("T20260728 376794") is None

    def test_pure_docid_rejected(self):
        assert accept_title("2026072812345678") is None

    def test_cjk_boilerplate_under_floor_rejected(self):
        assert accept_title("ニュース一覧") is None

    def test_short_latin_rejected(self):
        assert accept_title("Porsche Cayenne Electric") is None

    def test_empty_rejected(self):
        assert accept_title("   ") is None


class TestParseGkgTitles:
    def _row(self, url: str, title: str | None) -> str:
        cols = [""] * 27
        cols[0] = "20260728120000"
        cols[4] = url
        if title is not None:
            cols[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
        return "\t".join(cols)

    def test_extracts_and_validates(self):
        data = "\n".join([
            self._row("https://a.jp/1", "【茨城新聞】島国ナウル、「ナオエロ」に改称"),
            self._row("https://a.jp/2", "Content 23748045"),   # junk -> dropped
            self._row("https://a.jp/3", None),                  # no title
            "short\tline",                                       # malformed
        ]).encode("utf-8")
        out: dict[str, str] = {}
        n = parse_gkg_titles(data, out)
        assert n == 1
        assert out == {"https://a.jp/1": "【茨城新聞】島国ナウル、「ナオエロ」に改称"}

    def test_first_title_wins_across_reprints(self):
        out = {"https://a.jp/1": "既存タイトルはそのまま維持される"}
        parse_gkg_titles(
            self._row("https://a.jp/1", "別のタイトルで上書きしようとする").encode(),
            out)
        assert out["https://a.jp/1"] == "既存タイトルはそのまま維持される"


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _content_sha(lines: list[str]) -> str:
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


class TestRewritePartition:
    def _make_archive(self, tmp_path: Path):
        """A miniature run dir: manifest.jsonl + one partition of 3 rows."""
        base = tmp_path / "Archive"
        part_rel = "signals/year=2026/month=07/day=20/source_family=mixed/part-abc.jsonl.gz"
        part = base / part_rel
        part.parent.mkdir(parents=True)
        rows = [
            {"id": "1", "headline": "kept untouched",
             "attribution_method": "gdelt_gkg", "source_url": "https://x/1",
             "timestamp": "2026-07-20T01:00:00Z"},
            {"id": "2", "headline": None,
             "attribution_method": "gdelt_gkg_translated",
             "source_url": "https://x/2", "timestamp": "2026-07-20T02:00:00Z"},
            {"id": "3", "headline": None,
             "attribution_method": "gdelt_gkg_translated",
             "source_url": "https://x/3", "timestamp": "2026-07-20T03:00:00Z"},
        ]
        lines = [_dumps(r) for r in rows]
        with gzip.open(part, "wt", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")
        manifest = base / "manifest.jsonl"
        rec = {"archive_version": 1, "kind": "signals_v2_export",
               "relative_path": part_rel, "row_count": 3,
               "sha256": _content_sha(lines), "bytes": part.stat().st_size}
        manifest.write_text(_dumps(rec) + "\n", encoding="utf-8")
        return base, part, manifest, lines

    def test_dry_run_touches_nothing(self, tmp_path):
        base, part, manifest, _ = self._make_archive(tmp_path)
        before = part.read_bytes()
        out = rewrite_partition(part, {2: "新しい見出しが入る"}, base,
                                tmp_path / "bak", execute=False)
        assert out["changed"] == 1
        assert part.read_bytes() == before
        assert not (tmp_path / "bak").exists()

    def test_rewrite_updates_row_manifest_and_backs_up(self, tmp_path):
        base, part, manifest, orig_lines = self._make_archive(tmp_path)
        bak = tmp_path / "bak"
        title = "避難所が暑く、被災者が路上で眠る"
        out = rewrite_partition(part, {2: title}, base, bak, execute=True)
        assert out["changed"] == 1 and out["rows"] == 3

        with gzip.open(part, "rt", encoding="utf-8") as fh:
            new_lines = [ln.rstrip("\n") for ln in fh]
        # untouched lines byte-identical, fixed row carries the title
        assert new_lines[0] == orig_lines[0]
        assert new_lines[2] == orig_lines[2]
        assert json.loads(new_lines[1])["headline"] == title
        # only the headline field differs on the fixed row
        a, b = json.loads(orig_lines[1]), json.loads(new_lines[1])
        a.pop("headline"), b.pop("headline")
        assert a == b

        # manifest: row_count unchanged, sha256 = archive_export digest of the
        # new uncompressed lines, bytes = new file size
        rec = json.loads(manifest.read_text().splitlines()[0])
        assert rec["row_count"] == 3
        assert rec["sha256"] == _content_sha(new_lines)
        assert rec["bytes"] == part.stat().st_size

        # backups hold the true originals
        assert gzip.open(bak / part.relative_to(base), "rt").read() == \
            "\n".join(orig_lines) + "\n"
        assert (bak / "manifest.jsonl").exists()

    def test_second_rewrite_keeps_first_backup(self, tmp_path):
        base, part, manifest, orig_lines = self._make_archive(tmp_path)
        bak = tmp_path / "bak"
        rewrite_partition(part, {2: "一回目の書き換えのタイトル"}, base, bak,
                          execute=True)
        rewrite_partition(part, {3: "二回目の書き換えのタイトル"}, base, bak,
                          execute=True)
        # the backup is still the pristine original, not the intermediate
        assert gzip.open(bak / part.relative_to(base), "rt").read() == \
            "\n".join(orig_lines) + "\n"
        with gzip.open(part, "rt", encoding="utf-8") as fh:
            new_lines = [ln.rstrip("\n") for ln in fh]
        assert json.loads(new_lines[1])["headline"] == "一回目の書き換えのタイトル"
        assert json.loads(new_lines[2])["headline"] == "二回目の書き換えのタイトル"
        rec = json.loads(manifest.read_text().splitlines()[0])
        assert rec["sha256"] == _content_sha(new_lines)

    def test_rewrite_is_idempotent_noop_when_no_null_left(self, tmp_path):
        base, part, manifest, _ = self._make_archive(tmp_path)
        bak = tmp_path / "bak"
        rewrite_partition(part, {2: "既に埋め戻された見出し"}, base, bak,
                          execute=True)
        after_first = part.read_bytes()
        out = rewrite_partition(part, {2: "既に埋め戻された見出し"}, base, bak,
                                execute=True)
        # row 2 no longer matches headline IS NULL -> nothing to change
        assert out["changed"] == 0
        assert part.read_bytes() == after_first
