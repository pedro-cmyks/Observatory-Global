"""Deterministic Investigation Graph and shared publication-package contracts.

This module is deliberately stateless and LLM-free.  It turns already-frozen
nodes into inspectable relation receipts, then serializes the same editorial
inputs for a system-authored L1 edition or an analyst-authored L3 dossier.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.investigation_nodes import InvestigationNode
from app.services.subject_geography import (
    infer_receipt_subject_geography,
    measure_subject_geography_coherence,
)

GRAPH_CONTRACT = "atlas-investigation-graph-v1"
PUBLICATION_CONTRACT = "atlas-publication-package-v1"

TruthTier = Literal["measured", "inferred", "contextual", "analyst"]


class InvestigationEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    truth_tier: TruthTier
    direction: Literal["directed", "undirected"] = "undirected"
    strength: float | None = None
    method: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    measured_at: datetime


class GraphCompletion(BaseModel):
    requested_nodes: int
    resolved_nodes: int
    requested_pairs: int
    processed_pairs: int
    engines: dict[str, Literal["complete", "degraded", "unavailable"]]
    truncated: bool = False


class GraphRequest(BaseModel):
    nodes: list[InvestigationNode] = Field(default_factory=list)
    analyst_edges: list[InvestigationEdge] = Field(default_factory=list)
    enabled_engines: list[str] = Field(default_factory=lambda: ["exact", "context"])
    # Already-measured provider payloads. The graph adapts these contracts; it
    # does not recreate their relation math from lossy generic snapshots.
    relation_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)


class InvestigationGraph(BaseModel):
    contract: Literal["atlas-investigation-graph-v1"] = GRAPH_CONTRACT
    nodes: list[InvestigationNode]
    edges: list[InvestigationEdge]
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    relation_context: dict[str, Any] = Field(default_factory=dict)
    unresolved_ledger: list[str] = Field(default_factory=list)
    completion: GraphCompletion
    measured_at: datetime


class ReadinessItem(BaseModel):
    status: Literal["ready", "partial", "missing"]
    values: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class PublicationReceipt(BaseModel):
    n: int
    node_id: str
    headline: str
    source: str | None = None
    url: str | None = None
    date: str | None = None
    language: str | None = None
    tier: str | None = None
    frozen: bool = True


class PublicationPackageRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    authorship: Literal["system", "analyst"]
    graph: InvestigationGraph
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    corroboration: dict[str, Any] | None = None
    selection_ledger: dict[str, Any] | None = None
    input_gaps: list[str] = Field(default_factory=list)


class PublicationPackage(BaseModel):
    contract: Literal["atlas-publication-package-v1"] = PUBLICATION_CONTRACT
    title: str
    authorship: Literal["system", "analyst"]
    generated_at: datetime
    readiness: dict[str, ReadinessItem]
    narrative_spine: list[dict[str, Any]]
    who_says_what: dict[str, Any]
    corroboration: dict[str, Any] | None = None
    gaps: list[str]
    receipts: list[PublicationReceipt]
    method: dict[str, Any]
    reproducibility: dict[str, Any]
    selection_ledger: dict[str, Any] | None = None
    prose_status: Literal["not_requested", "generated", "unavailable"] = "not_requested"
    article: dict[str, Any] | None = None
    # Workbench-enrichment bridge (spec 2026-07-20): fetched-page excerpts for
    # the edition's receipt URLs (all three sections), keyed by url, + honest
    # yield. Frozen at seal time. None = enrichment not attempted.
    article_enrichment: dict[str, Any] | None = None
    # Cross-read over the LEAD story's fetched bodies: corroboration/tension
    # findings with verbatim quotes ("possible — verify quotes"). None = not run.
    coverage_check: dict[str, Any] | None = None


class RelationAdapterResult(BaseModel):
    edges: list[InvestigationEdge] = Field(default_factory=list)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    relation_context: dict[str, Any] = Field(default_factory=dict)
    status: Literal["complete", "degraded", "unavailable"] = "complete"


def _stable_edge_id(a: str, b: str, relation: str, direction: str) -> str:
    pair = [a, b] if direction == "directed" else sorted((a, b))
    raw = json.dumps([*pair, relation, direction], separators=(",", ":"))
    return "edge-" + hashlib.sha256(raw.encode()).hexdigest()[:18]


def _live(node: InvestigationNode) -> dict[str, Any]:
    value = node.snapshot.get("live")
    return value if isinstance(value, dict) else {}


def _evidence_rows(node: InvestigationNode) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    live = _live(node)
    if node.node_type == "evidence" and live:
        rows.append(live)
    for parent in (node.snapshot, live):
        for key in ("evidence", "evidence_samples"):
            value = parent.get(key)
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
    return rows


def _signal_identity(row: dict[str, Any]) -> tuple[str, str] | None:
    sid = row.get("id") or row.get("signal_id")
    if sid is not None:
        return ("signal_id", str(sid))
    url = row.get("source_url") or row.get("url")
    if url:
        return ("url", str(url))
    return None


def _country_codes(node: InvestigationNode) -> set[str]:
    codes: set[str] = set()
    if node.node_type == "country":
        codes.add(str(node.snapshot.get("country_code") or node.live_ref.get("id") or "").upper())
    for parent in (node.snapshot, _live(node)):
        for key in ("country_code", "subject_country"):
            if parent.get(key):
                codes.add(str(parent[key]).upper())
        for key in ("top_countries", "top_country_codes", "countries"):
            value = parent.get(key)
            if isinstance(value, list):
                for item in value:
                    code = item.get("code") if isinstance(item, dict) else item
                    if code:
                        codes.add(str(code).upper())
    return {c for c in codes if c}


def _verified_subject_country_codes(node: InvestigationNode) -> set[str]:
    codes: set[str] = set()
    for parent in (node.quality, node.snapshot, _live(node)):
        status = str(parent.get("subject_country_status") or parent.get("subject_status") or "").lower()
        value = parent.get("subject_country")
        if value and status == "verified":
            codes.add(str(value).upper())
        raw = parent.get("verified_subject_countries")
        if isinstance(raw, list):
            for item in raw:
                code = item.get("code") if isinstance(item, dict) else item
                if code:
                    codes.add(str(code).upper())
    return {code for code in codes if code}


def _receipt_verified_subject_country_codes(node: InvestigationNode) -> set[str]:
    """Independently corroborated subject geography from a node's frozen
    receipts, via the shipped ``atlas-subject-geography-v1`` contract.

    The deployed thread detail does not pre-compute a verified-subject field, so
    a resolved story would otherwise abstain on Where/Who even when its own
    receipts name a country under the corroboration bar. This adapts the
    existing decoder over the frozen receipts; it never invents a country the
    receipts do not independently name, and it maps the served ``source`` outlet
    field onto the decoder's ``source_name`` key.
    """
    rows = _evidence_rows(node)
    if not rows:
        return set()
    normalized = []
    for row in rows:
        outlet = row.get("source_name") or row.get("source")
        normalized.append({**row, "source_name": outlet} if outlet else row)
    inferred = infer_receipt_subject_geography(normalized)
    return {str(code).upper() for code in inferred.get("verified_subject_countries", [])}


def _verified_subjects(node: InvestigationNode) -> set[str]:
    values: set[str] = set()
    for parent in (node.quality, node.snapshot, _live(node)):
        for key in ("verified_subjects",):
            raw = parent.get(key)
            if isinstance(raw, list):
                for item in raw:
                    name = item.get("name") if isinstance(item, dict) else item
                    if name:
                        values.add(str(name).strip().lower())
    if node.node_type == "subject" and node.quality.get("verified", False):
        values.add(node.label.strip().lower())
    return {v for v in values if v}


def _edge(
    a: InvestigationNode,
    b: InvestigationNode,
    relation: str,
    tier: TruthTier,
    method: str,
    measured_at: datetime,
    *,
    direction: Literal["directed", "undirected"] = "undirected",
    source: InvestigationNode | None = None,
    target: InvestigationNode | None = None,
    strength: float | None = None,
    receipts: list[dict[str, Any]] | None = None,
    reasons: list[str] | None = None,
    caveats: list[str] | None = None,
) -> InvestigationEdge:
    source = source or a
    target = target or b
    return InvestigationEdge(
        edge_id=_stable_edge_id(source.node_id, target.node_id, relation, direction),
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        relation_type=relation,
        truth_tier=tier,
        direction=direction,
        strength=strength,
        method=method,
        valid_from=max(a.observation_window.range_start, b.observation_window.range_start),
        valid_to=min(a.observation_window.range_end, b.observation_window.range_end),
        receipts=receipts or [],
        reason_codes=reasons or [],
        caveats=caveats or [],
        measured_at=measured_at,
    )


def _payload_node_map(
    payload: dict[str, Any],
    nodes: list[InvestigationNode],
) -> dict[str, InvestigationNode]:
    """Map provider-local ids back to investigation nodes without guessing
    story identity from labels unless no stable live ref exists."""
    by_ref = {
        str(node.live_ref.get("id")): node
        for node in nodes if node.live_ref.get("id") is not None
    }
    by_label: dict[str, InvestigationNode] = {}
    for node in nodes:
        by_label.setdefault(node.label.strip().casefold(), node)

    mapped: dict[str, InvestigationNode] = {}
    for raw in payload.get("nodes") or []:
        if not isinstance(raw, dict):
            continue
        keys = [raw.get("id"), raw.get("base_id")]
        target = next((by_ref.get(str(key)) for key in keys if key is not None and str(key) in by_ref), None)
        if target is None and raw.get("label"):
            target = by_label.get(str(raw["label"]).strip().casefold())
        if target is None:
            continue
        for key in keys:
            if key is not None:
                mapped[str(key)] = target
    return mapped


def adapt_dossier_connections(
    payload: dict[str, Any],
    nodes: list[InvestigationNode],
    *,
    measured_at: datetime | None = None,
) -> RelationAdapterResult:
    """Adapt the shipped dossier-connections-v1 contract into typed edges.

    One legacy edge can contain several bases. They become separate typed
    relations so semantic proximity, coverage coincidence, text reference, and
    shared actors never launder one another's truth tier.
    """
    measured_at = measured_at or datetime.now(timezone.utc)
    if payload.get("reason"):
        return RelationAdapterResult(
            unresolved=[f"dossier_connections:{payload['reason']}"],
            relation_context={"dossier_connections": payload},
            status="degraded",
        )
    if not str(payload.get("contract") or "").startswith("dossier-connections-v"):
        return RelationAdapterResult(
            unresolved=["dossier_connections:unsupported_contract"],
            relation_context={"dossier_connections": payload},
            status="unavailable",
        )

    mapped = _payload_node_map(payload, nodes)
    edges: list[InvestigationEdge] = []
    unresolved: list[str] = []
    for raw in payload.get("edges") or []:
        if not isinstance(raw, dict):
            continue
        a = mapped.get(str(raw.get("a")))
        b = mapped.get(str(raw.get("b")))
        if a is None or b is None:
            unresolved.append(f"dossier_edge_unmapped:{raw.get('a')}:{raw.get('b')}")
            continue
        bases = set(raw.get("basis") or [])
        if "shared_person" in bases and raw.get("shared_persons"):
            people = [str(p) for p in raw.get("shared_persons") or []]
            edges.append(_edge(
                a, b, "shared_actor", "measured", "dossier_distinctive_person_overlap", measured_at,
                strength=float(raw.get("weight")) if raw.get("weight") is not None else None,
                receipts=[{"subject": p, "subject_type": "person"} for p in people],
                reasons=["distinctive_clean_actor_overlap"],
                caveats=["actor_overlap_not_causality"],
            ))
        if "text_mention" in bases and raw.get("text_mentions"):
            terms = [str(t) for t in raw.get("text_mentions") or []]
            edges.append(_edge(
                a, b, "mentions", "measured", "dossier_evidence_text_cross_reference", measured_at,
                receipts=[{"matched_text": term} for term in terms],
                reasons=["verbatim_cross_reference"],
                caveats=["text_reference_requires_receipt_open", "not_causality"],
            ))
        if "shared_country" in bases and raw.get("shared_countries"):
            countries = [str(cc).upper() for cc in raw.get("shared_countries") or []]
            edges.append(_edge(
                a, b, "same_coverage_country", "contextual", "dossier_coverage_country_overlap", measured_at,
                receipts=[{"country_code": cc} for cc in countries],
                reasons=["coverage_geography_overlap"],
                caveats=["not_subject_geography", "not_story_identity", "not_causality"],
            ))
        if "semantic" in bases:
            score = raw.get("whitened_sim")
            method = "dossier_whitened_e5_k1"
            if score is None:
                score = raw.get("semantic_sim")
                method = "dossier_raw_e5_fallback"
            edges.append(_edge(
                a, b, "semantic_near", "inferred", method, measured_at,
                strength=max(0.0, min(1.0, float(score))) if score is not None else None,
                reasons=["dossier_semantic_relation"],
                caveats=["semantic_proximity_not_story_identity", "not_causality"],
            ))

    suggestions: list[dict[str, Any]] = []
    for raw in payload.get("neighbors") or []:
        if not isinstance(raw, dict) or not raw.get("base_id"):
            continue
        suggestions.append({
            "live_ref": {"kind": "thread", "id": str(raw["base_id"])},
            "label": raw.get("label") or str(raw["base_id"]),
            "category": raw.get("category"),
            "method": "dossier_whitened_neighbor",
            "links": raw.get("links") or [],
            "status": "suggested_not_pinned",
        })
    unresolved.extend(f"dossier_node_unresolved:{value}" for value in payload.get("unresolved") or [])
    return RelationAdapterResult(
        edges=edges,
        suggestions=suggestions,
        unresolved=list(dict.fromkeys(unresolved)),
        relation_context={
            "dossier_connections": {
                "contract": payload.get("contract"),
                "measured_at": payload.get("measured_at"),
                "distributions": payload.get("distributions"),
                "meta": payload.get("meta"),
            }
        },
        status="degraded" if unresolved else "complete",
    )


def assemble_investigation_graph(
    request: GraphRequest,
    *,
    measured_at: datetime | None = None,
) -> InvestigationGraph:
    measured_at = measured_at or datetime.now(timezone.utc)
    nodes = list(request.nodes)
    edges: list[InvestigationEdge] = list(request.analyst_edges)
    suggestions: list[dict[str, Any]] = []
    relation_context: dict[str, Any] = {}
    unresolved: list[str] = []
    engines: dict[str, Literal["complete", "degraded", "unavailable"]] = {}
    pairs = list(combinations(nodes, 2))

    if "exact" in request.enabled_engines:
        for a, b in pairs:
            a_rows = {_signal_identity(r): r for r in _evidence_rows(a) if _signal_identity(r)}
            b_rows = {_signal_identity(r): r for r in _evidence_rows(b) if _signal_identity(r)}
            shared_receipts = sorted(set(a_rows) & set(b_rows))
            if shared_receipts:
                receipt_list = []
                for kind, value in shared_receipts:
                    row = a_rows[(kind, value)]
                    receipt_list.append({kind: int(value) if kind == "signal_id" and value.isdigit() else value,
                                         "url": row.get("source_url") or row.get("url")})
                if {a.node_type, b.node_type} == {"story", "evidence"}:
                    evidence = a if a.node_type == "evidence" else b
                    story = b if evidence is a else a
                    edges.append(_edge(
                        a, b, "member_of", "measured", "exact_signal_membership", measured_at,
                        direction="directed", source=evidence, target=story,
                        receipts=receipt_list, reasons=["shared_signal_receipt"],
                    ))
                else:
                    edges.append(_edge(
                        a, b, "shared_evidence", "measured", "exact_signal_or_url_identity", measured_at,
                        receipts=receipt_list, reasons=["shared_signal_receipt"],
                    ))
            shared_subjects = sorted(_verified_subjects(a) & _verified_subjects(b))
            if shared_subjects:
                edges.append(_edge(
                    a, b, "same_verified_subject", "measured", "verified_subject_intersection", measured_at,
                    receipts=[{"subject": s} for s in shared_subjects[:20]],
                    reasons=["verified_subject_overlap"],
                ))
        engines["exact"] = "complete"

    if "context" in request.enabled_engines:
        for a, b in pairs:
            shared = sorted(_country_codes(a) & _country_codes(b))
            if shared:
                edges.append(_edge(
                    a, b, "same_coverage_country", "contextual", "coverage_country_intersection", measured_at,
                    receipts=[{"country_code": cc} for cc in shared],
                    reasons=["coverage_geography_overlap"],
                    caveats=["not_subject_geography", "not_story_identity", "not_causality"],
                ))
        engines["context"] = "complete"

    if "semantic" in request.enabled_engines:
        found = False
        for a, b in pairs:
            scores = a.snapshot.get("semantic_scores")
            score = scores.get(b.node_id) if isinstance(scores, dict) else None
            if isinstance(score, (int, float)):
                found = True
                edges.append(_edge(
                    a, b, "semantic_near", "inferred", "caller_supplied_measured_embedding_cosine", measured_at,
                    strength=max(0.0, min(1.0, float(score))),
                    reasons=["explicit_semantic_measurement"],
                    caveats=["semantic_proximity_not_story_identity", "not_causality"],
                ))
        if found or not pairs:
            engines["semantic"] = "complete"
        else:
            engines["semantic"] = "degraded"
            unresolved.append("semantic_inputs_missing")

    dossier_payload = request.relation_payloads.get("dossier_connections")
    if dossier_payload is not None:
        adapted = adapt_dossier_connections(dossier_payload, nodes, measured_at=measured_at)
        edges.extend(adapted.edges)
        suggestions.extend(adapted.suggestions)
        unresolved.extend(adapted.unresolved)
        relation_context.update(adapted.relation_context)
        engines["dossier_connections"] = adapted.status

    # Stable ordering makes the graph reproducible and easy to diff/export.
    # Provider adapters are appended after generic engines and therefore win an
    # identical stable edge id with their more specific method/receipts.
    edges = list({edge.edge_id: edge for edge in edges}.values())
    edges.sort(key=lambda e: (e.source_node_id, e.target_node_id, e.relation_type, e.edge_id))
    resolved = sum(n.resolution_status in {"resolved", "partial"} for n in nodes)
    return InvestigationGraph(
        nodes=nodes,
        edges=edges,
        suggestions=suggestions,
        relation_context=relation_context,
        unresolved_ledger=list(dict.fromkeys(unresolved)),
        completion=GraphCompletion(
            requested_nodes=len(nodes),
            resolved_nodes=resolved,
            requested_pairs=len(pairs),
            processed_pairs=len(pairs),
            engines=engines,
            truncated=False,
        ),
        measured_at=measured_at,
    )


def _receipt_rows(nodes: list[InvestigationNode]) -> list[PublicationReceipt]:
    rows: list[PublicationReceipt] = []
    seen: set[tuple[str, str]] = set()
    for node in nodes:
        for item in _evidence_rows(node):
            headline = str(item.get("headline") or item.get("title") or "").strip()
            if not headline:
                continue
            identity = _signal_identity(item) or ("headline", headline.lower())
            if identity in seen:
                continue
            seen.add(identity)
            timestamp = item.get("timestamp") or item.get("date")
            date = str(timestamp)[:10] if timestamp else None
            rows.append(PublicationReceipt(
                n=len(rows) + 1,
                node_id=node.node_id,
                headline=headline,
                source=item.get("source_name") or item.get("source"),
                url=item.get("source_url") or item.get("url"),
                date=date,
                language=item.get("source_lang") or item.get("language"),
                tier=item.get("credibility_tier") or item.get("tier"),
            ))
    return rows


def _item(values: set[str], missing: str, *, partial_below: int = 1) -> ReadinessItem:
    cleaned = sorted(v for v in values if v)
    if not cleaned:
        return ReadinessItem(status="missing", reason_codes=[missing])
    status: Literal["ready", "partial", "missing"] = "partial" if len(cleaned) < partial_below else "ready"
    return ReadinessItem(status=status, values=cleaned)


def build_publication_package(request: PublicationPackageRequest) -> PublicationPackage:
    graph = request.graph
    receipts = _receipt_rows(graph.nodes)
    subjects: set[str] = set()
    coverage_countries: set[str] = set()
    subject_countries: set[str] = set()
    sources: set[str] = set()
    languages: set[str] = set()
    what: set[str] = set()
    movement: set[str] = set()
    story_nodes = [node for node in graph.nodes if node.node_type == "story"]
    story_nodes_with_actor = 0
    story_nodes_with_subject_geo = 0
    grab_bag_stories: list[str] = []

    for node in graph.nodes:
        live = _live(node)
        verified_subjects = _verified_subjects(node)
        verified_subject_countries = _verified_subject_country_codes(node)
        if node.node_type == "story" and not verified_subject_countries:
            verified_subject_countries = _receipt_verified_subject_country_codes(node)
        if node.node_type in {"story", "evidence", "event", "anomaly", "attention"}:
            what.add(node.label)
        if node.node_type == "subject":
            subjects.add(node.label)
        subjects.update(s.title() for s in verified_subjects)
        # Atlas's actor canon is intentionally broad: a corroborated place is
        # an actor/subject too. Keep the typed prefix so Who and Where can both
        # expose it without turning shared-country context into an actor edge.
        subjects.update(
            f"{ISO_COUNTRY_NAMES.get(code, code)} (place)"
            for code in verified_subject_countries
        )
        coverage_countries.update(_country_codes(node))
        subject_countries.update(verified_subject_countries)
        if node.node_type == "story":
            if measure_subject_geography_coherence(_evidence_rows(node)).get("grab_bag"):
                grab_bag_stories.append(node.label)
            if verified_subjects or verified_subject_countries:
                story_nodes_with_actor += 1
            if verified_subject_countries:
                story_nodes_with_subject_geo += 1
        for parent in (node.snapshot, live):
            for key in ("top_sources", "sources"):
                raw = parent.get(key)
                if isinstance(raw, list):
                    for value in raw:
                        source = value.get("source") if isinstance(value, dict) else value
                        if source:
                            sources.add(str(source))
            for key in ("source_lang", "language"):
                if parent.get(key):
                    languages.add(str(parent[key]))
            delta = parent.get("changed_10h")
            if isinstance(delta, (int, float)):
                movement.add(f"{node.label}: changed_10h={delta:+g}")
            movement_row = parent.get("movement")
            if isinstance(movement_row, dict):
                velocity = movement_row.get("velocity")
                surprise = movement_row.get("surprise")
                if isinstance(velocity, (int, float)):
                    movement.add(f"{node.label}: velocity={float(velocity):+.4f}")
                if isinstance(surprise, (int, float)):
                    movement.add(f"{node.label}: surprise={float(surprise):.4f}")
    for receipt in receipts:
        if receipt.source:
            sources.add(receipt.source)
        if receipt.language:
            languages.add(receipt.language)

    dates = {r.date for r in receipts if r.date}
    measured_relations = [e for e in graph.edges if e.truth_tier in {"measured", "analyst"}]
    inferred_relations = [e for e in graph.edges if e.truth_tier == "inferred"]
    contextual_relations = [e for e in graph.edges if e.truth_tier == "contextual"]
    why_values = movement | {
        f"{e.relation_type}:{e.source_node_id}->{e.target_node_id}"
        for e in measured_relations
    }

    if subject_countries and story_nodes_with_subject_geo == len(story_nodes):
        where_readiness = ReadinessItem(status="ready", values=sorted(subject_countries))
    elif subject_countries:
        where_readiness = ReadinessItem(
            status="partial",
            values=sorted(subject_countries),
            reason_codes=["subject_geography_incomplete_for_story_nodes"],
        )
    elif coverage_countries:
        where_readiness = ReadinessItem(
            status="partial",
            values=sorted(coverage_countries),
            reason_codes=["coverage_geography_only_not_subject"],
        )
    else:
        where_readiness = ReadinessItem(status="missing", reason_codes=["no_geography_context"])
    why_readiness = _item(why_values, "no_measured_movement_or_relation")
    if why_readiness.status == "ready":
        why_readiness.status = "partial"
        why_readiness.reason_codes.append("causal_explanation_not_measured")

    if subjects and story_nodes_with_actor == len(story_nodes):
        who_readiness = ReadinessItem(status="ready", values=sorted(subjects))
    elif subjects:
        who_readiness = ReadinessItem(
            status="partial",
            values=sorted(subjects),
            reason_codes=["actor_attribution_incomplete_for_story_nodes"],
        )
    else:
        who_readiness = ReadinessItem(
            status="missing", reason_codes=["no_verified_subjects"],
        )

    readiness = {
        "who": who_readiness,
        "what": _item(what, "no_story_or_event_nodes"),
        "when": _item(dates, "no_dated_receipts"),
        "where": where_readiness,
        "how": _item(sources | {f"language:{x}" for x in languages}, "no_source_or_language_receipts"),
        "why": why_readiness,
    }

    gaps = [code for item in readiness.values() for code in item.reason_codes]
    gaps.extend(graph.unresolved_ledger)
    gaps.extend(request.input_gaps)
    if contextual_relations:
        gaps.append("contextual_relations_are_exploration_context_not_story_proof")
    if inferred_relations:
        gaps.append("inferred_relations_require_method_caveats")
    if graph.completion.resolved_nodes < graph.completion.requested_nodes:
        gaps.append("one_or_more_nodes_are_metadata_only_or_unavailable")
    for label in grab_bag_stories:
        gaps.append(f"subject_geography_grab_bag:{label}")
    gaps = list(dict.fromkeys(gaps))

    spine = [
        {
            "edge_id": e.edge_id,
            "source": e.source_node_id,
            "target": e.target_node_id,
            "relation_type": e.relation_type,
            "truth_tier": e.truth_tier,
            "method": e.method,
            "receipt_count": len(e.receipts),
        }
        for e in measured_relations
    ]
    dossier_context = graph.relation_context.get("dossier_connections")
    distributions = dossier_context.get("distributions") if isinstance(dossier_context, dict) else None
    distributions = distributions if isinstance(distributions, dict) else {}
    role_counts = distributions.get("roles") if isinstance(distributions.get("roles"), dict) else {}
    measured_languages = {
        str(row.get("lang")) for row in distributions.get("languages") or []
        if isinstance(row, dict) and row.get("lang")
    }
    languages.update(measured_languages)
    measured_press = role_counts.get("press")
    measured_public = role_counts.get("public")

    return PublicationPackage(
        title=request.title,
        authorship=request.authorship,
        generated_at=request.generated_at,
        readiness=readiness,
        narrative_spine=spine,
        who_says_what={
            "sources": sorted(sources),
            "languages": sorted(languages),
            "press_receipts": int(measured_press) if measured_press is not None else len(receipts),
            "public_receipts": int(measured_public) if measured_public is not None else 0,
            "public_lane_status": "measured" if measured_public is not None else "not_present_in_supplied_nodes",
            "measurement_contract": dossier_context.get("contract") if isinstance(dossier_context, dict) else None,
        },
        corroboration=request.corroboration,
        gaps=gaps,
        receipts=receipts,
        method={
            "relation_engines": graph.completion.engines,
            "contextual_edges_excluded_from_spine": len(contextual_relations),
            "measured_at": graph.measured_at.isoformat(),
            "llm_used": False,
        },
        reproducibility={
            "graph_contract": graph.contract,
            "node_contract": "atlas-investigation-v2",
            "node_ids": [node.node_id for node in graph.nodes],
            "edge_ids": [edge.edge_id for edge in graph.edges],
            "completion": graph.completion.model_dump(mode="json"),
        },
        selection_ledger=request.selection_ledger,
    )
