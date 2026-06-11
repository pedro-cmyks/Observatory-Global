"""Pin-event telemetry contract (#218, Phase 2 day-one deliverable).

Validates the request models and the relevance-label vocabulary. The endpoint
itself is best-effort by design (DB down -> accepted=0, never 500); the write
path is covered by live smoke after the migration is applied.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

import app.main_v2  # noqa: F401 — load the app first (router imports it back)
from app.routers.research import PinEvent, PinEventBatch


def test_event_types_are_the_closed_relevance_vocabulary():
    for et in ("impression", "open", "pin", "unpin", "dismiss"):
        PinEvent(anchor_id="water-stress-drought--ir", event_type=et)
    with pytest.raises(ValidationError):
        PinEvent(anchor_id="x", event_type="click")  # not a graded judgment


def test_batch_requires_plan_id_and_events():
    batch = PinEventBatch(
        plan_id="rp-abc123",
        investigation_id="inv-local-1",
        query_text="crisis hídrica en Teherán",
        events=[
            PinEvent(anchor_id="water-stress-drought--ir", event_type="impression",
                     rank_shown=0, visibility="primary", investigative_score=0.381),
            PinEvent(anchor_id="water-stress-drought--ir", event_type="pin"),
        ],
    )
    assert len(batch.events) == 2
    with pytest.raises(ValidationError):
        PinEventBatch(plan_id="rp-abc123", events=[])
    with pytest.raises(ValidationError):
        PinEventBatch(plan_id="", events=[PinEvent(anchor_id="a", event_type="pin")])


def test_score_and_rank_bounds():
    with pytest.raises(ValidationError):
        PinEvent(anchor_id="a", event_type="open", investigative_score=1.5)
    with pytest.raises(ValidationError):
        PinEvent(anchor_id="a", event_type="open", rank_shown=-1)
    with pytest.raises(ValidationError):
        PinEvent(anchor_id="a", event_type="open", dwell_ms=-5)
