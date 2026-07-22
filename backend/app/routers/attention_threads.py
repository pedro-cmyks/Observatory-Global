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

import asyncio
import json as _json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import db
from app.services.coverage_gaps import fetch_coverage_gaps
from app.services.stream_relevance import classify_stream_lane
from app.services.silent_risk import (
    category_to_lane,
    is_noise_title,
    is_silent_risk,
    normalize_title,
    why_silent,
)

logger = logging.getLogger(__name__)


def _ckey(title: str) -> str:
    return title.replace("_", " ").strip().lower()


async def _fetch_wiki_categories(titles: list[str], project: str = "en") -> dict[str, list[str]]:
    """Batch-fetch each article's Wikipedia categories (MediaWiki API) so a bare
    entity title can be classified by WHAT IT IS ('Argentine footballers' ->
    sports) instead of dropped. Best-effort: on any failure, returns what it has
    and the caller falls back to the keyword lane. Keyed by normalized title."""
    out: dict[str, list[str]] = {}
    # Small batches: MediaWiki caps total categories per response (~500), so a
    # large batch silently truncates later pages to zero categories. 12 keeps
    # every page's categories in one response.
    for i in range(0, len(titles), 12):
        batch = titles[i:i + 12]
        q = urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "categories",
            "cllimit": "max", "redirects": "1", "titles": "|".join(batch),
        })
        url = f"https://{project}.wikipedia.org/w/api.php?{q}"

        def _get():
            req = urllib.request.Request(url, headers={"User-Agent": "AtlasOSINT/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=6) as r:
                return _json.loads(r.read())

        try:
            data = await asyncio.to_thread(_get)
            for p in data.get("query", {}).get("pages", {}).values():
                cats = [c.get("title", "").replace("Category:", "")
                        for c in p.get("categories", [])]
                out[_ckey(p.get("title", ""))] = cats
        except Exception:
            continue
    return out

router = APIRouter()

_MEDIA_FLOOR = 3            # < this many media matches = silent (#172)
_INFO_DESERT_FLOOR = 40     # country with < this many window signals = desert
_MAX_TOPICS = 25            # cap per call
_STOPWORDS = {"the", "and", "for", "with", "from", "2025", "2026", "new", "list"}

# Forum source (#172 pivot): the Reddit ingest is curated to country + topical
# subreddits. Measure-first finding (2026-06-29): country subs (r/myanmar,
# r/Nigeria, r/colombia) are mostly daily-life chatter ("where can I buy a
# cardigan"), while the TOPICAL subs are genuine news. So the forum silent-risk
# source prefers the news-oriented subreddits.
_NEWS_SUBREDDITS = {
    "reddit/r/geopolitics", "reddit/r/worldnews", "reddit/r/credibledefense",
    "reddit/r/syriancivilwar", "reddit/r/middleeast", "reddit/r/globalnews",
    "reddit/r/anime_titties",  # (notorious news sub despite the name)
}


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


async def _forum_topics(conn, cc: str | None, hours: int) -> list[dict]:
    """Build silent-risk topics from the Reddit forum lane (#172 pivot). Prefers
    news-oriented subreddits; country-subreddit daily-life chatter is included but
    de-prioritised. Each post is a discussion topic; coverage is measured the same
    way as the wiki path."""
    rows = await conn.fetch(
        f"""
        SELECT s.headline, s.source_name, s.country_code, s.source_url,
               (lower(s.source_name) = ANY($2::text[])) AS is_news_sub
        FROM signals_v2 s
        WHERE s.source_family = 'social'
          AND s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND s.headline IS NOT NULL AND s.headline <> ''
          AND ($1::text IS NULL OR s.country_code = $1)
        ORDER BY (lower(s.source_name) = ANY($2::text[])) DESC, s.timestamp DESC
        LIMIT 120
        """, cc, list(_NEWS_SUBREDDITS))
    topics, seen = [], set()
    for r in rows:
        norm = normalize_title(r["headline"])
        tok = _distinctive_token(norm)
        if not tok:
            continue
        key = norm.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        topics.append({
            "title": r["headline"], "normalized": norm[:120], "token": tok,
            "lane": classify_stream_lane([], norm), "lane_basis": "keyword",
            "views": 0, "baseline": 0, "velocity": 0.0,
            "subreddit": (r["source_name"] or "").replace("reddit/", ""),
            "is_news_sub": bool(r["is_news_sub"]),
            "source_url": r["source_url"],
            "country_code": r["country_code"],
        })
        if len(topics) >= _MAX_TOPICS:
            break
    return topics


@router.get("/api/v2/attention/silent-risks")
async def get_silent_risks(
    country: str | None = Query(None, min_length=2, max_length=2),
    source: str = Query("wiki", pattern="^(wiki|forum)$"),
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

        # ── Forum source (#172 pivot): Reddit discussion minus media coverage.
        if source == "forum":
            topics = (await _forum_topics(conn, cc, hours))[:limit]  # cap coverage queries
            items = []
            for t in topics:
                media_count, samples = await _lexical_coverage(conn, t["token"], hours)
                silent = is_silent_risk(1, media_count, media_floor=_MEDIA_FLOOR)
                items.append({**t, "media_count": media_count, "match_basis": "lexical",
                              "is_silent_risk": silent,
                              "why_silent": why_silent(t["title"], cc, media_count) if silent else None,
                              "top_media": samples})
            # News-subreddit silent risks first, then by nothing (recency order kept).
            items.sort(key=lambda x: (x["is_silent_risk"], x.get("is_news_sub", False)), reverse=True)
            silent_by_lane: dict[str, int] = {}
            for x in items:
                if x["is_silent_risk"]:
                    silent_by_lane[x["lane"]] = silent_by_lane.get(x["lane"], 0) + 1
            return {
                "contract": "silent-risks-v0", "source": "forum", "country": cc,
                "hours": hours, "match_basis": "lexical",
                "silent_count": sum(1 for x in items if x["is_silent_risk"]),
                "silent_by_lane": silent_by_lane, "items": items, "notes": notes,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # ── Wiki source (default): pageviews minus media coverage.
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

        # CLASSIFY, don't drop (Pedro 2026-06-29, the no-silent-filtering
        # guardrail): a sports/entertainment topic may still carry relevant
        # information — label it with its #177 lane and let the consumer filter,
        # never discard it. Only true Wikipedia housekeeping / scraper artifacts
        # (Main_Page, .phtml) are dropped — those are not topics at all.
        dropped_noise = 0
        topics = []
        for r in rows:
            title = r["article_title"]
            norm = normalize_title(title)
            if is_noise_title(title):
                dropped_noise += 1
                continue
            tok = _distinctive_token(norm)
            if not tok:
                continue
            topics.append({"title": title, "normalized": norm, "token": tok,
                           "lane": classify_stream_lane([], norm),
                           "views": int(r["views"]),
                           "baseline": int(r["v_base"]),
                           "velocity": round(float(r["velocity"]), 1),
                           "language": r.get("language") if cc else None,
                           "country_count": r.get("country_count") if not cc else None})
            if len(topics) >= _MAX_TOPICS:
                break

        # Classify each title by its Wikipedia categories (what the entity IS),
        # falling back to the #177 keyword lane when categories are unavailable
        # (non-English title / API down). CLASSIFY, never drop.
        cat_map = await _fetch_wiki_categories([t["title"] for t in topics]) if topics else {}
        for t in topics:
            cats = cat_map.get(_ckey(t["title"]), [])
            t["lane"] = category_to_lane(cats) if cats else t["lane"]
            t["lane_basis"] = "wiki-category" if cats else "keyword"

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
        notes.append(f"dropped {dropped_noise} housekeeping/scraper artifacts (not topics)")
    items.sort(key=lambda x: (x["is_silent_risk"], x["velocity"]), reverse=True)
    silent_count = sum(1 for x in items if x["is_silent_risk"])
    # Lane breakdown of the silent set — so a consumer can filter (news vs
    # sports vs entertainment) instead of us dropping anything.
    silent_by_lane: dict[str, int] = {}
    for x in items:
        if x["is_silent_risk"]:
            silent_by_lane[x["lane"]] = silent_by_lane.get(x["lane"], 0) + 1

    return {
        "contract": "silent-risks-v0",
        "source": "wiki",
        "country": cc, "hours": hours, "days": days,
        "match_basis": "lexical",
        "information_desert": information_desert,
        "silent_count": silent_count,
        "silent_by_lane": silent_by_lane,
        "items": items,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v2/attention/coverage-gaps")
async def get_coverage_gaps(
    country: str | None = Query(None, min_length=2, max_length=2),
    hours: int = Query(24, ge=1, le=168),
) -> dict:
    """Coverage gaps for one scope — the "Under the Radar" substrate.

    Global (no country) mirrors the Brief's "What is missing"; with a country it
    is the domestic band. Same definition either way (services/coverage_gaps).
    Degrades to an empty list with an explicit note — a secondary lens must never
    500 the dock, and an empty list alone would read as a false "nothing here".
    """
    cc = country.upper() if country else None
    scope = "country" if cc else "global"
    notes: list[str] = []
    gaps: list[dict] = []

    if db.pool is None:
        return {"contract": "coverage-gaps-v0", "scope": scope, "country": cc,
                "hours": hours, "gaps": [], "notes": ["database unavailable"],
                "generated_at": datetime.now(timezone.utc).isoformat()}

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 12000")
            gaps = await fetch_coverage_gaps(conn, hours=hours, country=cc)
    except Exception:
        logger.exception("coverage-gaps query failed scope=%s cc=%s", scope, cc)
        notes.append("coverage gaps temporarily unavailable")

    if not gaps and not notes:
        notes.append(
            "no coverage gaps in this window — every category with signal cleared the gate"
        )

    return {
        "contract": "coverage-gaps-v0",
        "scope": scope,
        "country": cc,
        "hours": hours,
        "gaps": gaps,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
