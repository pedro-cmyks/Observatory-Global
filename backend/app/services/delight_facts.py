"""Loading-delight fact phrasing (math-first, no LLM).

Turns already-measured aggregates into the short sentences the frontend
LoadingMoment rotates during load states. Every fact is template-phrased from
real numbers; the honesty metadata (kind='measured', window_hours) travels
with each fact so the UI can label it. A fact builder returns None when its
inputs don't clear the bar — the feed simply omits it.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _fmt(n: int) -> str:
    return f"{int(n):,}"


def _fact(fact_id: str, text: str, window_hours: int = 24) -> dict:
    return {
        "id": fact_id,
        "kind": "measured",
        "text": text,
        "window_hours": window_hours,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


def pulse_fact(signals_24h: int, countries: int, languages: int) -> dict | None:
    """Global pulse: how much the system actually read in the window."""
    if signals_24h < 1000 or countries < 10:
        return None
    text = (
        f"In the last 24 hours Atlas read {_fmt(signals_24h)} headlines "
        f"across {_fmt(countries)} countries"
    )
    if languages >= 5:
        text += f" in {_fmt(languages)} languages"
    return _fact("pulse", text + ".")


def language_fact(total_known: int, english: int, languages: int) -> dict | None:
    """Non-English share — the diversity program as a daily number."""
    if total_known < 500 or languages < 5:
        return None
    pct = round(100 * (total_known - english) / total_known)
    if pct < 2:
        return None
    return _fact(
        "voices",
        f"{pct}% of what Atlas read today was not in English — "
        f"{_fmt(languages)} languages, one map.",
    )


def mover_fact(label: str | None) -> dict | None:
    """Fastest-rising story per the shared Kalman movement field."""
    if not label or len(label.strip()) < 4:
        return None
    return _fact("mover", f"Fastest-rising story right now: “{label.strip()}”.")


def gap_fact(label: str | None, raw_signals: int) -> dict | None:
    """Coverage gap: attention without verified coverage — shown, not hidden."""
    if not label or raw_signals < 20:
        return None
    return _fact(
        "gap",
        f"{_fmt(raw_signals)} headlines touched “{label.strip()}” today — "
        "none verified yet. Atlas shows its gaps instead of hiding them.",
    )


def quiet_fact(country_name: str | None, volume: int) -> dict | None:
    """Under the radar: high composite heat on low volume."""
    if not country_name or volume <= 0 or volume > 500:
        return None
    return _fact(
        "quiet",
        f"Under the radar: {country_name} runs hot on Atlas’s composite heat "
        f"with only {_fmt(volume)} headlines. Low volume, high signal.",
    )
