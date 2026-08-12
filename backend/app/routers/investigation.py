"""Stateless typed Investigation Graph node normalization."""
from __future__ import annotations

import asyncio
import json
import math
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app import db
from app.services.investigation_nodes import (
    CONTRACT,
    ResolveNodeInput,
    resolve_investigation_node,
)
from app.services.investigation_graph import (
    GraphRequest,
    PublicationPackageRequest,
    assemble_investigation_graph,
    build_publication_package,
)
from app.services.edition_status import normalize_stored_status
from app.services.seal_schedule import build_seal_schedule
from app.services.thread_intelligence import fetch_thread_detail
from app.routers.dossier import ConnectionsRequest, dossier_connections

router = APIRouter(prefix="/api/v2/investigation", tags=["investigation"])
DOSSIER_RELATION_PROVIDER_WINDOW = 64
NODE_RESOLUTION_CONCURRENCY = 8


class ResolveNodesRequest(BaseModel):
    # Operational concurrency is bounded; the semantic universe is not.
    nodes: list[ResolveNodeInput] = Field(default_factory=list)


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


async def _fetch_dossier_relation_payload(
    topic_ids: list[str],
    *,
    days: int,
    timeout_s: float,
) -> dict[str, Any]:
    # The typed graph still processes every node/pair through exact + context.
    # This older, heavier provider has a finite request shape; disclose that
    # engine as unavailable for the whole set instead of silently taking the
    # first N and implying complete semantic coverage.
    if len(topic_ids) > DOSSIER_RELATION_PROVIDER_WINDOW:
        return {
            "contract": "dossier-connections-v1",
            "nodes": [],
            "edges": [],
            "neighbors": [],
            "distributions": None,
            "unresolved": topic_ids,
            "reason": "provider_operational_window_exceeded",
            "meta": {
                "requested_topics": len(topic_ids),
                "provider_window": DOSSIER_RELATION_PROVIDER_WINDOW,
                "truncated": False,
                "omission_policy": "none_processed_by_this_engine",
            },
        }
    try:
        return await asyncio.wait_for(
            dossier_connections(ConnectionsRequest(
                topic_ids=topic_ids,
                days=days,
                collapse_umbrellas=True,
            )),
            timeout=timeout_s,
        )
    except TimeoutError:
        return {
            "contract": "dossier-connections-v1",
            "nodes": [],
            "edges": [],
            "neighbors": [],
            "distributions": None,
            "unresolved": topic_ids,
            "reason": "provider_timeout",
            "meta": {"timeout_s": timeout_s, "degraded": True},
        }


async def _fetch_signal(signal_id: int) -> dict[str, Any] | None:
    if db.pool is None:
        return None
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, headline, snippet, source_name, source_url, source_lang,
                   country_code, timestamp, sentiment, persons, themes
            FROM signals_v2
            WHERE id = $1
            """,
            signal_id,
            timeout=5,
        )
    return dict(row) if row else None


@router.post("/resolve-node")
async def resolve_node(body: ResolveNodeInput) -> dict[str, Any]:
    node = await resolve_investigation_node(
        body,
        thread_fetcher=fetch_thread_detail,
        signal_fetcher=_fetch_signal,
    )
    statuses = {name: 0 for name in (
        "resolved", "partial", "metadata_only", "unavailable"
    )}
    statuses[node.resolution_status] = 1
    return {
        "contract": CONTRACT,
        "node": node,
        "completion": {"requested": 1, **statuses},
    }


@router.post("/resolve-nodes")
async def resolve_nodes(body: ResolveNodesRequest) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(NODE_RESOLUTION_CONCURRENCY)

    async def _resolve(item: ResolveNodeInput):
        async with semaphore:
            return await resolve_investigation_node(
                item,
                thread_fetcher=fetch_thread_detail,
                signal_fetcher=_fetch_signal,
            )

    nodes = await asyncio.gather(*(_resolve(item) for item in body.nodes))
    statuses = {name: 0 for name in (
        "resolved", "partial", "metadata_only", "unavailable"
    )}
    for node in nodes:
        statuses[node.resolution_status] += 1
    return {
        "contract": CONTRACT,
        "nodes": nodes,
        "completion": {
            "requested": len(body.nodes),
            "processed": len(nodes),
            **statuses,
            "cursor_exhausted": True,
            "truncated": False,
        },
    }


@router.post("/graph")
async def investigation_graph(body: GraphRequest):
    # Reuse the shipped constellation/connection measurement. The typed graph
    # adds truth tiers and heterogeneous adapters; it must not invent a second
    # story-relation implementation from generic snapshots.
    if "dossier_connections" not in body.relation_payloads:
        topic_ids = list(dict.fromkeys(
            str(node.live_ref.get("id"))
            for node in body.nodes
            if node.node_type == "story" and node.live_ref.get("id")
        ))
        if topic_ids:
            max_hours = max(
                (
                    node.observation_window.range_end
                    - node.observation_window.range_start
                ).total_seconds() / 3600
                for node in body.nodes if node.node_type == "story"
            )
            days = max(7, min(90, math.ceil(max_hours / 24)))
            payload = await _fetch_dossier_relation_payload(
                topic_ids, days=days, timeout_s=12,
            )
            relation_payloads = dict(body.relation_payloads)
            relation_payloads["dossier_connections"] = payload
            body = body.model_copy(update={"relation_payloads": relation_payloads})
    return assemble_investigation_graph(body)


@router.post("/publication-package")
async def publication_package(body: PublicationPackageRequest):
    return build_publication_package(body)


async def fetch_stored_daily_publication() -> dict[str, Any]:
    """Serving path: one compact row, never builds the edition in-request.

    CONTRACT (`atlas-daily-publication-v1`; seal grading is
    `atlas-edition-status-v1`, T3.2):

        status          'sealed_full' | 'sealed_partial' | 'sealed_thin'
                        Graded from the edition's MEASURED readiness fractions
                        — never the old unreachable ready/degraded binary.
                        Legacy rows are remapped ('ready'->sealed_full,
                        'degraded'->sealed_partial).
        stored_status   what the row literally holds, for provenance.
        status_reasons  named shortfalls, e.g. ['who_below_bar','data_lag'].
                        `<dim>_below_bar` (under the partial bar 0.40),
                        `<dim>_below_full_bar` (under the full bar 0.55),
                        `<dim>_missing`, `receipts_incomplete`, `data_lag`,
                        `legacy_status_not_graded` (remap, not a measurement).
        completion.status_facts / .status_dimensions
                        the bars, the lag, and the per-dimension fractions the
                        grade was computed from (graded seals only).
        package.readiness[dim].measured
                        {ready, total, fraction, basis} — the number behind the
                        row, so a reader can be told "6 of 12 stories carry
                        verified subjects" instead of a bare 'partial'.
                        `basis` is 'story_nodes' | 'nodes' | 'receipts'.

    A thin edition is still a SEALED edition: nothing here voids a night —
    `SEAL_FAILED` in the reliability ledger remains the only such marker.
    """
    if db.pool is None:
        return {
            "contract": "atlas-daily-publication-v1",
            "edition_date": None,
            "sealed_at": None,
            "seal_schedule": build_seal_schedule(),
            "package": None,
            "graph": None,
            "selection": None,
            "completion": {
                "stored": False,
                "truncated": False,
                "reason": "no_db",
            },
        }
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT edition_date, edition_start, edition_end, generated_at,
                   contract, status, package, graph, selection, completion,
                   updated_at
            FROM atlas_daily_editions
            ORDER BY edition_end DESC
            LIMIT 1
            """,
            timeout=5,
        )
    if row is None:
        return {
            "contract": "atlas-daily-publication-v1",
            "edition_date": None,
            "sealed_at": None,
            "seal_schedule": build_seal_schedule(),
            "package": None,
            "graph": None,
            "selection": None,
            "completion": {
                "stored": False,
                "truncated": False,
                "reason": "not_precomputed",
            },
        }
    payload = dict(row)
    # The staleness banner reads WHAT edition + HOW OLD off the top level.
    # generated_at is the seal moment; it remains in completion for compat.
    sealed_at = payload["generated_at"]
    completion = _json_value(payload.pop("completion")) or {}
    # Graded seal (atlas-edition-status-v1). Rows sealed before the graded
    # vocabulary are remapped readably and carry `legacy_status_not_graded` —
    # the remap is never presented as a measurement. Reasons come from the seal
    # itself when it graded, from the remap when it did not.
    seal = normalize_stored_status(payload.pop("status"))
    stored_reasons = completion.get("status_reasons")
    reasons = stored_reasons if isinstance(stored_reasons, list) else seal["reasons"]
    return {
        "contract": payload.pop("contract"),
        "edition_date": payload.pop("edition_date"),
        "sealed_at": sealed_at,
        # Council N10: next-attempt truth from the actual launchd schedule
        # constant (+ in-flight window inference) — the staleness banner
        # consumes this instead of promising a hardcoded "02:30".
        "seal_schedule": build_seal_schedule(last_sealed_at=sealed_at),
        "status": seal["status"],
        "stored_status": seal["stored_status"],
        "status_reasons": reasons,
        "package": _json_value(payload.pop("package")),
        "graph": _json_value(payload.pop("graph")),
        "selection": _json_value(payload.pop("selection")),
        "completion": {
            **completion,
            "stored": True,
            "edition_start": payload.pop("edition_start"),
            "edition_end": payload.pop("edition_end"),
            "generated_at": payload.pop("generated_at"),
            "updated_at": payload.pop("updated_at"),
        },
    }


@router.get("/daily-publication")
async def daily_publication(hours: int = Query(24, ge=1, le=24)):
    # The contract is intentionally fixed at 24h; `hours` remains validated for
    # compatibility but never triggers heavy computation in serving.
    return await fetch_stored_daily_publication()
