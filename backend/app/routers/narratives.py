from datetime import datetime, timezone

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.utils import extract_domain
from app.core.gdelt_taxonomy import classify_source, get_concepts_for_theme

router = APIRouter()

@router.get("/api/v2/narratives")
async def get_narratives(hours: int = Query(24, ge=1, le=8760), limit: int = Query(5, ge=1, le=20)):
    """Get top narrative threads. Cached 5 min in Redis."""
    from app.core.gdelt_taxonomy import get_theme_label
    import json as _json

    cache_key = f"narratives:{hours}:{limit}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 20000")
            timeline_hours = min(hours, 24)
            # Phase 2 scans signals_v2 with theme unnest — cap at 48h to avoid timeout.
            # Phase 1 (theme_hourly_v2) still uses full hours for accurate counts.
            detail_hours = min(hours, 48)
            has_theme_hourly = await conn.fetchval(
                "SELECT to_regclass('theme_hourly_v2') IS NOT NULL"
            )

            # Phase 1: Get top themes from pre-aggregated table (instant, any window)
            if has_theme_hourly:
                top_rows = await conn.fetch("""
                    SELECT
                        theme,
                        SUM(signal_count)   AS signal_count,
                        SUM(country_count)  AS country_count,
                        SUM(source_count)   AS source_count,
                        AVG(avg_sentiment)  AS avg_sentiment
                    FROM theme_hourly_v2
                    WHERE hour > NOW() - ($1 || ' hours')::INTERVAL
                    GROUP BY theme
                    ORDER BY signal_count DESC
                    LIMIT $2
                """, str(hours), limit)
            else:
                top_rows = await conn.fetch("""
                    SELECT
                        theme,
                        SUM(signal_count) AS signal_count,
                        0::bigint         AS country_count,
                        0::bigint         AS source_count,
                        AVG(avg_sentiment) AS avg_sentiment
                    FROM signals_theme_hourly
                    WHERE bucket > NOW() - ($1 || ' hours')::INTERVAL
                    GROUP BY theme
                    ORDER BY signal_count DESC
                    LIMIT $2
                """, str(hours), limit)

            if not top_rows:
                return {"narratives": [], "hours": hours,
                        "total_active_countries": 0,
                        "generated_at": datetime.now(timezone.utc).isoformat()}

            top_themes = [r["theme"] for r in top_rows]

            # Phase 2: Velocity + timeline + countries — scoped to top themes only
            # GIN index on signals_v2.themes makes this fast even at 24h
            rows = await conn.fetch("""
                WITH
                total_active AS (
                    SELECT COUNT(DISTINCT country_code) AS cnt
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                ),
                filtered AS (
                    SELECT country_code, source_name, themes, timestamp
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                      AND themes IS NOT NULL
                      AND themes && $1::text[]
                ),
                theme_scope AS (
                    SELECT
                        theme,
                        COUNT(DISTINCT country_code) AS country_count,
                        COUNT(DISTINCT source_name) AS source_count
                    FROM (
                        SELECT unnest(themes) AS theme, country_code, source_name
                        FROM filtered
                    ) expanded
                    WHERE theme = ANY($1::text[])
                    GROUP BY theme
                ),
                velocity AS (
                    SELECT
                        unnest(themes) AS theme,
                        COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '1 hour') AS last_hour,
                        COUNT(*) FILTER (WHERE timestamp <= NOW() - INTERVAL '1 hour'
                                          AND timestamp > NOW() - INTERVAL '2 hours') AS prev_hour
                    FROM filtered
                    GROUP BY 1
                ),
                tl_base AS (
                    SELECT unnest(themes) AS theme, date_trunc('hour', timestamp) AS hour, COUNT(*) AS cnt
                    FROM filtered
                    WHERE timestamp > NOW() - ($3 || ' hours')::INTERVAL
                    GROUP BY 1, 2
                ),
                timeline AS (
                    SELECT theme,
                        JSON_AGG(JSON_BUILD_OBJECT('hour', TO_CHAR(hour, 'HH24:MI'), 'count', cnt)
                                 ORDER BY hour) AS tl
                    FROM tl_base WHERE theme = ANY($1::text[]) GROUP BY theme
                ),
                ctry_base AS (
                    SELECT unnest(themes) AS theme, country_code, COUNT(*) AS cnt
                    FROM filtered GROUP BY 1, 2
                ),
                top_ctry AS (
                    SELECT theme, ARRAY_AGG(country_code ORDER BY cnt DESC) AS countries
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY theme ORDER BY cnt DESC) AS rn
                        FROM ctry_base WHERE theme = ANY($1::text[])
                    ) r WHERE rn <= 3
                    GROUP BY theme
                ),
                first_seen AS (
                    SELECT unnest(themes) AS theme, MIN(timestamp) AS first_seen
                    FROM filtered GROUP BY 1
                )
                SELECT
                    (SELECT cnt FROM total_active) AS total_active,
                    v.theme,
                    COALESCE(v.last_hour, 0)   AS last_hour,
                    COALESCE(v.prev_hour, 0)   AS prev_hour,
                    COALESCE(tc.countries, '{}') AS top_countries,
                    COALESCE(tl.tl::text, '[]') AS hourly_timeline,
                    COALESCE(ts.country_count, 0) AS country_count,
                    COALESCE(ts.source_count, 0) AS source_count,
                    fs.first_seen
                FROM (SELECT DISTINCT unnest($1::text[]) AS theme) base
                LEFT JOIN velocity v    ON v.theme = base.theme
                LEFT JOIN top_ctry tc   ON tc.theme = base.theme
                LEFT JOIN timeline tl   ON tl.theme = base.theme
                LEFT JOIN theme_scope ts ON ts.theme = base.theme
                LEFT JOIN first_seen fs ON fs.theme = base.theme
            """, top_themes, str(detail_hours), str(timeline_hours))

            total_active = max(int((rows[0]["total_active"] if rows else None) or 1), 1)

            # Merge: top_rows has counts, rows has velocity/timeline/countries
            detail_by_theme = {r["theme"]: r for r in rows}
            theme_codes = [r["theme"] for r in top_rows]

            # Top persons — scoped to top themes, GIN-indexed lookup
            persons_map: dict = {tc: [] for tc in theme_codes}
            try:
                p_rows = await conn.fetch("""
                    SELECT theme, ARRAY_AGG(person ORDER BY cnt DESC) AS persons
                    FROM (
                        SELECT unnest(themes) AS theme, unnest(persons) AS person, COUNT(*) AS cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
                          AND themes IS NOT NULL AND persons IS NOT NULL
                          AND themes && $2
                        GROUP BY 1, 2
                    ) sub
                    WHERE person IS NOT NULL AND person != ''
                      AND theme = ANY($2)
                    GROUP BY theme
                """, str(min(hours, 6)), theme_codes)
                for pr in p_rows:
                    persons_map[pr["theme"]] = (pr["persons"] or [])[:3]
            except Exception:
                pass

            # Batch enrich with Trends + Wiki flags (non-fatal if tables empty)
            trends_flags: dict = {tc: False for tc in theme_codes}
            wiki_flags: dict = {tc: False for tc in theme_codes}
            try:
                theme_word_map: dict = {}
                for tc in theme_codes:
                    label = get_theme_label(tc).lower()
                    words = [w for w in label.split() if len(w) > 3]
                    if words:
                        theme_word_map[tc] = words

                if theme_word_map:
                    all_words = list({w for ws in theme_word_map.values() for w in ws})

                    trend_rows = await conn.fetch("""
                        SELECT DISTINCT LOWER(keyword) AS kw
                        FROM trends_v2
                        WHERE timestamp > NOW() - INTERVAL '48 hours'
                          AND LOWER(keyword) LIKE ANY(
                              SELECT '%' || w || '%' FROM unnest($1::text[]) w
                          )
                        LIMIT 100
                    """, all_words)
                    matched_kws = {r["kw"] for r in trend_rows}
                    for tc, words in theme_word_map.items():
                        if any(any(w in kw for kw in matched_kws) for w in words):
                            trends_flags[tc] = True

                    wiki_rows = await conn.fetch("""
                        SELECT DISTINCT LOWER(article_title) AS title
                        FROM wiki_pageviews_v2
                        WHERE fetch_date >= CURRENT_DATE - 3
                          AND LOWER(article_title) LIKE ANY(
                              SELECT '%' || w || '%' FROM unnest($1::text[]) w
                          )
                        LIMIT 100
                    """, all_words)
                    matched_titles = {r["title"] for r in wiki_rows}
                    for tc, words in theme_word_map.items():
                        if any(any(w in title for title in matched_titles) for w in words):
                            wiki_flags[tc] = True
            except Exception:
                pass

            narratives = []
            for tr in top_rows:
                tc = tr["theme"]
                det = detail_by_theme.get(tc, {})
                last_h = int((det.get("last_hour") or 0))
                prev_h = int((det.get("prev_hour") or 0))
                if prev_h > 0 and last_h > prev_h * 1.2:
                    trend = "accelerating"
                elif prev_h > 0 and last_h < prev_h * 0.8:
                    trend = "fading"
                else:
                    trend = "stable"

                tl_raw = det.get("hourly_timeline", "[]")
                try:
                    hourly_timeline = _json.loads(tl_raw) if isinstance(tl_raw, str) else tl_raw
                except Exception:
                    hourly_timeline = []

                first_seen_val = det.get("first_seen")

                narratives.append({
                    "theme_code": tc,
                    "label": get_theme_label(tc),
                    "signal_count": int(tr["signal_count"]),
                    "country_count": int(det.get("country_count") or 0),
                    "source_count": int(det.get("source_count") or 0),
                    "first_seen": first_seen_val.isoformat() if first_seen_val else None,
                    "velocity": last_h,
                    "trend": trend,
                    "spread_pct": round((int(det.get("country_count") or 0) / total_active) * 100, 1),
                    "avg_sentiment": round(float(tr["avg_sentiment"] or 0), 2),
                    "top_persons": persons_map.get(tc, []),
                    "hourly_timeline": hourly_timeline or [],
                    "top_countries": list((det.get("top_countries") or [])),
                    "has_public_interest": trends_flags.get(tc, False),
                    "trending_keywords": [],
                    "has_wiki_activity": wiki_flags.get(tc, False),
                    "wiki_views": 0,
                })

            result = {
                "narratives": narratives,
                "hours": hours,
                "effective_hours": detail_hours,
                "total_active_countries": total_active,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result))
                except Exception:
                    pass
            return result
    except Exception as e:
        return {"narratives": [], "hours": hours, "error": str(e)}


@router.get("/api/v2/concepts")
async def list_concepts():
    """Return all investigative concepts available for search."""
    from app.core.gdelt_taxonomy import get_all_concepts
    return {"concepts": get_all_concepts()}


@router.get("/api/v2/concepts/search")
async def search_concepts_endpoint(
    q: str = Query(..., min_length=1, description="Free-text query (English or Spanish, typos OK)"),
    limit: int = Query(10, ge=1, le=25),
):
    """Hybrid investigative search.

    Pipeline (tries each step until something hits):
      1. Fuzzy concept match — curated investigative frames (blood-diamonds, femicide, ...).
      2. Fuzzy theme match — falls back to GDELT themes if no concept matches.
      3. "Did you mean" — suggest closest concepts when nothing matched.

    Always returns a usable response: concepts, themes, suggestions, or all three.
    Stdlib-only (difflib + unicodedata). No new pip deps. No LLM calls.
    """
    from app.core.gdelt_taxonomy import (
        search_concepts as _search_concepts,
        search_themes as _search_themes,
        find_closest_concepts,
    )

    concepts = _search_concepts(q, limit=limit)
    # Only run theme fallback when no concepts hit — avoids noisy secondary matches
    # ("femicide" should NOT also surface "Inflation" as a theme suggestion)
    themes = _search_themes(q, limit=limit) if not concepts else []
    suggestions = []
    if not concepts and not themes:
        suggestions = find_closest_concepts(q, limit=3)

    # Trim payload — frontend doesn't need every field, just enough to render result rows
    concept_results = [
        {
            "slug": c["slug"],
            "label": c["label"],
            "description": c["description"],
            "themes": c["themes"],
            "related_concepts": c.get("related_concepts", []),
        }
        for c in concepts
    ]
    theme_results = [
        {
            "code": t["code"],
            "label": t["label"],
            "category": t["category"],
            "description": t["description"],
        }
        for t in themes
    ]

    return {
        "query": q,
        "concepts": concept_results,
        "themes": theme_results,
        "suggestions": suggestions,
        "result_count": len(concept_results) + len(theme_results),
    }


@router.get("/api/v2/concept/{slug}")
async def get_concept_narratives(
    slug: str,
    hours: int = Query(24, ge=1, le=168),
    region: str | None = Query(None, description="2-letter region hint, e.g. AF for Africa"),
):
    """
    Aggregate narrative signals for an investigative concept (e.g. 'blood-diamonds').
    Returns per-country signal count, tone, dominant frame, and top sources for the
    bundle of GDELT themes that compose the concept.
    """
    from app.core.gdelt_taxonomy import get_concept, get_theme_label
    import json as _json, traceback

    concept = get_concept(slug)
    if not concept:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Concept '{slug}' not found")

    themes = concept["themes"]
    cache_key = f"concept:{slug}:{hours}:{region or 'all'}"

    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")

            if hours > 24:
                # Fast path: query pre-aggregated table (sub-second even at 168h)
                rows = await conn.fetch("""
                    SELECT
                        country_code,
                        SUM(signal_count)::bigint AS signal_count,
                        (SUM(signal_count * COALESCE(avg_sentiment, 0)) /
                            NULLIF(SUM(signal_count), 0)) AS avg_sentiment
                    FROM theme_country_hourly_v2
                    WHERE hour > NOW() - ($2 || ' hours')::INTERVAL
                      AND theme = ANY($1::text[])
                    GROUP BY country_code
                    ORDER BY signal_count DESC
                    LIMIT 50
                """, themes, str(hours))

                totals = await conn.fetchrow("""
                    SELECT
                        SUM(signal_count)::bigint                      AS total_signals,
                        COUNT(DISTINCT country_code)                    AS total_countries,
                        (SUM(signal_count * COALESCE(avg_sentiment, 0)) /
                            NULLIF(SUM(signal_count), 0))               AS avg_sentiment,
                        MIN(hour)                                       AS first_seen,
                        MAX(hour)                                       AS last_seen
                    FROM theme_country_hourly_v2
                    WHERE hour > NOW() - ($2 || ' hours')::INTERVAL
                      AND theme = ANY($1::text[])
                """, themes, str(hours))

                countries = []
                for r in rows:
                    countries.append({
                        "country_code": r["country_code"],
                        "signal_count": int(r["signal_count"] or 0),
                        "avg_sentiment": round(float(r["avg_sentiment"] or 0), 3),
                        "dominant_frame": None,
                        "top_sources": [],
                    })
            else:
                # Direct path: query signals_v2 (fast enough for <= 24h)
                rows = await conn.fetch("""
                    SELECT
                        country_code,
                        COUNT(*) AS signal_count,
                        AVG(sentiment) AS avg_sentiment,
                        (array_agg(DISTINCT source_name ORDER BY source_name))[1:5] AS top_sources,
                        ($1::text[])[1] AS dominant_theme
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                      AND themes IS NOT NULL
                      AND themes && $1::text[]
                    GROUP BY country_code
                    ORDER BY signal_count DESC
                    LIMIT 50
                """, themes, str(hours))

                totals = await conn.fetchrow("""
                    SELECT
                        COUNT(*)                              AS total_signals,
                        COUNT(DISTINCT country_code)          AS total_countries,
                        AVG(sentiment)                        AS avg_sentiment,
                        MIN(timestamp)                        AS first_seen,
                        MAX(timestamp)                        AS last_seen
                    FROM signals_v2
                    WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                      AND themes IS NOT NULL
                      AND themes && $1::text[]
                """, themes, str(hours))

                countries = []
                for r in rows:
                    dominant_label = get_theme_label(r["dominant_theme"]) if r["dominant_theme"] else None
                    countries.append({
                        "country_code": r["country_code"],
                        "signal_count": int(r["signal_count"] or 0),
                        "avg_sentiment": round(float(r["avg_sentiment"] or 0), 3),
                        "dominant_frame": dominant_label,
                        "top_sources": list(r["top_sources"] or [])[:3],
                    })

            result = {
                "slug": slug,
                "label": concept["label"],
                "description": concept["description"],
                "themes": themes,
                "related_concepts": concept.get("related_concepts", []),
                "hours": hours,
                "effective_hours": hours,
                "total_signals": int(totals["total_signals"] or 0),
                "total_countries": int(totals["total_countries"] or 0),
                "avg_sentiment": round(float(totals["avg_sentiment"] or 0), 3),
                "first_seen": totals["first_seen"].isoformat() if totals["first_seen"] else None,
                "countries": countries,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result, default=str))
                except Exception:
                    pass

            return result

    except Exception as e:
        traceback.print_exc()
        return {"slug": slug, "error": str(e), "countries": []}

