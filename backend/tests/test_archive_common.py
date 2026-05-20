from __future__ import annotations

import json
from datetime import datetime, timezone

from scripts.archive_common import (
    ARCHIVE_VERSION,
    ArchiveFilters,
    ArchiveManifestRecord,
    append_manifest,
    iter_archive_rows,
    parse_timestamp,
    partition_path,
    row_matches,
    write_jsonl_gzip,
)
from scripts.archive_query import query_archive
from scripts.local_archive_worker import is_inside_window, parse_clock
from scripts.nlp_sla_report import coverage_pct


def test_partition_path_is_date_and_family_scoped(tmp_path):
    ts = parse_timestamp("2026-05-19T00:00:00Z")

    path = partition_path(tmp_path, ts, "social", "job:123")

    assert path.relative_to(tmp_path).as_posix() == (
        "signals/year=2026/month=05/day=19/source_family=social/part-job-123.jsonl.gz"
    )


def test_write_manifest_and_query_archive(tmp_path):
    ts = parse_timestamp("2026-05-19T03:00:00Z")
    path = partition_path(tmp_path, ts, "social", "abc")
    rows = [
        {
            "id": 1,
            "timestamp": "2026-05-19T03:00:00Z",
            "country_code": "CO",
            "source_family": "social",
            "source_name": "reddit",
            "headline": "Colombia energy protest discussion",
            "themes": ["energy_security"],
        },
        {
            "id": 2,
            "timestamp": "2026-05-19T04:00:00Z",
            "country_code": "MX",
            "source_family": "api",
            "source_name": "newsdata",
            "headline": "Mexico infrastructure update",
            "themes": ["infrastructure"],
        },
    ]

    count, digest, byte_count = write_jsonl_gzip(path, rows)
    append_manifest(
        tmp_path,
        ArchiveManifestRecord(
            archive_version=ARCHIVE_VERSION,
            kind="signals_v2_export",
            created_at="2026-05-20T00:00:00Z",
            from_ts="2026-05-19T00:00:00Z",
            to_ts="2026-05-20T00:00:00Z",
            source_family="mixed",
            row_count=count,
            relative_path=str(path.relative_to(tmp_path)),
            sha256=digest,
            bytes=byte_count,
            command="test",
        ),
    )

    assert count == 2
    manifest = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(manifest)["row_count"] == 2
    assert len(list(iter_archive_rows(tmp_path))) == 2

    matches = query_archive(
        archive_dir=tmp_path,
        filters=ArchiveFilters(country="CO", source_family="social", topic="energy"),
        limit=10,
    )
    assert [row["id"] for row in matches] == [1]


def test_row_matches_time_window_and_source_name():
    row = {
        "timestamp": "2026-05-19T03:00:00Z",
        "country_code": "CO",
        "source_family": "rss",
        "source_name": "BBC Mundo",
        "headline": "Election coverage",
        "themes": ["politics"],
    }

    assert row_matches(
        row,
        ArchiveFilters(
            from_ts=parse_timestamp("2026-05-19T00:00:00Z"),
            to_ts=parse_timestamp("2026-05-20T00:00:00Z"),
            source_name_contains="bbc",
        ),
    )
    assert not row_matches(row, ArchiveFilters(country="BR"))


def test_parse_timestamp_normalizes_to_utc():
    parsed = parse_timestamp("2026-05-19T03:00:00-05:00")

    assert parsed.tzinfo == timezone.utc
    assert parsed.hour == 8


def test_sla_coverage_pct():
    assert coverage_pct(90, 100) == 90.0
    assert coverage_pct(0, 0) == 100.0


def test_local_worker_window():
    assert is_inside_window(
        datetime(2026, 5, 20, 3, 0),
        parse_clock("00:00"),
        parse_clock("06:00"),
    )
    assert not is_inside_window(
        datetime(2026, 5, 20, 10, 0),
        parse_clock("00:00"),
        parse_clock("06:00"),
    )
