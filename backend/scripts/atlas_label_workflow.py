#!/usr/bin/env python3
"""Manage Atlas benchmark labeling batches.

This helper is intentionally file-based and read-only against production data.
It keeps the paper/validation workflow reproducible:

- `split` turns a JSONL sample into numbered batch files.
- `progress` reports how many rows have labels.
- `merge` combines batch files back into one JSONL file for scoring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def split_batches(
    *,
    input_path: Path,
    output_dir: Path,
    batch_size: int,
    prefix: str,
) -> list[Path]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    rows = read_jsonl(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, start in enumerate(range(0, len(rows), batch_size), start=1):
        batch_rows = rows[start : start + batch_size]
        path = output_dir / f"{prefix}-batch-{index:02d}.jsonl"
        write_jsonl(path, batch_rows)
        written.append(path)

    return written


def label_progress(paths: Iterable[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_rows = 0
    labeled_rows = 0

    for path in sorted(paths):
        rows = read_jsonl(path)
        row_count = len(rows)
        labeled_count = sum(1 for row in rows if row.get("gold_decision") is not None)
        total_rows += row_count
        labeled_rows += labeled_count
        files.append(
            {
                "path": str(path),
                "rows": row_count,
                "labeled": labeled_count,
                "remaining": row_count - labeled_count,
            }
        )

    return {
        "files": files,
        "total_rows": total_rows,
        "labeled_rows": labeled_rows,
        "remaining_rows": total_rows - labeled_rows,
        "progress_pct": round(labeled_rows / total_rows, 4) if total_rows else None,
    }


def merge_batches(*, input_dir: Path, output_path: Path, pattern: str) -> int:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob(pattern)):
        rows.extend(read_jsonl(path))
    write_jsonl(output_path, rows)
    return len(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas labeling workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    split = subparsers.add_parser("split", help="Split a sample JSONL into batches")
    split.add_argument("--input", type=Path, required=True)
    split.add_argument("--output-dir", type=Path, required=True)
    split.add_argument("--batch-size", type=int, default=32)
    split.add_argument("--prefix", required=True)

    progress = subparsers.add_parser("progress", help="Report label progress")
    progress.add_argument("paths", type=Path, nargs="+")

    merge = subparsers.add_parser("merge", help="Merge labeled batches")
    merge.add_argument("--input-dir", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--pattern", default="*.jsonl")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "split":
        paths = split_batches(
            input_path=args.input,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            prefix=args.prefix,
        )
        print(json.dumps({"written": [str(path) for path in paths]}, indent=2))
        return

    if args.command == "progress":
        print(json.dumps(label_progress(args.paths), indent=2, sort_keys=True))
        return

    row_count = merge_batches(
        input_dir=args.input_dir,
        output_path=args.output,
        pattern=args.pattern,
    )
    print(json.dumps({"output": str(args.output), "rows": row_count}, indent=2))


if __name__ == "__main__":
    main()
