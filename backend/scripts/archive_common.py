"""Local archive helpers for Atlas hot/cold data operations.

The archive format intentionally starts with stdlib-only JSONL gzip partitions.
That keeps the local worker independent from Fly image size and lets us add
DuckDB/Parquet as an optional local accelerator later.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Iterator

import gzip
import hashlib
import json
import re


ARCHIVE_VERSION = 1
MANIFEST_FILE = "manifest.jsonl"


@dataclass(frozen=True)
class ArchiveManifestRecord:
    archive_version: int
    kind: str
    created_at: str
    from_ts: str
    to_ts: str
    source_family: str
    row_count: int
    relative_path: str
    sha256: str
    bytes: int
    command: str


@dataclass(frozen=True)
class ArchiveFilters:
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    country: str | None = None
    source_family: str | None = None
    source_name_contains: str | None = None
    topic: str | None = None


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp, accepting a trailing Z."""
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def normalize_row(row: Any) -> dict[str, Any]:
    """Convert asyncpg rows, dicts, and nested values to JSON-safe dictionaries."""
    if hasattr(row, "items"):
        items = row.items()
    else:
        items = dict(row).items()
    return {str(k): to_jsonable(v) for k, v in items}


def slug(value: str | None, fallback: str = "unknown") -> str:
    raw = (value or fallback).strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    return cleaned or fallback


def partition_path(
    archive_dir: Path,
    from_ts: datetime,
    source_family: str | None,
    job_id: str,
) -> Path:
    family = slug(source_family or "mixed")
    return (
        archive_dir
        / "signals"
        / f"year={from_ts.year:04d}"
        / f"month={from_ts.month:02d}"
        / f"day={from_ts.day:02d}"
        / f"source_family={family}"
        / f"part-{slug(job_id)}.jsonl.gz"
    )


def write_jsonl_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> tuple[int, str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            encoded = line.encode("utf-8")
            digest.update(encoded)
            digest.update(b"\n")
            handle.write(line)
            handle.write("\n")
            count += 1
    return count, digest.hexdigest(), path.stat().st_size


def append_manifest(archive_dir: Path, record: ArchiveManifestRecord) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest = archive_dir / MANIFEST_FILE
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def iter_manifest_records(archive_dir: Path) -> Iterator[ArchiveManifestRecord]:
    manifest = archive_dir / MANIFEST_FILE
    if not manifest.exists():
        return
    with manifest.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            yield ArchiveManifestRecord(**payload)


def verify_archive_file(archive_dir: Path, record: ArchiveManifestRecord) -> dict[str, Any]:
    path = archive_dir / record.relative_path
    result: dict[str, Any] = {
        "relative_path": record.relative_path,
        "from_ts": record.from_ts,
        "to_ts": record.to_ts,
        "source_family": record.source_family,
        "expected_rows": record.row_count,
        "expected_sha256": record.sha256,
        "exists": path.exists(),
        "ok": False,
    }
    if not path.exists():
        result["error"] = "missing_file"
        return result

    digest = hashlib.sha256()
    count = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                encoded = line.rstrip("\n").encode("utf-8")
                digest.update(encoded)
                digest.update(b"\n")
                count += 1
    except OSError as exc:
        result["error"] = f"gzip_read_failed:{exc}"
        return result

    actual_sha = digest.hexdigest()
    actual_bytes = path.stat().st_size
    result.update(
        {
            "actual_rows": count,
            "actual_sha256": actual_sha,
            "expected_bytes": record.bytes,
            "actual_bytes": actual_bytes,
            "rows_ok": count == record.row_count,
            "sha256_ok": actual_sha == record.sha256,
            "bytes_ok": actual_bytes == record.bytes,
        }
    )
    result["ok"] = bool(result["rows_ok"] and result["sha256_ok"] and result["bytes_ok"])
    return result


def iter_archive_files(archive_dir: Path) -> Iterator[Path]:
    yield from sorted((archive_dir / "signals").glob("**/*.jsonl.gz"))


def iter_archive_rows(archive_dir: Path) -> Iterator[dict[str, Any]]:
    for path in iter_archive_files(archive_dir):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def row_matches(row: dict[str, Any], filters: ArchiveFilters) -> bool:
    if filters.country and (row.get("country_code") or "").upper() != filters.country.upper():
        return False
    if filters.source_family and row.get("source_family") != filters.source_family:
        return False
    if filters.source_name_contains:
        needle = filters.source_name_contains.lower()
        if needle not in (row.get("source_name") or "").lower():
            return False
    if filters.topic:
        needle = filters.topic.lower()
        themes = [str(t).lower() for t in row.get("themes") or []]
        headline = (row.get("headline") or "").lower()
        if needle not in headline and not any(needle in theme for theme in themes):
            return False
    ts_raw = row.get("timestamp") or row.get("created_at")
    if ts_raw and (filters.from_ts or filters.to_ts):
        ts = parse_timestamp(str(ts_raw))
        if filters.from_ts and ts < filters.from_ts:
            return False
        if filters.to_ts and ts >= filters.to_ts:
            return False
    return True
