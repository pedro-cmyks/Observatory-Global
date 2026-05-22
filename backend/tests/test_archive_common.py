from __future__ import annotations

import json
from datetime import datetime, timezone

from scripts.archive_common import (
    ARCHIVE_VERSION,
    ArchiveFilters,
    ArchiveManifestRecord,
    append_manifest,
    iter_manifest_records,
    iter_archive_rows,
    parse_timestamp,
    partition_path,
    row_matches,
    verify_archive_file,
    write_jsonl_gzip,
)
from scripts.archive_verify import verify_archive
from scripts.prune_archived_signals import covered_manifest_ranges
from scripts.archive_query import query_archive
from scripts.local_archive_worker import is_inside_window, parse_clock
from scripts.local_hot_cold_catchup import (
    collect_rows_for_day,
    days_touched_by_records,
    discover_archive_roots,
)
from scripts.nlp_sla_report import BREAKDOWN_SQL, coverage_pct


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
    assert len(list(iter_manifest_records(tmp_path))) == 1
    file_check = verify_archive_file(tmp_path, next(iter_manifest_records(tmp_path)))
    assert file_check["ok"] is True
    assert file_check["actual_rows"] == 2

    archive_check = verify_archive(tmp_path)
    assert archive_check["ok"] is True
    assert archive_check["total_rows"] == 2

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


def test_sla_breakdown_reports_enrichment_gap_not_only_raw_rows():
    assert "AS gap_rows" in BREAKDOWN_SQL
    assert "provenance_only_rows" in BREAKDOWN_SQL
    assert "ORDER BY gap_rows DESC" in BREAKDOWN_SQL


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


def test_archive_verify_detects_modified_file(tmp_path):
    ts = parse_timestamp("2026-05-19T03:00:00Z")
    path = partition_path(tmp_path, ts, "api", "abc")
    count, digest, byte_count = write_jsonl_gzip(
        path,
        [{"id": 1, "timestamp": "2026-05-19T03:00:00Z", "headline": "original"}],
    )
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
    write_jsonl_gzip(path, [{"id": 2, "timestamp": "2026-05-19T03:00:00Z", "headline": "changed"}])

    result = verify_archive(tmp_path)

    assert result["ok"] is False
    assert result["failed_records"] == 1
    assert result["failures"][0]["sha256_ok"] is False


def test_archive_verify_detects_overlapping_manifest_ranges(tmp_path):
    ts = parse_timestamp("2026-05-19T00:00:00Z")
    path_a = partition_path(tmp_path, ts, "mixed", "a")
    path_b = partition_path(tmp_path, ts, "mixed", "b")
    count_a, digest_a, bytes_a = write_jsonl_gzip(path_a, [{"id": 1}])
    count_b, digest_b, bytes_b = write_jsonl_gzip(path_b, [{"id": 2}])
    for path, count, digest, byte_count, from_ts, to_ts in [
        (path_a, count_a, digest_a, bytes_a, "2026-05-19T00:00:00Z", "2026-05-19T01:00:00Z"),
        (path_b, count_b, digest_b, bytes_b, "2026-05-19T00:30:00Z", "2026-05-19T02:00:00Z"),
    ]:
        append_manifest(
            tmp_path,
            ArchiveManifestRecord(
                archive_version=ARCHIVE_VERSION,
                kind="signals_v2_export",
                created_at="2026-05-20T00:00:00Z",
                from_ts=from_ts,
                to_ts=to_ts,
                source_family="mixed",
                row_count=count,
                relative_path=str(path.relative_to(tmp_path)),
                sha256=digest,
                bytes=byte_count,
                command="test",
            ),
        )

    result = verify_archive(tmp_path)

    assert result["ok"] is False
    assert result["failed_records"] == 0
    assert result["overlap_count"] == 1


def test_prune_ranges_only_include_manifest_ranges_before_cutoff(tmp_path):
    ts = parse_timestamp("2026-05-19T00:00:00Z")
    path_a = partition_path(tmp_path, ts, "mixed", "a")
    path_b = partition_path(tmp_path, ts, "mixed", "b")
    count_a, digest_a, bytes_a = write_jsonl_gzip(path_a, [{"id": 1}])
    count_b, digest_b, bytes_b = write_jsonl_gzip(path_b, [{"id": 2}])
    for path, count, digest, byte_count, from_ts, to_ts in [
        (path_a, count_a, digest_a, bytes_a, "2026-05-18T00:00:00Z", "2026-05-19T00:00:00Z"),
        (path_b, count_b, digest_b, bytes_b, "2026-05-20T00:00:00Z", "2026-05-21T00:00:00Z"),
    ]:
        append_manifest(
            tmp_path,
            ArchiveManifestRecord(
                archive_version=ARCHIVE_VERSION,
                kind="signals_v2_export",
                created_at="2026-05-20T00:00:00Z",
                from_ts=from_ts,
                to_ts=to_ts,
                source_family="mixed",
                row_count=count,
                relative_path=str(path.relative_to(tmp_path)),
                sha256=digest,
                bytes=byte_count,
                command="test",
            ),
        )

    ranges = covered_manifest_ranges(tmp_path, parse_timestamp("2026-05-20T00:00:00Z"))

    assert len(ranges) == 1
    assert ranges[0]["row_count"] == 1


def test_catchup_days_touched_by_records_handles_cross_day_range():
    record = ArchiveManifestRecord(
        archive_version=ARCHIVE_VERSION,
        kind="signals_v2_export",
        created_at="2026-05-20T00:00:00Z",
        from_ts="2026-05-19T23:30:00Z",
        to_ts="2026-05-20T00:30:00Z",
        source_family="mixed",
        row_count=2,
        relative_path="signals/year=2026/month=05/day=19/source_family=mixed/part-test.jsonl.gz",
        sha256="abc",
        bytes=123,
        command="test",
    )

    assert [day.isoformat() for day in days_touched_by_records([record])] == [
        "2026-05-19",
        "2026-05-20",
    ]


def test_catchup_collects_combined_day_rows_without_partial_overwrite(tmp_path):
    archive_root = tmp_path / "AtlasArchive"
    cutover = archive_root / "cutovers" / "2026-05-20"
    incremental = archive_root / "incremental" / "2026-05-22-catchup"

    old_ts = parse_timestamp("2026-05-20T03:00:00Z")
    new_ts = parse_timestamp("2026-05-20T15:00:00Z")
    old_path = partition_path(cutover, old_ts, "mixed", "old")
    new_path = partition_path(incremental, new_ts, "mixed", "new")
    old_count, old_digest, old_bytes = write_jsonl_gzip(
        old_path,
        [
            {
                "id": "old",
                "timestamp": "2026-05-20T03:00:00Z",
                "country_code": "CO",
                "headline": "Old archive row",
            }
        ],
    )
    new_count, new_digest, new_bytes = write_jsonl_gzip(
        new_path,
        [
            {
                "id": "new",
                "timestamp": "2026-05-20T15:00:00Z",
                "country_code": "CO",
                "headline": "Incremental archive row",
            }
        ],
    )
    append_manifest(
        cutover,
        ArchiveManifestRecord(
            archive_version=ARCHIVE_VERSION,
            kind="signals_v2_export",
            created_at="2026-05-20T00:00:00Z",
            from_ts="2026-05-20T00:00:00Z",
            to_ts="2026-05-20T12:00:00Z",
            source_family="mixed",
            row_count=old_count,
            relative_path=str(old_path.relative_to(cutover)),
            sha256=old_digest,
            bytes=old_bytes,
            command="test",
        ),
    )
    append_manifest(
        incremental,
        ArchiveManifestRecord(
            archive_version=ARCHIVE_VERSION,
            kind="signals_v2_export",
            created_at="2026-05-22T00:00:00Z",
            from_ts="2026-05-20T12:00:00Z",
            to_ts="2026-05-21T00:00:00Z",
            source_family="mixed",
            row_count=new_count,
            relative_path=str(new_path.relative_to(incremental)),
            sha256=new_digest,
            bytes=new_bytes,
            command="test",
        ),
    )

    roots = discover_archive_roots(archive_root)
    rows = collect_rows_for_day(roots, parse_timestamp("2026-05-20T00:00:00Z").date())

    assert [row["id"] for row in rows] == ["old", "new"]
