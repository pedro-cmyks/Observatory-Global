import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, extract_domain
from app.core.gdelt_taxonomy import classify_source
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

BRIEFING_DB_TIMEOUT_SECONDS = float(os.getenv("BRIEFING_DB_TIMEOUT_SECONDS", "8"))
BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS = float(
    os.getenv("BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS", "1.5")
)
# LO QUE SUBE / EL VACÍO get their own, more patient budget. Measured on prod
# 2026-08-12: the movement query costs 49 ms server-side and 0.6 s warm, but
# under the nightly load the pooler queues it past the shared 8 s budget and the
# marquee section degrades over a query that is not expensive. The whole payload
# is cached 15 min, so waiting a few more seconds once per cache fill is the
# cheap side of that trade. Stays under the connection's 15 s statement_timeout.
BRIEF_SECTION_DB_TIMEOUT_SECONDS = float(
    os.getenv("BRIEF_SECTION_DB_TIMEOUT_SECONDS", "12")
)
# Volume floor percentile for the hot-AND-voluminous lens (#187). 0.75 keeps
# the top quartile by volume before re-ranking by atlas_heat.
HEAT_VOLUMINOUS_PERCENTILE = float(os.getenv("BRIEFING_HEAT_VOLUMINOUS_PERCENTILE", "0.75"))
HISTORICAL_PROCESSED_MODEL_VERSION = os.getenv(
    "BRIEFING_HISTORICAL_MODEL_VERSION",
    "atlas-hist-v1",
)

from app.services.sentiment_fusion import (  # noqa: E402 — kept here to group briefing config
    NLP_COVERAGE_THRESHOLD,
    NLP_SENTIMENT_SCALE,
    choose_sentiment,
    choose_sentiment_weighted,
    sentiment_scale_descriptor,
    serialize_country_row,
)
from app.services.thread_intelligence import (  # noqa: E402
    _NO_CATEGORY,
    clean_thread_label,
    fetch_threads,
)
from app.services.coverage_gaps import (  # noqa: E402
    GLOBAL_GAP_FLOOR,
    GLOBAL_GAPS_SQL,
    fetch_extended_receipts_by_slug,
    gap_status,
)
from app.services.brief_sections import fetch_gap, fetch_rising  # noqa: E402
from app.services.insight_text import (  # noqa: E402
    repair_scale_claims,
    taxonomy_line,
)


TOP_THREADS_CONTRACT = "living-narrative-threads-v0"

# #249 — Atlas's OWN R3.1 categories: the Brief's category chart and (since the
# 2026-08-13 re-judge) the Editor's Analysis read THIS query, not two of their
# own. Counts = current (latest-snapshot) volume per category over active
# top-level stories. One lane, so the paragraph and the chart under it cannot
# name two different populations on one screen.
_CATEGORY_COUNTS_SQL = """
    SELECT dt.category,
           COUNT(DISTINCT dt.id)::int    AS topics,
           COALESCE(SUM(x.n), 0)::bigint AS signals
    FROM dynamic_topics dt
    JOIN LATERAL (
        SELECT SUM(ec.n_signals) AS n
        FROM dynamic_topic_members m
        JOIN emergent_clusters ec ON ec.id = m.emergent_cluster_id
        WHERE m.dynamic_topic_id = dt.id
          AND m.snapshot_at = (
              SELECT MAX(snapshot_at) FROM dynamic_topic_members
              WHERE dynamic_topic_id = dt.id)
    ) x ON true
    WHERE dt.state = 'active' AND dt.parent_id IS NULL
      AND dt.category IS NOT NULL
    GROUP BY dt.category
    ORDER BY signals DESC
    LIMIT 8
"""
TOP_THREADS_LIMIT = int(os.getenv("BRIEFING_TOP_THREADS_LIMIT", "10"))


async def _fetch_section(
    conn,
    degraded_segments: list[str],
    segment: str,
    query: str,
    *args,
    row: bool = False,
    timeout_seconds: float | None = None,
    timings: dict | None = None,
):
    # T1 profiler (spec §9): time the WHOLE body in a finally — a degraded
    # section must still report its cost (a 14.9s degrade is exactly what we
    # are hunting). Milliseconds, rounded to 1 decimal, keyed by segment name.
    _t0 = time.perf_counter()
    try:
        if row and timeout_seconds is None:
            return await conn.fetchrow(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
        if row:
            return await conn.fetchrow(query, *args, timeout=timeout_seconds)
        if timeout_seconds is None:
            return await conn.fetch(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
        return await conn.fetch(query, *args, timeout=timeout_seconds)
    except Exception as exc:
        degraded_segments.append(segment)
        logger.warning("briefing section degraded: %s: %s", segment, exc)
        return None if row else []
    finally:
        if timings is not None:
            timings[segment] = round((time.perf_counter() - _t0) * 1000, 1)

def _build_theme_country_map(rows) -> list:
    """Group theme_country_hourly rows into [{theme, countries: [{code, name, count}]}]."""
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for r in rows:
        grouped[r['theme']].append({
            "code": r['country_code'],
            "name": r['country_name'] or r['country_code'],
            "count": int(r['cnt'])
        })
    return [
        {"theme": theme, "countries": countries[:4]}
        for theme, countries in grouped.items()
    ]


# NOTE (re-judge 2026-08-13 §4a): `_clean_theme_label` used to live here —
# strip a prefix, `.title()`, hand the result to the Editor's Analysis prompt.
# It is what printed "Ungp Forests Rivers Oceans, Crisislexrec" as English on
# the front page, and its last caller is gone, so it is gone with it. Prose
# names come from app/services/theme_labels.human_theme_label, which returns
# None (= leave it out of the sentence) for anything it cannot name.


def _record_get(row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def _use_historical_processed(hours: int) -> bool:
    """Use compact processed history for windows outside the hot raw horizon."""
    return hours > 24


@router.get("/api/v2/briefing")
async def get_briefing(
    hours: int = Query(24, ge=1, le=8760),
    profile: bool = Query(False),
):
    """Get morning briefing summary."""
    cache_key = f"briefing_data:{hours}"
    cache_ttl = 900 if hours <= 24 else 1800
    # T1 profiler (spec §9): collected ALWAYS (one log line per compute);
    # served in the payload only under ?profile=1, which bypasses the cache
    # read AND write — a profiled payload never poisons the cache.
    timings: dict[str, float] = {}
    if not profile and hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            # 2026-08-17: was a bare `pass` — the L1-blackout class. A broken
            # cache read must not break the response, but it must be SEEN.
            logger.warning("briefing cache READ failed (%s): %s", cache_key, exc)

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 15000")
        degraded_segments: list[str] = []
        _t0 = time.perf_counter()
        has_theme_country_hourly = await conn.fetchval(
            "SELECT to_regclass('theme_country_hourly_v2') IS NOT NULL"
        )
        has_historical_processed = await conn.fetchval(
            "SELECT to_regclass('historical_topic_country_daily') IS NOT NULL"
        )
        has_historical_source_daily = await conn.fetchval(
            "SELECT to_regclass('historical_source_daily') IS NOT NULL"
        )
        timings["schema_probes"] = round((time.perf_counter() - _t0) * 1000, 1)
        # Use pre-agg tables for every window. Sentiment payload selects NLP
        # transformer-normalized values when bucket NLP coverage clears the
        # threshold, otherwise falls back to GDELT V2Tone. chosen_sentiment_raw
        # drives ORDER BY so rankings reflect what we actually serve.
        top_countries = await _fetch_section(conn, degraded_segments, "top_countries", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)             AS sig_total,
                       SUM(h.nlp_signal_count)         AS nlp_total,
                       SUM(h.nlp_sentiment_weight_sum) AS nlp_weight_sum,
                       SUM(h.nlp_confidence_sum)       AS nlp_conf_sum,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END               AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END               AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   sig_total::bigint                          AS signal_count,
                   nlp_total::bigint                          AS nlp_signal_count,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   nlp_weight_sum::float                      AS nlp_sentiment_weight_sum,
                   nlp_conf_sum::float                        AS nlp_confidence_sum,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage
            FROM agg
            ORDER BY total DESC LIMIT 10
        """, hours, timings=timings)
        negative_sentiment = await _fetch_section(conn, degraded_segments, "negative_sentiment", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)             AS sig_total,
                       SUM(h.nlp_signal_count)         AS nlp_total,
                       SUM(h.nlp_sentiment_weight_sum) AS nlp_weight_sum,
                       SUM(h.nlp_confidence_sum)       AS nlp_conf_sum,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END               AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END               AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                HAVING SUM(h.signal_count) > 50  -- #249: >10 let 11-signal micro-countries
                -- ('Antilles' legacy AN, bare 'RM') top most-negative/positive
                -- with noise averages; 50 is the floor for a meaningful mean
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   sig_total::bigint                          AS signal_count,
                   nlp_total::bigint                          AS nlp_signal_count,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   nlp_weight_sum::float                      AS nlp_sentiment_weight_sum,
                   nlp_conf_sum::float                        AS nlp_confidence_sum,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage,
                   CASE
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_conf_sum > 0
                       THEN (nlp_weight_sum / nlp_conf_sum) * $3::float
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_avg IS NOT NULL
                       THEN nlp_avg * $3::float
                       ELSE COALESCE(gdelt_avg, 0)
                   END                                         AS chosen_sentiment_raw
            FROM agg
            ORDER BY chosen_sentiment_raw ASC LIMIT 10
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE, timings=timings)
        positive_sentiment = await _fetch_section(conn, degraded_segments, "positive_sentiment", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)             AS sig_total,
                       SUM(h.nlp_signal_count)         AS nlp_total,
                       SUM(h.nlp_sentiment_weight_sum) AS nlp_weight_sum,
                       SUM(h.nlp_confidence_sum)       AS nlp_conf_sum,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END               AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END               AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                HAVING SUM(h.signal_count) > 50  -- #249: >10 let 11-signal micro-countries
                -- ('Antilles' legacy AN, bare 'RM') top most-negative/positive
                -- with noise averages; 50 is the floor for a meaningful mean
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   sig_total::bigint                          AS signal_count,
                   nlp_total::bigint                          AS nlp_signal_count,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   nlp_weight_sum::float                      AS nlp_sentiment_weight_sum,
                   nlp_conf_sum::float                        AS nlp_confidence_sum,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage,
                   CASE
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_conf_sum > 0
                       THEN (nlp_weight_sum / nlp_conf_sum) * $3::float
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_avg IS NOT NULL
                       THEN nlp_avg * $3::float
                       ELSE COALESCE(gdelt_avg, 0)
                   END                                         AS chosen_sentiment_raw
            FROM agg
            ORDER BY chosen_sentiment_raw DESC LIMIT 10
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE, timings=timings)

        # #249: the Brief's back-matter index is ATLAS categories (R3.1 — our
        # own open category level), not the GDELT taxonomy. The Editor's
        # Analysis reads the SAME constant (see _CATEGORY_COUNTS_SQL).
        category_counts = await _fetch_section(
            conn, degraded_segments, "category_counts", _CATEGORY_COUNTS_SQL, timings=timings
        )

        # B3 (L1 review 2026-07-05): the #225 gap box, finally fed — categories
        # where coverage EXISTS in the window but NOTHING clears the quality
        # gate ("attention without verified coverage" — the wedge's "what is
        # missing"). Honest by construction: raw>=20 avoids thin-noise rows;
        # gate_pending (scored=0) is labeled, never conflated with rejected.
        coverage_gaps = await _fetch_section(
            conn, degraded_segments, "coverage_gaps",
            GLOBAL_GAPS_SQL, hours, GLOBAL_GAP_FLOOR, timings=timings,
        )

        # Gap-box extended receipts (measured 2026-07-16, docs/research/gap-pool):
        # the 2-3 most newsworthy hits in a gap category sit above its extended
        # (~75%) threshold and are recoverable now — max K=3, tier-labeled.
        # Guarded per gap inside the shared helper.
        _t0 = time.perf_counter()
        gap_receipts_by_slug = await fetch_extended_receipts_by_slug(
            conn, [g["slug"] for g in coverage_gaps], hours
        )
        timings["gap_extended_receipts"] = round((time.perf_counter() - _t0) * 1000, 1)

        # Long windows should use compact processed historical tables, not raw
        # historical scans. For hot windows, theme_hourly_v2 remains the live
        # pre-agg populated by ingest_v2.refresh. The legacy
        # signals_theme_hourly table from migration 006 is dead.
        if _use_historical_processed(hours) and has_historical_processed:
            top_themes = await _fetch_section(
                conn, degraded_segments, "top_themes_historical", """
                SELECT topic_slug AS theme,
                       SUM(signal_count)::bigint        AS count,
                       AVG(topic_coverage)::float       AS topic_coverage,
                       AVG(sentiment_coverage)::float   AS sentiment_coverage,
                       'historical_topic_country_daily' AS source_table,
                       $2::text                         AS model_version
                FROM historical_topic_country_daily
                WHERE day >= CURRENT_DATE - GREATEST(1, CEIL($1::numeric / 24)::int)
                  AND model_version = $2::text
                GROUP BY topic_slug
                ORDER BY count DESC LIMIT 10
            """, hours, HISTORICAL_PROCESSED_MODEL_VERSION, timings=timings)
            top_themes_source = "historical_topic_country_daily"
        else:
            top_themes = await _fetch_section(conn, degraded_segments, "top_themes", """
                SELECT theme,
                       SUM(signal_count)::bigint AS count,
                       NULL::float               AS topic_coverage,
                       NULL::float               AS sentiment_coverage,
                       'theme_hourly_v2'         AS source_table,
                       NULL::text                AS model_version
                FROM theme_hourly_v2
                WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY theme ORDER BY count DESC LIMIT 10
            """, hours, timings=timings)
            top_themes_source = "theme_hourly_v2"
        # Long-window source rankings use compact processed history. Hot windows
        # keep the bounded raw scan so same-day sources reflect current ingestion
        # before the local archive/sync path has produced daily aggregates.
        if _use_historical_processed(hours) and has_historical_source_daily:
            top_sources = await _fetch_section(
                conn, degraded_segments, "top_sources_historical", """
                SELECT source_domain AS source_name,
                       SUM(signal_count)::bigint AS count,
                       AVG(sentiment_coverage)::float AS sentiment_coverage,
                       'historical_source_daily' AS source_table,
                       $2::text AS model_version
                FROM historical_source_daily
                WHERE day >= CURRENT_DATE - GREATEST(1, CEIL($1::numeric / 24)::int)
                  AND model_version = $2::text
                GROUP BY source_domain
                ORDER BY count DESC
                LIMIT 5
            """, hours, HISTORICAL_PROCESSED_MODEL_VERSION,
                timeout_seconds=BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS, timings=timings)
            top_sources_source = "historical_source_daily"
        else:
            top_sources = await _fetch_section(conn, degraded_segments, "top_sources", """
                SELECT source_name,
                       COUNT(*)::bigint AS count,
                       NULL::float AS sentiment_coverage,
                       'signals_v2' AS source_table,
                       NULL::text AS model_version
                FROM signals_v2
                WHERE timestamp > NOW() - ($1::int * INTERVAL '1 hour')
                  AND source_name IS NOT NULL
                GROUP BY source_name
                ORDER BY count DESC
                LIMIT 5
            """, hours, timeout_seconds=BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS, timings=timings)
            top_sources_source = "signals_v2"
        # Heat ranking (#149): atlas_heat from country_heat_v2 ranks countries by
        # what is heating up right now (velocity + surprise + source diversity +
        # local voice + frame polyphony + geo confidence − duplication), not raw
        # signal volume. Complements top_countries (volume rank) so the briefing
        # exposes both lenses without forcing a single ranking metric.
        #
        # ⚠ The `voice` field below is `country_heat_v2.local_voice_ratio`, which
        # answers a literal 0.5 when `known_origin_n < 50` — a SENTINEL for
        # "cannot judge", not "half local" (M0 §b.2; see the note in
        # routers/heat.py). No consumer reads it today. The `gap` section
        # further down deliberately does NOT read this column: it counts outlet
        # ownership itself so an unjudgeable country comes back null + reason.
        _t0 = time.perf_counter()
        has_country_heat = await conn.fetchval(
            "SELECT to_regclass('country_heat_v2') IS NOT NULL"
        )
        timings["schema_probes"] = round(
            timings.get("schema_probes", 0.0)
            + (time.perf_counter() - _t0) * 1000, 1
        )
        if has_country_heat:
            heat_countries = await _fetch_section(conn, degraded_segments, "heat_countries", """
                SELECT h.country_code,
                       COALESCE(c.name, h.country_code)        AS name,
                       h.volume_now::bigint                    AS volume,
                       h.atlas_heat::float                     AS heat,
                       h.z_velocity_norm::float                AS velocity,
                       h.surprise_kl_norm::float               AS surprise,
                       h.source_diversity_norm::float          AS diversity,
                       h.local_voice_ratio::float              AS voice,
                       h.polyphony_norm::float                 AS polyphony,
                       h.geo_confidence_mean::float            AS geo_confidence,
                       h.duplication_index_norm::float         AS duplication
                FROM country_heat_v2 h
                LEFT JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hours_window = 24
                  AND h.atlas_heat IS NOT NULL
                ORDER BY h.atlas_heat DESC
                LIMIT 10
            """, timings=timings)
            # Hot AND voluminous (#187): filter heat to countries whose volume
            # clears the configurable percentile, then re-rank by atlas_heat.
            # Surfaces stories big enough to matter and surprising enough to
            # investigate — avoids the "low-volume noise" failure mode where a
            # country with 5 signals tops the heat board because its baseline
            # is tiny.
            heat_voluminous_countries = await _fetch_section(
                conn, degraded_segments, "heat_voluminous_countries", """
                WITH volume_floor AS (
                    SELECT percentile_disc($1::float) WITHIN GROUP (ORDER BY volume_now)::bigint AS v
                    FROM country_heat_v2
                    WHERE hours_window = 24
                      AND atlas_heat IS NOT NULL
                )
                SELECT h.country_code,
                       COALESCE(c.name, h.country_code)         AS name,
                       h.volume_now::bigint                     AS volume,
                       (SELECT v FROM volume_floor)             AS volume_floor,
                       h.atlas_heat::float                      AS heat,
                       h.z_velocity_norm::float                 AS velocity,
                       h.surprise_kl_norm::float                AS surprise,
                       h.source_diversity_norm::float           AS diversity,
                       h.local_voice_ratio::float               AS voice,
                       h.polyphony_norm::float                  AS polyphony,
                       h.geo_confidence_mean::float             AS geo_confidence,
                       h.duplication_index_norm::float          AS duplication
                FROM country_heat_v2 h
                LEFT JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hours_window = 24
                  AND h.atlas_heat IS NOT NULL
                  AND h.volume_now >= (SELECT v FROM volume_floor)
                ORDER BY h.atlas_heat DESC
                LIMIT 10
            """, HEAT_VOLUMINOUS_PERCENTILE, timings=timings)
        else:
            heat_countries = []
            heat_voluminous_countries = []

        # Atlas topic surface (#171 / PR #197 v2 classifier):
        # signal_topic_assignments holds the curated atlas_topics taxonomy
        # (disease-outbreak, labor-strike-disruption, etc.) instead of raw
        # GDELT codes (WB_*, TAX_*). top_themes still ships the GDELT layer
        # for back-compat; top_atlas_topics is the product-grade ranking
        # that lets the briefing speak in concepts the user recognizes.
        # PK (signal_id, topic_id, method, model_version) guarantees unique
        # signal per (topic, version), so COUNT(*) == COUNT(DISTINCT signal_id)
        # within each group — the cheap COUNT avoids a 200ms sort.
        # Hot path measured at ~40 ms on 33k assignments (24h window).
        _t0 = time.perf_counter()
        has_atlas_assignments = await conn.fetchval(
            "SELECT to_regclass('signal_topic_assignments') IS NOT NULL"
        )
        has_dynamic_topics = await conn.fetchval(
            "SELECT to_regclass('dynamic_topics') IS NOT NULL"
        )
        has_dynamic_topic_members = await conn.fetchval(
            "SELECT to_regclass('dynamic_topic_members') IS NOT NULL"
        )
        has_emergent_clusters = await conn.fetchval(
            "SELECT to_regclass('emergent_clusters') IS NOT NULL"
        )
        timings["schema_probes"] = round(
            timings.get("schema_probes", 0.0)
            + (time.perf_counter() - _t0) * 1000, 1
        )

        # Topic surface: prefer the self-curated dynamic_topics lifecycle when
        # active rows exist, then raw emergent_clusters, then static
        # atlas_topics. This keeps the product read path quality-gated while
        # preserving fallbacks if the lifecycle or snapshot cron is empty.
        #
        # Mapped to the existing top_atlas_topics frontend contract so the
        # brief renders unchanged. Dynamic rows use slug = 'dynamic-topic-<id>',
        # which resolves in /api/v2/theme/{slug}; raw cluster fallback still
        # uses slug = 'cluster-<id>'.
        top_atlas_topics: list = []
        if has_dynamic_topics and has_dynamic_topic_members:
            # Outer LATERAL (over the LIMIT-10 result only, so it stays cheap)
            # fetches a few member receipts per row: the serving-layer label
            # guard needs receipts to render a NULL/placeholder label as a
            # receipt-derived fallback instead of a raw stub (Lane A).
            top_atlas_topics = await _fetch_section(
                conn, degraded_segments, "top_atlas_topics", """
                SELECT q.*, COALESCE(sh.headlines, ARRAY[]::text[]) AS sample_headlines
                FROM (
                    SELECT
                        dt.id                                              AS topic_pk,
                        ('dynamic-topic-' || dt.id::text)                  AS slug,
                        dt.label,
                        dt.category                                        AS category,
                        NULL::text                                         AS parent_domain,
                        dt.agg_n_signals::bigint                           AS signal_count,
                        CASE
                            WHEN dt.noise_rate IS NULL THEN NULL::float
                            ELSE (1 - dt.noise_rate)::float
                        END                                                AS avg_confidence,
                        dt.agg_n_signals::bigint                           AS high_confidence_count,
                        dt.agg_n_signals::bigint                           AS gated_signal_count,
                        dt.agg_n_signals::bigint                           AS gate_scored_count,
                        'dynamic_topics'                                   AS source_table,
                        'dynamic-topics-v1'                                AS model_version,
                        NULL::text                                         AS description,
                        NULL::int                                          AS velocity,
                        ARRAY[]::text[]                                    AS top_country_codes,
                        dt.mean_cohesion::float                            AS cohesion,
                        NULL::float                                        AS vendor_agreement,
                        dt.noise_rate::float                               AS noise_rate
                    FROM dynamic_topics dt
                    WHERE dt.state = 'active'
                      AND dt.last_seen > NOW() - ($1::int * INTERVAL '1 hour')
                    ORDER BY dt.agg_n_signals DESC, dt.last_seen DESC
                    LIMIT 10
                ) q
                LEFT JOIN LATERAL (
                    SELECT array_agg(h.headline) AS headlines
                    FROM (
                        SELECT s.headline
                        FROM dynamic_topic_members dtm
                        JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
                        CROSS JOIN LATERAL unnest(ec.sample_signal_ids) AS sid(signal_id)
                        JOIN signals_v2 s ON s.id = sid.signal_id
                        WHERE dtm.dynamic_topic_id = q.topic_pk
                          AND s.headline IS NOT NULL
                        ORDER BY s.timestamp DESC
                        LIMIT 4
                    ) h
                ) sh ON TRUE
            """, hours, timings=timings)

        if not top_atlas_topics and has_emergent_clusters:
            _t0 = time.perf_counter()
            snap_row = await conn.fetchrow(
                "SELECT MAX(snapshot_at) AS snap FROM emergent_clusters "
                "WHERE snapshot_at > NOW() - ($1::int * INTERVAL '1 hour')",
                hours,
            )
            timings["top_atlas_topics_snap_probe"] = round(
                (time.perf_counter() - _t0) * 1000, 1
            )
            snap = snap_row["snap"] if snap_row else None
            if snap is not None:
                top_atlas_topics = await _fetch_section(
                    conn, degraded_segments, "top_atlas_topics", """
                    SELECT
                        ('cluster-' || id::text)                AS slug,
                        label,
                        NULL::text                              AS parent_domain,
                        raw_signal_count::bigint                AS signal_count,
                        NULL::float                             AS avg_confidence,
                        n_signals::bigint                       AS high_confidence_count,
                        n_signals::bigint                       AS gated_signal_count,
                        raw_signal_count::bigint                AS gate_scored_count,
                        'emergent_clusters'                     AS source_table,
                        'emergent-snapshot-v1'                  AS model_version,
                        description,
                        velocity,
                        top_country_codes,
                        cohesion,
                        vendor_agreement,
                        NULL::float AS noise_rate
                    FROM emergent_clusters
                    WHERE snapshot_at = $1
                    ORDER BY velocity DESC NULLS LAST, n_signals DESC
                    LIMIT 10
                """, snap, timings=timings)

        if not top_atlas_topics and has_atlas_assignments:
            # Fallback: original static atlas_topics ranking. Same contract.
            top_atlas_topics = await _fetch_section(
                conn, degraded_segments, "top_atlas_topics", """
                SELECT t.slug,
                       t.label,
                       t.parent_domain,
                       COUNT(*)::bigint                                         AS signal_count,
                       ROUND(AVG(a.confidence)::numeric, 3)::float              AS avg_confidence,
                       COUNT(*) FILTER (WHERE a.confidence >= 0.75)::bigint     AS high_confidence_count,
                       COUNT(*) FILTER (WHERE a.gate_kept)::bigint              AS gated_signal_count,
                       COUNT(*) FILTER (WHERE a.gate_kept IS NOT NULL)::bigint  AS gate_scored_count,
                       'signal_topic_assignments'                               AS source_table,
                       a.model_version                                          AS model_version,
                       NULL::float                                              AS noise_rate
                FROM signal_topic_assignments a
                JOIN atlas_topics t ON t.id = a.topic_id
                WHERE a.method = 'lexicon'
                  AND a.model_version = 'theme-hint-lex-v2'
                  AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY t.slug, t.label, t.parent_domain, a.model_version
                ORDER BY signal_count DESC
                LIMIT 10
            """, hours, timings=timings)

        # Living Narrative Threads (Milestone 2): assemble the same product
        # contract that /api/v2/threads serves so Brief leads with natural
        # threads (label, why_now, changed_10h, confidence band) instead of
        # raw atlas-topic counts. Reuses the briefing connection through
        # fetch_threads(conn=...). Degrades to [] on any failure so the
        # briefing payload still ships.
        top_threads: list = []
        if has_atlas_assignments:
            _t0 = time.perf_counter()
            try:
                top_threads = await fetch_threads(
                    hours=hours,
                    limit=TOP_THREADS_LIMIT,
                    attach_evidence=True,
                    conn=conn,
                )
            except Exception as exc:
                degraded_segments.append("top_threads")
                logger.warning("briefing section degraded: top_threads: %s", exc)
                top_threads = []
            finally:
                timings["top_threads"] = round((time.perf_counter() - _t0) * 1000, 1)

        # LO QUE SUBE + EL VACÍO (T3.2, spec §3b): the two sections that make the
        # Brief the diary of the COVERAGE rather than a late wire front page.
        # Both are template prose over measured fields — zero LLM calls — and the
        # SAME functions run inside the nightly seal, so the front page and the
        # sealed artifact can never say different things. Both degrade into a
        # served reason; neither can 500 the briefing.
        _t0 = time.perf_counter()
        rising_section = await fetch_rising(
            conn, hours=hours, timeout=BRIEF_SECTION_DB_TIMEOUT_SECONDS,
        )
        timings["rising"] = round((time.perf_counter() - _t0) * 1000, 1)
        if rising_section.get("status") == "unavailable":
            degraded_segments.append("rising")
        _t0 = time.perf_counter()
        gap_section = await fetch_gap(
            conn, computed_by="live", timeout=BRIEF_SECTION_DB_TIMEOUT_SECONDS,
        )
        timings["gap"] = round((time.perf_counter() - _t0) * 1000, 1)
        if gap_section.get("status") == "unavailable":
            degraded_segments.append("gap")

        # Atlas hierarchy + co-occurrence (2026-05-23 narrative-cluster spec):
        # parent_domain (10 domains, 2-5 topics each) is the natural cluster
        # level. topics_by_domain agrees the same window as top_atlas_topics
        # but groups under domain so the briefing can render the taxonomy as
        # a tree. related_topics is a co-occurrence map (topic -> top-3
        # related) using a Jaccard-proxy score sqrt(|A|*|B|) so big topics
        # don't always dominate the relations of small ones. Both queries
        # only touch signal_topic_assignments (no signals_v2 join) — they
        # use assigned_at instead of signals_v2.timestamp, which is fine
        # because the cron's idempotent upsert refreshes assigned_at on
        # every pass. Hot path: ~80 ms (topics_by_domain) + ~47 ms
        # (related_topics).
        if has_atlas_assignments:
            topics_by_domain = await _fetch_section(
                conn, degraded_segments, "topics_by_domain", """
                WITH per_topic AS (
                    SELECT t.parent_domain, t.slug, t.label,
                           COUNT(*)::bigint                                         AS signal_count,
                           ROUND(AVG(a.confidence)::numeric, 3)::float              AS avg_confidence,
                           COUNT(*) FILTER (WHERE a.confidence >= 0.75)::bigint     AS high_confidence_count
                    FROM signal_topic_assignments a
                    JOIN atlas_topics t ON t.id = a.topic_id
                    WHERE a.method = 'lexicon'
                      AND a.model_version = 'theme-hint-lex-v2'
                      AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY t.parent_domain, t.slug, t.label
                )
                SELECT parent_domain,
                       SUM(signal_count)::bigint                                   AS domain_signal_count,
                       COUNT(*)::int                                               AS topics_in_domain,
                       jsonb_agg(
                           jsonb_build_object(
                               'slug', slug, 'label', label,
                               'signal_count', signal_count,
                               'avg_confidence', avg_confidence,
                               'high_confidence_count', high_confidence_count
                           ) ORDER BY signal_count DESC
                       )                                                           AS topics
                FROM per_topic
                GROUP BY parent_domain
                ORDER BY domain_signal_count DESC
            """, hours, timings=timings)
            related_topics = await _fetch_section(
                conn, degraded_segments, "related_topics", """
                WITH pairs AS (
                    SELECT LEAST(a1.topic_id, a2.topic_id)    AS t_lo,
                           GREATEST(a1.topic_id, a2.topic_id) AS t_hi,
                           COUNT(*)::int                       AS co
                    FROM signal_topic_assignments a1
                    JOIN signal_topic_assignments a2
                      ON a1.signal_id = a2.signal_id
                     AND a1.topic_id < a2.topic_id
                     AND a2.method = 'lexicon'
                     AND a2.model_version = 'theme-hint-lex-v2'
                     AND a2.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                    WHERE a1.method = 'lexicon'
                      AND a1.model_version = 'theme-hint-lex-v2'
                      AND a1.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY t_lo, t_hi
                ),
                topic_totals AS (
                    SELECT a.topic_id, COUNT(*)::int AS sigs
                    FROM signal_topic_assignments a
                    WHERE a.method = 'lexicon'
                      AND a.model_version = 'theme-hint-lex-v2'
                      AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY a.topic_id
                ),
                expanded AS (
                    SELECT p.t_lo AS topic_id, p.t_hi AS other_id, p.co,
                           p.co::float / NULLIF(SQRT(tl.sigs * th.sigs), 0) AS strength
                    FROM pairs p
                    JOIN topic_totals tl ON tl.topic_id = p.t_lo
                    JOIN topic_totals th ON th.topic_id = p.t_hi
                    UNION ALL
                    SELECT p.t_hi, p.t_lo, p.co,
                           p.co::float / NULLIF(SQRT(tl.sigs * th.sigs), 0)
                    FROM pairs p
                    JOIN topic_totals tl ON tl.topic_id = p.t_lo
                    JOIN topic_totals th ON th.topic_id = p.t_hi
                ),
                ranked AS (
                    SELECT e.topic_id, t.slug AS topic_slug,
                           ot.slug AS other_slug, e.co,
                           ROUND(e.strength::numeric, 3) AS strength,
                           ROW_NUMBER() OVER (
                               PARTITION BY e.topic_id
                               ORDER BY e.strength DESC, e.co DESC
                           ) AS rnk
                    FROM expanded e
                    JOIN atlas_topics t  ON t.id  = e.topic_id
                    JOIN atlas_topics ot ON ot.id = e.other_id
                )
                SELECT topic_slug,
                       jsonb_agg(
                           jsonb_build_object(
                               'slug', other_slug,
                               'co_signals', co,
                               'strength', strength
                           ) ORDER BY rnk
                       ) AS related
                FROM ranked
                WHERE rnk <= 3
                GROUP BY topic_slug
            """, hours, timings=timings)
        else:
            topics_by_domain = []
            related_topics = []

        stats = await _fetch_section(conn, degraded_segments, "stats", """
            SELECT SUM(signal_count)::bigint                          AS total_signals,
                   COUNT(DISTINCT country_code)                       AS countries,
                   SUM(unique_sources)::bigint                        AS sources,
                   SUM(signal_count)::bigint                          AS signal_count,
                   SUM(nlp_signal_count)::bigint                      AS nlp_signal_count,
                   CASE WHEN SUM(signal_count) > 0
                        THEN SUM(avg_sentiment * signal_count) / SUM(signal_count)
                        ELSE 0 END                                    AS gdelt_sentiment,
                   CASE WHEN SUM(nlp_signal_count) > 0
                        THEN SUM(avg_nlp_sentiment * nlp_signal_count) / SUM(nlp_signal_count)
                        ELSE NULL END                                 AS nlp_sentiment,
                   SUM(nlp_sentiment_weight_sum)::float               AS nlp_sentiment_weight_sum,
                   SUM(nlp_confidence_sum)::float                     AS nlp_confidence_sum,
                   (SUM(nlp_signal_count)::float
                       / NULLIF(SUM(signal_count), 0))                AS nlp_coverage
            FROM country_hourly_v2
            WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
        """, hours, row=True, timings=timings)

        # Theme-country: always use 24h window — fast index lookup, "right now" framing
        top_theme_codes = [r['theme'] for r in top_themes[:6]]
        if top_theme_codes and has_theme_country_hourly:
            theme_country_rows = await _fetch_section(conn, degraded_segments, "theme_country", """
                SELECT tc.theme, tc.country_code, c.name as country_name,
                       SUM(tc.signal_count)::bigint as cnt
                FROM theme_country_hourly_v2 tc
                LEFT JOIN countries_v2 c ON tc.country_code = c.code
                WHERE tc.theme = ANY($1::text[])
                  AND tc.hour > NOW() - INTERVAL '24 hours'
                GROUP BY tc.theme, tc.country_code, c.name
                ORDER BY tc.theme, cnt DESC
            """, top_theme_codes,
                timeout_seconds=BRIEFING_OPTIONAL_DB_TIMEOUT_SECONDS, timings=timings)
        else:
            theme_country_rows = []

        stats = stats or {
            "total_signals": 0,
            "countries": 0,
            "sources": 0,
            "gdelt_sentiment": 0,
            "nlp_sentiment": None,
            "nlp_sentiment_weight_sum": None,
            "nlp_confidence_sum": None,
            "signal_count": 0,
            "nlp_signal_count": 0,
            "nlp_coverage": 0,
        }

        global_sentiment, global_source, global_coverage = choose_sentiment_weighted(
            stats.get("gdelt_sentiment") if isinstance(stats, dict) else stats["gdelt_sentiment"],
            stats.get("nlp_sentiment_weight_sum"),
            stats.get("nlp_confidence_sum"),
            stats.get("nlp_signal_count"),
            stats.get("signal_count") or stats.get("total_signals"),
            fallback_nlp_avg=stats.get("nlp_sentiment"),
        )

        result = {
            "period_hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "degraded": bool(degraded_segments),
            "degraded_segments": degraded_segments,
            "stats": {
                "total_signals": stats['total_signals'] or 0,
                "countries": stats['countries'] or 0,
                "sources": stats['sources'] or 0,
                "avg_sentiment": global_sentiment,
                "sentiment_source": global_source,
                "nlp_coverage": round(global_coverage, 3),
            },
            # C2: the strip (±1) and the tone panels (×10) print the SAME fused
            # number on two scales, and the fusion can serve past the panels'
            # −10…+10 legend. Serve the bridge + the true range so neither
            # surface has to assert a scale it cannot prove.
            "sentiment_scale": sentiment_scale_descriptor(),
            "top_countries": [serialize_country_row(r) for r in top_countries],
            "negative_sentiment": [serialize_country_row(r) for r in negative_sentiment],
            "category_counts": [
                {"category": r["category"], "topics": int(r["topics"]), "signals": int(r["signals"])}
                for r in category_counts
            ],
            # B3: gap box — attention without verified coverage (see query note).
            "coverage_gaps": [
                {
                    "slug": r["slug"],
                    "label": r["label"],
                    "raw_signals": int(r["raw_signals"]),
                    "verified": int(r["verified"]),
                    "scored": int(r["scored"]),
                    "status": gap_status(int(r["scored"])),
                    # measured gap-slice precision of this tier is 29-43% —
                    # hence K<=3 and the mandatory unverified-extended label.
                    "extended_receipts": gap_receipts_by_slug.get(r["slug"], []),
                }
                for r in coverage_gaps
            ],
            "positive_sentiment": [serialize_country_row(r) for r in positive_sentiment],
            "heat_countries": [
                {
                    "code": r["country_code"],
                    "name": r["name"],
                    "volume": r["volume"],
                    "heat": round(float(r["heat"] or 0), 3),
                    "components": {
                        "velocity": round(float(r["velocity"] or 0), 3),
                        "surprise": round(float(r["surprise"] or 0), 3),
                        "diversity": round(float(r["diversity"] or 0), 3),
                        "voice": round(float(r["voice"] or 0), 3),
                        "polyphony": round(float(r["polyphony"] or 0), 3),
                        "geo_confidence": round(float(r["geo_confidence"] or 0), 3),
                        "duplication": round(float(r["duplication"] or 0), 3),
                    },
                }
                for r in heat_countries
            ],
            "heat_voluminous_countries": [
                {
                    "code": r["country_code"],
                    "name": r["name"],
                    "volume": r["volume"],
                    "volume_floor": r["volume_floor"],
                    "heat": round(float(r["heat"] or 0), 3),
                    "components": {
                        "velocity": round(float(r["velocity"] or 0), 3),
                        "surprise": round(float(r["surprise"] or 0), 3),
                        "diversity": round(float(r["diversity"] or 0), 3),
                        "voice": round(float(r["voice"] or 0), 3),
                        "polyphony": round(float(r["polyphony"] or 0), 3),
                        "geo_confidence": round(float(r["geo_confidence"] or 0), 3),
                        "duplication": round(float(r["duplication"] or 0), 3),
                    },
                }
                for r in heat_voluminous_countries
            ],
            "heat_voluminous_percentile": HEAT_VOLUMINOUS_PERCENTILE,
            "top_themes": [
                {
                    "theme": r['theme'],
                    "count": r['count'],
                    "source_table": _record_get(r, "source_table", top_themes_source),
                    "model_version": _record_get(r, "model_version"),
                    "topic_coverage": (
                        round(float(r["topic_coverage"]), 3)
                        if _record_get(r, "topic_coverage") is not None else None
                    ),
                    "sentiment_coverage": (
                        round(float(r["sentiment_coverage"]), 3)
                        if _record_get(r, "sentiment_coverage") is not None else None
                    ),
                }
                for r in top_themes
            ],
            "top_themes_source": top_themes_source,
            "top_atlas_topics": [
                {
                    "slug": r["slug"],
                    # Serving-layer label guard (Lane A): a NULL/placeholder
                    # label renders as a receipt-derived fallback, never a
                    # raw "(label failed)" stub. Display-only.
                    "label": clean_thread_label(
                        r["label"],
                        [{"headline": h} for h in (_record_get(r, "sample_headlines") or [])],
                        r["slug"],
                        country_codes=[
                            str(c) for c in (_record_get(r, "top_country_codes") or [])
                        ],
                        category=_record_get(r, "category", _NO_CATEGORY),
                    ),
                    "parent_domain": _record_get(r, "parent_domain"),
                    "signal_count": int(r["signal_count"]),
                    "avg_confidence": (
                        float(r["avg_confidence"])
                        if _record_get(r, "avg_confidence") is not None else None
                    ),
                    "high_confidence_count": int(r["high_confidence_count"]),
                    "gated_signal_count": int(_record_get(r, "gated_signal_count", 0) or 0),
                    "gate_scored_count": int(_record_get(r, "gate_scored_count", 0) or 0),
                    "source_table": _record_get(r, "source_table", "signal_topic_assignments"),
                    "model_version": _record_get(r, "model_version", "theme-hint-lex-v2"),
                    # New optional fields populated when the emergent layer
                    # supplied this row; null/empty for the static atlas
                    # fallback.
                    "description": _record_get(r, "description"),
                    "velocity": (
                        int(r["velocity"])
                        if _record_get(r, "velocity") is not None else None
                    ),
                    "top_country_codes": list(_record_get(r, "top_country_codes") or []),
                    "cohesion": (
                        float(r["cohesion"])
                        if _record_get(r, "cohesion") is not None else None
                    ),
                    "vendor_agreement": _record_get(r, "vendor_agreement"),
                    "noise_rate": (
                        float(r["noise_rate"])
                        if _record_get(r, "noise_rate") is not None else None
                    ),
                }
                for r in top_atlas_topics
            ],
            "top_atlas_topics_source": (
                _record_get(top_atlas_topics[0], "source_table",
                            "signal_topic_assignments")
                if top_atlas_topics else "signal_topic_assignments"
            ),
            "top_threads": top_threads,
            "top_threads_contract": TOP_THREADS_CONTRACT,
            "rising": rising_section,
            "gap": gap_section,
            "topics_by_domain": [
                {
                    "parent_domain": r["parent_domain"],
                    "domain_signal_count": int(r["domain_signal_count"]),
                    "topics_in_domain": int(r["topics_in_domain"]),
                    "topics": (
                        json.loads(r["topics"])
                        if isinstance(_record_get(r, "topics"), str)
                        else _record_get(r, "topics")
                    ),
                }
                for r in topics_by_domain
            ],
            "related_topics": {
                r["topic_slug"]: (
                    json.loads(r["related"])
                    if isinstance(_record_get(r, "related"), str)
                    else _record_get(r, "related")
                )
                for r in related_topics
            },
            "historical_coverage": {
                "source": (
                    "historical_processed"
                    if top_themes_source == "historical_topic_country_daily" else "hot"
                ),
                "topicCoverage": (
                    round(
                        sum(float(_record_get(r, "topic_coverage") or 0) for r in top_themes)
                        / len(top_themes),
                        3,
                    )
                    if top_themes_source == "historical_topic_country_daily" and top_themes
                    else None
                ),
                "sentimentCoverage": (
                    round(
                        sum(float(_record_get(r, "sentiment_coverage") or 0) for r in top_themes)
                        / len(top_themes),
                        3,
                    )
                    if top_themes_source == "historical_topic_country_daily" and top_themes
                    else None
                ),
                "modelVersion": (
                    HISTORICAL_PROCESSED_MODEL_VERSION
                    if top_themes_source == "historical_topic_country_daily" else None
                ),
            },
            "top_sources": [
                {
                    "source": extract_domain(r['source_name']),
                    "count": r['count'],
                    "source_table": _record_get(r, "source_table", top_sources_source),
                    "model_version": _record_get(r, "model_version"),
                    "sentiment_coverage": (
                        round(float(r["sentiment_coverage"]), 3)
                        if _record_get(r, "sentiment_coverage") is not None else None
                    ),
                }
                for r in top_sources
            ],
            "top_sources_source": top_sources_source,
            "theme_country": _build_theme_country_map(theme_country_rows)
        }
    # T1 profiler: ALWAYS log the breakdown (descending — the culprit leads);
    # attach it to the payload only under ?profile=1, and never cache a
    # profiled payload (it bypassed the cache read, it must bypass the write).
    total_ms = round(sum(timings.values()), 1)
    logger.info(
        "briefing sections total=%sms breakdown=%s", total_ms,
        dict(sorted(timings.items(), key=lambda kv: -kv[1])),
    )
    if profile:
        result["meta_profile"] = {
            "section_timings_ms": timings,
            "sections_total_ms": total_ms,
        }
    if not profile and hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, cache_ttl, json.dumps(result))
        except Exception as exc:
            # 2026-08-17: was a bare `pass`. Measured consequence of the
            # silence: three back-to-back "warm" requests each recomputed the
            # full 15-18s serialized fill — the 900s cache had been dead with
            # nobody watching. Same rule as the read: degrade, but say so.
            logger.warning("briefing cache WRITE failed (%s): %s", cache_key, exc)
    return result


@router.get("/api/v2/briefing/insight")
async def get_briefing_insight(hours: int = Query(24, ge=1, le=8760)):
    """AI meta-summary of the global news landscape for the current time window."""
    cache_key = f"briefing_insight:{hours}"
    generated_at = datetime.now(timezone.utc).isoformat()

    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached_raw = await app.state.redis.get(cache_key)
            if cached_raw:
                data = json.loads(cached_raw)
                data["cached"] = True
                # A paragraph cached before this fix (TTL 30 min) must not
                # outlive it — the guard runs on the way out, not only on the
                # way in.
                data["insight"] = repair_scale_claims(data.get("insight"))
                return data
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            degraded_segments: list[str] = []
            has_theme_hourly = await conn.fetchval(
                "SELECT to_regclass('theme_hourly_v2') IS NOT NULL"
            )

            # Stats + top_countries come from country_hourly_v2 (same fast path as /briefing).
            stats = await _fetch_section(conn, degraded_segments, "insight_stats", """
                SELECT SUM(signal_count)::bigint AS total,
                       COUNT(DISTINCT country_code) AS countries,
                       CASE WHEN SUM(signal_count) > 0
                            THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                            ELSE 0::float END AS avg_sent
                FROM country_hourly_v2
                WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
            """, hours, row=True)

            top_countries = await _fetch_section(conn, degraded_segments, "insight_top_countries", """
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)::bigint AS cnt,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN (SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count))::float
                            ELSE 0::float END AS avg_s
                FROM country_hourly_v2 h
                LEFT JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                ORDER BY cnt DESC LIMIT 5
            """, hours)

            # top_themes uses theme_hourly_v2 (post-mig 008 + 025). Falls back to
            # signals_theme_hourly if the v2 pre-agg is unavailable on a given env.
            if has_theme_hourly:
                top_themes = await _fetch_section(conn, degraded_segments, "insight_top_themes", """
                    SELECT theme, SUM(signal_count)::bigint AS cnt
                    FROM theme_hourly_v2
                    WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """, hours)
            else:
                top_themes = await _fetch_section(conn, degraded_segments, "insight_top_themes_fallback", """
                    SELECT theme, SUM(signal_count)::bigint AS cnt
                    FROM signals_theme_hourly
                    WHERE bucket > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """, hours)

            # Re-judge §4a: the paragraph named GDELT theme codes while the
            # chart directly under it named Atlas R3 categories. Same constant
            # as the chart (_CATEGORY_COUNTS_SQL) → same lane, same order; the
            # GDELT rows above stay only as the fallback the chart itself uses
            # when no category is live.
            insight_categories = await _fetch_section(
                conn, degraded_segments, "insight_categories", _CATEGORY_COUNTS_SQL
            )
    except Exception as exc:
        logger.warning("briefing/insight db failed: %s", exc)
        return {"insight": None, "error": "db_error", "generated_at": generated_at}

    stats = stats or {"total": 0, "countries": 0, "avg_sent": 0}

    total = int(stats["total"] or 0)
    countries = int(stats["countries"] or 0)
    avg_sent = float(stats["avg_sent"] or 0) / 10
    # Re-judge §4a: `_clean_theme_label` (strip a prefix, .title()) is the code
    # path that printed "Ungp Forests Rivers Oceans, Crisislexrec" as English.
    # taxonomy_line reads the served CATEGORY lane first and drops any code it
    # cannot name — a missing bullet, never a mangled one.
    taxonomy_bullet = taxonomy_line(insight_categories, top_themes)
    countries_str = ", ".join([
        f"{r['name'] or r['country_code']} ({int(r['cnt'])} signals, {float(r['avg_s'] or 0) / 10:+.2f})"
        for r in top_countries
    ])

    # C3(ii) — THE GLASS BOX, HARDENED (blind judge 2026-08-12 §5).
    #
    # The judge's charge against this paragraph was precise: "Western outlets are
    # driving a narrative of instability or crisis" is a geopolitical
    # INTERPRETATION asserted from tone averages, on a page whose masthead
    # promises "measured from coverage, not editorialized". Two structural
    # corrections, both in the prompt because that is where the claim is born:
    #
    #  1. The BASIS is now stated in the data lines rather than left implicit.
    #     What this model receives is the FIVE most-covered countries with tone
    #     on the normalized ±1 scale — a different population and a different
    #     scale from the tone columns the reader sees below the paragraph (all
    #     countries, raw −10…+10). Unlabelled, "Russia −0.20" beside a table
    #     showing "Yemen −10.0" read as the page contradicting itself inside one
    #     screen. The surface prints the same basis deterministically
    #     (frontend-v2/src/lib/editorAnalysis.ts) — this is the belt to that
    #     brace, so the prose does not describe a population it never saw.
    #
    #  2. Causal and motive claims are OUT OF SCOPE. Coverage tone measures how
    #     something is being written about; it cannot support who is "driving" a
    #     narrative, why an outlet frames something, or what a state intends.
    #     Describable aggregates only — volumes, shares, tones, and where they
    #     sit relative to each other.
    #
    #  3. (re-judge 2026-08-13 §4a) The TAXONOMY and the SCALE, the two things
    #     this paragraph got visibly wrong in front of a reader:
    #     - the theme bullet is now the served category lane, named, so the
    #       paragraph and the chart under it cannot describe two populations;
    #     - the scale bullet declares its bounds as CONSTANTS and separates
    #       them from the measured figure. The model had filled "on the
    #       X…Y scale" with the one number it had ("−0.48 on the −0.48…−0.48
    #       scale"), so the bounds also get checked after generation
    #       (repair_scale_claims) — wording alone cannot close a generative slip.
    top_n = len(top_countries)
    user_prompt = (
        f"Describe the measured shape of the press coverage ATLAS INGESTED over the last {hours} hours.\n"
        f"- Total coverage ingested: {total:,} articles across {countries} countries, "
        "counted over Atlas's own feed set (~220 curated feeds plus the GDELT firehose) "
        "— a sample of the world's press, not a census of it\n"
        "- Tone scale: -1.00 to +1.00, fixed bounds (negative = critical/conflict-heavy "
        "wording, positive = supportive wording). Those two bounds are constants of the "
        "scale; a measured tone is never one of them.\n"
        f"- Average tone across all coverage: {avg_sent:+.2f} on that -1..+1 scale\n"
        + (f"{taxonomy_bullet}\n" if taxonomy_bullet else "")
        + f"- The {top_n} MOST-COVERED countries only, with article count and their own "
        f"average tone on the same -1..+1 scale: {countries_str}\n\n"
        "Write 2-3 sentences describing: what the press is covering most, how the tone is "
        "distributed across these countries, and any notable concentration in the volumes.\n"
        "When you cite a country's tone, make clear it is among these most-covered countries "
        "and on the -1..+1 scale — never call a figure the highest or lowest overall, because "
        "you have not been shown the other countries."
    )
    system_prompt = (
        "You describe measured aggregates of press coverage. You are NOT an analyst offering "
        "a view of world events, and the surface you write for states plainly that this is "
        "interpretation rather than measurement.\n"
        "RULES:\n"
        "1. Every claim must be supported by a number in the data given to you. If a number "
        "is not there, the claim is not yours to make.\n"
        "2. No causal or motive claims. Never say who is 'driving', 'shaping', 'pushing' or "
        "'framing' a narrative, never attribute intent to outlets, governments or blocs, and "
        "never explain WHY coverage looks as it does. Tone measures wording, not motive.\n"
        "3. No geopolitical judgement: no bloc language ('Western media', 'state-aligned "
        "media'), no claims about stability, legitimacy, or what any of this means for the "
        "world. Describe the coverage, not the events behind it.\n"
        "4. No superlatives beyond the rows you were given, and no forecasting.\n"
        "5. Name the taxonomy exactly as the data line labels it (say 'Atlas categories' or "
        "'GDELT themes' as given), never rename or reinterpret a category, and never state a "
        "volume for one — you were given their names, not their counts. If no such line is "
        "present, do not mention themes or categories at all.\n"
        "6. When you mention the tone scale, write its bounds exactly as given (-1 to +1). "
        "Never restate a scale using a measured figure as one of its bounds.\n"
        # X1 (2026-08-13): the systemic class from the veracity scorecard — the
        # shape of Atlas's ingest served as the shape of the world's press.
        "7. These counts are Atlas's ingested sample, never the whole press. NEVER say "
        "a country, region or outlet is absent, silent, missing or not covering something; "
        "a low or zero count is a fact about Atlas's feeds. Do not call the coverage "
        "global, worldwide or complete.\n"
        "Be concise and neutral. No markdown, no bullet points — flowing prose only."
    )

    # B0 (2026-07-05): provider chain Anthropic → DeepSeek — the Anthropic-only
    # path went silently dark for ~6 days on dry credits; the chain + the
    # provider field make an AI-lane death visible to the weekly read.
    from app.services.insight_llm import generate_insight
    insight_text, provider, error_code, _usage = await generate_insight(
        system_prompt, user_prompt, max_tokens=200, surface="brief",
    )
    if insight_text is None:
        return {"insight": None, "error": error_code, "generated_at": generated_at}

    # The bounds are constants, so they are enforced rather than requested:
    # any range the model asserts as "the scale" that is not the real scale is
    # rewritten to it. Healthy prose comes back byte-identical.
    insight_text = repair_scale_claims(insight_text)

    result = {"insight": insight_text, "provider": provider, "generated_at": generated_at, "cached": False}
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 1800, json.dumps(result))
        except Exception:
            pass
    return result


# =============================================================================
# TRUST INDICATORS API (v3)
# =============================================================================
