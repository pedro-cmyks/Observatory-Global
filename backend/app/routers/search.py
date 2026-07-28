import asyncio
import json
import logging
import re

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.services.search_contract import should_show_concept_suggestions
from app.utils import _is_valid_person, extract_domain

router = APIRouter()
logger = logging.getLogger(__name__)
SEARCH_SEGMENT_TIMEOUT_SECONDS = 8.0
SEARCH_MATCH_TIMEOUT_SECONDS = 5.0

@router.get("/api/v2/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    hours: int = Query(168, ge=1, le=720),
    country: str | None = Query(None, min_length=2, max_length=2),
    include_aggregates: bool = Query(True, description="Include slower theme/person aggregate segments")
):
    """Search across themes, countries, and persons. Returns top_countries per result for map fly-to."""
    from app.core.search_normalization import build_like_patterns, build_query_variants

    query_variants = build_query_variants(q)
    query = query_variants[0] if query_variants else q.lower().strip()
    like_patterns = build_like_patterns(q)
    country_code = country.upper() if country else None
    cache_key = f"search:v3:{query}:{hours}:{country_code or 'all'}:{int(include_aggregates)}"
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

        degraded_segments: list[str] = []

        theme_rows = []
        person_rows = []

        # Themes — grouped with top 3 countries each
        # Exclude pure taxonomy prefixes (TAX_WORLDFISH, TAX_WORLDLANGUAGES, etc.) that
        # match on biological/language names and produce misleading results
        if include_aggregates:
            try:
                theme_rows = await conn.fetch("""
                    WITH matches AS (
                        SELECT unnest(themes) as theme, country_code, COUNT(*) as cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - INTERVAL '%s hours'
                          -- `themes IS NOT NULL` is not redundant: migration
                          -- 090's trigram index is PARTIAL on exactly that, and
                          -- without it the planner cannot use the index.
                          AND themes IS NOT NULL
                          AND lower(f_arr_text(themes)) LIKE ANY($1::text[])
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
                """ % (hours, country_clause), *search_params, timeout=SEARCH_SEGMENT_TIMEOUT_SECONDS)
            except Exception as exc:
                logger.warning("Search themes segment degraded for q=%r country=%r: %r", q, country_code, exc)
                degraded_segments.append("themes")
                theme_rows = []

        # Persons — same grouping pattern
        if include_aggregates:
            try:
                person_rows = await conn.fetch("""
                    WITH matches AS (
                        SELECT unnest(persons) as person, country_code, COUNT(*) as cnt
                        FROM signals_v2
                        WHERE timestamp > NOW() - INTERVAL '%s hours'
                          AND persons IS NOT NULL AND array_length(persons, 1) > 0
                          AND f_unaccent(lower(f_arr_text(persons))) LIKE ANY($1::text[])
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
                """ % (hours, country_clause), *search_params, timeout=SEARCH_SEGMENT_TIMEOUT_SECONDS)
            except Exception as exc:
                logger.warning("Search persons segment degraded for q=%r country=%r: %r", q, country_code, exc)
                degraded_segments.append("persons")
                person_rows = []

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
            "degraded": bool(degraded_segments),
            "degraded_segments": degraded_segments,
        }

    # NEVER cache a degraded answer (same rule as query_thread): a 120s TTL
    # would freeze one timeout into two minutes of confident-looking emptiness.
    if app.state.redis and not degraded_segments:
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

QUERY_THREAD_SIGNAL_LIMIT = 300


@router.get("/api/v2/search/thread")
async def query_thread(
    q: str = Query(..., min_length=2, description="Free-text query to build a thread from"),
    hours: int = Query(168, ge=1, le=720),
    country: str | None = Query(None, min_length=2, max_length=2),
    country_code: str | None = Query(None, min_length=2, max_length=2),
):
    """Build a temporary Narrative Thread from arbitrary query text.

    Matches signals directly (headline / themes / persons / source via the
    multilingual query variants), then assembles a theme-detail-shaped payload
    through the shared thread packet. No minimum-evidence gate: sparse matches
    still return a thread, tagged with a ``coverage`` tier so the UI can show a
    THIN badge.
    """
    from app.core.search_normalization import build_query_variants
    from app.services.query_thread import build_query_thread

    query_variants = build_query_variants(q)
    selected_country = country_code or country
    country_code = selected_country.upper() if selected_country else None
    cache_key = f"qthread:v1:{q.lower().strip()}:{hours}:{country_code or 'all'}"
    if app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    like_patterns = [f"%{variant}%" for variant in query_variants]
    country_clause = "AND country_code = $2" if country_code else ""
    params: list = [like_patterns]
    if country_code:
        params.append(country_code)

    # Degrade, never 500: this match query can still exceed
    # SEARCH_SEGMENT_TIMEOUT_SECONDS. On timeout (or any DB error) fall back to
    # an empty match set — build_query_thread([]) returns a valid thin thread —
    # mirroring the unified endpoint's per-segment graceful degrade rather than
    # raising QueryCanceledError to the client.
    #
    # WHY it can be slow, MEASURED on prod 2026-07-28 (168h, 947,468 rows).
    # An earlier version of this comment called it "sort-bound". That was
    # WRONG, and the correction matters because it points at a different fix:
    # it is PLAN-CHOICE-bound. Postgres has two viable plans here —
    #   WALK   = Index Scan on idx_signals_v2_timestamp newest-first, OR as a
    #            filter, stop at 300. Cost ~ 300 / match_density.
    #   BITMAP = BitmapOr over the four trigram indexes, then top-N sort.
    #            Cost ~ number of matches.
    # WALK is right for a dense needle, BITMAP for a sparse one, and the
    # planner chooses from the ESTIMATED density:
    #   trump  WALK,   ~7,800 rows walked                        341ms  (right)
    #   gaza   WALK,  259,680 rows walked                     26,722ms  (wrong)
    #   gaza   BITMAP forced via SET enable_indexscan=off         228ms
    # The 117x-better plan for 'gaza' existed all along; the planner declined
    # it because it estimated 15,195 matching rows against a true 1,233. That
    # overestimate is contributed almost entirely by the themes and source_name
    # branches (est 8,109 each; true 0 and 11), whose expressions have NO
    # statistics the planner will read: both trigram indexes are PARTIAL, and
    # examine_variable() skips a partial index's expression stats (the exact
    # mechanism migration 092 documented and fixed for persons — which is why
    # 'trump', whose dominant branch is the one branch that HAS statistics, is
    # the single fast needle today).
    #
    # The fix is therefore statistics, not a query rewrite: migration 093 adds
    # CREATE STATISTICS on both expressions. Do not "optimise" this query by
    # splitting the OR into per-branch UNION subqueries — that was built and
    # MEASURED, and it is a net loss: it rescues the sparse case (gaza 26.7s ->
    # 0.49s) but regresses the dense one, because the BitmapOr does ONE
    # deduplicated heap pass over the union while the UNION form pays
    # overlapping passes per branch (election 4.98s -> 7.70s, weather
    # 9.05s -> 9.74s, both measured). Statistics fix the sparse case with no
    # dense-case regression.
    #
    # Honest residual: a needle that is a broad GDELT theme token legitimately
    # matches ~30k signals ('%weather%' -> 29,799 via NATURAL_DISASTER_WEATHER
    # and friends) scattered across a 1.1 GB table, i.e. ~26k cold heap-block
    # reads. No plan makes that instant. For that class the 8s cap plus the
    # honest degraded marker below is the correct behaviour, not a bug.
    signal_rows: list = []
    degraded_reason: str | None = None
    try:
        async with db.pool.acquire() as conn:
            signal_rows = await conn.fetch(f"""
            SELECT timestamp, country_code, source_name, source_url,
                   sentiment, headline, themes, persons
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND (
                -- f_unaccent both sides (the Mbappé hole again, 2026-07-22):
                -- like_patterns come from normalize_search_text and are ALREADY
                -- accent-folded, so plain LOWER(headline) compared '%eleccion%'
                -- against 'elección' and never matched. Measured on prod (24h):
                -- peru +16, eleccion +15, mexico +14 rows recovered — and it is
                -- marginally FASTER, because f_unaccent(lower(headline)) is the
                -- exact expression migration 064 built the trigram index on.
                --
                -- The themes/persons branches must be spelled EXACTLY as
                -- migration 090 indexed them (through the IMMUTABLE f_arr_text
                -- wrapper — array_to_string is only STABLE, so it cannot be
                -- indexed directly). Before 090 those two branches had no
                -- index and one rare keyword seq-scanned the whole window:
                -- measured >45s each, against 0.3s for headline and
                -- source_name, which is what blew this endpoint's 8s segment
                -- timeout. Neither branch can simply be dropped — they carry
                -- most of the recall (6h: themes +794 rows for 'election',
                -- persons +703 for 'trump').
                (headline IS NOT NULL AND f_unaccent(LOWER(headline)) LIKE ANY($1::text[]))
                OR (source_name IS NOT NULL AND LOWER(source_name) LIKE ANY($1::text[]))
                OR (themes IS NOT NULL AND lower(f_arr_text(themes)) LIKE ANY($1::text[]))
                OR (persons IS NOT NULL AND f_unaccent(lower(f_arr_text(persons))) LIKE ANY($1::text[]))
              )
              {country_clause}
            ORDER BY timestamp DESC
            LIMIT {QUERY_THREAD_SIGNAL_LIMIT}
        """, *params, timeout=SEARCH_SEGMENT_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("query_thread match degraded for q=%r country=%r: %r",
                       q, country_code, exc)
        # The empty result below is "we could not look", NOT "there is nothing".
        # Say which, or the caller cannot tell an honest absence from a timeout.
        degraded_reason = (
            "match_timeout" if isinstance(exc, asyncio.TimeoutError)
            else type(exc).__name__
        )

    result = build_query_thread(signal_rows, q, hours=hours, country=country_code,
                                degraded_reason=degraded_reason)

    # NEVER cache a degraded answer: a 120s TTL would freeze one timeout into
    # two minutes of confident-looking emptiness for every caller.
    if app.state.redis and not degraded_reason:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result))
        except Exception:
            pass

    return result


@router.get("/api/v2/persons/suggest")
async def persons_suggest(
    q: str = Query(..., min_length=2, max_length=60),
):
    """Person typeahead over the materialized vocab (mig 063, capture-doc G2).
    The live unnest aggregate costs ~14-25s; this table answers in ms and is
    rebuilt every 30 min by the M1 cron alongside the matview refresh."""
    rows = []
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT person, signal_count
                FROM person_vocab
                WHERE person ILIKE '%' || $1 || '%'
                ORDER BY signal_count DESC
                LIMIT 8
                """,
                q.strip().lower(), timeout=4)
    except Exception as exc:
        logger.warning("persons/suggest degraded for q=%r: %r", q, exc)
    return {
        "persons": [
            {"person": r["person"], "total_signals": int(r["signal_count"]), "top_countries": []}
            for r in rows
        ]
    }


@router.get("/api/v2/search/unified")
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    hours: int = Query(168, ge=1, le=720),
    country: str | None = Query(None, min_length=2, max_length=2)
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
    explicit_country_code = country.upper() if country else None
    country_match = match_country(query)
    topic_query = country_match["query"] if country_match else query
    country_filter = country_match["code"] if country_match else explicit_country_code
    query_variants = build_query_variants(topic_query)
    normalized_query = query_variants[0] if query_variants else topic_query.lower().strip()

    cache_key = f"usearch:v11:{query_lower}:{hours}:{country_filter or 'all'}"
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
        country=country_filter,
        include_aggregates=False,
    )

    # --- 4b. Public attention + headline matches ---
    public_attention = []
    signal_matches = []
    live_threads = []
    fuzzy_suggestions = []
    degraded_segments = list(db_result.get("degraded_segments", []))
    try:
        async with db.pool.acquire() as conn:
            like_queries = [f"%{variant}%" for variant in query_variants]

            # --- 4a-bis. LIVE THREADS (#245 / search-engine-plan P1) ---
            # The served dynamic_topics ARE the product's processed answer; a
            # search that can't find them sends users past Atlas's own output.
            # Token-AND over the label (every ≥3-char token must appear), then
            # a token-ANY fallback marked 'partial'. Optional country scope via
            # member top_country_codes (the "Burkina Faso" case).
            thread_tokens = [
                f"%{t}%" for t in re.split(r"[^a-z0-9áéíóúüñ]+", topic_query.lower())
                if len(t) >= 3
            ][:6]
            # P2a (the "Burkina Faso" case): a PURE country query — "what's
            # happening in X" — should surface X's top live threads inline,
            # not just the country entry. match_country signals this by
            # returning the ORIGINAL query as the topic remainder.
            pure_country = bool(country_match) and country_match["query"] == query and country_filter
            if pure_country:
                thread_tokens = ["%"]  # match-all label; the country EXISTS clause scopes
            if thread_tokens:
                # DISTINCT ON label: R1 scoped passes can mint near-duplicate
                # topics for one event across countries; serving dedupes them
                # under the R2 umbrella but a label search would list all 6 —
                # keep the highest-volume one per label.
                _LIVE_THREADS_SQL = """
                    SELECT id, label, category, crisis_relevant, agg_n_signals, is_umbrella,
                           label_status
                    FROM (
                        SELECT DISTINCT ON (LOWER(dt.label))
                               dt.id, dt.label, dt.category, dt.crisis_relevant,
                               dt.agg_n_signals, dt.is_umbrella, dt.last_seen,
                               dt.label_status
                        FROM dynamic_topics dt
                        WHERE dt.state = 'active'
                          AND dt.label ILIKE {match} ($1::text[])
                          AND ($2::text IS NULL OR EXISTS (
                              SELECT 1 FROM dynamic_topic_members dtmc
                              JOIN emergent_clusters ecc ON ecc.id = dtmc.emergent_cluster_id
                              WHERE dtmc.dynamic_topic_id = dt.id
                                AND {country_pred}))
                        ORDER BY LOWER(dt.label), dt.agg_n_signals DESC
                    ) t
                    ORDER BY t.last_seen DESC, t.agg_n_signals DESC
                    LIMIT 6
                """
                # Pure-country: PRIMARY-country scope (top_country_codes[1]) —
                # ANY() let global threads that merely touch the country leak
                # in ("Ukraine War Updates" for a BF query). Compound queries
                # keep the looser ANY (the label already narrows).
                country_pred = (
                    "ecc.top_country_codes[1] = $2" if pure_country
                    else "$2 = ANY(ecc.top_country_codes)"
                )
                try:
                    thread_rows = await conn.fetch(
                        _LIVE_THREADS_SQL.format(match="ALL", country_pred=country_pred),
                        thread_tokens, country_filter,
                        timeout=SEARCH_MATCH_TIMEOUT_SECONDS)
                    match_kind = "all"
                    if not thread_rows and len(thread_tokens) > 1:
                        thread_rows = await conn.fetch(
                            _LIVE_THREADS_SQL.format(match="ANY", country_pred=country_pred),
                            thread_tokens, country_filter,
                            timeout=SEARCH_MATCH_TIMEOUT_SECONDS)
                        match_kind = "partial"
                except Exception as exc:
                    logger.warning("Unified search live_threads degraded for q=%r: %r", q, exc)
                    degraded_segments.append("live_threads")
                    thread_rows = []
                    match_kind = "all"
                live_threads = [
                    {
                        "id": f"dynamic-topic-{r['id']}",
                        "label": r["label"],
                        "category": r["category"],
                        "crisis_relevant": bool(r["crisis_relevant"]),
                        "total_signals": int(r["agg_n_signals"] or 0),
                        "is_umbrella": bool(r["is_umbrella"]),
                        "match": match_kind,
                        # Label Court verdict (N15): result rows mark
                        # failed/partial labels under review, same as /threads.
                        "label_status": r["label_status"],
                    }
                    for r in thread_rows
                ]

            wiki_days = max(1, min(7, (hours + 23) // 24))
            try:
                wiki_rows = await conn.fetch("""
                    SELECT article_title, SUM(views) AS views, COUNT(DISTINCT country_code) AS country_count
                    FROM wiki_pageviews_v2
                    WHERE fetch_date >= CURRENT_DATE - $2::int
                      AND LOWER(article_title) LIKE ANY($1::text[])
                    GROUP BY article_title
                    ORDER BY views DESC
                    LIMIT 5
                """, like_queries, wiki_days, timeout=SEARCH_MATCH_TIMEOUT_SECONDS)
            except Exception as exc:
                logger.warning("Unified search public_attention degraded for q=%r: %r", q, exc)
                degraded_segments.append("public_attention")
                wiki_rows = []
            public_attention = [
                {
                    "title": r["article_title"],
                    "views": int(r["views"] or 0),
                    "country_count": int(r["country_count"] or 0),
                }
                for r in wiki_rows
            ]

            # L1 (Mbappé hole): headlines WITH diacritics never matched the
            # unaccented variants — 'Kylian Mbappé' in the headline vs pattern
            # '%kylian mbappe%'. unaccent() both sides (extension enabled).
            # Also try the SURNAME alone for multi-word person-like queries —
            # most headlines say just 'Mbappé' (24h: 3 → 27 matches measured).
            signal_like = list(like_queries)
            _toks = [t for t in re.split(r"[^a-z0-9]+", normalized_query) if len(t) >= 4]
            if len(_toks) >= 2:
                signal_like.append(f"%{_toks[-1]}%")
            signal_country_clause = "AND country_code = $2" if country_filter else ""
            signal_params = [signal_like]
            if country_filter:
                signal_params.append(country_filter)
            try:
                signal_rows = await conn.fetch(f"""
                    SELECT id, timestamp, country_code, source_name, headline, themes
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                      AND (
                        (headline IS NOT NULL AND f_unaccent(LOWER(headline)) LIKE ANY($1::text[]))
                        OR (source_name IS NOT NULL AND LOWER(source_name) LIKE ANY($1::text[]))
                      )
                      {signal_country_clause}
                    ORDER BY timestamp DESC
                    LIMIT 12
                """, *signal_params, timeout=SEARCH_MATCH_TIMEOUT_SECONDS)
            except Exception as exc:
                logger.warning("Unified search signal_matches degraded for q=%r country=%r: %r", q, country_filter, exc)
                degraded_segments.append("signal_matches")
                signal_rows = []
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
        degraded_segments.append("db_matches")
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
    if country_match:
        # Prefer the alias table's display name — DB entries from signals carry
        # the bare code as name ("BF"/"BF").
        countries = [c for c in countries if c.get("code") != country_match["code"]]
        countries = [{"code": country_match["code"], "name": country_match["name"]}, *countries]

    has_direct_results = (
        bool(live_threads)
        or any(t.get("total_signals", 0) > 0 for t in merged_themes)
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
        ] if should_show_concept_suggestions(
            concept_hits=concept_hits,
            merged_themes=merged_themes,
            persons=db_result.get("persons", []),
            countries=countries,
            public_attention=public_attention,
            signal_matches=signal_matches,
        ) else [],
        "region": region_match,
        "live_threads": live_threads,
        "persons": db_result.get("persons", []),
        "countries": countries,
        "public_attention": public_attention,
        "signal_matches": signal_matches,
        "fuzzy_suggestions": fuzzy_suggestions,
        "degraded": bool(degraded_segments),
        "degraded_segments": sorted(set(degraded_segments)),
    }

    # NEVER cache a degraded answer (same rule as query_thread): degraded means
    # a lane FAILED, and caching it would serve the failure for 120s after the
    # DB recovered — the frontend's failed-lookup notice would lie stale.
    if app.state.redis and not degraded_segments:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result))
        except Exception:
            pass

    return result
