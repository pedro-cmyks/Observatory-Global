"""Web-corroboration lane (P0.6b) — pure-math tests, no network.

Freezes the G2 independence rule (syndicated wire = one source; count
independently-operated outlets), query building, and status assignment.
"""
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
