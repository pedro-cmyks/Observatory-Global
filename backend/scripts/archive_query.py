"""Query the local Atlas archive without connecting to Supabase."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scripts.archive_common import ArchiveFilters, iter_archive_rows, parse_timestamp, row_matches


def query_archive(
    *,
    archive_dir: Path,
    filters: ArchiveFilters,
    limit: int,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in iter_archive_rows(archive_dir):
        if row_matches(row, filters):
            matches.append(row)
            if len(matches) >= limit:
                break
    return matches


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas local archive query")
    parser.add_argument("--archive-dir", default=os.environ.get("ATLAS_ARCHIVE_DIR"))
    parser.add_argument("--from", dest="from_ts", default=None, help="Inclusive ISO timestamp")
    parser.add_argument("--to", dest="to_ts", default=None, help="Exclusive ISO timestamp")
    parser.add_argument("--country", default=None)
    parser.add_argument("--source-family", default=None)
    parser.add_argument("--source-name-contains", default=None)
    parser.add_argument("--topic", default=None, help="Substring match against headline or themes")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--summary", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.archive_dir:
        raise SystemExit("ATLAS_ARCHIVE_DIR or --archive-dir is required")
    filters = ArchiveFilters(
        from_ts=parse_timestamp(args.from_ts) if args.from_ts else None,
        to_ts=parse_timestamp(args.to_ts) if args.to_ts else None,
        country=args.country,
        source_family=args.source_family,
        source_name_contains=args.source_name_contains,
        topic=args.topic,
    )
    rows = query_archive(
        archive_dir=Path(args.archive_dir).expanduser(),
        filters=filters,
        limit=max(args.limit, 1),
    )
    if args.summary:
        print(json.dumps({"matched": len(rows), "limit": args.limit}, sort_keys=True))
        return
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
