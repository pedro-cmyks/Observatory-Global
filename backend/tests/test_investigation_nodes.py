from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from app.services.investigation_nodes import (
    NODE_TYPES,
    ResolveNodeInput,
    resolve_investigation_node,
)


def _input(node_type: str, ref_id: str = "ref-1") -> ResolveNodeInput:
    return ResolveNodeInput(
        node_type=node_type,
        subtype="test",
        ref_id=ref_id,
        label=f"Test {node_type}",
        observation_window={
            "range_start": "2026-07-11T00:00:00Z",
            "range_end": "2026-07-12T00:00:00Z",
            "mode": "live",
        },
        snapshot={"summary": "visible at pin time", "count": 7},
    )


def test_every_declared_node_type_normalizes_without_enrichment():
    for node_type in NODE_TYPES:
        node = asyncio.run(resolve_investigation_node(_input(node_type)))
        assert node.node_type == node_type
        assert node.resolution_status == "metadata_only"
        assert node.snapshot["summary"] == "visible at pin time"
        assert node.resolution_receipt.retryable is True


def test_node_identity_is_stable_for_same_type_subtype_and_live_ref():
    first = asyncio.run(resolve_investigation_node(_input("country", "IR")))
    second = asyncio.run(resolve_investigation_node(_input("country", "IR")))

    assert first.node_id == second.node_id
    assert first.pinned_at != ""


def test_observation_window_rejects_inverted_range():
    with pytest.raises(ValidationError):
        ResolveNodeInput(
            node_type="country",
            subtype="country",
            ref_id="IR",
            label="Iran",
            observation_window={
                "range_start": "2026-07-12T00:00:00Z",
                "range_end": "2026-07-11T00:00:00Z",
            },
        )


def test_snapshot_is_deep_copied_at_resolution_boundary():
    request = _input("country", "IR")
    request.snapshot["nested"] = {"voices": ["fa", "en"]}

    node = asyncio.run(resolve_investigation_node(request))
    request.snapshot["nested"]["voices"].append("es")

    assert node.snapshot["nested"]["voices"] == ["fa", "en"]


def test_thread_adapter_preserves_frozen_snapshot_and_adds_live_receipts():
    async def fetch_thread(*, thread_id: str, hours: int):
        assert thread_id == "dynamic-topic-1594"
        assert hours == 24
        return {
            "thread_id": thread_id,
            "label": "Iran negotiations",
            "signal_count": 66,
            "evidence_samples": [{"id": 1, "source_url": "https://example.com/1"}],
        }

    request = _input("story", "dynamic-topic-1594")
    request.subtype = "thread"
    node = asyncio.run(resolve_investigation_node(request, thread_fetcher=fetch_thread))

    assert node.resolution_status == "resolved"
    assert node.snapshot["summary"] == "visible at pin time"
    assert node.snapshot["live"]["signal_count"] == 66
    assert node.snapshot["live"]["evidence_samples"][0]["source_url"]


def test_signal_adapter_captures_canonical_source_receipt():
    async def fetch_signal(signal_id: int):
        assert signal_id == 42
        return {
            "id": 42,
            "headline": "A canonical signal",
            "source_name": "Reuters",
            "source_url": "https://example.com/42",
            "timestamp": "2026-07-12T00:00:00Z",
        }

    request = _input("evidence", "42")
    request.subtype = "signal"
    node = asyncio.run(resolve_investigation_node(request, signal_fetcher=fetch_signal))

    assert node.resolution_status == "resolved"
    assert node.snapshot["live"]["source_url"] == "https://example.com/42"


def test_adapter_failure_keeps_metadata_node_and_names_caveat():
    async def broken_thread(**kwargs):
        raise TimeoutError("thread adapter timeout")

    request = _input("story", "dynamic-topic-1594")
    request.subtype = "thread"
    node = asyncio.run(resolve_investigation_node(request, thread_fetcher=broken_thread))

    assert node.resolution_status == "metadata_only"
    assert node.snapshot["summary"] == "visible at pin time"
    assert node.resolution_receipt.caveat == "thread_adapter_unavailable:TimeoutError"
