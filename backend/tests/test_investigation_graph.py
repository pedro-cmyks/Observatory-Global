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


def test_publication_who_requires_a_broad_actor_for_every_story_node():
    actor_story = node(
        "node-story-1", "story", "thread", "Election dispute",
        {"live": {"evidence_samples": []}},
        quality={"verified_subjects": ["Donald Trump"]},
    )
    actorless_story = node(
        "node-story-2", "story", "thread", "Unattributed disruption",
        {"live": {"evidence_samples": []}},
    )
    graph = assemble_investigation_graph(
        GraphRequest(nodes=[actor_story, actorless_story]), measured_at=STAMP,
    )

    package = build_publication_package(PublicationPackageRequest(
        title="Daily edition", authorship="system", graph=graph, generated_at=STAMP,
    ))

    assert package.readiness["who"].status == "partial"
    assert package.readiness["who"].reason_codes == [
        "actor_attribution_incomplete_for_story_nodes"
    ]


def test_verified_subject_place_is_a_broad_actor_without_becoming_actor_edge():
    story = node(
        "node-story-1", "story", "thread", "Bangkok bar fire",
        {"live": {"evidence_samples": []}},
        quality={
            "subject_country_status": "verified",
            "verified_subject_countries": ["TH"],
        },
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)

    package = build_publication_package(PublicationPackageRequest(
        title="Daily edition", authorship="system", graph=graph, generated_at=STAMP,
    ))

    assert package.readiness["who"].status == "ready"
    assert "Thailand (place)" in package.readiness["who"].values
    assert graph.edges == []


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


def test_publication_where_is_partial_when_some_story_nodes_lack_subject_geography():
    verified = node(
        "node-story-verified", "story", "thread", "Verified", {},
        quality={
            "verified_subject_countries": ["TR"],
            "subject_country_status": "verified",
        },
    )
    unknown = node(
        "node-story-unknown", "story", "thread", "Unknown",
        {"live": {"top_countries": ["DE"]}},
    )
    graph = assemble_investigation_graph(
        GraphRequest(nodes=[verified, unknown]), measured_at=STAMP,
    )

    package = build_publication_package(PublicationPackageRequest(
        title="Two stories", authorship="system", graph=graph, generated_at=STAMP,
    ))

    assert package.readiness["where"].status == "partial"
    assert package.readiness["where"].values == ["TR"]
    assert "subject_geography_incomplete_for_story_nodes" in package.readiness["where"].reason_codes


def test_publication_where_and_who_promote_from_frozen_receipt_subject_geography():
    # A resolved story pins its frozen receipts but no pre-computed
    # verified-subject field (the deployed thread detail never sets one). The
    # receipts independently corroborate Iran (>=2 receipts, >=2 distinct
    # outlets naming it), so the shipped subject-geography contract must promote
    # Where from the receipts alone, and the verified place must count as a
    # broad actor so Who promotes with it.
    story = node(
        "node-story-1", "story", "thread", "Iran water crisis",
        {"live": {"evidence_samples": [
            {"id": 1, "headline": "Iran faces worst drought in decades",
             "source": "Reuters", "url": "https://r/1"},
            {"id": 2, "headline": "Iran rations water as reservoirs fall",
             "source": "AP", "url": "https://ap/2"},
        ]}},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Iran", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    assert package.readiness["where"].status == "ready"
    assert package.readiness["where"].values == ["IR"]
    assert package.readiness["who"].status == "ready"
    assert any("(place)" in value for value in package.readiness["who"].values)


def test_publication_flags_grab_bag_umbrella_from_disjoint_receipt_geography():
    # A story whose receipts split into disjoint country groups (Belgium heatwave
    # + France budget, never co-occurring) is an incoherent umbrella (#257). The
    # package must flag it, reason-coded, without dropping any receipt.
    story = node(
        "node-story-1", "story", "thread", "Canicule en Belgique",
        {"live": {"evidence_samples": [
            {"id": 1, "headline": "Heatwave grips Belgium as Brussels issues alert", "source": "R"},
            {"id": 2, "headline": "Belgium swelters as Brussels breaks records", "source": "A"},
            {"id": 3, "headline": "France debates its budget in Paris", "source": "L"},
            {"id": 4, "headline": "Paris braces as France reviews spending", "source": "M"},
        ]}},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Belgium", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    assert any("grab_bag" in gap for gap in package.gaps)


def test_publication_does_not_flag_coherent_multi_country_story():
    story = node(
        "node-story-1", "story", "thread", "Iran plot",
        {"live": {"evidence_samples": [
            {"id": 1, "headline": "Israel warns US of Iranian plot to kill Trump", "source": "R"},
            {"id": 2, "headline": "US and Israel brief allies on Iran plot", "source": "A"},
        ]}},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Iran", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    assert not any("grab_bag" in gap for gap in package.gaps)


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


# Frank test 2026-08-12 (break d.4): the 5W+H HOW row — which an editor reads as
# the sourcing list — listed `language:en` and `bluesky` beside tass.com/dw.com
# as if they were outlets. HOW carries OUTLETS only; the language tokens and the
# social-platform lanes are excluded, and never silently (a HOW that goes empty
# because of the exclusion says so).
def test_publication_how_row_lists_outlets_not_languages_or_platform_lanes():
    story = node(
        "node-story-1", "story", "thread", "Syria Russia bases deal",
        {"live": {
            "top_countries": ["SY"],
            "top_sources": ["tass.com", "sana.sy", "dw.com", "bluesky", "lemmy/world@lemmy.ml"],
            "evidence_samples": [{
                "id": 42, "headline": "Syria says deal reached", "source_name": "naharnet.com",
                "source_url": "https://a/42", "timestamp": "2026-08-10T00:00:00Z",
                "source_lang": "en",
            }],
        }},
        quality={"verified_subjects": ["Vladimir Putin"]},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Syria Russia bases deal", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    how = package.readiness["how"]
    assert how.status == "ready"
    assert how.values == ["dw.com", "naharnet.com", "sana.sy", "tass.com"]
    assert not any(v.startswith("language:") for v in how.values)
    assert "bluesky" not in how.values
    assert not any(v.startswith("lemmy/") for v in how.values)


def test_publication_how_row_says_so_when_only_non_outlet_tokens_were_captured():
    story = node(
        "node-story-1", "story", "thread", "Forum chatter",
        {"live": {
            "top_sources": ["bluesky", "reddit"],
            "source_lang": "en",
            "evidence_samples": [],
        }},
    )
    graph = assemble_investigation_graph(GraphRequest(nodes=[story]), measured_at=STAMP)
    package = build_publication_package(PublicationPackageRequest(
        title="Forum chatter", authorship="analyst", graph=graph, generated_at=STAMP,
    ))

    how = package.readiness["how"]
    assert how.status == "missing"
    assert how.values == []
    assert "no_outlet_receipts" in how.reason_codes
    # never a silent drop: the excluded lanes are named as the reason HOW is empty
    assert "non_outlet_tokens_excluded_from_how" in how.reason_codes


# --- readiness carries MEASURED FRACTIONS, not a unanimity verdict (T3.2) ----
# `who`/`where` used to be `ready` only when EVERY story node carried
# attribution. With ~50% per-node coverage that conjunction can never fire over
# 12 nodes, so 25/25 sealed editions read `degraded`. Readiness now reports the
# fraction it measured, and the bar is a fraction (see test_edition_status.py).

def _story_with_actor(node_id: str, country: str) -> InvestigationNode:
    return node(
        node_id, "story", "thread", f"Story {node_id}", {},
        quality={
            "verified_subject_countries": [country],
            "subject_country_status": "verified",
        },
    )


def _story_without_actor(node_id: str) -> InvestigationNode:
    return node(node_id, "story", "thread", f"Story {node_id}", {"live": {"top_countries": ["DE"]}})


def _package_of(nodes):
    graph = assemble_investigation_graph(GraphRequest(nodes=nodes), measured_at=STAMP)
    return build_publication_package(PublicationPackageRequest(
        title="Edition", authorship="system", graph=graph, generated_at=STAMP,
    ))


def test_readiness_reports_the_measured_fraction_for_every_dimension():
    package = _package_of([_story_with_actor("node-story-1", "TR"), _story_without_actor("node-story-2")])

    for dim in ("who", "what", "when", "where", "how", "why"):
        measured = package.readiness[dim].measured
        assert measured is not None, dim
        assert measured.basis, dim
        assert measured.ready <= measured.total or measured.total == 0

    where = package.readiness["where"].measured
    assert (where.ready, where.total, where.basis) == (1, 2, "story_nodes")
    assert where.fraction == 0.5


def test_who_and_where_clear_the_bar_without_unanimity():
    # 7 of 12 story nodes attributed — above the measured full bar (0.55) and
    # far from unanimity. The old rule called this `partial` forever.
    nodes = [_story_with_actor(f"node-story-{i}", "TR") for i in range(7)]
    nodes += [_story_without_actor(f"node-story-b{i}") for i in range(5)]

    package = _package_of(nodes)

    assert package.readiness["who"].status == "ready"
    assert package.readiness["where"].status == "ready"
    assert package.readiness["where"].measured.ready == 7
    assert package.readiness["where"].measured.total == 12


def test_below_the_partial_bar_readiness_still_serves_what_it_measured():
    nodes = [_story_with_actor("node-story-1", "TR")]
    nodes += [_story_without_actor(f"node-story-b{i}") for i in range(11)]

    package = _package_of(nodes)
    where = package.readiness["where"]

    assert where.status == "partial"  # measured, not missing: the value exists
    assert where.values == ["TR"]
    assert "subject_geography_incomplete_for_story_nodes" in where.reason_codes
    assert where.measured.ready == 1 and where.measured.total == 12


def test_a_dimension_with_nothing_measured_is_missing_not_a_zero_fraction():
    package = _package_of([_story_without_actor("node-story-1")])
    where = package.readiness["where"]

    assert where.status == "partial"  # coverage geography only
    assert "coverage_geography_only_not_subject" in where.reason_codes
    assert where.measured.ready == 0 and where.measured.total == 1


def test_why_never_reaches_ready_however_high_the_fraction():
    story = node(
        "node-story-1", "story", "thread", "Moving story",
        {"live": {"changed_10h": 12, "top_countries": ["TR"]}},
        quality={"verified_subject_countries": ["TR"], "subject_country_status": "verified"},
    )
    package = _package_of([story])
    why = package.readiness["why"]

    assert why.status == "partial"
    assert "causal_explanation_not_measured" in why.reason_codes
    assert why.measured is not None
