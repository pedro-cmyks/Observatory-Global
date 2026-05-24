"""Generate a repeatable quality snapshot for Narrative Threads.

The script intentionally reads the public `/api/v2/threads` contract instead
of querying production databases. That keeps it usable locally and makes the
quality grading functions easy to test without network access.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


HIGH_VOLUME_SIGNAL_COUNT = 100


def _get_quality(thread: dict[str, Any]) -> dict[str, Any]:
    quality = thread.get("quality")
    return quality if isinstance(quality, dict) else {}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _truthy_flags(value: Any) -> list[str]:
    """Normalize flag shapes from old/new contracts into a list of active flags."""
    if isinstance(value, dict):
        return sorted(str(key) for key, active in value.items() if bool(active))
    if isinstance(value, (list, tuple, set)):
        return sorted(str(item) for item in value if item)
    if isinstance(value, str) and value:
        return [value]
    return []


def thread_id(thread: dict[str, Any]) -> str:
    return str(
        thread.get("thread_id")
        or thread.get("topic_slug")
        or thread.get("slug")
        or thread.get("id")
        or "unknown"
    )


def thread_label(thread: dict[str, Any]) -> str:
    return str(
        thread.get("label")
        or thread.get("thread_label")
        or thread.get("topic_label")
        or thread_id(thread)
    )


def lex_pct(thread: dict[str, Any]) -> float | None:
    quality = _get_quality(thread)
    value = quality.get("lex_pct", thread.get("lex_pct"))
    return _as_float(value)


def quality_flags(thread: dict[str, Any], flag_name: str) -> list[str]:
    quality = _get_quality(thread)
    return _truthy_flags(quality.get(flag_name, thread.get(flag_name)))


def grade_thread_quality(thread: dict[str, Any]) -> str:
    """Return `pass`, `review`, or `fail` for a thread quality row.

    Heuristic is intentionally conservative and explainable:
    - any active entity/source/geography flag fails the row;
    - high-volume rows fail when fewer than 20% of assignments are lexical;
    - rows pass only when lexical support is at least 30% and no flags fire;
    - everything else needs review.
    """
    active_flags = (
        quality_flags(thread, "source_flags")
        + quality_flags(thread, "geo_flags")
        + quality_flags(thread, "entity_flags")
    )
    if active_flags:
        return "fail"

    signal_count = _as_int(thread.get("signal_count"))
    lexical_pct = lex_pct(thread)
    if (
        signal_count >= HIGH_VOLUME_SIGNAL_COUNT
        and lexical_pct is not None
        and lexical_pct < 0.2
    ):
        return "fail"

    if lexical_pct is not None and lexical_pct >= 0.3:
        return "pass"

    return "review"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1%}"


def _format_flags(flags: list[str]) -> str:
    return ", ".join(flags) if flags else "-"


def _escape_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def thread_quality_row(thread: dict[str, Any]) -> dict[str, str]:
    return {
        "topic/thread id": thread_id(thread),
        "label": thread_label(thread),
        "signal_count": str(_as_int(thread.get("signal_count"))),
        "lex_pct": _format_pct(lex_pct(thread)),
        "confidence": str(thread.get("confidence") or thread.get("confidence_band") or "n/a"),
        "source_flags": _format_flags(quality_flags(thread, "source_flags")),
        "geo_flags": _format_flags(quality_flags(thread, "geo_flags")),
        "entity_flags": _format_flags(quality_flags(thread, "entity_flags")),
        "grade": grade_thread_quality(thread),
    }


def format_markdown(threads: list[dict[str, Any]], *, hours: int, api_url: str) -> str:
    rows = [thread_quality_row(thread) for thread in threads]
    headers = [
        "topic/thread id",
        "label",
        "signal_count",
        "lex_pct",
        "confidence",
        "source_flags",
        "geo_flags",
        "entity_flags",
        "grade",
    ]

    lines = [
        "# Thread Quality Snapshot",
        "",
        f"- API: `{api_url}`",
        f"- Window: `{hours}h`",
        f"- Rows: `{len(rows)}`",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(row[header]) for header in headers) + " |")

    for thread in threads:
        evidence = thread.get("evidence_samples")
        if not isinstance(evidence, list) or not evidence:
            continue

        lines.extend(["", f"## Evidence: `{thread_id(thread)}`", ""])
        for item in evidence[:8]:
            if not isinstance(item, dict):
                continue
            headline = _escape_cell(item.get("headline") or item.get("title") or "")
            source = _escape_cell(item.get("source") or item.get("source_name") or "unknown")
            country = _escape_cell(item.get("country_code") or "")
            role = _escape_cell(item.get("evidence_role") or "representative")
            lines.append(f"- **{source}** {country} `{role}`: {headline}")
    lines.append("")
    return "\n".join(lines)


def fetch_threads(api_url: str, *, hours: int, limit: int) -> list[dict[str, Any]]:
    base = api_url.rstrip("/")
    params = urllib.parse.urlencode({"hours": hours, "limit": limit})
    url = f"{base}/api/v2/threads?{params}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    candidates = payload.get("threads") or payload.get("items") or payload.get("data") or []
    if not isinstance(candidates, list):
        raise ValueError("Thread API response did not contain a thread list")
    return [item for item in candidates if isinstance(item, dict)]


def fetch_thread_detail(api_url: str, thread: dict[str, Any], *, hours: int) -> dict[str, Any]:
    base = api_url.rstrip("/")
    encoded_id = urllib.parse.quote(thread_id(thread), safe="")
    params = urllib.parse.urlencode({"hours": hours})
    url = f"{base}/api/v2/threads/{encoded_id}?{params}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("thread"), dict):
        return payload["thread"]
    if isinstance(payload, dict):
        return payload
    return thread


def attach_evidence(api_url: str, threads: list[dict[str, Any]], *, hours: int) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for thread in threads:
        try:
            detail = fetch_thread_detail(api_url, thread, hours=hours)
        except Exception as exc:  # pragma: no cover - network-specific fallback
            copy = dict(thread)
            copy["evidence_error"] = str(exc)
            enriched.append(copy)
            continue
        merged = dict(thread)
        if isinstance(detail.get("evidence_samples"), list):
            merged["evidence_samples"] = detail["evidence_samples"]
        enriched.append(merged)
    return enriched


def write_report(markdown: str, out: str | None) -> None:
    if not out:
        return
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Narrative Threads quality report")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--out", help="Optional markdown output path")
    args = parser.parse_args(argv)

    threads = fetch_threads(args.api_url, hours=args.hours, limit=args.limit)
    threads = attach_evidence(args.api_url, threads, hours=args.hours)
    markdown = format_markdown(threads, hours=args.hours, api_url=args.api_url)
    write_report(markdown, args.out)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
