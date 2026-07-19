"""Community discussion content (#237 Phase 1 — the claim-origin layer).

The relationship endpoint (#168) gives the RATIO (media-led / public-led /
social-led); this gives the actual POSTS behind that ratio — the
non-traditional / forum / social signal attached to a topic as
`role='discussion'` in `topic_members`.

Load-bearing guardrail (#237 canon, #149): this is PUBLIC DISCUSSION, never
evidence. verified=false always; it can show emergence and trace claim
ORIGIN, but never counts as corroboration or inflates a thread's confidence.
The serializer stamps every item so no consumer can mistake it for evidence.
"""
from __future__ import annotations

import html
import logging
from typing import Any

from app.services.public_attention import _forum_noise_lane, subreddit_label

logger = logging.getLogger(__name__)

# Newest, most-corroborated forum/social posts attached to the topic.
# source_origin_country carries the instance home (Lemmy) or NER geocode
# (Bluesky); source_name is the platform/instance.
_DISCUSSION_SQL = """
    SELECT s.headline, s.source_name, s.source_url, s.source_lang,
           s.source_origin_country, s.country_code, s.timestamp,
           tm.confidence
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1
      AND tm.role = 'discussion'
      AND tm.engine_version = $2
      AND s.headline IS NOT NULL
    ORDER BY s.timestamp DESC
    LIMIT $3
"""


def build_discussion_items(rows: list[Any]) -> list[dict]:
    """Serialize discussion rows with the #248 relevance-honesty contract.

    * ``similarity`` = the engine's MEASURED attach confidence (tm.confidence),
      served so an analyst can judge relevance; absent when the engine recorded
      none — never faked to 0.
    * ``lane`` = hobby/sports/entertainment/lifestyle noise tag (community name
      + headline markers, same classifier as the forum dock). Noise DAMPS to
      the bottom, never drops — no silent filtering.
    Order within the news group and within the noise group is preserved
    (rows arrive newest-first).
    """
    items = []
    for r in rows:
        item = {
            "headline": html.unescape(r["headline"]),
            "platform": r["source_name"],
            "url": r["source_url"],
            "lang": r["source_lang"],
            "origin": r["source_origin_country"] or r["country_code"],
            "at": r["timestamp"].isoformat() if r["timestamp"] else None,
            # invariant stamps — no consumer can promote these to evidence
            "verified": False,
            "role": "discussion",
        }
        if r["confidence"] is not None:
            item["similarity"] = round(float(r["confidence"]), 4)
        lane = _forum_noise_lane(subreddit_label(r["source_name"]), r["headline"])
        if lane:
            item["lane"] = lane
        items.append(item)
    # Damp, don't gate: news-y discussion first, noise-tagged after (stable).
    items.sort(key=lambda it: 1 if it.get("lane") else 0)
    return items


async def fetch_community_discussion(
    conn: Any, topic_id: str, engine_version: str, limit: int = 12,
) -> dict:
    base = topic_id.strip().split("--", 1)[0]
    try:
        rows = await conn.fetch(_DISCUSSION_SQL, base, engine_version, limit)
    except Exception as exc:  # noqa: BLE001 — absent section, never a 500
        logger.warning("community discussion fetch failed: %s", exc)
        rows = []
    items = build_discussion_items(list(rows))
    return {
        "contract": "community-discussion-v0",
        "topic_id": base,
        "count": len(items),
        "noise_count": sum(1 for it in items if it.get("lane")),
        "items": items,
        "caveat": "public discussion — non-traditional/forum/social sources; "
                  "never evidence, never corroboration (claim-origin layer only)",
    }
