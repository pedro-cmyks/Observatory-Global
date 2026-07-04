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


# #248 hobby/personal noise class (2026-07-04, Pedro's dt-981 review: "Little
# wolf girl I made my daughter" crochet@lemmy.ca ranking in the GLOBAL forum
# dock). Fediverse communities are self-labeled topics — the community NAME is
# a stronger signal than any headline keyword. Damp, never gate: hobby posts
# sort BELOW news discussion and carry lane='hobby' so nothing is silently
# dropped (an analyst can still scroll to them).
_HOBBY_COMMUNITIES = {
    "crochet", "knitting", "sewing", "quilting", "crossstitch", "embroidery",
    "woodworking", "diy", "crafts", "gardening", "houseplants", "plants",
    "cooking", "baking", "recipes", "food", "fooddiscussion", "mealtimevideos",
    "aviation", "flying", "trains", "modelrailroads", "cars", "motorcycles",
    "gaming", "games", "boardgames", "rpg", "dnd", "patientgamers", "steam",
    "pcgaming", "nintendo", "playstation", "xbox", "retrogaming",
    "photography", "art", "drawing", "painting", "sketchdaily", "music",
    "guitar", "piano", "hiking", "camping", "fishing", "cycling", "running",
    "fitness", "sports", "soccer", "nfl", "nba", "formula1", "baseball",
    "cats", "dogs", "pets", "aww", "birding", "aquariums",
    "asklemmy", "showerthoughts", "mildlyinteresting", "casualconversation",
    "movies", "television", "anime", "manga", "books", "fantasy", "scifi",
}
_HOBBY_HEADLINE_MARKERS = (
    "i made ", "i built ", "i finished ", "my first ", "look at my ",
    "finally finished", "wip:", "[oc]", "what's your favorite",
    "whats your favorite", "recommendations?", "any recommendations",
)


def _forum_noise_lane(subreddit: str | None, headline: str | None) -> str | None:
    """'hobby' when the community or headline reads personal/hobby; else the
    stream noise lane (sports/entertainment/lifestyle) or None for news-y."""
    from app.services.stream_relevance import classify_stream_lane

    community = (subreddit or "").split("@")[0].strip().lower()
    if community in _HOBBY_COMMUNITIES:
        return "hobby"
    h = (headline or "").lower()
    if any(m in h for m in _HOBBY_HEADLINE_MARKERS):
        return "hobby"
    lane = classify_stream_lane([], headline)
    return lane if lane in ("sports", "entertainment", "lifestyle") else None


async def fetch_forum_attention(
    *, country: str | None, hours: int, limit: int = 30
) -> dict[str, Any]:
    """Recent forum (Reddit) posts, optionally country-scoped.

    Returns a discussion-lane block — labeled ``verified=False`` so callers can
    never mistake it for evidence. Degrades to an empty list on error/no rows.
    News-y discussion sorts first; hobby/sports/entertainment posts are damped
    to the bottom with a ``lane`` tag (#248) — never dropped.
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
    else:
        # Global lane: only geolocated discussion. Un-anchored social posts
        # ("CSS tricks for markdown blogs") are noise in a global intelligence
        # dock — a post must at least name a place to rank globally (L2).
        where.append("s.country_code IS NOT NULL AND s.country_code <> 'XX'")
    params.append(limit * 3)  # overfetch so the noise damp still fills the dock
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

    items = []
    for r in rows:
        sub = subreddit_label(r["source_name"])
        noise = _forum_noise_lane(sub, r["headline"])
        items.append({
            "id": r["id"],
            "timestamp": r["timestamp"].isoformat(),
            "country": r["country_code"],
            "subreddit": sub,
            "headline": r["headline"],
            "url": r["source_url"],
            "source_lang": (r["source_lang"] or "").strip() or None,
            **({"lane": noise} if noise else {}),
        })
    # Damp, don't gate: news-y discussion first (fresh→old), noise after.
    items.sort(key=lambda it: (1 if it.get("lane") else 0,))
    items = items[:limit]
    return {
        "source": "forum",  # Reddit + Lemmy + Bluesky — "reddit" mislabeled Lemmy items (L0-L3 audit)
        "lane": "discussion",
        "verified": False,
        "count": len(items),
        "items": items,
    }


def adaptive_noise_cut(background_sims: list[float], *, floor: float, sigmas: float = 2.5) -> float:
    """Per-centroid discussion threshold: mean + ``sigmas``·σ of similarities
    against a random social background, never below ``floor``. The e5
    multilingual noise floor varies per centroid (measured 0.898 vs 0.936 on
    two live threads), so a fixed threshold either serves noise or starves
    real discussion. Too small a sample → keep the floor (honest default)."""
    if len(background_sims) < 40:
        return floor
    mean = sum(background_sims) / len(background_sims)
    var = sum((x - mean) ** 2 for x in background_sims) / len(background_sims)
    return max(floor, mean + sigmas * (var ** 0.5))


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
        # Adaptive noise floor (Pedro's Iraq case, 2026-07-02: Pasta Grannies
        # served at 0.85 "similarity"): the e5 multilingual noise floor VARIES
        # per centroid — measured: unrelated social posts hit 0.898 vs dt-800
        # but 0.936 vs dt-52, so no fixed threshold separates. Estimate THIS
        # centroid's background (mean + 2.5σ over a random social sample) and
        # only serve discussion clearly above it; an empty list is honest,
        # noise dressed as discussion is not.
        background = await conn.fetch(
            f"""
            SELECT 1 - (e.vec <=> $1::halfvec) AS sim
            FROM signal_embeddings e
            JOIN signals_v2 s ON s.id = e.signal_id
            WHERE s.source_family = $2
              AND s.timestamp > NOW() - INTERVAL '{int(max(hours, 96))} hours'
            ORDER BY random()
            LIMIT 200
            """,
            vec_literal,
            FORUM_SOURCE_FAMILY,
        )

    noise_cut = adaptive_noise_cut(
        [float(b["sim"]) for b in background], floor=min_similarity,
    )

    raw = [
        {**dict(r), "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None}
        for r in rows
    ]
    members = build_semantic_members(
        raw, min_similarity=noise_cut, limit=limit
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
        "noise_floor": round(noise_cut, 4),
    }
