"""Search performance guardrails for production query shape.

These tests intentionally inspect source text because the expensive behavior only
appears against the production-sized Supabase dataset.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROUTER = ROOT / "app" / "routers" / "search.py"
MIGRATION_022 = ROOT / "migrations" / "022_search_trigram_indexes.sql"
MIGRATION_090 = ROOT / "migrations" / "090_signals_themes_persons_trgm.sql"
MIGRATION_093 = ROOT / "migrations" / "093_signals_themes_source_ext_stats.sql"


def _search_source() -> str:
    return SEARCH_ROUTER.read_text(encoding="utf-8")


def _migration_source() -> str:
    return MIGRATION_022.read_text(encoding="utf-8")


def test_migration_022_adds_trigram_indexes_for_search_and_topic_backfill():
    sql = _migration_source()

    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql
    assert "idx_signals_v2_headline_trgm" in sql
    assert "lower(headline) gin_trgm_ops" in sql
    assert "idx_signals_v2_source_name_trgm" in sql
    assert "lower(source_name) gin_trgm_ops" in sql
    assert "idx_signals_v2_themes_gin" in sql
    assert "ON signals_v2 USING gin (themes)" in sql
    assert "idx_signals_v2_created_id_headline" in sql
    assert "idx_wiki_pageviews_v2_article_title_lower_trgm" in sql
    assert "lower(article_title) gin_trgm_ops" in sql
    assert "CONCURRENTLY" in sql


def test_unified_search_accepts_explicit_country_param_from_frontend():
    source = _search_source()

    assert "country: str | None = Query(None, min_length=2, max_length=2)" in source
    assert "explicit_country_code = country.upper() if country else None" in source
    assert "country_filter = country_match[\"code\"] if country_match else explicit_country_code" in source
    assert "country=country_filter" in source


def test_search_segments_have_timeouts_and_degraded_response():
    source = _search_source()

    assert "SEARCH_SEGMENT_TIMEOUT_SECONDS = 8.0" in source
    assert "SEARCH_MATCH_TIMEOUT_SECONDS = 5.0" in source
    assert "timeout=SEARCH_SEGMENT_TIMEOUT_SECONDS" in source
    assert "timeout=SEARCH_MATCH_TIMEOUT_SECONDS" in source
    assert '"degraded": bool(degraded_segments)' in source
    assert '"degraded_segments": sorted(set(degraded_segments))' in source


def test_unified_signal_matches_use_index_compatible_lower_columns():
    """Headline matching must use an expression a trigram index was BUILT on.

    Two are: lower(headline) (migration 022) and f_unaccent(lower(headline))
    (migration 064). Both qualify — the assertion is against wrapping the
    column in something unindexable, e.g. LOWER(COALESCE(headline, '')).

    Updated 2026-07-22: this used to pin the plain lower(headline) form
    literally, which had become a guard against the CORRECT fix. Every
    headline predicate now folds accents, because the LIKE patterns arrive
    accent-folded from normalize_search_text and the raw column never matched
    them (measured on prod, 24h: peru +16, eleccion +15, mexico +14 rows) —
    at no cost, since migration 064 indexed exactly that expression.
    """
    source = _search_source()

    assert "LOWER(COALESCE(headline" not in source
    assert "headline IS NOT NULL AND f_unaccent(LOWER(headline)) LIKE ANY" in source
    assert "source_name IS NOT NULL AND LOWER(source_name) LIKE ANY" in source


def test_query_thread_array_branches_use_migration_090_indexed_expressions():
    """The /search/thread OR-branches over themes/persons must be spelled
    exactly as migration 090's trigram indexes were built.

    Measured 2026-07-22: before 090 those two branches
    (lower(array_to_string(themes|persons,' ')) LIKE) had no index, so a rare
    keyword seq-scanned the whole window (>45s each vs 0.3s for the indexed
    headline/source_name branches) and blew the 8s segment timeout. array_to_
    string is only STABLE, so the index goes through the IMMUTABLE f_arr_text
    wrapper — and the query must use the identical expression or the planner
    silently falls back to the seq scan.
    """
    source = _search_source()

    assert "array_to_string(themes" not in source
    assert "array_to_string(persons" not in source
    assert "lower(f_arr_text(themes)) LIKE ANY" in source
    assert "f_unaccent(lower(f_arr_text(persons))) LIKE ANY" in source


def test_migration_093_gives_the_blind_or_branches_readable_statistics():
    """The themes/source_name branches must carry CREATE STATISTICS objects.

    Measured 2026-07-28 (prod, 168h, 947,468 rows): /search/thread?q=gaza took
    26,722ms and tripped the 8s segment timeout on every call, serving a
    degraded EMPTY thread. The cause is not the indexes (migration 090 built
    them) and not the sort — it is plan choice. Postgres picked the
    walk-idx_signals_v2_timestamp-and-filter plan (259,680 rows walked) over
    the BitmapOr plan, which the same query runs in 228ms when forced with
    SET enable_indexscan=off.

    It picked wrong because it estimated 15,195 matching rows against a true
    1,233, and that 12x overestimate comes almost entirely from these two
    branches: est 8,109 each, true 0 (themes) and 11 (source_name). Both
    trigram indexes are PARTIAL, and the planner never reads a partial index's
    expression statistics, so both fell through to like_selectivity()'s
    pattern-length heuristic — the identical mechanism migration 092 fixed for
    persons, which is exactly why 'trump' (persons-dominant) is the one fast
    needle at 341ms.

    A statistics object is not partial, so the planner does read it.
    """
    sql = MIGRATION_093.read_text(encoding="utf-8")

    assert "CREATE STATISTICS IF NOT EXISTS stats_signals_v2_themes_text" in sql
    assert "CREATE STATISTICS IF NOT EXISTS stats_signals_v2_source_name" in sql
    assert "FROM signals_v2" in sql
    # Statistics only help if ANALYZE has populated them.
    assert "ANALYZE signals_v2" in sql


def test_statistics_expressions_match_the_indexed_and_queried_expressions():
    """A respelling silently disables BOTH the index and the statistics.

    Postgres matches an expression statistics object to a predicate textually
    (post-parse), same as an expression index. So the three spellings — the
    migration-090 index, the migration-093 statistics, and the search.py
    predicate — must stay byte-identical. Drifting any one of them costs the
    trigram index AND the selectivity estimate at once, with no error: the
    planner just quietly returns to the 26.7s walk plan.
    """
    stats_sql = MIGRATION_093.read_text(encoding="utf-8")
    index_sql = MIGRATION_090.read_text(encoding="utf-8")
    source = _search_source()

    themes_expr = "lower(f_arr_text(themes))"
    source_expr = "lower(source_name)"

    # statistics object <- the expression migration 090 indexed
    assert f"ON ({themes_expr})" in stats_sql
    assert f"{themes_expr} gin_trgm_ops" in index_sql
    assert f"ON ({source_expr})" in stats_sql

    # ... and the expression the endpoint actually queries.
    assert f"{themes_expr} LIKE ANY" in source
    assert f"{source_expr.upper()} LIKE ANY" in source.upper()

    # persons already carries its own statistics from migration 092; the
    # headline index is non-partial, so its expression stats are read directly.
    assert "f_unaccent(lower(f_arr_text(persons))) LIKE ANY" in source


def test_query_thread_or_branches_are_not_split_into_per_branch_unions():
    """Guard the MEASURED negative result, so it is not "fixed" again.

    Splitting the four-branch OR into per-branch UNION subqueries is the
    obvious optimisation and it was built and measured on prod. It rescues the
    sparse needle (gaza 26,722ms -> 488ms) but regresses the dense ones
    (election 4,981ms -> 7,699ms, weather 9,053ms -> 9,745ms), because a
    BitmapOr makes ONE deduplicated heap pass over the union of all branches
    while the UNION form pays overlapping heap passes branch by branch.

    Migration 093 fixes the sparse case with no dense-case regression, so the
    single-OR shape stays. This test fails loudly if someone re-introduces the
    rewrite without new measurements.
    """
    source = _search_source()

    # Isolate the executed SQL itself, then drop its -- comment lines: prose
    # about the rejected rewrite must not be mistaken for the rewrite.
    body = source[source.index("SELECT timestamp, country_code, source_name, source_url"):]
    body = body[: body.index("LIMIT {QUERY_THREAD_SIGNAL_LIMIT}")]
    statement = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    )

    # one OR-ed predicate, not four UNION-ed subqueries
    assert "UNION" not in statement.upper()
    assert statement.count("LIKE ANY($1::text[])") == 4
    assert statement.upper().count(" OR ") == 3


def test_query_thread_degrades_instead_of_500_on_slow_match():
    """query_thread must never 500 when its match query is slow.

    The fetch caps at SEARCH_SEGMENT_TIMEOUT_SECONDS and the default window is
    168h, so a bare high-frequency token ('election', 'peru') can still exceed
    the cap even with the 090 indexes (a sort-bound match set, not a seq scan).
    On timeout the endpoint must degrade to an empty/thin thread — the same
    graceful-degrade the unified endpoint uses — not raise QueryCanceledError
    to the client. build_query_thread([]) already returns a valid thin payload.
    """
    source = _search_source()

    # the query_thread fetch is wrapped, and the except path builds a result
    # from an empty match set rather than propagating.
    assert "except Exception" in source
    assert "signal_rows: list = []" in source or "query_thread_rows = []" in source


def test_search_never_caches_degraded_responses():
    """A degraded payload means a retrieval lane FAILED — degraded_segments is
    appended only inside except blocks around timed-out queries, never for
    "ran and found nothing". Caching one would freeze that failure into 120s
    of confident-looking emptiness for every caller (the query_thread rule,
    now applied to both /search and /search/unified cache writes; gold UI
    eval batch 3 caught the frontend rendering these as 'No results')."""
    source = _search_source()

    # both cache sites (/api/v2/search and /api/v2/search/unified) gate on a
    # clean degraded_segments before writing to Redis
    assert source.count("if app.state.redis and not degraded_segments:") == 2
    # query_thread keeps its own no-cache-degraded gate
    assert "if app.state.redis and not degraded_reason:" in source
    # and no cache write is left unguarded on the degraded state
    assert "if app.state.redis:\n        try:\n            await app.state.redis.setex" not in source
