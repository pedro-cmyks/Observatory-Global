from __future__ import annotations

from datetime import datetime, timezone

from app.services.investigation_graph import (
    GraphRequest,
    PublicationPackageRequest,
    adapt_dossier_connections,
    assemble_investigation_graph,
    build_publication_package,
)
from app.services.investigation_nodes import InvestigationNode, ObservationWindow, ResolutionReceipt


WINDOW = ObservationWindow(
    range_start="2026-07-11T00:00:00Z",
    range_end="2026-07-12T00:00:00Z",
)
STAMP = datetime(2026, 7, 12, tzinfo=timezone.utc)


def node(node_id: str, node_type: str, subtype: str, label: str, snapshot: dict, *, quality=None):
    return InvestigationNode(
        node_id=node_id,
        node_type=node_type,
        subtype=subtype,
        label=label,
        live_ref={"kind": subtype, "id": node_id.split("-")[-1]},
        pinned_at=STAMP,
        observation_window=WINDOW,
        snapshot=snapshot,
        quality=quality or {},
        resolution_status="resolved",
        resolution_receipt=ResolutionReceipt(
            adapter=f"{node_type}:{subtype}", resolved_at=STAMP, retryable=False,
        ),
    )


def test_graph_resolves_membership_verified_subject_and_context_without_promotion():
    story = node(
        "node-story-1", "story", "thread", "Iran negotiations",
        {"live": {
            "top_countries": ["IR"],
            "evidence_samples": [{"id": 42, "headline": "Talks continue", "source_url": "https://a/42"}],
        }},
        quality={"verified_subjects": ["donald trump"]},
    )
    evidence = node(
        "node-evidence-42", "evidence", "signal", "Talks continue",
        {"live": {"id": 42, "headline": "Talks continue", "source_url": "https://a/42", "country_code": "IR"}},
        quality={"verified_subjects": ["donald trump"]},
    )
    country = node("node-country-IR", "country", "country", "Iran", {"country_code": "IR"})

    graph = assemble_investigation_graph(GraphRequest(nodes=[story, evidence, country]), measured_at=STAMP)

    by_type = {edge.relation_type: edge for edge in graph.edges}
    assert by_type["member_of"].truth_tier == "measured"
    assert by_type["member_of"].receipts[0]["signal_id"] == 42
    assert by_type["same_verified_subject"].truth_tier == "measured"
    assert by_type["same_coverage_country"].truth_tier == "contextual"
    assert "not_subject_geography" in by_type["same_coverage_country"].caveats
    assert graph.completion.requested_pairs == 3
    assert graph.completion.processed_pairs == 3
    assert graph.completion.truncated is False


def test_graph_names_unresolved_engines_and_never_silently_caps_pairs():
    nodes = [
        node(f"node-country-{cc}", "country", "country", cc, {"country_code": cc})
        for cc in ("IR", "TR", "SY", "US")
    ]
    graph = assemble_investigation_graph(
        GraphRequest(nodes=nodes, enabled_engines=["exact", "semantic"]),
        measured_at=STAMP,
    )

    assert graph.completion.requested_pairs == 6
    assert graph.completion.processed_pairs == 6
    assert graph.completion.engines["exact"] == "complete"
    assert graph.completion.engines["semantic"] == "degraded"
    assert "semantic_inputs_missing" in graph.unresolved_ledger


def test_publication_package_is_deterministic_and_receipts_are_authoritative():
    story = node(
        "node-story-1", "story", "thread", "Iran negotiations",
        {"live": {
            "top_countries": ["IR"],
            "top_entities": ["Donald Trump"],
            "top_sources": ["Reuters"],
            "evidence_samples": [{
                "id": 42, "headline": "Talks continue", "source_name": "Reuters",
                "source_url": "https://a/42", "timestamp": "2026-07-12T00:00:00Z",
                "source_lang": "en",
            }],
            "changed_10h": 8,
        }},
        quality={"verified_subjects": ["Donald Trump"]},
    )
    country = node("node-country-IR", "country", "country", "Iran", {"country_code": "IR"})
    graph = assemble_investigation_graph(GraphRequest(nodes=[story, country]), measured_at=STAMP)
    req = PublicationPackageRequest(
        title="Iran talks",
        authorship="analyst",
        graph=graph,
        generated_at=STAMP,
    )

    first = build_publication_package(req)
    second = build_publication_package(req)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.contract == "atlas-publication-package-v1"
    assert first.receipts[0].n == 1
    assert first.receipts[0].url == "https://a/42"
    assert first.readiness["what"].status == "ready"
    assert first.readiness["when"].status == "ready"
    assert first.readiness["where"].status == "partial"
    assert "coverage_geography_only_not_subject" in first.readiness["where"].reason_codes
    assert first.readiness["who"].status == "ready"
    assert first.reproducibility["graph_contract"] == "atlas-investigation-graph-v1"


def test_dossier_adapter_preserves_each_relation_basis_as_its_own_truth_tier():
    a = node("node-story-1", "story", "thread", "NATO Summit Ankara", {})
    b = node("node-story-2", "story", "thread", "Trump Putin call", {})
    payload = {
        "contract": "dossier-connections-v1",
        "measured_at": "2026-07-12T00:00:00Z",
        "nodes": [
            {"id": "1", "base_id": "1", "label": a.label},
            {"id": "2", "base_id": "2", "label": b.label},
        ],
        "edges": [{
            "a": "1", "b": "2",
            "basis": ["shared_person", "shared_country", "text_mention", "semantic"],
            "weight": 0.8,
            "semantic_sim": 0.98,
            "whitened_sim": 0.61,
            "shared_countries": ["TR"],
            "shared_persons": ["tayyip erdogan"],
            "text_mentions": ["nato summit"],
        }],
        "neighbors": [{
            "base_id": "dynamic-topic-9", "label": "Summit tariff dispute",
            "category": "Trade", "links": [{"pin": "1", "sim": 0.55}],
        }],
        "distributions": {
            "countries": [{"cc": "TR", "n": 30}],
            "languages": [{"lang": "tr", "n": 22}],
            "roles": {"press": 140, "public": 7},
        },
        "unresolved": [],
        "meta": {"semantic_space": "whitened-e5-k1"},
    }

    adapted = adapt_dossier_connections(payload, [a, b], measured_at=STAMP)
    by_relation = {edge.relation_type: edge for edge in adapted.edges}

    assert by_relation["shared_actor"].truth_tier == "measured"
    assert by_relation["mentions"].truth_tier == "measured"
    assert by_relation["same_coverage_country"].truth_tier == "contextual"
    assert "not_story_identity" in by_relation["same_coverage_country"].caveats
    assert by_relation["semantic_near"].truth_tier == "inferred"
    assert by_relation["semantic_near"].strength == 0.61
    assert adapted.suggestions[0]["live_ref"]["id"] == "dynamic-topic-9"
    assert adapted.relation_context["dossier_connections"]["distributions"]["roles"]["public"] == 7


def test_publication_package_reuses_real_dossier_role_and_language_distributions():
    a = node(
        "node-story-1", "story", "thread", "NATO Summit Ankara",
        {"live": {"evidence_samples": [{
            "id": 7, "headline": "Ankara summit opens", "source_name": "AA",
            "source_lang": "tr", "timestamp": "2026-07-12T00:00:00Z",
        }]}},
    )
    graph = assemble_investigation_graph(GraphRequest(
        nodes=[a],
        relation_payloads={"dossier_connections": {
            "contract": "dossier-connections-v1",
            "nodes": [{"id": "1", "base_id": "1", "label": a.label}],
            "edges": [],
            "neighbors": [],
            "unresolved": [],
            "distributions": {
                "countries": [{"cc": "TR", "n": 30}],
                "languages": [{"lang": "tr", "n": 22}, {"lang": "ro", "n": 8}],
                "roles": {"press": 140, "public": 7},
            },
        }},
    ), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="NATO", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    assert package.who_says_what["press_receipts"] == 140
    assert package.who_says_what["public_receipts"] == 7
    assert package.who_says_what["public_lane_status"] == "measured"
    assert package.who_says_what["languages"] == ["ro", "tr"]


def test_publication_where_is_ready_only_with_verified_subject_geography():
    story = node(
        "node-story-1", "story", "thread", "Iran negotiations",
        {"live": {"top_countries": ["RO"]}},
        quality={"subject_country": "IR", "subject_country_status": "verified"},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Iran", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    assert package.readiness["where"].status == "ready"
    assert package.readiness["where"].values == ["IR"]


def test_publication_package_exposes_missing_dimensions_instead_of_padding():
    metadata = node("node-subject-x", "subject", "person", "Unknown actor", {})
    graph = assemble_investigation_graph(GraphRequest(nodes=[metadata]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Thin package", authorship="system", graph=graph, generated_at=STAMP,
    ))

    assert package.receipts == []
    assert package.readiness["when"].status == "missing"
    assert package.readiness["where"].status == "missing"
    assert any("no_dated_receipts" in gap for gap in package.gaps)
    assert package.prose_status == "not_requested"


def test_publication_package_carries_upstream_operational_gaps():
    graph = assemble_investigation_graph(GraphRequest(nodes=[]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Degraded but explicit",
        authorship="system",
        graph=graph,
        generated_at=STAMP,
        input_gaps=["edition_cutoff_stale", "receipt_signal_provider_timeout"],
    ))

    assert "edition_cutoff_stale" in package.gaps
    assert "receipt_signal_provider_timeout" in package.gaps
