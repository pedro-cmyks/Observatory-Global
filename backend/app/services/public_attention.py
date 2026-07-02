"""Public-attention / forum lane (L2 review C1, #160).

Surfaces forum discussion (Reddit — ``source_family = 'social'``) per country.
This is the narrative-DISCOVERY lane: discussion that suggests what people are
talking about, NOT verified evidence. Reddit is ingested with a subreddit→country
map but no surface ever exposed it, so it was dark weight. Items here are always
labeled as discussion and never folded into gated counts, heat, or evidence.
"""
from __future__ import annotations

import re
from typing import Any

from app import db
from app.services.research_semantic import (
    THREAD_MEMBER_LIMIT,
    THREAD_MEMBER_MIN_SIMILARITY,
    build_semantic_members,
)

FORUM_SOURCE_FAMILY = "social"

# A thread token may arrive as `dynamic-topic-<id>` or a bare numeric id.
# Only dynamic_topics carry a centroid_vec, so per-thread forum matching is a
# no-op (empty, honest) for atlas/emergent/query threads.
_TOPIC_ID_RE = re.compile(r"(\d+)\s*$")


def parse_dynamic_topic_id(thread: str | None) -> int | None:
    """`dynamic-topic-12` / `12` -> 12; anything else -> None."""
    if not thread:
        return None
    token = thread.strip()
    if not (token.isdigit() or token.lower().startswith("dynamic-topic-")):
        return None
    m = _TOPIC_ID_RE.search(token)
    return int(m.group(1)) if m else None


def subreddit_label(source_name: str | None) -> str | None:
    """'reddit/r/colombia' -> 'r/colombia'; 'lemmy/x@inst' -> 'x@inst'; pass through."""
    if not source_name:
        return None
    if source_name.startswith(("reddit/", "lemmy/")):
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
        "source": "forum",  # Reddit + Lemmy + Bluesky — "reddit" mislabeled Lemmy items (L0-L3 audit)
        "lane": "discussion",
        "verified": False,
        "count": len(items),
        "items": items,
    }


async def fetch_forum_thread_attention(
    *,
    topic_id: int,
    hours: int,
    limit: int = THREAD_MEMBER_LIMIT,
    min_similarity: float = THREAD_MEMBER_MIN_SIMILARITY,
) -> dict[str, Any]:
    """Forum (Reddit) discussion that is a SEMANTIC neighbor of a thread.

    Pulls ``source_family='social'`` signals nearest the dynamic topic's
    centroid (via the signal_embeddings ANN — language-blind, unlike the lexical
    theme-code match), so a thread can aggregate the people-side discussion of
    its own narrative. Always discussion-lane (``verified=False``); never folded
    into gated evidence. Degrades to an empty list when the topic has no
    centroid or no forum signal is embedded yet.
    """
    empty = {
        "source": "forum",  # Reddit + Lemmy + Bluesky — "reddit" mislabeled Lemmy items (L0-L3 audit)
        "lane": "discussion",
        "verified": False,
        "thread_id": topic_id,
        "count": 0,
        "items": [],
    }
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")
        centroid_row = await conn.fetchrow(
            "SELECT centroid_vec FROM dynamic_topics "
            "WHERE id = $1 AND centroid_vec IS NOT NULL",
            topic_id,
        )
        if not centroid_row:
            return empty
        centroid = [float(x) for x in centroid_row["centroid_vec"]]
        vec_literal = "[" + ",".join(f"{x:.5f}" for x in centroid) + "]"
        rows = await conn.fetch(
            f"""
            SELECT s.id, s.headline, s.country_code, s.source_name, s.source_url,
                   s.timestamp, s.sentiment,
                   COALESCE(NULLIF(s.source_lang, ''), 'xx') AS source_lang,
                   1 - (e.vec <=> $1::halfvec) AS similarity,
                   FALSE AS has_topic
            FROM signal_embeddings e
            JOIN signals_v2 s ON s.id = e.signal_id
            WHERE s.source_family = $2
              AND s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
              AND s.headline IS NOT NULL AND s.headline <> ''
            ORDER BY e.vec <=> $1::halfvec
            LIMIT {int(limit * 4)}
            """,
            vec_literal,
            FORUM_SOURCE_FAMILY,
        )

    raw = [
        {**dict(r), "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None}
        for r in rows
    ]
    members = build_semantic_members(
        raw, min_similarity=min_similarity, limit=limit
    )
    items = [
        {
            **m,
            "subreddit": subreddit_label(m.get("source_name")),
        }
        for m in members
    ]
    return {
        "source": "forum",  # Reddit + Lemmy + Bluesky — "reddit" mislabeled Lemmy items (L0-L3 audit)
        "lane": "discussion",
        "verified": False,
        "thread_id": topic_id,
        "count": len(items),
        "items": items,
    }
