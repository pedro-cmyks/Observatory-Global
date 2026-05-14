import json

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, extract_domain

router = APIRouter()

@router.get("/api/v2/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    hours: int = Query(168, ge=1, le=720),
    country: str | None = Query(None, min_length=2, max_length=2)
):
    """Search across themes, countries, and persons. Returns top_countries per result for map fly-to."""
    from app.core.search_normalization import build_like_patterns, build_query_variants

    query_variants = build_query_variants(q)
    query = query_variants[0] if query_variants else q.lower().strip()
    like_patterns = build_like_patterns(q)
    country_code = country.upper() if country else None
    cache_key = f"search:v2:{query}:{hours}:{country_code or 'all'}"
    if app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    async with db.pool.acquire() as conn:
        country_clause = "AND country_code = $2" if country_code else ""
        search_params = [like_patterns]
        if country_code:
            search_params.append(country_code)

        # Themes — grouped with top 3 countries each
        # Exclude pure taxonomy prefixes (TAX_WORLDFISH, TAX_WORLDLANGUAGES, etc.) that
        # match on biological/language names and produce misleading results
        theme_rows = await conn.fetch("""
            WITH matches AS (
                SELECT unnest(themes) as theme, country_code, COUNT(*) as cnt
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND LOWER(array_to_string(themes, ' ')) LIKE ANY($1::text[])
                  %s
                GROUP BY theme, country_code
                HAVING COUNT(*) >= 2
            ),
            filtered AS (
                SELECT * FROM matches
                WHERE theme NOT LIKE 'TAX_%%'
                  AND theme NOT LIKE 'WORLDLANGUAGES_%%'
            ),
            totals AS (
                SELECT theme, SUM(cnt) as total_signals
                FROM filtered GROUP BY theme
                ORDER BY total_signals DESC LIMIT 10
            ),
            ranked AS (
                SELECT m.theme, m.country_code, m.cnt,
                       ROW_NUMBER() OVER (PARTITION BY m.theme ORDER BY m.cnt DESC) as rn
                FROM filtered m JOIN totals t ON t.theme = m.theme
            )
            SELECT
                t.theme,
                t.total_signals,
                array_agg(r.country_code ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_codes,
                array_agg(r.cnt::int ORDER BY r.rn)     FILTER (WHERE r.rn <= 3) as top_counts,
                array_agg(COALESCE(c.name, r.country_code) ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_names
            FROM totals t
            JOIN ranked r ON r.theme = t.theme AND r.rn <= 3
            LEFT JOIN countries_v2 c ON c.code = r.country_code
            GROUP BY t.theme, t.total_signals
            ORDER BY t.total_signals DESC
        """ % (hours, country_clause), *search_params)

        # Persons — same grouping pattern
        person_rows = await conn.fetch("""
            WITH matches AS (
                SELECT unnest(persons) as person, country_code, COUNT(*) as cnt
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND persons IS NOT NULL AND array_length(persons, 1) > 0
                  AND LOWER(array_to_string(persons, ' ')) LIKE ANY($1::text[])
                  %s
                GROUP BY person, country_code
                HAVING COUNT(*) >= 2
            ),
            totals AS (
                SELECT person, SUM(cnt) as total_signals
                FROM matches GROUP BY person
                ORDER BY total_signals DESC LIMIT 8
            ),
            ranked AS (
                SELECT m.person, m.country_code, m.cnt,
                       ROW_NUMBER() OVER (PARTITION BY m.person ORDER BY m.cnt DESC) as rn
                FROM matches m JOIN totals t ON t.person = m.person
            )
            SELECT
                t.person,
                t.total_signals,
                array_agg(r.country_code ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_codes,
                array_agg(r.cnt::int ORDER BY r.rn)     FILTER (WHERE r.rn <= 3) as top_counts,
                array_agg(COALESCE(c.name, r.country_code) ORDER BY r.rn) FILTER (WHERE r.rn <= 3) as top_names
            FROM totals t
            JOIN ranked r ON r.person = t.person AND r.rn <= 3
            LEFT JOIN countries_v2 c ON c.code = r.country_code
            GROUP BY t.person, t.total_signals
            ORDER BY t.total_signals DESC
        """ % (hours, country_clause), *search_params)

        # Countries — simple name/code match
        if country_code:
            country_rows = await conn.fetch("""
                SELECT code, name FROM countries_v2
                WHERE code = $1
                LIMIT 1
            """, country_code)
        else:
            country_prefix_patterns = [f"{variant}%" for variant in query_variants]
            country_codes = [
                variant.upper()
                for variant in query_variants
                if 2 <= len(variant) <= 3 and variant.isascii()
            ]
            country_rows = await conn.fetch("""
                SELECT code, name FROM countries_v2
                WHERE code = ANY($1::text[])
                   OR LOWER(name) = ANY($2::text[])
                   OR LOWER(name) LIKE ANY($3::text[])
                ORDER BY
                    CASE
                        WHEN code = ANY($1::text[]) THEN 0
                        WHEN LOWER(name) = ANY($2::text[]) THEN 1
                        ELSE 2
                    END,
                    name
                LIMIT 8
            """, country_codes, query_variants, country_prefix_patterns)

        def build_top_countries(codes, names, counts):
            if not codes:
                return []
            return [
                {"code": codes[i], "name": names[i], "count": counts[i]}
                for i in range(len(codes))
            ]

        result = {
            "query": q,
            "normalized_query": query,
            "query_variants": query_variants,
            "themes": [
                {
                    "theme": r['theme'],
                    "total_signals": int(r['total_signals']),
                    "top_countries": build_top_countries(r['top_codes'], r['top_names'], r['top_counts'])
                }
                for r in theme_rows
            ],
            "persons": [
                {
                    "person": r['person'],
                    "total_signals": int(r['total_signals']),
                    "top_countries": build_top_countries(r['top_codes'], r['top_names'], r['top_counts'])
                }
                for r in person_rows
            ],
            "countries": [{"code": r['code'], "name": r['name']} for r in country_rows],
        }

    if app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result))
        except Exception:
            pass

    return result

async def _get_fuzzy_search_suggestions(
    conn,
    query: str,
    hours: int,
    limit: int = 5,
) -> list[dict]:
    """Return pg_trgm-backed suggestions when available.

    Supabase/Postgres may not have pg_trgm enabled in every environment; callers
    should treat an empty list as a safe fallback, not an error state.
    """
    from app.core.search_normalization import normalize_search_text, should_offer_fuzzy_suggestion

    normalized_query = normalize_search_text(query)
    if len(normalized_query) < 3:
        return []

    try:
        rows = await conn.fetch("""
            WITH candidates AS (
                SELECT person AS value, 'person' AS type, COUNT(*)::int AS signal_count
                FROM signals_v2, unnest(persons) AS person
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND persons IS NOT NULL
                  AND length(person) >= 3
                GROUP BY person

                UNION ALL

                SELECT name AS value, 'country' AS type, 0::int AS signal_count
                FROM countries_v2

                UNION ALL

                SELECT article_title AS value, 'public_attention' AS type, SUM(views)::int AS signal_count
                FROM wiki_pageviews_v2
                WHERE fetch_date >= CURRENT_DATE - 7
                GROUP BY article_title
            )
            SELECT value, type, signal_count, similarity(LOWER(value), $1) AS score
            FROM candidates
            WHERE similarity(LOWER(value), $1) >= 0.25
            ORDER BY score DESC, signal_count DESC
            LIMIT $2
        """ % hours, normalized_query, limit)
    except Exception:
        return []

    suggestions = []
    seen = set()
    for row in rows:
        value = row["value"]
        score = float(row["score"] or 0)
        if not should_offer_fuzzy_suggestion(normalized_query, value, score):
            continue
        key = (row["type"], value.lower())
        if key in seen:
            continue
        seen.add(key)
        signal_count = int(row["signal_count"] or 0)
        if row["type"] == "person" and signal_count < 10 and score < 0.5:
            continue
        suggestions.append({
            "value": value,
            "type": row["type"],
            "score": round(score, 3),
            "signal_count": signal_count,
        })

    strong_country_suggestions = [
        suggestion
        for suggestion in suggestions
        if suggestion["type"] == "country" and suggestion["score"] >= 0.5
    ]
    if strong_country_suggestions:
        return strong_country_suggestions[:limit]

    strong_public_suggestions = [
        suggestion
        for suggestion in suggestions
        if suggestion["type"] == "public_attention" and suggestion["score"] >= 0.55
    ]
    if strong_public_suggestions:
        return strong_public_suggestions[:limit]

    return suggestions

@router.get("/api/v2/search/unified")
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    hours: int = Query(168, ge=1, le=720)
):
    """Unified search: merges taxonomy aliases, investigative concepts, region matching,
    and live DB signal search into a single response.

    Pipeline:
      1. Taxonomy search (in-memory, instant) — handles aliases, typos, multilingual
      2. Concept search (in-memory, instant) — investigative frames
      3. Region match (in-memory, instant) — continent/region detection
      4. DB search (async) — themes/persons/countries from live signals
      5. Merge + deduplicate: taxonomy themes get priority over DB-only hits
    """
    from app.core.gdelt_taxonomy import (
        search_themes, search_concepts, find_closest_concepts,
        match_country, match_region, get_theme_label,
    )
    from app.core.search_normalization import build_query_variants

    query = q.strip()
    query_lower = query.lower()
    country_match = match_country(query)
    topic_query = country_match["query"] if country_match else query
    query_variants = build_query_variants(topic_query)
    normalized_query = query_variants[0] if query_variants else topic_query.lower().strip()

    cache_key = f"usearch:v7:{query_lower}:{hours}"
    if app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # --- 1. Taxonomy search (in-memory, instant) ---
    taxonomy_hits = search_themes(topic_query, limit=8, min_score=0.55)

    # --- 2. Concept search (in-memory, instant) ---
    concept_hits = search_concepts(topic_query, limit=4, min_score=0.6)
    # If no concepts found, offer suggestions
    concept_suggestions = []
    if not concept_hits:
        concept_suggestions = find_closest_concepts(topic_query, limit=2)

    # --- 3. Region match (in-memory, instant) ---
    region_match = match_region(topic_query)

    # --- 4. DB search (async) — reuse existing search logic ---
    db_result = await search(
        q=topic_query,
        hours=hours,
        country=country_match["code"] if country_match else None,
    )

    # --- 4b. Public attention + headline matches ---
    public_attention = []
    signal_matches = []
    fuzzy_suggestions = []
    try:
        async with db.pool.acquire() as conn:
            like_queries = [f"%{variant}%" for variant in query_variants]
            wiki_days = max(1, min(7, (hours + 23) // 24))
            wiki_rows = await conn.fetch("""
                SELECT article_title, SUM(views) AS views, COUNT(DISTINCT country_code) AS country_count
                FROM wiki_pageviews_v2
                WHERE fetch_date >= CURRENT_DATE - $2::int
                  AND LOWER(article_title) LIKE ANY($1::text[])
                GROUP BY article_title
                ORDER BY views DESC
                LIMIT 5
            """, like_queries, wiki_days)
            public_attention = [
                {
                    "title": r["article_title"],
                    "views": int(r["views"] or 0),
                    "country_count": int(r["country_count"] or 0),
                }
                for r in wiki_rows
            ]

            signal_country_clause = "AND country_code = $2" if country_match else ""
            signal_params = [like_queries]
            if country_match:
                signal_params.append(country_match["code"])
            signal_rows = await conn.fetch(f"""
                SELECT id, timestamp, country_code, source_name, headline, themes
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                  AND (
                    LOWER(COALESCE(headline, '')) LIKE ANY($1::text[])
                    OR LOWER(COALESCE(source_name, '')) LIKE ANY($1::text[])
                  )
                  {signal_country_clause}
                ORDER BY timestamp DESC
                LIMIT 6
            """, *signal_params, timeout=5.0)
            signal_matches = [
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"].isoformat(),
                    "country": r["country_code"],
                    "source": r["source_name"],
                    "headline": r["headline"],
                    "themes": (r["themes"] or [])[:5],
                }
                for r in signal_rows
            ]
    except Exception:
        public_attention = []
        signal_matches = []
        fuzzy_suggestions = []

    # --- 5. Merge themes: taxonomy first, then DB hits (deduped) ---
    seen_themes = set()
    merged_themes = []

    # Taxonomy themes first (these have labels, categories, descriptions)
    for th in taxonomy_hits:
        code = th["code"]
        if code in seen_themes:
            continue
        seen_themes.add(code)
        # Find DB signal count for this theme if available
        db_match = next((t for t in db_result.get("themes", []) if t["theme"] == code), None)
        merged_themes.append({
            "theme": code,
            "label": th["label"],
            "category": th.get("category", "other"),
            "description": th.get("description", ""),
            "source": "taxonomy",
            "total_signals": db_match["total_signals"] if db_match else 0,
            "top_countries": db_match["top_countries"] if db_match else [],
        })

    # DB themes that weren't in taxonomy results
    for db_th in db_result.get("themes", []):
        code = db_th["theme"]
        if code in seen_themes:
            continue
        seen_themes.add(code)
        merged_themes.append({
            "theme": code,
            "label": get_theme_label(code),
            "category": "other",
            "description": "",
            "source": "signals",
            "total_signals": db_th["total_signals"],
            "top_countries": db_th["top_countries"],
        })

    countries = db_result.get("countries", [])
    if country_match and not any(c.get("code") == country_match["code"] for c in countries):
        countries = [{"code": country_match["code"], "name": country_match["name"]}, *countries]

    has_direct_results = (
        any(t.get("total_signals", 0) > 0 for t in merged_themes)
        or any(p.get("total_signals", 0) > 0 for p in db_result.get("persons", []))
        or bool(countries)
        or bool(public_attention)
        or bool(signal_matches)
    )
    if not has_direct_results:
        try:
            async with db.pool.acquire() as conn:
                fuzzy_suggestions = await _get_fuzzy_search_suggestions(conn, topic_query, hours)
        except Exception:
            fuzzy_suggestions = []

    result = {
        "query": q,
        "normalized_query": normalized_query,
        "query_variants": query_variants,
        "themes": merged_themes,
        "concepts": [
            {
                "slug": c["slug"],
                "label": c["label"],
                "description": c["description"],
                "themes": c.get("themes", []),
                "related_concepts": c.get("related_concepts", []),
            }
            for c in concept_hits
        ],
        "concept_suggestions": [
            {"slug": c["slug"], "label": c["label"], "description": c["description"]}
            for c in concept_suggestions
        ],
        "region": region_match,
        "persons": db_result.get("persons", []),
        "countries": countries,
        "public_attention": public_attention,
        "signal_matches": signal_matches,
        "fuzzy_suggestions": fuzzy_suggestions,
    }

    if app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result))
        except Exception:
            pass

    return result
