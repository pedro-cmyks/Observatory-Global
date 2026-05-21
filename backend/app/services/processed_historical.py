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
