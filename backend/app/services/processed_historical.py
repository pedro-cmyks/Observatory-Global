"""Helpers for routing long product windows to compact processed history."""
from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any


HISTORICAL_MODEL_VERSION = os.getenv("HISTORICAL_PROCESSED_MODEL_VERSION", "atlas-hist-v1")
HOT_STORE_FLOOR_RAW = os.getenv("HOT_STORE_FLOOR", "2026-05-20T03:33:29Z")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


HOT_STORE_FLOOR = _parse_utc(HOT_STORE_FLOOR_RAW)


@dataclass(frozen=True)
class CoverageRange:
    from_: str
    to: str
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["from"] = data.pop("from_")
        return data


@dataclass(frozen=True)
class CoverageMeta:
    source: str
    model_version: str
    requested_hours: int
    covered_days: int
    hot_floor: str
    processed: CoverageRange | None
    partial_coverage: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "modelVersion": self.model_version,
            "requestedHours": self.requested_hours,
            "coveredDays": self.covered_days,
            "hotFloor": self.hot_floor,
            "processed": self.processed.to_dict() if self.processed else None,
            "partialCoverage": self.partial_coverage,
        }


def use_processed_history(hours: int) -> bool:
    return hours > 24


def days_for_hours(hours: int) -> int:
    return max(1, math.ceil(hours / 24))


def _iso_day(value: date | None) -> str | None:
    return value.isoformat() if value else None


async def build_historical_coverage(
    conn,
    *,
    hours: int,
    model_version: str = HISTORICAL_MODEL_VERSION,
) -> CoverageMeta:
    days = days_for_hours(hours)
    row = await conn.fetchrow(
        """
        SELECT MIN(day)::date AS first_day,
               MAX(day)::date AS last_day,
               COUNT(*)::bigint AS aggregate_rows,
               SUM(signal_count)::bigint AS represented_signals
        FROM historical_topic_country_daily
        WHERE day >= CURRENT_DATE - $1::int
          AND model_version = $2::text
        """,
        days,
        model_version,
    )
    aggregate_rows = int(row["aggregate_rows"] or 0) if row else 0
    represented_signals = int(row["represented_signals"] or 0) if row else 0
    first_day = row["first_day"] if row else None
    last_day = row["last_day"] if row else None
    covered_days = ((last_day - first_day).days + 1) if first_day and last_day else 0
    processed = CoverageRange(
        from_=_iso_day(first_day) or "",
        to=_iso_day(last_day) or "",
        row_count=represented_signals,
    ) if represented_signals else None
    return CoverageMeta(
        source="historical_processed",
        model_version=model_version,
        requested_hours=hours,
        covered_days=covered_days,
        hot_floor=HOT_STORE_FLOOR.isoformat().replace("+00:00", "Z"),
        processed=processed,
        partial_coverage=covered_days < days or aggregate_rows == 0,
    )


async def query_historical_country_attention(
    conn,
    *,
    hours: int,
    limit: int,
    model_version: str = HISTORICAL_MODEL_VERSION,
) -> list[dict[str, Any]]:
    """Return volume-normalized country attention for long historical windows.

    This is not 24h composite heat. It is the historical processed fallback for
    the same UI slot, scaled 0..1 by log volume so countries remain comparable.
    """
    days = days_for_hours(hours)
    rows = await conn.fetch(
        """
        WITH country_totals AS (
            SELECT h.country_code,
                   SUM(h.signal_count)::bigint AS signal_count,
                   CASE WHEN SUM(h.signal_count) > 0
                        THEN (
                            SUM(COALESCE(h.avg_sentiment, 0) * h.signal_count)
                            / SUM(h.signal_count)
                        )::float
                        ELSE 0::float END AS avg_sentiment,
                   AVG(h.topic_coverage)::float AS topic_coverage,
                   AVG(h.sentiment_coverage)::float AS sentiment_coverage,
                   AVG(h.entity_coverage)::float AS entity_coverage,
                   AVG(h.source_diversity)::float AS source_diversity
            FROM historical_topic_country_daily h
            WHERE h.day >= CURRENT_DATE - $1::int
              AND h.model_version = $2::text
            GROUP BY h.country_code
        ),
        ranked AS (
            SELECT *,
                   MAX(LN(signal_count + 1)) OVER () AS max_log_volume
            FROM country_totals
        )
        SELECT r.country_code,
               c.name AS country_name,
               c.latitude,
               c.longitude,
               r.signal_count,
               r.avg_sentiment,
               r.topic_coverage,
               r.sentiment_coverage,
               r.entity_coverage,
               r.source_diversity,
               CASE WHEN r.max_log_volume > 0
                    THEN (LN(r.signal_count + 1) / r.max_log_volume)::float
                    ELSE 0::float END AS historical_attention
        FROM ranked r
        LEFT JOIN countries_v2 c ON c.code = r.country_code
        ORDER BY r.signal_count DESC
        LIMIT $3::int
        """,
        days,
        model_version,
        limit,
    )
    return [dict(row) for row in rows]


async def query_historical_country_detail(
    conn,
    *,
    country_code: str,
    hours: int,
    model_version: str = HISTORICAL_MODEL_VERSION,
) -> dict[str, Any] | None:
    """Return compact processed country detail for long historical windows."""
    days = days_for_hours(hours)
    stats = await conn.fetchrow(
        """
        SELECT h.country_code,
               c.name AS country_name,
               SUM(h.signal_count)::bigint AS signal_count,
               CASE WHEN SUM(h.signal_count) > 0
                    THEN (
                        SUM(COALESCE(h.avg_sentiment, 0) * h.signal_count)
                        / SUM(h.signal_count)
                    )::float
                    ELSE 0::float END AS avg_sentiment,
               MIN(h.avg_sentiment)::float AS min_sentiment,
               MAX(h.avg_sentiment)::float AS max_sentiment,
               AVG(h.topic_coverage)::float AS topic_coverage,
               AVG(h.sentiment_coverage)::float AS sentiment_coverage,
               AVG(h.entity_coverage)::float AS entity_coverage,
               AVG(h.local_voice_ratio)::float AS local_voice_ratio,
               AVG(h.source_diversity)::float AS source_diversity
        FROM historical_topic_country_daily h
        LEFT JOIN countries_v2 c ON c.code = h.country_code
        WHERE h.country_code = $1::text
          AND h.day >= CURRENT_DATE - $2::int
          AND h.model_version = $3::text
        GROUP BY h.country_code, c.name
        """,
        country_code,
        days,
        model_version,
    )
    if not stats or not stats["signal_count"]:
        return None

    themes = await conn.fetch(
        """
        SELECT topic_slug, SUM(signal_count)::bigint AS signal_count
        FROM historical_topic_country_daily
        WHERE country_code = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
        GROUP BY topic_slug
        ORDER BY signal_count DESC
        LIMIT 10
        """,
        country_code,
        days,
        model_version,
    )
    source_mix = await conn.fetch(
        """
        SELECT source_family,
               signal_class,
               SUM(signal_count)::bigint AS signal_count
        FROM historical_topic_country_daily
        WHERE country_code = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
        GROUP BY source_family, signal_class
        ORDER BY signal_count DESC
        LIMIT 20
        """,
        country_code,
        days,
        model_version,
    )
    evidence = await conn.fetch(
        """
        SELECT headline,
               source_name,
               source_url,
               topic_slug,
               signal_timestamp,
               sentiment
        FROM historical_evidence_samples
        WHERE country_code = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
        ORDER BY day DESC, signal_timestamp DESC NULLS LAST
        LIMIT 12
        """,
        country_code,
        days,
        model_version,
    )

    return {
        "stats": dict(stats),
        "themes": [dict(row) for row in themes],
        "source_mix": [dict(row) for row in source_mix],
        "evidence": [dict(row) for row in evidence],
    }


async def query_historical_topic_detail(
    conn,
    *,
    topic_slug: str,
    hours: int,
    country_code: str | None = None,
    model_version: str = HISTORICAL_MODEL_VERSION,
) -> dict[str, Any] | None:
    """Return compact processed topic detail for Atlas topic slugs."""
    days = days_for_hours(hours)
    stats = await conn.fetchrow(
        """
        SELECT h.topic_slug,
               SUM(h.signal_count)::bigint AS signal_count,
               CASE WHEN SUM(h.signal_count) > 0
                    THEN (
                        SUM(COALESCE(h.avg_sentiment, 0) * h.signal_count)
                        / SUM(h.signal_count)
                    )::float
                    ELSE 0::float END AS avg_sentiment,
               COUNT(DISTINCT h.country_code)::int AS country_count,
               AVG(h.topic_coverage)::float AS topic_coverage,
               AVG(h.sentiment_coverage)::float AS sentiment_coverage,
               AVG(h.entity_coverage)::float AS entity_coverage,
               AVG(h.source_diversity)::float AS source_diversity
        FROM historical_topic_country_daily h
        WHERE h.topic_slug = $1::text
          AND h.day >= CURRENT_DATE - $2::int
          AND h.model_version = $3::text
          AND ($4::text IS NULL OR h.country_code = $4::text)
        GROUP BY h.topic_slug
        """,
        topic_slug,
        days,
        model_version,
        country_code,
    )
    if not stats or not stats["signal_count"]:
        return None

    timeline = await conn.fetch(
        """
        SELECT day,
               SUM(signal_count)::bigint AS signal_count,
               CASE WHEN SUM(signal_count) > 0
                    THEN (
                        SUM(COALESCE(avg_sentiment, 0) * signal_count)
                        / SUM(signal_count)
                    )::float
                    ELSE 0::float END AS avg_sentiment
        FROM historical_topic_country_daily
        WHERE topic_slug = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
          AND ($4::text IS NULL OR country_code = $4::text)
        GROUP BY day
        ORDER BY day
        """,
        topic_slug,
        days,
        model_version,
        country_code,
    )
    countries = await conn.fetch(
        """
        SELECT h.country_code,
               c.name AS country_name,
               SUM(h.signal_count)::bigint AS signal_count,
               CASE WHEN SUM(h.signal_count) > 0
                    THEN (
                        SUM(COALESCE(h.avg_sentiment, 0) * h.signal_count)
                        / SUM(h.signal_count)
                    )::float
                    ELSE 0::float END AS avg_sentiment
        FROM historical_topic_country_daily h
        LEFT JOIN countries_v2 c ON c.code = h.country_code
        WHERE h.topic_slug = $1::text
          AND h.day >= CURRENT_DATE - $2::int
          AND h.model_version = $3::text
          AND ($4::text IS NULL OR h.country_code = $4::text)
        GROUP BY h.country_code, c.name
        ORDER BY signal_count DESC
        LIMIT 15
        """,
        topic_slug,
        days,
        model_version,
        country_code,
    )
    source_mix = await conn.fetch(
        """
        SELECT source_family,
               signal_class,
               SUM(signal_count)::bigint AS signal_count
        FROM historical_topic_country_daily
        WHERE topic_slug = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
          AND ($4::text IS NULL OR country_code = $4::text)
        GROUP BY source_family, signal_class
        ORDER BY signal_count DESC
        LIMIT 20
        """,
        topic_slug,
        days,
        model_version,
        country_code,
    )
    evidence = await conn.fetch(
        """
        SELECT headline,
               source_name,
               source_url,
               country_code,
               signal_timestamp,
               sentiment
        FROM historical_evidence_samples
        WHERE topic_slug = $1::text
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
          AND ($4::text IS NULL OR country_code = $4::text)
        ORDER BY day DESC, signal_timestamp DESC NULLS LAST
        LIMIT 12
        """,
        topic_slug,
        days,
        model_version,
        country_code,
    )

    return {
        "stats": dict(stats),
        "timeline": [dict(row) for row in timeline],
        "countries": [dict(row) for row in countries],
        "source_mix": [dict(row) for row in source_mix],
        "evidence": [dict(row) for row in evidence],
    }


async def query_historical_theme_anomalies(
    conn,
    *,
    hours: int,
    limit: int,
    model_version: str = HISTORICAL_MODEL_VERSION,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return daily topic anomalies from compact history for long windows.

    Historical archive data is daily-grain. For anomaly detection, compare the
    latest complete archived day before HOT_STORE_FLOOR against previous days in
    the requested window. This avoids treating the partial cutover day as a drop.
    """
    days = days_for_hours(hours)
    current_day = await conn.fetchval(
        """
        SELECT MAX(day)::date
        FROM historical_topic_country_daily
        WHERE day < $1::date
          AND day >= CURRENT_DATE - $2::int
          AND model_version = $3::text
        """,
        HOT_STORE_FLOOR.date(),
        days,
        model_version,
    )
    if not current_day:
        return [], {
            "baseline_window_days": days,
            "current_day": None,
            "days_observed": 0,
            "degraded": True,
            "degraded_reason": "no_complete_historical_day",
        }

    rows = await conn.fetch(
        """
        WITH daily_topic AS (
            SELECT day,
                   topic_slug,
                   SUM(signal_count)::bigint AS daily_count,
                   AVG(topic_coverage)::float AS topic_coverage,
                   AVG(sentiment_coverage)::float AS sentiment_coverage
            FROM historical_topic_country_daily
            WHERE day <= $1::date
              AND day >= $1::date - $2::int
              AND model_version = $3::text
            GROUP BY day, topic_slug
        ),
        current_window AS (
            SELECT topic_slug,
                   daily_count,
                   topic_coverage,
                   sentiment_coverage
            FROM daily_topic
            WHERE day = $1::date
              AND daily_count >= 10
        ),
        baseline AS (
            SELECT topic_slug,
                   COUNT(*)::int AS days_observed,
                   AVG(daily_count)::float AS avg_daily,
                   STDDEV(daily_count)::float AS stddev_daily
            FROM daily_topic
            WHERE day < $1::date
            GROUP BY topic_slug
            HAVING COUNT(*) >= 2
        )
        SELECT c.topic_slug,
               c.daily_count,
               b.avg_daily,
               b.days_observed,
               c.topic_coverage,
               c.sentiment_coverage,
               ROUND((c.daily_count::numeric / NULLIF(b.avg_daily, 0)::numeric), 2) AS multiplier,
               ROUND(((c.daily_count - b.avg_daily) /
                      NULLIF(COALESCE(b.stddev_daily, b.avg_daily * 0.3), 0))::numeric, 2) AS zscore
        FROM current_window c
        JOIN baseline b ON b.topic_slug = c.topic_slug
        WHERE ((c.daily_count - b.avg_daily) /
               NULLIF(COALESCE(b.stddev_daily, b.avg_daily * 0.3), 0)) > 1.5
        ORDER BY zscore DESC NULLS LAST, c.daily_count DESC
        LIMIT $4::int
        """,
        current_day,
        days,
        model_version,
        limit,
    )
    meta = {
        "baseline_window_days": days,
        "current_day": current_day.isoformat(),
        "degraded": False,
        "degraded_reason": None,
        "method": "historical_daily_topic_zscore",
    }
    return [dict(row) for row in rows], meta
