"""Custom query-thread builder.

Turns an arbitrary user search into a temporary Narrative Thread: a
theme-detail-shaped payload assembled from whatever signals directly match the
query. There is no minimum-evidence gate — a sparse match still produces a
thread, flagged with a ``coverage`` tier ("thin" | "limited" | "ok") so the
reading panel can show a THIN badge like country-scoped threads do.

Pure function over rows — DB fetching lives in the router, mirroring the
existing emergent/dynamic-topic detail paths.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.services.thread_packet import build_thread_packet

# Coverage thresholds match the frontend badges used across CountryBrief,
# NarrativeThreads, and ChokepointPanel: n<10 -> thin, 10<=n<50 -> limited.
_THIN_MAX = 10
_LIMITED_MAX = 50


def _slugify(text: str) -> str:
    """Lowercase ASCII slug: accents folded, non-alphanumerics -> single dash."""
    folded = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
    return slug


def _coverage_tier(sample: int) -> str:
    if sample < _THIN_MAX:
        return "thin"
    if sample < _LIMITED_MAX:
        return "limited"
    return "ok"


def build_query_thread(
    rows: list,
    query: str,
    *,
    hours: int,
    country: str | None = None,
) -> dict[str, Any]:
    """Assemble a temporary thread detail payload from matched signal rows.

    Parameters
    ----------
    rows:
        Signal rows with the columns ``build_thread_packet`` consumes.
    query:
        The raw user query; preserved as ``label`` and ``query``.
    hours, country:
        Echoed back into the payload for scope display.
    """
    query = query.strip()
    packet = build_thread_packet(rows, own_topic=None)
    sample = len(rows)
    avg_sentiment = (
        sum(float(r["sentiment"] or 0) for r in rows) / sample if sample else 0
    )
    coverage = _coverage_tier(sample)

    warnings: list[str] = []
    if coverage == "thin":
        warnings.append("query_thread_thin_coverage")

    return {
        "theme": f"query-thread-{_slugify(query)}",
        "label": query,
        "description": None,
        "country": country,
        "hours": hours,
        "total": sample,
        "rawTotal": sample,
        "gated": sample,
        "source": "query_thread",
        "query": query,
        "coverageTier": coverage,
        "relatedThemes": [],
        "countryFraming": [],
        "relatedConcepts": [],
        "signalSample": sample,
        "avgSentiment": round(avg_sentiment, 3),
        "signals": packet["graphSignals"],
        "graphSignals": packet["graphSignals"],
        "countryBreakdown": packet["countryBreakdown"],
        "topSources": packet["topSources"],
        "topPersons": packet["topPersons"],
        "timeline": packet["timeline"],
        "lanes": packet["lanes"],
        "warnings": warnings,
    }
