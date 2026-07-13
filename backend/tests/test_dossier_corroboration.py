"""Web-corroboration lane (P0.6b) — pure-math tests, no network.

Freezes the G2 independence rule (syndicated wire = one source; count
independently-operated outlets), query building, and status assignment.
"""
import pytest

from app.services.corroboration import (
    ESTABLISHED_MIN_OUTLETS,
    build_pin_queries,
    cluster_syndicated,
    independence,
    pin_status,
)


def _art(title: str, outlet: str) -> dict:
    return {"title": title, "outlet": outlet, "url": f"https://{outlet}/x"}


class TestBuildPinQueries:
    def test_label_tokens_form_primary_query(self):
        qs = build_pin_queries("NATO Summit Ankara")
        assert qs[0] == "nato summit ankara"

    def test_actor_query_added_with_label_anchor(self):
        qs = build_pin_queries("NATO Summit Ankara", ["erdogan"])
        assert len(qs) == 2
        assert "erdogan" in qs[1] and "nato" in qs[1]

    def test_frozen_evidence_supplies_fallback_query_for_synthetic_label(self):
        qs = build_pin_queries(
            "Iran Attacks on Bahrain and Kuwait",
            evidence=[
                "Explosions heard in Bahrain's Manama as sirens activated"
                " — thepeninsulaqatar.com, 2026-07-09",
            ],
        )
        assert qs == [
            "iran attacks bahrain kuwait",
            "bahrain explosions manama sirens",
        ]

    def test_stopwords_and_noise_dropped(self):
        qs = build_pin_queries("The latest news updates on the crisis in Sudan")
        assert qs[0] == "sudan"

    def test_caps_at_two_queries(self):
        qs = build_pin_queries("Trump Putin call", ["putin", "ushakov", "trump"])
        assert len(qs) == 2

    def test_empty_label_no_queries(self):
        assert build_pin_queries("") == []


class TestSyndicationClustering:
    def test_identical_titles_cluster(self):
        arts = [
            _art("Trump orders cutoff of US trade with Spain", "a.com"),
            _art("Trump orders cutoff of US trade with Spain", "b.com"),
            _art("Trump orders cutoff of U.S. trade with Spain", "c.com"),
        ]
        clusters = cluster_syndicated(arts)
        assert len(clusters) == 1 and len(clusters[0]) == 3

    def test_distinct_accounts_stay_separate(self):
        arts = [
            _art("Trump orders cutoff of US trade with Spain", "cnbc.com"),
            _art("Erdogan opens NATO summit with defense pledge", "aljazeera.com"),
        ]
        assert len(cluster_syndicated(arts)) == 2


class TestIndependence:
    def test_wire_reprints_count_as_one(self):
        # 4 reprints of the same wire story on 4 domains = 1 independent source
        arts = [_art("Trump orders cutoff of US trade with Spain", f"local{i}.com")
                for i in range(4)]
        ind = independence(arts)
        assert ind["independent_outlets"] == 1
        assert ind["total_articles"] == 4
        assert ind["syndicated_clusters"] == 1

    def test_distinct_outlets_count_independently(self):
        arts = [
            _art("Trump orders cutoff of US trade with Spain", "cnbc.com"),
            _art("Trump says Spain 'hopeless, bad people' at NATO summit", "time.com"),
            _art("At Ankara summit, Trump escalates Spain trade fight", "abcnews.go.com"),
        ]
        ind = independence(arts)
        assert ind["independent_outlets"] == 3

    def test_same_domain_never_counts_twice(self):
        arts = [
            _art("Trump orders cutoff of US trade with Spain", "cnbc.com"),
            _art("Markets react to Spain trade cutoff order", "cnbc.com"),
        ]
        assert independence(arts)["independent_outlets"] == 1

    def test_mixed_wire_plus_originals(self):
        arts = [
            _art("Wire: NATO summit opens in Ankara", "local1.com"),
            _art("Wire: NATO summit opens in Ankara", "local2.com"),
            _art("Erdogan hosts 36th NATO summit", "nato.int"),
            _art("Ankara declaration prioritizes defense trade", "aljazeera.com"),
        ]
        ind = independence(arts)
        assert ind["independent_outlets"] == 3   # wire cluster=1 + 2 originals
        assert ind["citations"][0]["outlet"] == "local1.com"

    def test_empty(self):
        ind = independence([])
        assert ind["independent_outlets"] == 0 and ind["citations"] == []


class TestPinStatus:
    def test_established_at_threshold(self):
        status, note = pin_status(ESTABLISHED_MIN_OUTLETS, True)
        assert status == "established"
        assert "independently-operated" in note

    def test_single_source_is_unverified(self):
        status, note = pin_status(1, True)
        assert status == "unverified"
        assert "single-sourced" in note

    def test_zero_results_is_unverified(self):
        status, note = pin_status(0, True)
        assert status == "unverified"
        assert "no matching web coverage" in note

    def test_lane_unavailable_is_honest(self):
        status, note = pin_status(5, False)
        assert status == "unverified"
        assert "unavailable" in note

    def test_metadata_only_context_is_not_a_claim_to_corroborate(self):
        status, note = pin_status(0, False, applicable=False)
        assert status == "not_applicable"
        assert "no frozen evidence claim" in note


@pytest.mark.asyncio
async def test_router_tracks_search_availability_per_pin_and_skips_context(monkeypatch):
    from app.routers import dossier as dossier_module
    from app.services import external_depth

    async def fake_fetch(_label, *, raw_query, timespan):
        assert timespan == "14d"
        if raw_query.startswith("failed"):
            return None
        return {"items": []}

    monkeypatch.setattr(external_depth, "fetch_external_depth", fake_fetch)
    response = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(
            force=True,
            pins=[
                {
                    "id": "failed-pin",
                    "label": "Failed lane topic",
                    "anchor_type": "thread",
                    "evidence": ["Failed evidence claim"],
                },
                {
                    "id": "empty-pin",
                    "label": "Empty measured topic",
                    "anchor_type": "thread",
                    "evidence": ["Measured query with no matches"],
                },
                {
                    "id": "country-ir",
                    "label": "Iran",
                    "anchor_type": "country",
                    "evidence": [],
                },
            ],
        )
    )

    by_id = {pin["id"]: pin for pin in response["pins"]}
    assert by_id["failed-pin"]["note"] == (
        "web-search lane unavailable — corroboration not measured"
    )
    assert by_id["empty-pin"]["note"] == (
        "no matching web coverage found in the window"
    )
    assert by_id["country-ir"]["status"] == "not_applicable"
    assert by_id["country-ir"]["queries"] == []
    assert response["meta"]["dropped_pins"] == 0

    context_only = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(
            force=True,
            pins=[{
                "id": "country-only-ir",
                "label": "Iran",
                "anchor_type": "country",
                "evidence": [],
            }],
        )
    )
    assert context_only["search_available"] is False
    assert context_only["meta"]["search_note"] == (
        "no evidence-bearing pins — context remains in the dossier but has "
        "no frozen claim to corroborate"
    )
