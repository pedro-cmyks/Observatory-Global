import json
import logging
import os
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
    serialize_country_row,
)
from app.services.thread_intelligence import fetch_threads  # noqa: E402


TOP_THREADS_CONTRACT = "living-narrative-threads-v0"
TOP_THREADS_LIMIT = int(os.getenv("BRIEFING_TOP_THREADS_LIMIT", "10"))


async def _fetch_section(
    conn,
    degraded_segments: list[str],
    segment: str,
    query: str,
    *args,
    row: bool = False,
):
    try:
        if row:
            return await conn.fetchrow(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
        return await conn.fetch(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
    except Exception as exc:
        degraded_segments.append(segment)
        logger.warning("briefing section degraded: %s: %s", segment, exc)
        return None if row else []

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


def _clean_theme_label(theme_code: str) -> str:
    """Convert theme code like WB_475_DIGITAL_GOVERNMENT to 'Digital Government'."""
    label = (theme_code or "").upper()
    prefixes = (
        "WB_", "TAX_", "GDELT_", "CRISISLEX_", "USPEC_", "UN_",
        "SOC_", "ENV_", "ECON_", "EPU_", "MIL_", "CRIME_", "HEALTH_",
    )
    for prefix in prefixes:
        if label.startswith(prefix):
            parts = label.split("_", 2)
            label = parts[-1] if len(parts) >= 2 else label
            break
    parts = label.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        label = parts[1]
    return label.replace("_", " ").title()


def _record_get(row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def _use_historical_processed(hours: int) -> bool:
    """Use compact processed history for windows outside the hot raw horizon."""
    return hours > 24


@router.get("/api/v2/briefing")
async def get_briefing(hours: int = Query(24, ge=1, le=8760)):
    """Get morning briefing summary."""
    cache_key = f"briefing_data:{hours}"
    cache_ttl = 900 if hours <= 24 else 1800
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 15000")
        degraded_segments: list[str] = []
        has_theme_country_hourly = await conn.fetchval(
            "SELECT to_regclass('theme_country_hourly_v2') IS NOT NULL"
        )
        has_historical_processed = await conn.fetchval(
            "SELECT to_regclass('historical_topic_country_daily') IS NOT NULL"
        )
        has_historical_source_daily = await conn.fetchval(
            "SELECT to_regclass('historical_source_daily') IS NOT NULL"
        )
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
        """, hours)
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
                HAVING SUM(h.signal_count) > 10
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
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE)
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
                HAVING SUM(h.signal_count) > 10
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
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE)
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
            """, hours, HISTORICAL_PROCESSED_MODEL_VERSION)
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
            """, hours)
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
            """, hours, HISTORICAL_PROCESSED_MODEL_VERSION)
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
            """, hours)
            top_sources_source = "signals_v2"
        # Heat ranking (#149): atlas_heat from country_heat_v2 ranks countries by
        # what is heating up right now (velocity + surprise + source diversity +
        # local voice + frame polyphony + geo confidence − duplication), not raw
        # signal volume. Complements top_countries (volume rank) so the briefing
        # exposes both lenses without forcing a single ranking metric.
        has_country_heat = await conn.fetchval(
            "SELECT to_regclass('country_heat_v2') IS NOT NULL"
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
            """)
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
            """, HEAT_VOLUMINOUS_PERCENTILE)
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
        has_atlas_assignments = await conn.fetchval(
            "SELECT to_regclass('signal_topic_assignments') IS NOT NULL"
        )
        has_emergent_clusters = await conn.fetchval(
            "SELECT to_regclass('emergent_clusters') IS NOT NULL"
        )

        # Topic surface: prefer the emergent layer (HDBSCAN + ≥90%-precision
        # gate + DeepSeek labels, mig 046, spec
        # docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md)
        # when a fresh snapshot is available. Falls back to the static
        # atlas_topics ranking pre-snapshot or during a snapshot pipeline
        # outage so the brief Watchlist never goes empty.
        #
        # Mapped to the existing top_atlas_topics frontend contract so the
        # brief renders unchanged: signal_count = raw cluster size,
        # gated_signal_count = post-gate kept, gate_scored_count = raw size
        # (every cluster member was scored by the gate). slug = 'cluster-<id>'
        # resolves in /api/v2/theme/{slug} via the cluster-N detail branch.
        top_atlas_topics: list = []
        if has_emergent_clusters:
            snap_row = await conn.fetchrow(
                "SELECT MAX(snapshot_at) AS snap FROM emergent_clusters "
                "WHERE snapshot_at > NOW() - ($1::int * INTERVAL '1 hour')",
                hours,
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
                        vendor_agreement
                    FROM emergent_clusters
                    WHERE snapshot_at = $1
                    ORDER BY velocity DESC NULLS LAST, n_signals DESC
                    LIMIT 10
                """, snap)

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
                       a.model_version                                          AS model_version
                FROM signal_topic_assignments a
                JOIN atlas_topics t ON t.id = a.topic_id
                WHERE a.method = 'lexicon'
                  AND a.model_version = 'theme-hint-lex-v2'
                  AND a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY t.slug, t.label, t.parent_domain, a.model_version
                ORDER BY signal_count DESC
                LIMIT 10
            """, hours)

        # Living Narrative Threads (Milestone 2): assemble the same product
        # contract that /api/v2/threads serves so Brief leads with natural
        # threads (label, why_now, changed_10h, confidence band) instead of
        # raw atlas-topic counts. Reuses the briefing connection through
        # fetch_threads(conn=...). Degrades to [] on any failure so the
        # briefing payload still ships.
        top_threads: list = []
        if has_atlas_assignments:
            try:
                top_threads = await fetch_threads(
                    hours=hours,
                    limit=TOP_THREADS_LIMIT,
                    conn=conn,
                )
            except Exception as exc:
                degraded_segments.append("top_threads")
                logger.warning("briefing section degraded: top_threads: %s", exc)
                top_threads = []

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
            """, hours)
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
            """, hours)
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
        """, hours, row=True)

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
            """, top_theme_codes)
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
            "top_countries": [serialize_country_row(r) for r in top_countries],
            "negative_sentiment": [serialize_country_row(r) for r in negative_sentiment],
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
                    "label": r["label"],
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
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, cache_ttl, json.dumps(result))
        except Exception:
            pass
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
    except Exception as exc:
        logger.warning("briefing/insight db failed: %s", exc)
        return {"insight": None, "error": "db_error", "generated_at": generated_at}

    stats = stats or {"total": 0, "countries": 0, "avg_sent": 0}

    total = int(stats["total"] or 0)
    countries = int(stats["countries"] or 0)
    avg_sent = float(stats["avg_sent"] or 0) / 10
    themes_str = ", ".join([_clean_theme_label(r["theme"]) for r in top_themes])
    countries_str = ", ".join([
        f"{r['name'] or r['country_code']} ({int(r['cnt'])} signals, {float(r['avg_s'] or 0) / 10:+.2f})"
        for r in top_countries
    ])

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return {"insight": None, "error": "insight_unavailable", "generated_at": generated_at}

    user_prompt = (
        f"Summarize the global information landscape over the last {hours} hours.\n"
        f"- Total coverage: {total:,} articles across {countries} countries\n"
        f"- Global sentiment: {avg_sent:+.1f} (negative = concern/crisis, positive = stability/progress)\n"
        f"- Dominant topics: {themes_str}\n"
        f"- Most-covered countries (with their tone): {countries_str}\n\n"
        "Write 2-3 sentences describing what the world's media is focused on right now, "
        "what emotional tenor dominates, and any notable geographic patterns in coverage."
    )
    system_prompt = (
        "You are an intelligence analyst giving a morning media briefing. "
        "Describe what the world's press is covering and how, using the data provided. "
        "Be concise, neutral, and analytical. No markdown, no bullet points — flowing prose only."
    )

    try:
        import anthropic as _anthropic
        client = _anthropic.AsyncAnthropic(api_key=anthropic_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        insight_text = next((b.text for b in response.content if b.type == "text"), None)
    except Exception as e:
        err = str(e)
        code = "insight_no_credits" if "credit balance" in err.lower() else "insight_unavailable"
        return {"insight": None, "error": code, "generated_at": generated_at}

    result = {"insight": insight_text, "generated_at": generated_at, "cached": False}
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 1800, json.dumps(result))
        except Exception:
            pass
    return result


# =============================================================================
# TRUST INDICATORS API (v3)
# =============================================================================
