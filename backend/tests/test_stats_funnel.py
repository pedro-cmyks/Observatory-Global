from __future__ import annotations

from app.routers.stats import build_funnel_stages


def _stage(stages, key):
    return next(s for s in stages if s["stage"] == key)


def test_full_funnel_deltas_and_pct():
    stages = build_funnel_stages([
        ("raw", "Ingested (raw)", 1000),
        ("deduped", "Deduped", 800),
        ("classified", "Classified", 600),
        ("gate_survived", "Gate-survived", 300),
        ("thread_served", "Thread-served", 120),
    ])

    assert [s["stage"] for s in stages] == [
        "raw", "deduped", "classified", "gate_survived", "thread_served",
    ]

    raw = _stage(stages, "raw")
    assert raw["count"] == 1000
    assert raw["dropped_from_previous"] is None  # nothing before raw
    assert raw["pct_of_raw"] == 100.0

    deduped = _stage(stages, "deduped")
    assert deduped["dropped_from_previous"] == 200
    assert deduped["pct_of_raw"] == 80.0

    gate = _stage(stages, "gate_survived")
    assert gate["dropped_from_previous"] == 300  # 600 -> 300
    assert gate["pct_of_raw"] == 30.0

    served = _stage(stages, "thread_served")
    assert served["dropped_from_previous"] == 180  # 300 -> 120
    assert served["pct_of_raw"] == 12.0


def test_null_stage_never_fabricates_zero_or_drop():
    # classified is degraded (None). It must NOT read as 0, must NOT invent a
    # drop into it, AND must null the delta of the stage AFTER it (we don't
    # know the intermediate, so the combined drop is not attributed across it).
    stages = build_funnel_stages([
        ("raw", "Ingested (raw)", 1000),
        ("deduped", "Deduped", 800),
        ("classified", "Classified", None),
        ("gate_survived", "Gate-survived", 300),
        ("thread_served", "Thread-served", 120),
    ])

    classified = _stage(stages, "classified")
    assert classified["count"] is None
    assert classified["dropped_from_previous"] is None
    assert classified["pct_of_raw"] is None

    gate = _stage(stages, "gate_survived")
    assert gate["count"] == 300
    # delta out of the unknown stage is null, not 800 - 300
    assert gate["dropped_from_previous"] is None
    # pct_of_raw still computable off the known raw anchor
    assert gate["pct_of_raw"] == 30.0

    served = _stage(stages, "thread_served")
    assert served["dropped_from_previous"] == 180  # 300 -> 120, known pair
    assert served["pct_of_raw"] == 12.0


def test_null_raw_leaves_pct_none_but_keeps_known_deltas():
    stages = build_funnel_stages([
        ("raw", "Ingested (raw)", None),
        ("deduped", "Deduped", 800),
        ("classified", "Classified", 600),
    ])

    raw = _stage(stages, "raw")
    assert raw["pct_of_raw"] is None

    deduped = _stage(stages, "deduped")
    assert deduped["pct_of_raw"] is None  # cannot normalize against unknown raw
    assert deduped["dropped_from_previous"] is None  # prev (raw) is None

    classified = _stage(stages, "classified")
    assert classified["dropped_from_previous"] == 200  # 800 -> 600 both known


def test_zero_raw_does_not_divide():
    stages = build_funnel_stages([
        ("raw", "Ingested (raw)", 0),
        ("deduped", "Deduped", 0),
    ])
    assert _stage(stages, "raw")["pct_of_raw"] is None  # falsy raw guarded
    assert _stage(stages, "deduped")["dropped_from_previous"] == 0


def test_empty_input():
    assert build_funnel_stages([]) == []
