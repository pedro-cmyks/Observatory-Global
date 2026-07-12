"""Conflict event -> narrative threads (#232 "events as narrative inputs").

The ConflictEventPanel used to ask a single loose question — "what threads are
in this event's COUNTRY?" — and rendered the answer as if it were "threads
about THIS event". Two problems: (1) it silently conflated a geographic
relation with an event relation, and (2) it showed a bare "No narrative
threads cleared the gate here" when the country query came up thin, which
reads as "this conflict has no coverage" when the truth is "we never joined
the event to a thread".

This resolves a clicked conflict event to threads in LAYERED tiers, each
carrying an honest `basis`, so the panel can say WHY a thread is shown:

  * `linked`   — the event is directly bound to this topic via
                 `topic_members(role='movement', member_kind='event',
                 member_ref=<global_event_id>)` — the source_url binding written
                 by `compute_event_movement.py`. This is a real event->thread
                 join (the article that reported the CAMEO event is a member of
                 the thread). Precise; often empty for the very freshest markers
                 whose article hasn't been ingested/assigned yet.
  * `geo_time` — active threads in the event's country over the window. This is
                 GEOGRAPHIC context, not an event join, and is labeled as such.
                 It is the near-always-non-empty fallback (an upgrade of the old
                 silent country query).

Read-only. No new binding is persisted here — the geo relation stays a
display-time context tier (conflict has no clean category->topic map the way
disasters do, so persisting it into the movement role would over-bind a
country's events to every thread). When `compute_event_movement` runs, its
rows light up the `linked` tier for free — this reads them, never writes them.
"""
from __future__ import annotations

import logging
from typing import Any

from app import db
from app.services.thread_intelligence import fetch_threads

logger = logging.getLogger(__name__)


def _base_topic_id(thread_id: str) -> str:
    """Served thread ids are `<topic_id>` (dynamic) or `<slug>--<cc>` (atlas).
    `topic_members.topic_id` is the un-suffixed form — strip the `--cc`."""
    return str(thread_id).split("--", 1)[0]


async def fetch_conflict_event_threads(
    *,
    event_id: str | None,
    country_code: str | None,
    hours: int = 48,
    limit: int = 6,
) -> dict[str, Any]:
    """Layered resolve of one conflict event -> {linked, geo_time} thread lists.

    Degrades to empty lists (never raises) so the panel always renders."""
    country = country_code.upper() if country_code else None
    empty = {
        "contract": "conflict-event-threads-v0",
        "event_id": event_id,
        "country_code": country,
        "linked": [],
        "geo_time": [],
    }
    if db.pool is None:
        return empty

    try:
        async with db.pool.acquire() as conn:
            # Tier 1 — direct source_url bindings for THIS event.
            bound: set[str] = set()
            if event_id:
                rows = await conn.fetch(
                    "SELECT DISTINCT topic_id FROM topic_members "
                    "WHERE role='movement' AND member_kind='event' "
                    "  AND member_ref = $1",
                    str(event_id),
                )
                bound = {r["topic_id"] for r in rows}

            # Tier 2 — the event's country threads (reuse the /threads spine).
            country_threads: list[dict[str, Any]] = []
            if country:
                country_threads = await fetch_threads(
                    hours=hours, limit=limit, country_codes=[country], conn=conn
                )

            linked: list[dict[str, Any]] = []
            geo_time: list[dict[str, Any]] = []
            seen: set[str] = set()
            for t in country_threads:
                base = _base_topic_id(t.get("thread_id", ""))
                seen.add(base)
                item = {
                    "thread_id": t.get("thread_id"),
                    "label": t.get("label"),
                    "signal_count": int(t.get("signal_count") or 0),
                }
                if base in bound:
                    item["basis"] = "linked"
                    linked.append(item)
                else:
                    item["basis"] = "geo_time"
                    geo_time.append(item)

            # Bound topics the country list didn't surface (e.g. the event's
            # thread is primarily in another country, or fell below the limit).
            missing = [tid for tid in bound if _base_topic_id(tid) not in seen]
            if missing:
                extra = await conn.fetch(
                    "SELECT tm.topic_id, "
                    "  COALESCE(dt.label, at.label, tm.topic_id) AS label, "
                    "  COUNT(*) FILTER (WHERE tm.role='evidence')::int AS cnt "
                    "FROM topic_members tm "
                    "LEFT JOIN dynamic_topics dt "
                    "  ON ('dynamic-topic-'||dt.id) = tm.topic_id "
                    "LEFT JOIN atlas_topics at ON at.slug = tm.topic_id "
                    "WHERE tm.topic_id = ANY($1::text[]) "
                    "GROUP BY tm.topic_id, dt.label, at.label",
                    missing,
                )
                for r in extra:
                    linked.append({
                        "thread_id": r["topic_id"],
                        "label": r["label"],
                        "signal_count": int(r["cnt"] or 0),
                        "basis": "linked",
                    })

            return {**empty, "linked": linked, "geo_time": geo_time}
    except Exception as exc:  # pragma: no cover — defensive, panel must render
        logger.warning("conflict-event threads degraded: %s", exc)
        return empty
