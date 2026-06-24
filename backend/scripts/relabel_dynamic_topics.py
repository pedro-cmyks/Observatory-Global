#!/usr/bin/env python3
"""Refresh stale/frozen dynamic_topic labels on a cadence, via the local Claude CLI.

#229 lever 5: labels were frozen at topic creation, so an evolving story kept a
stale or hallucinated label after its members drifted. This cron re-labels active
topics whose label is overdue (older than --max-age-days, or never stamped) or is
a known placeholder, using the LOCAL Claude CLI (Max plan, $0 marginal — no
external DeepSeek call). Writes label + label_updated_at + label_model.

Read-then-write, idempotent, safe to re-run. Heavy only in that it spawns the
Claude CLI per stale topic — bounded by --limit and the small active-topic count.
Run on the M1 worker (has the authenticated CLI + DATABASE_URL):
  DATABASE_URL=... .venv/bin/python -m scripts.relabel_dynamic_topics --max-age-days 7

Cron-wire it on the NIGHTLY schedule only (heavy local compute never during
working hours — same rule as the embed cron).
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.claude_label import LABEL_MODEL, label_via_claude
from scripts.project_dynamic_topics import is_roundup_label

# Placeholder labels a prior run (or a failed external call) may have written.
PLACEHOLDER_LABELS = {"", "(no label)", "(label failed)", "(label failed.)", "none", "null"}
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_LIMIT = 25
HEADLINES_PER_TOPIC = 12


def needs_relabel(
    topic: dict[str, Any],
    *,
    now: datetime,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> bool:
    """Pure staleness policy for one topic row.

    Relabel when the label is a placeholder, a roundup/grab-bag marker, or older
    than the cadence window (never-stamped rows count as overdue). Keeps recent,
    real labels untouched so the cron does no needless CLI work.
    """
    label = (topic.get("label") or "").strip()
    if label.lower() in PLACEHOLDER_LABELS:
        return True
    if is_roundup_label(label):
        return True
    updated = topic.get("label_updated_at")
    if updated is None:
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated) >= timedelta(days=max_age_days)


SELECT_ACTIVE_SQL = """
    SELECT dt.id, dt.label, dt.label_updated_at,
        COALESCE((
            SELECT array_agg(DISTINCT sid.signal_id)
            FROM dynamic_topic_members dtm
            JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
            LEFT JOIN LATERAL unnest(ec.sample_signal_ids) AS sid(signal_id) ON TRUE
            WHERE dtm.dynamic_topic_id = dt.id AND sid.signal_id IS NOT NULL
        ), ARRAY[]::bigint[]) AS sample_ids
    FROM dynamic_topics dt
    WHERE dt.state = 'active'
    ORDER BY dt.last_seen DESC NULLS LAST
"""


async def _headlines(conn: Any, sample_ids: list[int], limit: int) -> list[str]:
    if not sample_ids:
        return []
    rows = await conn.fetch(
        """
        SELECT headline FROM signals_v2
        WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL
        ORDER BY timestamp DESC LIMIT $2
        """,
        sample_ids, limit,
    )
    import html as _html
    return [_html.unescape(r["headline"]) for r in rows if r["headline"]]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    import asyncpg

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    now = datetime.now(timezone.utc)
    conn = await asyncpg.connect(db_url)
    summary = {"scanned": 0, "stale": 0, "relabeled": 0, "skipped_no_headlines": 0,
               "failed": 0, "changes": []}
    try:
        rows = await conn.fetch(SELECT_ACTIVE_SQL)
        summary["scanned"] = len(rows)
        stale = [r for r in rows if needs_relabel(dict(r), now=now, max_age_days=args.max_age_days)]
        summary["stale"] = len(stale)
        for r in stale[: args.limit]:
            heads = await _headlines(conn, list(r["sample_ids"] or []), HEADLINES_PER_TOPIC)
            if len(heads) < 3:
                summary["skipped_no_headlines"] += 1
                continue
            result = label_via_claude(heads, model=args.model)
            new_label = result.get("label") or ""
            if not new_label or new_label.startswith("(label failed"):
                summary["failed"] += 1
                continue
            summary["changes"].append(
                {"id": r["id"], "old": r["label"], "new": new_label}
            )
            if not args.dry_run:
                await conn.execute(
                    "UPDATE dynamic_topics SET label=$2, label_updated_at=$3, label_model=$4 "
                    "WHERE id=$1",
                    r["id"], new_label, now, LABEL_MODEL,
                )
            summary["relabeled"] += 1
    finally:
        await conn.close()
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Relabel stale dynamic topics via local Claude CLI.")
    ap.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="Max topics to relabel per run (bounds CLI calls).")
    ap.add_argument("--model", default=None, help="Override claude --model.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute new labels but do not write.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    summary = asyncio.run(run(args))
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
