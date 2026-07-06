"""Deep-history / story-history series builder (#236, 2026-07-06).

The archive activity strip lives or dies on `_build_series` producing a
DISCRIMINATIVE signal: at the permissive match floor the unit *count* tracks
total archive volume, so `peak_sim` (the day's strongest cluster match) is the
spike signal the consumer bars on. These freeze that contract.
"""
from app.services.deep_history import _build_series


def _row(day, n_signals, sim):
    return {"day": day, "n_signals": n_signals, "sim": sim,
            "label": "x", "samples": [], "top_cc": []}


def test_aggregates_units_and_signals_per_day():
    rows = [
        _row("2026-05-20", 100, 0.40),
        _row("2026-05-20", 50, 0.55),
        _row("2026-05-21", 30, 0.62),
    ]
    series = _build_series(rows)
    assert series == [
        {"day": "2026-05-20", "units": 2, "signals": 150, "peak_sim": 0.55},
        {"day": "2026-05-21", "units": 1, "signals": 30, "peak_sim": 0.62},
    ]


def test_peak_sim_is_the_day_max_not_the_count():
    # A busy background day (many weak matches) must NOT out-rank a quiet spike
    # day (one strong match) — peak_sim is what separates them.
    rows = [_row("2026-06-01", 40, 0.34) for _ in range(20)]
    rows.append(_row("2026-06-02", 40, 0.80))
    by_day = {s["day"]: s for s in _build_series(rows)}
    assert by_day["2026-06-01"]["units"] == 20  # high volume
    assert by_day["2026-06-01"]["peak_sim"] == 0.34  # but weak
    assert by_day["2026-06-02"]["peak_sim"] == 0.80  # the real spike


def test_sorted_by_day_and_empty_safe():
    assert _build_series([]) == []
    out = _build_series([_row("2026-05-10", 5, 0.5), _row("2026-05-04", 5, 0.5)])
    assert [s["day"] for s in out] == ["2026-05-04", "2026-05-10"]
