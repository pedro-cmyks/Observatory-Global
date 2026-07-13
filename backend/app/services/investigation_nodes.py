"""Typed, stateless pin normalization for the Atlas Investigation Graph."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field, model_validator

CONTRACT = "atlas-investigation-v2"
NODE_TYPES = (
    "story", "evidence", "subject", "country", "source", "event",
    "anomaly", "attention", "asset", "temporal_slice",
)
NodeType = Literal[
    "story", "evidence", "subject", "country", "source", "event",
    "anomaly", "attention", "asset", "temporal_slice",
]
ResolutionStatus = Literal["resolved", "partial", "metadata_only", "unavailable"]


class ObservationWindow(BaseModel):
    range_start: datetime
    range_end: datetime
    cursor_at: datetime | None = None
    mode: Literal["live", "historical"] = "live"

    @model_validator(mode="after")
    def validate_range(self) -> "ObservationWindow":
        if self.range_end < self.range_start:
            raise ValueError("range_end must be on or after range_start")
        if self.cursor_at is not None and not (
            self.range_start <= self.cursor_at <= self.range_end
        ):
            raise ValueError("cursor_at must fall inside the observation range")
        return self


class ResolveNodeInput(BaseModel):
    node_type: NodeType
    subtype: str = Field(..., min_length=1, max_length=80)
    ref_id: str = Field(..., min_length=1, max_length=500)
    label: str = Field(..., min_length=1, max_length=500)
    observation_window: ObservationWindow
    snapshot: dict[str, Any] = Field(default_factory=dict)
    analyst_note: str | None = Field(None, max_length=5000)
    quality: dict[str, Any] = Field(default_factory=dict)


class ResolutionReceipt(BaseModel):
    adapter: str
    resolved_at: datetime
    retryable: bool
    caveat: str | None = None


class InvestigationNode(BaseModel):
    contract: Literal["atlas-investigation-v2"] = CONTRACT
    node_id: str
    node_type: NodeType
    subtype: str
    label: str
    live_ref: dict[str, str]
    pinned_at: datetime
    observation_window: ObservationWindow
    snapshot: dict[str, Any]
    analyst_note: str | None = None
    quality: dict[str, Any] = Field(default_factory=dict)
    resolution_status: ResolutionStatus
    resolution_receipt: ResolutionReceipt


ThreadFetcher = Callable[..., Awaitable[dict[str, Any] | None]]
SignalFetcher = Callable[[int], Awaitable[dict[str, Any] | None]]


def _stable_node_id(request: ResolveNodeInput) -> str:
    identity = json.dumps(
        [request.node_type, request.subtype, request.ref_id],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return f"node-{request.node_type}-{digest}"


async def resolve_investigation_node(
    request: ResolveNodeInput,
    *,
    thread_fetcher: ThreadFetcher | None = None,
    signal_fetcher: SignalFetcher | None = None,
) -> InvestigationNode:
    """Freeze the visible observation, then best-effort enrich its live ref."""
    snapshot = copy.deepcopy(request.snapshot)
    adapter = f"{request.node_type}:{request.subtype}"
    status: ResolutionStatus = "metadata_only"
    caveat: str | None = "canonical_enrichment_not_available"
    retryable = True

    try:
        live: dict[str, Any] | None = None
        if request.node_type == "story" and request.subtype == "thread" and thread_fetcher:
            hours = max(
                1,
                round(
                    (request.observation_window.range_end - request.observation_window.range_start)
                    .total_seconds() / 3600
                ),
            )
            live = await thread_fetcher(thread_id=request.ref_id, hours=hours)
        elif request.node_type == "evidence" and request.subtype == "signal" and signal_fetcher:
            live = await signal_fetcher(int(request.ref_id))

        if live is not None:
            snapshot["live"] = copy.deepcopy(dict(live))
            status = "resolved"
            caveat = None
            retryable = False
        elif (
            (request.node_type == "story" and request.subtype == "thread" and thread_fetcher)
            or (request.node_type == "evidence" and request.subtype == "signal" and signal_fetcher)
        ):
            caveat = f"{request.subtype}_not_found"
    except Exception as exc:  # pin survives; receipt names the failed adapter
        caveat = f"{request.subtype}_adapter_unavailable:{exc.__class__.__name__}"

    now = datetime.now(timezone.utc)
    return InvestigationNode(
        node_id=_stable_node_id(request),
        node_type=request.node_type,
        subtype=request.subtype,
        label=request.label,
        live_ref={"kind": request.subtype, "id": request.ref_id},
        pinned_at=now,
        observation_window=request.observation_window,
        snapshot=snapshot,
        analyst_note=request.analyst_note,
        quality=copy.deepcopy(request.quality),
        resolution_status=status,
        resolution_receipt=ResolutionReceipt(
            adapter=adapter,
            resolved_at=now,
            retryable=retryable,
            caveat=caveat,
        ),
    )
