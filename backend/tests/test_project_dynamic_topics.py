from __future__ import annotations

import numpy as np

from scripts.project_dynamic_topics import (
    LifecycleConfig,
    Topic,
    chunk_ids,
    is_roundup_label,
    merge_duplicates,
    next_state,
    running_mean,
    process_snapshot,
)

CFG = LifecycleConfig()


def test_is_roundup_label():
    assert is_roundup_label("Daily News Roundup")
    assert is_roundup_label("Mixed News Headlines")
    assert not is_roundup_label("Iran Nuclear Talks Stance")
    assert not is_roundup_label(None)


def test_is_roundup_label_multilingual_grabbags():
    # #224 follow-up: non-English / generic grab-bag labels that slipped through
    # and promoted to living threads in the 2026-06-23 persisted-corpus snapshot.
    assert is_roundup_label("Notícias Diversas do Dia")     # pt "diverse news"
    assert is_roundup_label("Noticias Diversas")            # es
    assert is_roundup_label("Regional News and Events")     # generic listing
    assert is_roundup_label("Diverse News Updates")
    assert is_roundup_label("General News Roundup")
    # Real narrative threads must NOT be flagged, incl. non-English ones.
    assert not is_roundup_label("Operasyon ve Yolsuzluk")   # Turkish corruption probe
    assert not is_roundup_label("Russia-Ukraine War")
    assert not is_roundup_label("Qatargate and Political Scandals")
    assert not is_roundup_label("Crime Headlines")          # legit topic (per existing guard)


def test_content_roundup_distinguishes_digest_from_broad_thread():
    from scripts.project_dynamic_topics import (
        subject_concentration, source_concentration, is_roundup_by_content,
    )
    # Focused real thread: a shared subject token in every headline.
    focused = [f"Delhi hotel fire kills {n} as rescue continues" for n in range(8)]
    assert subject_concentration(focused) > 0.8

    # Grab-bag digest: every headline a different topic, ALL from one outlet.
    digest = [
        "SpaceX shares slide for third session",
        "Gold price edges lower this morning",
        "Two road accidents overnight leave five dead",
        "iPhone seventeen hits lowest local price",
        "Fireworks festival opens additional seating",
        "Rice export prices hold steady",
        "Football betting ring busted before World Cup",
        "Central bank governor signs two new decrees",
    ]
    one_src = ["vnexpress.net"] * len(digest)
    assert subject_concentration(digest) < 0.30
    assert source_concentration(one_src) == 1.0
    assert is_roundup_by_content(digest, one_src) is True

    # SAME dispersed headlines but spanning MANY outlets = broad real thread
    # (e.g. a war or market crash) — must NOT be flagged.
    many_src = [f"outlet{i}.com" for i in range(len(digest))]
    assert source_concentration(many_src) < 0.35
    assert is_roundup_by_content(digest, many_src) is False

    # Too few / no-whitespace → undecidable, never flagged.
    assert subject_concentration(["a", "b"]) is None
    assert is_roundup_by_content(["one two three", "four five six"], ["x", "x"]) is False


def test_single_outlet_wire_dump_with_boilerplate_prefix_flagged():
    # Real failure (#214, topic 23): aip.ci dumped 546 headlines all prefixed
    # "Côte d'Ivoire-AIP/", faking subject concentration 1.0 → escaped the guard
    # and got the hallucinated label "Russian Shadow Fleet Interceptions".
    from scripts.project_dynamic_topics import (
        subject_concentration, is_roundup_by_content,
    )
    aip = [
        "Côte d’Ivoire-AIP/ L’ONPC annonce la prochaine ouverture d’un centre",
        "Côte d’Ivoire-AIP/ Des caméras de surveillance pour renforcer la sécurité",
        "Côte d’Ivoire-AIP/ Le Bafing bientôt doté d’une plateforme",
        "Côte d’Ivoire-AIP/ La CNPS intensifie l’enrôlement des travailleurs",
        "Côte d’Ivoire-AIP/ Des réformes engagées par le gouvernement",
        "Côte d’Ivoire-AIP/ Lancement des Journées nationales du service public",
        "Côte d’Ivoire-AIP/ La plateforme de l’ONEF sur le système",
    ]
    one_src = ["aip.ci"] * len(aip)
    # the boilerplate prefix fools the raw subject metric...
    assert subject_concentration(aip) >= 0.30
    # ...but the single-outlet prefix-strip path catches it.
    assert is_roundup_by_content(aip, one_src) is True


def test_multi_outlet_focused_story_not_flagged():
    # A genuine story corroborated across MANY outlets is a real thread — the
    # single-outlet dump rule must not touch it (it spans outlets, not one feed).
    from scripts.project_dynamic_topics import is_roundup_by_content
    focused = [
        "Delhi hotel fire kills six as rescue teams search the upper floors",
        "Delhi hotel fire death toll rises while families wait for news",
        "Delhi hotel fire probe opens into blocked exits and alarms",
        "Delhi hotel fire survivors describe smoke filling the stairwell",
        "Delhi hotel fire owner detained as inspectors review permits",
        "Delhi hotel fire prompts citywide safety audit of old buildings",
    ]
    many_src = [f"outlet{i}.com" for i in range(len(focused))]
    assert is_roundup_by_content(focused, many_src) is False


def test_single_outlet_dump_flagged_even_when_subject_looks_coherent():
    # Atlas requires multi-outlet corroboration: a cluster owned by ONE outlet at
    # scale is that feed dumped, never a verified thread — flagged regardless of
    # an apparently coherent (slug-driven) subject.
    from scripts.project_dynamic_topics import is_roundup_by_content
    headlines = [f"OutletWire/ Story number {n} on an unrelated matter today"
                 for n in range(8)]
    one_src = ["onewire.example"] * len(headlines)
    assert is_roundup_by_content(headlines, one_src) is True


def test_running_mean():
    old = np.array([1.0, 1.0])
    out = running_mean(old, 1, np.array([3.0, 3.0]))
    assert list(out) == [2.0, 2.0]


def test_next_state_promotes_qualifying_candidate():
    s = next_state("candidate", seen_now=True, n_snapshots=2, mean_cohesion=0.8,
                   agg_n_signals=100, is_roundup=False, since_seen=0, cfg=CFG)
    assert s == "active"


def test_next_state_does_not_promote_roundup():
    s = next_state("candidate", seen_now=True, n_snapshots=5, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=True, since_seen=0, cfg=CFG)
    assert s == "candidate"


def test_next_state_does_not_promote_low_volume_or_cohesion():
    assert next_state("candidate", seen_now=True, n_snapshots=3, mean_cohesion=0.2,
                      agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG) == "candidate"
    assert next_state("candidate", seen_now=True, n_snapshots=3, mean_cohesion=0.9,
                      agg_n_signals=5, is_roundup=False, since_seen=0, cfg=CFG) == "candidate"


def test_next_state_deprecate_and_retire_on_staleness():
    assert next_state("active", seen_now=False, n_snapshots=3, mean_cohesion=0.8,
                      agg_n_signals=100, is_roundup=False, since_seen=2, cfg=CFG) == "deprecated"
    assert next_state("deprecated", seen_now=False, n_snapshots=3, mean_cohesion=0.8,
                      agg_n_signals=100, is_roundup=False, since_seen=4, cfg=CFG) == "retired"


def test_next_state_reactivates_on_reappearance():
    s = next_state("deprecated", seen_now=True, n_snapshots=4, mean_cohesion=0.8,
                   agg_n_signals=100, is_roundup=False, since_seen=0, cfg=CFG)
    assert s == "active"


def _cluster(snap, cid, vec, label, n=100, coh=0.9):
    return {"id": cid, "snapshot_at": snap, "cluster_id": cid, "label": label,
            "n_signals": n, "cohesion": coh, "centroid": np.array(vec, dtype=np.float64)}


def test_process_snapshot_promotes_persistent_real_topic():
    topics = []
    process_snapshot(topics, [_cluster("s1", 1, [1.0, 0.0], "Iran Talks")], "s1", CFG)
    assert topics[0].state == "candidate"  # only 1 snapshot
    process_snapshot(topics, [_cluster("s2", 2, [0.99, 0.01], "Iran Talks")], "s2", CFG)
    assert len(topics) == 1               # matched, not duplicated
    assert topics[0].state == "active"    # persisted 2 snapshots, cohesive, volume


def test_process_snapshot_keeps_roundup_as_candidate():
    topics = []
    process_snapshot(topics, [_cluster("s1", 1, [1.0, 0.0], "Daily News Roundup")], "s1", CFG)
    process_snapshot(topics, [_cluster("s2", 2, [1.0, 0.0], "Daily News Roundup")], "s2", CFG)
    assert len(topics) == 1
    assert topics[0].is_roundup
    assert topics[0].state == "candidate"  # never promoted despite persistence


def test_merge_duplicates_absorbs_near_duplicate_into_older_identity():
    older = Topic("dyn-s1-1", "Russia Warns", [1.0, 0.0], "s1", 100, 0.9, noise=0.1)
    older.members.append({"cluster_id": 1, "snapshot_at": "s1", "match_score": 1.0})
    older.state = "active"
    older.id = 10

    newer = Topic("dyn-s2-2", "Russia Warnings", [0.99, 0.01], "s2", 80, 0.8, noise=0.2)
    newer.members.append({"cluster_id": 2, "snapshot_at": "s2", "match_score": 1.0})
    newer.state = "candidate"
    newer.id = 11

    merged = merge_duplicates([newer, older], threshold=0.9)

    assert len(merged) == 1
    topic = merged[0]
    assert topic.identity_key == "dyn-s1-1"
    assert topic.id == 10
    assert topic.state == "active"
    assert topic.agg_n_signals == 180
    assert topic.n_member_clusters == 2
    assert topic.noise_rate == 0.15
    assert [m["cluster_id"] for m in topic.members] == [1, 2]


def test_merge_duplicates_does_not_merge_distinct_topics():
    first = Topic("dyn-s1-1", "Russia Warns", [1.0, 0.0], "s1", 100, 0.9)
    second = Topic("dyn-s1-2", "Local Politics", [0.0, 1.0], "s1", 100, 0.9)

    merged = merge_duplicates([first, second], threshold=0.9)

    assert len(merged) == 2


def test_merge_duplicates_requires_compatible_labels_even_with_close_centroids():
    first = Topic("dyn-s1-1", "Orchard Portfolio Sale", [1.0, 0.0], "s1", 100, 0.9)
    second = Topic("dyn-s1-2", "Virginia Bus Crash", [0.99, 0.01], "s1", 100, 0.9)

    merged = merge_duplicates([first, second], threshold=0.9)

    assert len(merged) == 2


def test_merge_duplicates_does_not_let_roundups_absorb_real_topics():
    roundup = Topic("dyn-s1-1", "Daily News Roundup", [1.0, 0.0], "s1", 100, 0.9)
    real = Topic("dyn-s1-2", "Agostina Vega Found Dead", [0.99, 0.01], "s1", 100, 0.9)

    merged = merge_duplicates([roundup, real], threshold=0.9)

    assert len(merged) == 2


# ── #224: black-hole guards ──────────────────────────────────────────────────

def _unit(v):
    import numpy as np
    a = np.array(v, dtype=float)
    return (a / np.linalg.norm(a)).tolist()


def _cluster224(cid, label, centroid, snap="2026-06-11T00:00:00", n=30):
    return {
        "id": cid, "snapshot_at": snap, "cluster_id": cid, "label": label,
        "n_signals": n, "cohesion": 0.7, "sample_signal_ids": [],
        "centroid": centroid, "noise": 0.1,
    }


def test_anchor_guard_blocks_drift_chain():
    """A topic whose running mean drifts must NOT absorb clusters that no
    longer resemble its original identity (the PSG black hole, #224)."""
    from scripts.project_dynamic_topics import (
        LifecycleConfig, Topic, process_snapshot,
    )
    cfg = LifecycleConfig()
    anchor_vec = _unit([1.0, 0.0, 0.0, 0.05])
    topic = Topic("t-psg", "PSG Victory Riots", anchor_vec,
                  "2026-06-01T00:00:00", 30, 0.7)
    # simulate drift: running centroid pulled toward a different region
    drift_vec = _unit([0.55, 0.8, 0.2, 0.0])
    topic.centroid = __import__("numpy").array(drift_vec)

    # cluster matches the DRIFTED centroid but not the anchor
    invader = _cluster224(101, "PM Modi's 12-Year Milestone", drift_vec)
    topics = process_snapshot([topic], [invader], "2026-06-11T00:00:00", cfg)

    # invader must open its own topic, not attach to PSG
    assert len(topics) == 2
    assert topics[0].n_member_clusters == 0  # PSG gained nothing
    assert topics[1].label == "PM Modi's 12-Year Milestone"


def test_anchor_guard_allows_genuine_continuation():
    from scripts.project_dynamic_topics import (
        LifecycleConfig, Topic, process_snapshot,
    )
    cfg = LifecycleConfig()
    anchor_vec = _unit([1.0, 0.0, 0.0, 0.05])
    topic = Topic("t-war", "Russia-Ukraine War Updates", anchor_vec,
                  "2026-06-01T00:00:00", 30, 0.7)
    near = _cluster224(102, "Russian Drone Strikes on Kyiv", _unit([0.98, 0.05, 0.0, 0.06]))
    topics = process_snapshot([topic], [near], "2026-06-11T00:00:00", cfg)
    assert len(topics) == 1
    assert topics[0].n_member_clusters == 1


def test_listing_format_labels_flagged_never_promote():
    """Recurring-format noise (listings) persists by nature; never a thread."""
    from scripts.project_dynamic_topics import is_roundup_label
    assert is_roundup_label("Stock Price Movements")
    assert is_roundup_label("Real Estate Listings")
    assert is_roundup_label("Company Information Summary")
    assert not is_roundup_label("Stock Market Crash in Tokyo")  # a story, not a listing


def test_multilingual_roundup_labels_flagged():
    from scripts.project_dynamic_topics import is_roundup_label
    assert is_roundup_label("Noticias Regionales Variadas")
    assert is_roundup_label("Noticias Variadas")
    assert is_roundup_label("Resumen de Noticias")
    assert is_roundup_label("Greek News Roundup")
    assert not is_roundup_label("Crime Headlines")
    assert not is_roundup_label("Iran Water Crisis")


def test_chunk_ids_bounds_every_statement():
    # 2026-07-19: ONE unbatched `id = ANY($1)` over every sample_signal_id hit
    # statement_timeout under post-snapshot contention and killed the whole
    # projection (the 07-12/13 "projection failed (non-fatal)" incidents).
    # Chunking bounds each statement — same medicine as keyset pagination.
    ids = list(range(25))
    chunks = chunk_ids(ids, size=10)
    assert chunks == [list(range(10)), list(range(10, 20)), list(range(20, 25))]
    # order + content preserved exactly
    assert [i for c in chunks for i in c] == ids


def test_chunk_ids_empty_and_degenerate_size():
    assert chunk_ids([], size=10) == []
    # size<=0 = one unbatched chunk (legacy behavior, explicit opt-out)
    assert chunk_ids([1, 2, 3], size=0) == [[1, 2, 3]]
    assert chunk_ids([1, 2, 3], size=-5) == [[1, 2, 3]]
    # exact multiple leaves no empty tail chunk
    assert chunk_ids([1, 2, 3, 4], size=2) == [[1, 2], [3, 4]]


def test_fetch_by_ids_issues_one_bounded_statement_per_chunk(monkeypatch):
    import asyncio

    import scripts.project_dynamic_topics as pdt

    class _FakeConn:
        def __init__(self):
            self.calls: list[list[int]] = []

        async def fetch(self, _sql, chunk):
            self.calls.append(list(chunk))
            return [{"id": i} for i in chunk]

    monkeypatch.setattr(pdt, "ID_FETCH_CHUNK", 3)
    conn = _FakeConn()
    rows = asyncio.run(pdt._fetch_by_ids(conn, "SELECT ...", list(range(7))))
    assert conn.calls == [[0, 1, 2], [3, 4, 5], [6]]  # no unbounded statement
    assert [r["id"] for r in rows] == list(range(7))  # all rows, in order


def test_hydrate_topics_excludes_umbrellas_from_matching():
    # 2026-07-28 orphan-cluster incident: hydrate loaded umbrella topics, so
    # clusters could attach DIRECTLY to an umbrella (greedy match). An umbrella's
    # member rows are derived — cleared + rebuilt from children every nightly
    # umbrella pass — so the direct attach was deleted each night, the cluster
    # re-adopted, re-attached, forever (72 orphans incl. the 70-signal Caspian
    # fragment; never founded a topic, never served). Umbrellas must not hydrate
    # into the matching population; their member rows still count toward `done`.
    import asyncio
    from datetime import datetime, timezone

    from scripts.project_dynamic_topics import hydrate_topics

    snap = datetime(2026, 7, 28, 3, 28, tzinfo=timezone.utc)
    cen = [1.0] + [0.0] * 3

    class _FakeConn:
        async def fetch(self, sql, *args):
            if "FROM dynamic_topics" in sql:
                base = {
                    "state": "active", "snapshots_since_seen": 0,
                    "centroid_vec": cen, "first_seen": snap, "last_seen": snap,
                    "n_snapshots": 2, "agg_n_signals": 20, "mean_cohesion": 0.9,
                    "noise_rate": None, "is_junk": False,
                }
                return [
                    {**base, "id": 1, "identity_key": "dyn-x-1", "label": "Real Story",
                     "is_umbrella": False},
                    {**base, "id": 2, "identity_key": "umbrella:1", "label": "Umbrella",
                     "is_umbrella": True},
                ]
            return [  # dynamic_topic_members
                {"dynamic_topic_id": 1, "emergent_cluster_id": 100, "snapshot_at": snap},
                # derived copy of the child's row on the umbrella
                {"dynamic_topic_id": 2, "emergent_cluster_id": 100, "snapshot_at": snap},
                # the orphan class: attached ONLY to the umbrella
                {"dynamic_topic_id": 2, "emergent_cluster_id": 200, "snapshot_at": snap},
            ]

    clusters_by_id = {
        100: {"id": 100, "label": "Real Story", "centroid": np.array(cen),
              "n_signals": 20, "cohesion": 0.9, "noise": None},
        200: {"id": 200, "label": "Swallowed", "centroid": np.array(cen),
              "n_signals": 10, "cohesion": 0.9, "noise": None},
    }
    topics, done = asyncio.run(hydrate_topics(_FakeConn(), clusters_by_id))
    assert [t.identity_key for t in topics] == ["dyn-x-1"]  # umbrella never a match target
    assert done == {100, 200}  # membership accounting unchanged
