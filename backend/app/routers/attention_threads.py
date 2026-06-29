"""Silent-risk detector (#172).

GET /api/v2/attention/silent-risks[?country=CC&hours=&days=&limit=]

A SILENT RISK = a topic the PUBLIC is paying attention to (Wikipedia pageviews)
that the PRESS is NOT covering (near-zero media signals in the window). Atlas's
strongest differentiator vs GDELT wrappers — the "what is missing" lens.

Coverage is measured LEXICALLY (does any media headline mention the topic's
distinctive token?). Measure-first finding (2026-06-29): semantic similarity is
the WRONG instrument here — a bare Wikipedia entity title ("2026 FIFA World Cup",
"Cristiano Ronaldo") rarely clears the 0.82 query↔headline floor against
event-shaped headlines, so it falsely reads media=0 for heavily-covered topics
("world cup" = 1,255 signals/24h). Entity coverage is an entity-match question,
not a semantic-neighbour one. Generous lexical matching biases toward "covered"
→ conservative silent flagging (we'd rather miss a silent risk than fabricate
one). Sports/entertainment pageview noise is dropped via the #177 editorial lane.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import db
from app.services.stream_relevance import classify_stream_lane
from app.services.silent_risk import (
    is_noise_title,
    is_silent_risk,
    normalize_title,
    why_silent,
)

router = APIRouter()

_MEDIA_FLOOR = 3            # < this many media matches = silent (#172)
_INFO_DESERT_FLOOR = 40     # country with < this many window signals = desert
_MAX_TOPICS = 25            # cap per call
_STOPWORDS = {"the", "and", "for", "with", "from", "2025", "2026", "new", "list"}
_NOISE_LANES = {"sports", "entertainment", "lifestyle"}


def _distinctive_token(normalized: str) -> str | None:
    """The most distinctive (longest, non-stopword) token to match coverage on.
    Generous on purpose — matching biases toward 'covered'."""
    tokens = [w for w in re.findall(r"[A-Za-z]{4,}", normalized)
              if w.lower() not in _STOPWORDS]
    return max(tokens, key=len) if tokens else None


async def _lexical_coverage(conn, token: str, hours: int) -> tuple[int, list[dict]]:
    count = int(await conn.fetchval(
        f"""SELECT COUNT(*) FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
              AND headline ILIKE '%' || $1 || '%'""", token) or 0)
    samples = []
    if count:
        rows = await conn.fetch(
            f"""SELECT headline, source_name, country_code FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
                  AND headline ILIKE '%' || $1 || '%'
                ORDER BY timestamp DESC LIMIT 3""", token)
        samples = [{"headline": r["headline"], "source": r["source_name"],
                    "country_code": r["country_code"]} for r in rows]
    return count, samples


@router.get("/api/v2/attention/silent-risks")
async def get_silent_risks(
    country: str | None = Query(None, min_length=2, max_length=2),
    hours: int = Query(24, ge=1, le=168),
    days: int = Query(1, ge=1, le=7),
    limit: int = Query(15, ge=1, le=30),
) -> dict:
    cc = country.upper() if country else None
    notes: list[str] = []
    if db.pool is None:
        return {"contract": "silent-risks-v0", "items": [], "notes": ["database unavailable"]}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 12000")

        # Velocity model (#172): rank by SURGE, not absolute views — today's
        # views vs the prior-7-day baseline. An evergreen celebrity/sport page
        # (steady views) is not news; a page that SPIKES today is. Brand-new
        # pages (no baseline) surface as the strongest surge by construction.
        # `country=NULL` aggregates across countries; else scopes to one.
        rows = await conn.fetch(
            """
            WITH latest AS (SELECT MAX(fetch_date) AS d FROM wiki_pageviews_v2),
            day AS (
                SELECT w.article_title, w.fetch_date, SUM(w.views) AS daily,
                       MAX(w.language) AS language,
                       COUNT(DISTINCT w.country_code) AS country_count
                FROM wiki_pageviews_v2 w, latest
                WHERE w.fetch_date >= latest.d - 7
                  AND ($1::text IS NULL OR w.country_code = $1)
                GROUP BY w.article_title, w.fetch_date
            ),
            agg AS (
                SELECT article_title,
                       MAX(language) AS language,
                       MAX(country_count) AS country_count,
                       SUM(daily) FILTER (WHERE fetch_date = (SELECT d FROM latest)) AS v_today,
                       AVG(daily) FILTER (WHERE fetch_date < (SELECT d FROM latest)) AS v_base
                FROM day GROUP BY article_title
            )
            SELECT article_title,
                   COALESCE(v_today, 0)::bigint AS views,
                   COALESCE(v_base, 0)::float AS v_base,
                   (COALESCE(v_today, 0) / GREATEST(COALESCE(v_base, 0), 1))::float AS velocity,
                   language, country_count
            FROM agg
            WHERE COALESCE(v_today, 0) > 0
            ORDER BY velocity DESC, views DESC
            LIMIT 80
            """, cc)

        information_desert = False
        if cc:
            base = int(await conn.fetchval(
                f"""SELECT COUNT(*) FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
                      AND country_code = $1""", cc) or 0)
            information_desert = base < _INFO_DESERT_FLOOR
            if information_desert:
                notes.append(f"{cc} is an information desert (only {base} media signals/"
                             f"{hours}h) — silent flags reflect low baseline, not topic gaps")

        # Filter: drop Wikipedia housekeeping noise AND sports/entertainment
        # pageview noise (reuse the #177 editorial lane — composes with the
        # 2026-06-29 thread-ranking work). What survives is plausibly NEWS.
        dropped_noise = 0
        topics = []
        for r in rows:
            title = r["article_title"]
            norm = normalize_title(title)
            if is_noise_title(title):
                dropped_noise += 1
                continue
            if classify_stream_lane([], norm) in _NOISE_LANES:
                dropped_noise += 1
                continue
            tok = _distinctive_token(norm)
            if not tok:
                continue
            topics.append({"title": title, "normalized": norm, "token": tok,
                           "views": int(r["views"]),
                           "baseline": int(r["v_base"]),
                           "velocity": round(float(r["velocity"]), 1),
                           "language": r.get("language") if cc else None,
                           "country_count": r.get("country_count") if not cc else None})
            if len(topics) >= _MAX_TOPICS:
                break

        items = []
        for t in topics:
            media_count, samples = await _lexical_coverage(conn, t["token"], hours)
            silent = is_silent_risk(t["views"], media_count, velocity=t["velocity"],
                                    media_floor=_MEDIA_FLOOR)
            items.append({
                **t,
                "media_count": media_count,
                "match_basis": "lexical",
                "is_silent_risk": silent,
                "why_silent": why_silent(t["title"], cc, media_count, information_desert)
                              if silent else None,
                "top_media": samples,
            })

    if dropped_noise:
        notes.append(f"dropped {dropped_noise} sports/entertainment/housekeeping pageview items")
    items.sort(key=lambda x: (x["is_silent_risk"], x["velocity"]), reverse=True)
    silent_count = sum(1 for x in items if x["is_silent_risk"])

    return {
        "contract": "silent-risks-v0",
        "country": cc, "hours": hours, "days": days,
        "match_basis": "lexical",
        "information_desert": information_desert,
        "silent_count": silent_count,
        "items": items,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
