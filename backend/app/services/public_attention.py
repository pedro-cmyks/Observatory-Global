"""Public-attention / forum lane (L2 review C1, #160).

Surfaces forum discussion (Reddit — ``source_family = 'social'``) per country.
This is the narrative-DISCOVERY lane: discussion that suggests what people are
talking about, NOT verified evidence. Reddit is ingested with a subreddit→country
map but no surface ever exposed it, so it was dark weight. Items here are always
labeled as discussion and never folded into gated counts, heat, or evidence.
"""
from __future__ import annotations

from typing import Any

from app import db

FORUM_SOURCE_FAMILY = "social"


def subreddit_label(source_name: str | None) -> str | None:
    """'reddit/r/colombia' -> 'r/colombia'; pass through anything else."""
    if not source_name:
        return None
    if source_name.startswith("reddit/"):
        return source_name.split("/", 1)[1]
    return source_name


async def fetch_forum_attention(
    *, country: str | None, hours: int, limit: int = 30
) -> dict[str, Any]:
    """Recent forum (Reddit) posts, optionally country-scoped.

    Returns a discussion-lane block — labeled ``verified=False`` so callers can
    never mistake it for evidence. Degrades to an empty list on error/no rows.
    """
    where = [
        "s.source_family = $1",
        "s.timestamp >= NOW() - ($2::int * INTERVAL '1 hour')",
        "s.headline IS NOT NULL",
        "s.headline <> ''",
    ]
    params: list[Any] = [FORUM_SOURCE_FAMILY, hours]
    if country:
        params.append(country)
        where.append(f"s.country_code = ${len(params)}")
    params.append(limit)
    sql = f"""
        SELECT s.id, s.timestamp, s.country_code, s.source_name,
               s.source_url, s.headline, s.source_lang
        FROM signals_v2 s
        WHERE {' AND '.join(where)}
        ORDER BY s.timestamp DESC
        LIMIT ${len(params)}
    """
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")
        rows = await conn.fetch(sql, *params)

    items = [
        {
            "id": r["id"],
            "timestamp": r["timestamp"].isoformat(),
            "country": r["country_code"],
            "subreddit": subreddit_label(r["source_name"]),
            "headline": r["headline"],
            "url": r["source_url"],
            "source_lang": (r["source_lang"] or "").strip() or None,
        }
        for r in rows
    ]
    return {
        "source": "reddit",
        "lane": "discussion",
        "verified": False,
        "count": len(items),
        "items": items,
    }
