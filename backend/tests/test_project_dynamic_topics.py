from __future__ import annotations

import numpy as np

from scripts.project_dynamic_topics import (
    LifecycleConfig,
    Topic,
    apply_new_clusters,
    chunk_ids,
    clustered_countries,
    count_passes,
    is_frozen_country,
    is_roundup_label,
    lifecycle_country_clock_enabled,
    lifecycle_tick_v2_enabled,
    load_snapshot_checkpoint,
    merge_duplicates,
    next_state,
    running_mean,
    process_snapshot,
    use_country_clock,
    use_tick_v2,
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
                    "revived_at": None, "label_status": None,
                    "blob_confirmed_at": None,
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


# ── P1 (2026-07-30): one lifecycle tick per pass ─────────────────────────────
# Defect: build_umbrella_topics DELETEs umbrella member rows nightly, so orphaned
# clusters re-enter at their ORIGINAL snapshot_at and each distinct snapshot_at
# fired a full aging tick. Measured 2-4 ticks/night against ONE snapshot/day →
# stale_k=2 + retire_m=4 both cleared in a single missed clustering pass.

def _far_cluster(snap, cid, label="Unrelated Story"):
    """A cluster that can never match the fixture topic (orthogonal centroid)."""
    return _cluster(snap, cid, [0.0, 1.0], label)


def _aged_active_topic():
    t = Topic("dyn-s0-1", "Colombia 42-Hour Workweek", [1.0, 0.0], "s0", 115, 0.9)
    t.state = "active"
    t.since_seen = 0
    t.new = False
    t.dirty = False
    return t


def _four_groups():
    """One real pass + three umbrella-orphan re-entrant groups (older snaps)."""
    return [
        ("2026-07-25T22:00:00", [_far_cluster("2026-07-25T22:00:00", 25)]),
        ("2026-07-26T22:00:00", [_far_cluster("2026-07-26T22:00:00", 26)]),
        ("2026-07-27T22:00:00", [_far_cluster("2026-07-27T22:00:00", 27)]),
        ("2026-07-28T22:00:00", [_far_cluster("2026-07-28T22:00:00", 28)]),
    ]


def test_lifecycle_tick_v2_enabled_defaults_off():
    assert lifecycle_tick_v2_enabled({}) is False
    assert lifecycle_tick_v2_enabled({"ATLAS_LIFECYCLE_TICK_V2": ""}) is False
    assert lifecycle_tick_v2_enabled({"ATLAS_LIFECYCLE_TICK_V2": "off"}) is False
    assert lifecycle_tick_v2_enabled({"ATLAS_LIFECYCLE_TICK_V2": "0"}) is False
    for on in ("1", "on", "true", "TRUE", " yes "):
        assert lifecycle_tick_v2_enabled({"ATLAS_LIFECYCLE_TICK_V2": on}) is True


def test_use_tick_v2_never_applies_to_rebuild():
    env = {"ATLAS_LIFECYCLE_TICK_V2": "on"}
    assert use_tick_v2(False, env) is True
    # --rebuild REPLAYS history from empty; each historical snapshot keeps its
    # own tick or the replayed population would never have been aged at all.
    assert use_tick_v2(True, env) is False
    assert use_tick_v2(False, {}) is False


def test_apply_new_clusters_flag_off_is_byte_identical_legacy_loop():
    """FROZEN: with the flag off, every snapshot group still fires a full tick."""
    topics = [_aged_active_topic()]
    ticks = apply_new_clusters(topics, _four_groups(), CFG, tick_v2=False)
    assert ticks == 4                       # n_snapshots_processed = 4 (the measured number)
    assert topics[0].since_seen == 4
    assert topics[0].state == "retired"     # active -> deprecated -> retired in ONE night


def test_apply_new_clusters_v2_fires_exactly_one_tick_per_pass():
    """The pass is the clock: 4 groups (3 orphan re-entrants) = 1 tick."""
    topics = [_aged_active_topic()]
    ticks = apply_new_clusters(topics, _four_groups(), CFG, tick_v2=True)
    assert ticks == 1
    assert topics[0].since_seen == 1        # not 4
    assert topics[0].state == "active"      # survives a single missed pass


def test_apply_new_clusters_v2_still_retires_on_genuinely_repeated_misses():
    """The clock is slowed, not stopped — stale_k/retire_m are untouched."""
    topics = [_aged_active_topic()]
    for _ in range(4):
        apply_new_clusters(topics, _four_groups(), CFG, tick_v2=True)
    assert topics[0].since_seen == 4
    assert topics[0].state == "retired"


def test_apply_new_clusters_v2_seen_reset_unchanged():
    """A topic matched anywhere in the pass resets to 0 exactly as today."""
    topics = [_aged_active_topic()]
    topics[0].since_seen = 1
    groups = [
        # the topic's own cluster comes back in a RE-ENTRANT (older) group —
        # the orphan guard's aging half: re-entrants are members of this pass.
        ("2026-07-27T22:00:00", [_cluster("2026-07-27T22:00:00", 27, [1.0, 0.0], "Colombia 42-Hour Workweek")]),
        ("2026-07-28T22:00:00", [_far_cluster("2026-07-28T22:00:00", 28)]),
    ]
    assert apply_new_clusters(topics, groups, CFG, tick_v2=True) == 1
    assert topics[0].since_seen == 0
    assert topics[0].state == "active"
    assert len(topics) == 2                 # the unrelated cluster founded its own topic


def test_apply_new_clusters_matching_is_identical_across_flag_states():
    """Deferring the aging step must not change which cluster attaches where."""
    def _run(tick_v2):
        topics = [_aged_active_topic()]
        apply_new_clusters(topics, _four_groups(), CFG, tick_v2=tick_v2)
        return [(t.identity_key, t.label, t.n_member_clusters, t.agg_n_signals)
                for t in topics]
    assert _run(True) == _run(False)


def test_apply_new_clusters_no_groups_fires_no_tick():
    topics = [_aged_active_topic()]
    assert apply_new_clusters(topics, [], CFG, tick_v2=True) == 0
    assert apply_new_clusters(topics, [], CFG, tick_v2=False) == 0
    assert topics[0].since_seen == 0        # an empty run never ages the field


def test_count_passes_reports_reentrants_not_extra_passes():
    acct = count_passes(_four_groups())
    assert acct["passes"] == 1              # n_snapshots_processed, the TF-1 metric
    assert acct["groups"] == 4
    assert acct["reentrant_groups"] == 3    # the umbrella-orphan ledger
    assert acct["primary_snapshot"] == "2026-07-28T22:00:00"


def test_count_passes_single_group_and_empty():
    one = [("2026-07-29T22:00:00", [_far_cluster("2026-07-29T22:00:00", 29)])]
    assert count_passes(one) == {
        "passes": 1, "groups": 1, "reentrant_groups": 0,
        "primary_snapshot": "2026-07-29T22:00:00",
    }
    assert count_passes([]) == {
        "passes": 0, "groups": 0, "reentrant_groups": 0, "primary_snapshot": None,
    }


# ── P2 (2026-07-30): the per-country lifecycle clock ─────────────────────────
# Defect: the 150-min weekday run budget defers 130-154 countries/night and the
# deferred countries' topics age anyway — BO/ML cluster fine (100% re-match)
# whenever the pass reaches them and die between passes. A topic ages only on
# passes that actually clustered one of its countries. MM is the control: it IS
# reached and returns "no gated clusters" every pass — an honest empty, which
# must keep aging.

PASS_SNAP = "2026-07-30T03:53:18.074187+00:00"


def _country_topic(cc, key="dyn-s0-1", label="Colombia 42-Hour Workweek"):
    t = Topic(key, label, [1.0, 0.0], "s0", 115, 0.9, countries=[cc])
    t.state = "active"
    t.since_seen = 0
    t.new = False
    t.dirty = False
    return t


def _pass_groups(snap=PASS_SNAP):
    """One pass whose clusters can never match the fixture topics."""
    return [(snap, [_far_cluster(snap, 1)])]


def _checkpoint(done, snap=PASS_SNAP):
    return {"snapshot_at": snap, "hours": 168, "started_at": snap,
            "next_base": 0, "done": done, "complete": True, "version": 1}


def test_lifecycle_country_clock_defaults_off():
    assert lifecycle_country_clock_enabled({}) is False
    assert lifecycle_country_clock_enabled({"ATLAS_LIFECYCLE_COUNTRY_CLOCK": ""}) is False
    assert lifecycle_country_clock_enabled({"ATLAS_LIFECYCLE_COUNTRY_CLOCK": "off"}) is False
    assert lifecycle_country_clock_enabled({"ATLAS_LIFECYCLE_COUNTRY_CLOCK": "0"}) is False
    for on in ("1", "on", "true", "TRUE", " yes "):
        assert lifecycle_country_clock_enabled({"ATLAS_LIFECYCLE_COUNTRY_CLOCK": on}) is True


def test_use_country_clock_never_applies_to_rebuild():
    env = {"ATLAS_LIFECYCLE_COUNTRY_CLOCK": "on"}
    assert use_country_clock(False, env) is True
    # --rebuild replays ALL history; one night's ledger would freeze it whole.
    assert use_country_clock(True, env) is False
    assert use_country_clock(False, {}) is False


def test_clustered_countries_reads_the_checkpoint_ledger():
    ccs, reason = clustered_countries(
        _checkpoint({"US": "ok", "tr": "ok", "MM": "no_clusters"}),
        primary_snapshot=PASS_SNAP)
    assert reason == "checkpoint"
    # MM ran and kept nothing — it IS in the ledger (an honest empty, not a gap).
    assert ccs == {"US", "TR", "MM"}


def test_clustered_countries_fails_open_on_a_stale_or_missing_ledger():
    """Any doubt = age everything (today's behaviour), never freeze the field."""
    assert clustered_countries(None, primary_snapshot=PASS_SNAP) == (None, "no_checkpoint")
    assert clustered_countries(_checkpoint({"US": "ok"}), primary_snapshot=None) \
        == (None, "no_primary_snapshot")
    # a checkpoint describing ANOTHER night must never gate this pass
    assert clustered_countries(_checkpoint({"US": "ok"}, snap="2026-07-29T22:00:00+00:00"),
                               primary_snapshot=PASS_SNAP) == (None, "snapshot_mismatch")
    assert clustered_countries(_checkpoint({"US": "ok"}, snap="not-a-date"),
                               primary_snapshot=PASS_SNAP) == (None, "unparsable_snapshot")
    # naive vs aware must not be compared, and an empty ledger is not a ledger
    assert clustered_countries(_checkpoint({"US": "ok"}, snap="2026-07-30T03:53:18.074187"),
                               primary_snapshot=PASS_SNAP) == (None, "snapshot_mismatch")
    assert clustered_countries(_checkpoint({}), primary_snapshot=PASS_SNAP) \
        == (None, "empty_ledger")


def test_load_snapshot_checkpoint_never_raises(tmp_path):
    assert load_snapshot_checkpoint(None) is None
    assert load_snapshot_checkpoint(str(tmp_path)) is None          # no file
    (tmp_path / "scoped-snapshot-checkpoint.json").write_text("{oops", encoding="utf-8")
    assert load_snapshot_checkpoint(str(tmp_path)) is None          # corrupt
    (tmp_path / "scoped-snapshot-checkpoint.json").write_text(
        '{"snapshot_at": "s", "done": {"US": "ok"}}', encoding="utf-8")
    assert load_snapshot_checkpoint(str(tmp_path))["done"] == {"US": "ok"}


def test_is_frozen_country_fails_open_both_ways():
    bo = _country_topic("BO")
    assert is_frozen_country(bo, None) is False          # unknown ledger -> age
    assert is_frozen_country(bo, {"US", "TR"}) is True   # BO never clustered
    assert is_frozen_country(bo, {"US", "BO"}) is False
    unattributable = Topic("dyn-x", "No members left", [1.0, 0.0], "s0", 10, 0.9)
    assert is_frozen_country(unattributable, {"US"}) is False   # no country -> age


def test_country_clock_freezes_a_deferred_country_topic():
    """BO deferred by the run budget: Atlas failed to look, so BO does not age."""
    bo = _country_topic("BO")
    report: dict = {}
    apply_new_clusters([bo], _pass_groups(), CFG, tick_v2=True,
                       clustered_ccs={"US", "TR"}, report=report)
    assert bo.since_seen == 0
    assert bo.state == "active"
    assert report["frozen"] == 1


def test_country_clock_still_ages_a_processed_but_empty_country():
    """MM ran and kept nothing — an honest empty. It must keep aging."""
    mm = _country_topic("MM", key="dyn-mm-1", label="Myanmar Story")
    report: dict = {}
    apply_new_clusters([mm], _pass_groups(), CFG, tick_v2=True,
                       clustered_ccs={"US", "MM"}, report=report)   # MM = "no_clusters"
    assert mm.since_seen == 1
    assert report["frozen"] == 0


def test_country_clock_never_holds_back_a_seen_topic():
    """A matched topic resets to 0 even if the ledger says its country sat out."""
    t = _country_topic("BO")
    t.since_seen = 3
    groups = [(PASS_SNAP, [_cluster(PASS_SNAP, 9, [1.0, 0.0], "Colombia 42-Hour Workweek")])]
    apply_new_clusters([t], groups, CFG, tick_v2=True, clustered_ccs={"US"})
    assert t.since_seen == 0
    assert t.state == "active"


def test_country_clock_slows_the_clock_it_does_not_stop_it():
    """Once BO IS clustered again, the ordinary staleness path still retires it."""
    bo = _country_topic("BO")
    for _ in range(3):                                   # three deferred nights
        apply_new_clusters([bo], _pass_groups(), CFG, tick_v2=True, clustered_ccs={"US"})
    assert bo.since_seen == 0 and bo.state == "active"
    for _ in range(4):                                   # four nights BO ran, unseen
        apply_new_clusters([bo], _pass_groups(), CFG, tick_v2=True, clustered_ccs={"BO"})
    assert bo.since_seen == 4
    assert bo.state == "retired"


def test_country_clock_composes_with_tick_v2_both_on():
    """4 groups (3 orphan re-entrants) + a deferred country = zero aging."""
    bo = _country_topic("BO")
    mm = _country_topic("MM", key="dyn-mm-1", label="Myanmar Story")
    report: dict = {}
    ticks = apply_new_clusters([bo, mm], _four_groups(), CFG, tick_v2=True,
                               clustered_ccs={"US", "MM"}, report=report)
    assert ticks == 1
    assert bo.since_seen == 0        # deferred country: frozen
    assert mm.since_seen == 1        # clustered country: one tick, not four
    assert report["frozen"] == 1


def test_country_clock_composes_with_tick_v2_off():
    """P1 off: the legacy per-group tick still respects the country ledger."""
    bo = _country_topic("BO")
    mm = _country_topic("MM", key="dyn-mm-1", label="Myanmar Story")
    report: dict = {}
    ticks = apply_new_clusters([bo, mm], _four_groups(), CFG, tick_v2=False,
                               clustered_ccs={"US", "MM"}, report=report)
    assert ticks == 4
    assert bo.since_seen == 0        # frozen in every one of the four ticks
    assert bo.state == "active"
    assert mm.since_seen == 4        # legacy phantom ticks, unchanged by P2
    assert mm.state == "retired"
    assert report["frozen"] == 4     # one skipped topic-tick per group


def test_country_clock_flag_off_is_byte_identical_legacy_behaviour():
    """FROZEN: clustered_ccs=None (the default) ages exactly as before P2."""
    def _run(clustered_ccs):
        bo = _country_topic("BO")
        mm = _country_topic("MM", key="dyn-mm-1", label="Myanmar Story")
        report: dict = {}
        for tick_v2 in (False, True):
            apply_new_clusters([bo, mm], _four_groups(), CFG, tick_v2=tick_v2,
                               clustered_ccs=clustered_ccs, report=report)
        return [(t.since_seen, t.state) for t in (bo, mm)], report.get("frozen", 0)

    states, frozen = _run(None)
    assert states == [(5, "retired"), (5, "retired")]   # 4 legacy ticks + 1 v2 tick
    assert frozen == 0
    # and the pre-P2 default path (no kwarg at all) is the same object
    bo = _country_topic("BO")
    apply_new_clusters([bo], _four_groups(), CFG, tick_v2=False)
    assert (bo.since_seen, bo.state) == (4, "retired")


def test_topic_countries_track_the_latest_member_snapshot():
    """`countries` = the LATEST member snapshot's codes (the serving-door rule)."""
    t = Topic("dyn-1", "Story", [1.0, 0.0], "s1", 20, 0.9, countries=["bo"])
    assert t.countries == {"BO"}
    same = _cluster("s1", 2, [1.0, 0.0], "Story")
    same["countries"] = ["PE"]
    t.attach(same, "s1", 1.0)
    assert t.countries == {"BO", "PE"}          # same snapshot unions
    newer = _cluster("s2", 3, [1.0, 0.0], "Story")
    newer["countries"] = ["CL"]
    t.attach(newer, "s2", 1.0)
    assert t.countries == {"CL"}                # newer snapshot replaces
    older = _cluster("s0", 4, [1.0, 0.0], "Story")
    older["countries"] = ["AR"]
    t.attach(older, "s0", 1.0)
    assert t.countries == {"CL"}                # older is ignored


def test_topic_countries_survive_a_merge():
    a = Topic("dyn-a", "Story", [1.0, 0.0], "s1", 20, 0.9, countries=["BO"])
    b = Topic("dyn-b", "Story", [1.0, 0.0], "s2", 20, 0.9, countries=["PE"])
    a.absorb(b)
    assert a.countries == {"PE"}                # b's snapshot is newer
    assert a.cc_snap == "s2"


# ── TF-3b (2026-07-31): revive-to-candidate + court-gated promotion ──────────
# TF-2 measured the disease: tick-v2 revived retired->active DIRECT (681 rows,
# 62.5% mislabeled/blob served). v2b closes the exit door: revival always lands
# candidate, and a revived candidate promotes only after the label court
# re-certifies its label against the CURRENT receipts (label_status='entailed').

def test_next_state_v2b_revival_lands_candidate_even_when_qualifying():
    # the exact TF-2 hole: retired + seen + mechanically-qualifying used to
    # jump straight to active. Under the regime it must land candidate.
    s = next_state("retired", seen_now=True, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG,
                   revive_to_candidate=True)
    assert s == "candidate"
    s = next_state("deprecated", seen_now=True, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG,
                   revive_to_candidate=True)
    assert s == "candidate"


def test_next_state_v2b_court_blocked_revived_candidate_stays_candidate():
    s = next_state("candidate", seen_now=True, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG,
                   revive_to_candidate=True, court_blocked=True)
    assert s == "candidate"


def test_next_state_v2b_court_cleared_revived_candidate_promotes():
    s = next_state("candidate", seen_now=True, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG,
                   revive_to_candidate=True, court_blocked=False)
    assert s == "active"


def test_next_state_regime_off_is_byte_identical():
    # flag off -> the historical behavior, including the direct resurrect
    s = next_state("retired", seen_now=True, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=0, cfg=CFG)
    assert s == "active"


def test_next_state_v2b_fresh_candidates_unaffected_by_court():
    # a NEVER-revived candidate (court_blocked defaults False) promotes
    # mechanically exactly as today — the court gate scopes to revived stock.
    s = next_state("candidate", seen_now=True, n_snapshots=2, mean_cohesion=0.8,
                   agg_n_signals=100, is_roundup=False, since_seen=0, cfg=CFG,
                   revive_to_candidate=True)
    assert s == "active"


def test_next_state_v2b_aging_unchanged():
    # not-seen aging is untouched by the regime
    s = next_state("active", seen_now=False, n_snapshots=50, mean_cohesion=0.9,
                   agg_n_signals=500, is_roundup=False, since_seen=2, cfg=CFG,
                   revive_to_candidate=True)
    assert s == "deprecated"


def test_advance_states_v2b_marks_revival_and_blocks_until_entailed():
    from scripts.project_dynamic_topics import advance_states, Topic
    t = Topic(identity_key="k1", label="Old Story", centroid=[1.0, 0.0],
              snap="2026-07-01T00:00:00", n_signals=500, cohesion=0.9)
    t.state = "retired"
    t.since_seen = 10
    t.snapshots = {f"s{i}" for i in range(50)}
    # pass 1: revival lands candidate + marked, never active
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "candidate"
    assert t.newly_revived is True
    # pass 2 (same in-memory run shape): still blocked — court has not entailed
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "candidate"
    # court certifies -> next seen pass promotes
    t.label_status = "entailed"
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "active"


def test_advance_states_legacy_regime_still_resurrects_direct():
    from scripts.project_dynamic_topics import advance_states, Topic
    t = Topic(identity_key="k2", label="Old Story", centroid=[1.0, 0.0],
              snap="2026-07-01T00:00:00", n_signals=500, cohesion=0.9)
    t.state = "retired"
    t.snapshots = {f"s{i}" for i in range(50)}
    advance_states([t], {0}, CFG)  # regime off
    assert t.state == "active"
    assert t.newly_revived is False


# ── Blob veto (2026-08-03 gate-(c) census) ───────────────────────────────────
# The census measured the court's `entailed` stamp at ~70% precision as a
# serving certificate: 28 judge-confirmable blob topics were certified AND
# promoted, and the nightly overmerge sweep missed all 28. detect_overmerge now
# stamps dynamic_topics.blob_confirmed_at on judge-confirmed fusions; promotion
# is vetoed while the stamp is FRESH (<7d), composed OR with the TF-3b court
# gate. A stale stamp (the sweep stopped re-confirming — membership re-formed)
# must NOT block: the horizon keeps the veto evidence-bound.

def _qualifying_candidate(stamp=None):
    t = Topic(identity_key="kb", label="Confirmed Fusion", centroid=[1.0, 0.0],
              snap="2026-07-01T00:00:00", n_signals=500, cohesion=0.9)
    t.state = "candidate"
    t.snapshots = {f"s{i}" for i in range(50)}
    t.blob_confirmed_at = stamp
    return t


def test_blob_confirmed_fresh_horizon():
    from datetime import datetime, timedelta, timezone

    from scripts.project_dynamic_topics import blob_confirmed_fresh
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    assert blob_confirmed_fresh(None, now=now) is False
    assert blob_confirmed_fresh(now - timedelta(days=1), now=now) is True
    assert blob_confirmed_fresh(now - timedelta(days=6, hours=23), now=now) is True
    assert blob_confirmed_fresh(now - timedelta(days=7), now=now) is False
    assert blob_confirmed_fresh(now - timedelta(days=30), now=now) is False


def test_advance_states_blob_fresh_stamp_blocks_promotion():
    from datetime import datetime, timedelta, timezone

    from scripts.project_dynamic_topics import advance_states
    t = _qualifying_candidate(datetime.now(timezone.utc) - timedelta(days=1))
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "candidate"


def test_advance_states_blob_stale_stamp_promotes():
    from datetime import datetime, timedelta, timezone

    from scripts.project_dynamic_topics import advance_states
    t = _qualifying_candidate(datetime.now(timezone.utc) - timedelta(days=8))
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "active"


def test_advance_states_blob_clear_promotes():
    from scripts.project_dynamic_topics import advance_states
    t = _qualifying_candidate(None)
    advance_states([t], {0}, CFG, revive_to_candidate=True)
    assert t.state == "active"


def test_advance_states_legacy_regime_ignores_blob_stamp():
    # ATLAS_LIFECYCLE_TICK_V2 off = byte-identical legacy: the veto rides ONLY
    # the v2 clock (same scoping as the TF-3b court gate).
    from datetime import datetime, timedelta, timezone

    from scripts.project_dynamic_topics import advance_states
    t = _qualifying_candidate(datetime.now(timezone.utc) - timedelta(days=1))
    advance_states([t], {0}, CFG)  # regime off
    assert t.state == "active"


def test_regrade_blob_fresh_stamp_blocks_promotion():
    # --regrade parity (the TF-3b review lesson): a manual regrade must not
    # bypass the blob veto any more than the court gate.
    from datetime import datetime, timedelta, timezone

    from scripts.project_dynamic_topics import regrade_states
    fresh = _qualifying_candidate(datetime.now(timezone.utc) - timedelta(days=1))
    stale = _qualifying_candidate(datetime.now(timezone.utc) - timedelta(days=8))
    promoted, demoted = regrade_states([fresh, stale], CFG)
    assert fresh.state == "candidate"
    assert stale.state == "active"
    assert (promoted, demoted) == (1, 0)
