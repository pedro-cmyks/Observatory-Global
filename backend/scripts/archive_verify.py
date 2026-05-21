"""Verify Atlas local archive manifest entries.

The verifier recomputes row counts, uncompressed-line SHA256 digests, and
compressed byte sizes for every manifest entry. It is intentionally local-only:
no Supabase connection is required.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.archive_common import iter_manifest_records, parse_timestamp, verify_archive_file


def _find_overlaps(records: list[Any]) -> list[dict[str, str]]:
    ranges_by_family: dict[str, list[tuple[Any, Any, str]]] = defaultdict(list)
    for record in records:
        ranges_by_family[record.source_family].append(
            (parse_timestamp(record.from_ts), parse_timestamp(record.to_ts), record.relative_path)
        )

    overlaps: list[dict[str, str]] = []
    for family, ranges in ranges_by_family.items():
        ordered = sorted(ranges, key=lambda item: (item[0], item[1], item[2]))
        previous: tuple[Any, Any, str] | None = None
        for current in ordered:
            if previous and current[0] < previous[1]:
                overlaps.append(
                    {
                        "source_family": family,
                        "previous_path": previous[2],
                        "current_path": current[2],
                        "previous_to": previous[1].isoformat().replace("+00:00", "Z"),
                        "current_from": current[0].isoformat().replace("+00:00", "Z"),
                    }
                )
            if previous is None or current[1] > previous[1]:
                previous = current
    return overlaps


def verify_archive(archive_dir: Path) -> dict[str, Any]:
    records = list(iter_manifest_records(archive_dir))
    checks = [verify_archive_file(archive_dir, record) for record in records]
    bad = [check for check in checks if not check.get("ok")]
    overlaps = _find_overlaps(records)
    return {
        "archive_dir": str(archive_dir),
        "manifest_records": len(records),
        "verified_records": len(checks) - len(bad),
        "failed_records": len(bad),
        "total_rows": sum(int(check.get("actual_rows") or 0) for check in checks),
        "total_bytes": sum(int(check.get("actual_bytes") or 0) for check in checks),
        "overlap_count": len(overlaps),
        "overlaps": overlaps[:20],
        "failures": bad[:20],
        "ok": not bad and not overlaps,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Atlas local archive manifest")
    parser.add_argument("--archive-dir", default=os.environ.get("ATLAS_ARCHIVE_DIR"))
    parser.add_argument("--allow-overlap", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.archive_dir:
        raise SystemExit("ATLAS_ARCHIVE_DIR or --archive-dir is required")
    result = verify_archive(Path(args.archive_dir).expanduser())
    if args.allow_overlap and result["ok"] is False and result["failed_records"] == 0:
        result["ok"] = True
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
