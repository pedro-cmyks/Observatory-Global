"""Archive search — the Archive Intelligence Tier serving path (spec 2026-07-10).

Query → OpenAI text-embedding-3-small (query-side only, ~$0.00002) → cosine
scan over the few-thousand archive_topics centroids (REAL[], NO vector index
by design — see docs/state/2026-07-08-embedding-throughput-fix.md) → topics +
daily series + evidence samples, tier-labeled 'archive'. Honest empty states:
missing OPENAI_API_KEY or embed failure degrades to a visible gap, never a 500.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import date

import httpx
from fastapi import APIRouter, Query

from app import db

logger = logging.getLogger(__name__)

router = APIRouter()

CONTRACT = "archive-search-v0"
_OPENAI_URL = "https://api.openai.com/v1/embeddings"
_MODEL = "text-embedding-3-small"
# Topic-centroid floor; anchored on the 2026-07-05 OpenAI tau artifact
# (junk p50 0.542 headline-level) — centroid-level sims run lower, start
# permissive and re-measure after the first backfill window.
_FLOOR = 0.30


def rank_topics(qvec: list[float], rows: list[dict], *, floor: float,
                limit: int) -> list[dict]:
    """Pure cosine ranking of archive topic rows against a query vector."""
    qn = math.sqrt(sum(x * x for x in qvec)) or 1.0
    out = []
    for r in rows:
        v = r["centroid_vec"]
        vn = math.sqrt(sum(x * x for x in v)) or 1.0
        sim = sum(a * b for a, b in zip(qvec, v)) / (qn * vn)
        if sim >= floor:
            out.append({**r, "similarity": round(sim, 4)})
    out.sort(key=lambda r: -r["similarity"])
    return out[:limit]


async def _embed_query(q: str) -> list[float] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    async with httpx.AsyncClient(timeout=8.0) as cli:
        resp = await cli.post(
            _OPENAI_URL,
            json={"model": _MODEL, "input": [q[:2000]]},
            headers={"Authorization": f"Bearer {key}"},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


@router.get("/api/v2/archive/search")
async def archive_search(
    q: str = Query(..., min_length=2, max_length=300),
    country: str | None = Query(None, min_length=2, max_length=2),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(10, ge=1, le=25),
):
    try:
        qvec = await _embed_query(q)
    except httpx.HTTPError as e:
        logger.error("archive-search query embed failed: %s", e)
        qvec = None
    if qvec is None:
        return {"contract": CONTRACT, "tier": "archive", "query": q,
                "topics": [],
                "gap": "archive semantic search unavailable "
                       "(query embedding lane down)"}

    async with db.pool.acquire() as conn:
        # centroid_vec is halfvec (mig 074) — read as text, parse to floats
        # (no pgvector codec registered on this pool; the scan is tiny anyway).
        sql = ["SELECT id, label, category, crisis_relevant, country_code,",
               "period_start, period_end, n_stories, n_signals,",
               "centroid_vec::text AS centroid_vec,",
               "top_sources FROM archive_topics WHERE 1=1"]
        params: list = []
        if country:
            params.append(country.upper())
            sql.append(f"AND country_code = ${len(params)}")
        if date_from:
            params.append(date_from)
            sql.append(f"AND period_end >= ${len(params)}")
        if date_to:
            params.append(date_to)
            sql.append(f"AND period_start <= ${len(params)}")
        rows = [dict(r) for r in await conn.fetch(" ".join(sql), *params)]
        for r in rows:
            v = r["centroid_vec"]
            if isinstance(v, str):
                r["centroid_vec"] = [float(x) for x in v.strip("[]").split(",")]
        if not rows:
            return {"contract": CONTRACT, "tier": "archive", "query": q,
                    "topics": [],
                    "gap": "archive has no topics for that scope "
                           "(coverage starts 2026-05-03)"}
        ranked = rank_topics(qvec, rows, floor=_FLOOR, limit=limit)
        out = []
        for t in ranked:
            slug = f"archive-topic-{t['id']}"
            series = await conn.fetch(
                "SELECT day, SUM(signal_count) AS n "
                "FROM historical_topic_country_daily "
                "WHERE topic_slug=$1 AND model_version='archive-topics-v1' "
                "GROUP BY day ORDER BY day", slug)
            evid = await conn.fetch(
                "SELECT day, headline, source_name, source_url "
                "FROM historical_evidence_samples WHERE topic_slug=$1 "
                "AND model_version='archive-topics-v1' ORDER BY day LIMIT 5", slug)
            t.pop("centroid_vec", None)
            t["period_start"] = t["period_start"].isoformat()
            t["period_end"] = t["period_end"].isoformat()
            out.append({**t, "topic_slug": slug,
                        "daily": [{"day": r["day"].isoformat(), "n": int(r["n"])}
                                  for r in series],
                        "evidence": [
                            {"day": r["day"].isoformat(),
                             "headline": r["headline"],
                             "source_name": r["source_name"],
                             "source_url": r["source_url"]} for r in evid]})
        return {"contract": CONTRACT, "tier": "archive", "query": q,
                "topics": out,
                "gap": None if out else "no archive topic clears the "
                       f"similarity floor ({_FLOOR}) for that query"}
