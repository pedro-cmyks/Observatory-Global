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
        # corroborate-v2 R1: the judged count is independent VOICES; the note
        # says so (status logic for the ungrouped path is unchanged).
        assert "independent voices" in note

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

    asymmetry_prompts = []

    async def fake_fetch(_label, *, raw_query, timespan, **_kw):
        assert timespan == "14d"
        if raw_query.startswith("failed"):
            return {"status": "down", "result": None}
        if raw_query.startswith("good"):
            return {"status": "ok", "result": {
                "items": [{
                    "title": "Good topic independently covered",
                    "url": "https://example.com/good",
                    "domain": "example.com",
                }],
            }}
        return {"status": "ok", "result": {"items": []}}

    async def fake_generate(_system, user, **_kwargs):
        asymmetry_prompts.append(user)
        return "Measured comparison.", "test-provider", None, None

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_fetch)
    monkeypatch.setattr(dossier_module, "generate_insight", fake_generate)
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
                {
                    "id": "good-pin",
                    "label": "Good topic",
                    "anchor_type": "thread",
                    "evidence": ["Good evidence claim"],
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
    assert len(asymmetry_prompts) == 1
    assert "STORY: Good topic" in asymmetry_prompts[0]
    assert "STORY: Failed lane topic" not in asymmetry_prompts[0]

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


@pytest.mark.asyncio
async def test_router_counts_voices_and_carries_ownership_and_tier(monkeypatch):
    """corroborate-v2 R1 at the serving edge (council witness M-N18).

    ria.ru + tass.com + rt.com + cnn.com writing four DIFFERENT stories is four
    independently-operated outlets but only TWO voices — one Russian state
    apparatus speaking three times, plus one independent newsroom. The pin must
    stay ``unverified`` and every citation must carry the ownership group and
    the credibility tier that explain why.
    """
    from app.routers import dossier as dossier_module
    from app.services import external_depth

    async def fake_fetch(_label, *, raw_query, timespan, **_kw):
        # DOC 2.0 silent — the client-supplied lane carries this pin.
        return {"status": "down", "result": None}

    async def fake_generate(_system, _user, **_kwargs):
        return "Measured comparison.", "test-provider", None, None

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_fetch)
    monkeypatch.setattr(dossier_module, "generate_insight", fake_generate)

    response = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(
            force=True,
            pins=[{
                "id": "grid-pin",
                "label": "Strike on Kyiv power grid",
                "anchor_type": "thread",
                "evidence": ["Twelve killed as Kyiv substations burn"],
            }],
            supplied_results=[
                {"pin_id": "grid-pin", "outlet": "ria.ru",
                 "title": "Defence ministry announces precision hit",
                 "url": "https://ria.ru/1"},
                {"pin_id": "grid-pin", "outlet": "tass.com",
                 "title": "Energy infrastructure targeted, military confirms",
                 "url": "https://tass.com/2"},
                {"pin_id": "grid-pin", "outlet": "rt.com",
                 "title": "Kiev blackout follows overnight barrage",
                 "url": "https://rt.com/3"},
                {"pin_id": "grid-pin", "outlet": "cnn.com",
                 "title": "Twelve dead as strikes darken Ukrainian capital",
                 "url": "https://cnn.com/4"},
            ],
        )
    )

    pin = response["pins"][0]
    assert pin["independent_outlets"] == 4        # receipts stay visible…
    assert pin["independent_voices"] == 2         # …but three of them are one
    assert pin["state_collapsed"] == 2
    assert pin["status"] == "unverified"
    assert "same-state outlets counted as one voice" in pin["note"]

    by_outlet = {c["outlet"]: c for c in pin["citations"]}
    assert by_outlet["ria.ru"]["ownership_group"] == "state:ru"
    assert by_outlet["tass.com"]["ownership_group"] == "state:ru"
    assert by_outlet["rt.com"]["ownership_group"] == "state:ru"
    assert by_outlet["cnn.com"]["ownership_group"] is None
    assert by_outlet["ria.ru"]["credibility"]["label"] == "state"
    assert by_outlet["cnn.com"]["credibility"]["label"] != "state"

    # The glass-box meta must name the bar it actually applies.
    assert "voices" in response["meta"]["status_rule"].lower()
    assert "same-state" in response["meta"]["independence_rule"]


@pytest.mark.asyncio
async def test_single_source_flag_keys_on_voices_not_outlets(monkeypatch):
    """corroborate-v2 R1 follow-through: three same-state outlets ARE one
    source. The flag and the voices bar must agree — an all-state pin reads
    single_source=True even though it shows three receipts."""
    from app.routers import dossier as dossier_module
    from app.services import external_depth

    async def fake_fetch(_label, *, raw_query, timespan, **_kw):
        return {"status": "down", "result": None}

    async def fake_generate(_system, _user, **_kwargs):
        return "Measured comparison.", "test-provider", None, None

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_fetch)
    monkeypatch.setattr(dossier_module, "generate_insight", fake_generate)

    response = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(
            force=True,
            pins=[{
                "id": "state-pin",
                "label": "Strike on Kyiv power grid",
                "anchor_type": "thread",
                "evidence": ["Twelve killed as Kyiv substations burn"],
            }],
            supplied_results=[
                {"pin_id": "state-pin", "outlet": "ria.ru",
                 "title": "Defence ministry announces precision hit",
                 "url": "https://ria.ru/1"},
                {"pin_id": "state-pin", "outlet": "tass.com",
                 "title": "Energy infrastructure targeted, military confirms",
                 "url": "https://tass.com/2"},
                {"pin_id": "state-pin", "outlet": "rt.com",
                 "title": "Kiev blackout follows overnight barrage",
                 "url": "https://rt.com/3"},
            ],
        )
    )
    pin = response["pins"][0]
    assert pin["independent_outlets"] == 3
    assert pin["independent_voices"] == 1
    assert pin["single_source"] is True
