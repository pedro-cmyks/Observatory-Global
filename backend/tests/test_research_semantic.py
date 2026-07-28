"""Phase 1.5a — semantic lane (query↔thread over e5 centroids).

Spec acceptance:
- A query with no lexical match surfaces related anchors labeled
  retrieval_lane=semantic.
- Cross-language: Spanish query matches a thread built from Persian/English
  headlines (real-model test, marked `integration` — needs --run-integration
  plus torch/transformers; run it on the M1 with mlvenv).
- Deployments without the embedder degrade to a visible coverage gap.
"""
from __future__ import annotations

import asyncio
import math

import pytest

from app.services.research_anchor_discovery import discover_anchors
from app.services.research_plan import parse_research_intent
from app.services.research_ranking import rank_plan, score_anchor
from app.services.research_semantic import (
    SEMANTIC_CONTEXT_SIMILARITY,
    SEMANTIC_MIN_SIMILARITY,
    cosine,
    semantic_evidence_label,
    semantic_topic_candidates,
)


def _unit(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


# Synthetic 4-dim centroids: water topic near the query, sports far.
QUERY_VEC = _unit([1.0, 0.2, 0.0, 0.0])
TOPICS = [
    {"topic_id": 10, "label": "Water stress and drought in Iran",
     "centroid_vec": _unit([0.95, 0.25, 0.05, 0.0]), "n_signals": 210},
    {"topic_id": 11, "label": "Regional sports roundup",
     "centroid_vec": _unit([0.0, 0.1, 1.0, 0.3]), "n_signals": 500},
    {"topic_id": 12, "label": "Gulf energy infrastructure strain",
     "centroid_vec": _unit([0.85, 0.2, 0.3, 0.1]), "n_signals": 90},
]


def test_cosine_basics():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([], [1.0]) == 0.0
    assert cosine([1, 0], [1, 0, 0]) == 0.0  # dim mismatch -> no match, no crash


def test_candidates_filtered_and_sorted():
    cands = semantic_topic_candidates(QUERY_VEC, TOPICS, min_similarity=0.8)
    ids = [c["topic_id"] for c in cands]
    assert 10 in ids and 11 not in ids
    sims = [c["similarity"] for c in cands]
    assert sims == sorted(sims, reverse=True)


def test_evidence_label_thresholds():
    assert semantic_evidence_label(SEMANTIC_CONTEXT_SIMILARITY + 0.01) == "context"
    assert semantic_evidence_label(SEMANTIC_MIN_SIMILARITY + 0.01) == "weak_support"


def _discover(embed_result, topics=TOPICS):
    intent = parse_research_intent("Iran climate water drought")

    async def no_threads(**kwargs):
        return []

    async def centroids():
        return topics

    def embed(_text):
        return embed_result

    return asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=embed,
        fetch_centroids_fn=centroids,
    ))


def test_semantic_anchors_added_with_lane_label():
    plan = _discover(QUERY_VEC)
    semantic = [a for a in plan["anchors"] if a.get("retrieval_lane") == "semantic"]
    assert semantic, "expected semantic anchors"
    assert all(a["lane"] == "semantic" for a in semantic)
    assert all("semantic_similarity" in a for a in semantic)
    assert all(a["evidence_label"] == "weak_support" for a in semantic)
    assert not any(a["id"] == "dynamic-topic-11" for a in semantic)  # sports filtered by sim
    # openable contract preserved
    assert all(a["open"]["surface"] == "thread_detail" for a in semantic)


def test_missing_embedder_yields_visible_gap_not_error():
    plan = _discover(None)
    gaps = [g for g in plan["coverage_gaps"] if g.get("lane") == "semantic"]
    assert gaps and gaps[0]["gap_type"] == "lane_unavailable"
    assert not [a for a in plan["anchors"] if a.get("retrieval_lane") == "semantic"]


def test_ranking_reads_similarity_as_intent_match():
    intent = parse_research_intent("Iran climate water drought")
    anchor = {
        "anchor_type": "thread", "id": "dynamic-topic-10",
        "label": "Water stress", "evidence_label": "context",
        "matched_terms": [], "semantic_similarity": 0.91,
        "signal_count": 50, "source_count": 5,
        "open": {"surface": "thread_detail", "params": {}},
    }
    explanation = score_anchor(anchor, intent)
    # 0.91 -> scaled (0.91-0.75)/0.20 = 0.8 > context floor 0.6
    assert explanation["score_components"]["intent_match"] >= 0.8
    assert "semantic_match" in explanation["reason_codes"]


def test_ranked_plan_keeps_semantic_anchor_visible():
    plan = rank_plan(_discover(QUERY_VEC))
    everything = plan["anchors"] + plan["low_confidence_tray"]
    assert any(a.get("retrieval_lane") == "semantic" for a in everything)


def test_atlas_anchor_basis_builds_country_scoped_thread_anchor():
    intent = parse_research_intent("rain theft Iran")  # geo IR, sparse lexical

    async def no_threads(**kwargs):
        return []

    async def centroids():
        return []  # no dynamic-topic centroids match

    async def atlas_anchors():
        return [
            {"slug": "water-stress-drought", "label": "Water stress and drought",
             "anchor_vec": _unit([1.0, 0.2, 0.0, 0.0])},
            {"slug": "sports-roundup", "label": "Sports roundup",
             "anchor_vec": _unit([0.0, 0.1, 1.0, 0.3])},
        ]

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _t: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_atlas_anchors_fn=atlas_anchors,
    ))
    semantic = [a for a in plan["anchors"] if a.get("retrieval_lane") == "semantic"]
    assert semantic, "expected atlas-basis semantic anchor"
    anchor = semantic[0]
    assert anchor["match_basis"] == "topic_description"
    assert anchor["evidence_label"] == "weak_support"
    assert anchor["id"] == "water-stress-drought--ir"  # country-scoped thread id
    assert anchor["open"]["params"]["country_code"] == "IR"
    assert not any("sports" in a["id"] for a in semantic)


def _torch_available() -> bool:
    import importlib.util
    return bool(importlib.util.find_spec("torch")
                and importlib.util.find_spec("transformers"))


# `integration` (conftest: skipped unless --run-integration) is load-bearing, not
# decoration. A torch/transformers PRESENCE check is not a sufficient gate on its
# own: `import transformers` runs importlib.metadata.packages_distributions() at
# import time, which reads the file RECORD of every installed distribution —
# measured here at 141.7s wall for 0.5s of CPU. So once torch landed in `.venv`
# this test silently flipped from "skipped" to "hangs the whole run", which is why
# `pytest tests/` could not be run over the directory.
@pytest.mark.integration
@pytest.mark.skipif(not _torch_available(),
                    reason="torch/transformers not installed in this venv "
                           "(run via mlvenv on the M1)")
def test_cross_language_real_model():
    """Spec acceptance: Spanish query ↔ Persian/English thread headlines.

    Uses the production embed path (`embed_texts`, identical pooling to the
    snapshot pipeline) and asserts the Spanish query clears the candidate
    threshold while an off-topic sports centroid does not.
    """
    from app.services.research_semantic import embed_query, embed_texts

    water_headlines = [
        "passage: بحران آب در ایران؛ سدها و جیره‌بندی آب در تهران",  # Persian: water crisis, dams, rationing
        "passage: Iran faces severe drought as reservoirs reach record lows",
        "passage: کاهش بارندگی و خشکسالی در فلات ایران",  # Persian: reduced rainfall and drought
    ]
    sports_headlines = [
        "passage: Champions League quarter final preview and predictions",
        "passage: نتایج هفته بیستم لیگ برتر فوتبال",  # Persian: football league results
    ]

    def centroid(texts):
        vecs = embed_texts(texts)
        assert vecs is not None
        return [sum(col) / len(vecs) for col in zip(*vecs)]

    topics = [
        {"topic_id": 1, "label": "Iran water crisis", "centroid_vec": centroid(water_headlines), "n_signals": 30},
        {"topic_id": 2, "label": "Football roundup", "centroid_vec": centroid(sports_headlines), "n_signals": 99},
    ]

    query_vec = embed_query("sequía y escasez de agua en Irán")
    assert query_vec is not None

    cands = semantic_topic_candidates(query_vec, topics)
    ids = [c["topic_id"] for c in cands]
    assert 1 in ids, f"cross-language match failed: {cands}"
    water_sim = next(c["similarity"] for c in cands if c["topic_id"] == 1)
    sports_sim = cosine(query_vec, topics[1]["centroid_vec"])
    assert water_sim > sports_sim + 0.03, (water_sim, sports_sim)


def test_signal_evidence_basis_labels_gate_status():
    """#223 deliverable 2: full-corpus matches are evidence items labeled
    with retrieval lane + gate status — reachable, never volunteered."""
    intent = parse_research_intent("rain theft Iran")

    async def no_threads(**kwargs):
        return []

    async def centroids():
        return []

    async def signal_matches(*, query_vec, hours):
        return [
            {"signal_id": 1, "headline": "Tehran reservoirs at record lows",
             "country_code": "IR", "source_name": "x", "timestamp": None,
             "similarity": 0.88, "gate_status": "below_gate"},
            {"signal_id": 2, "headline": "Iran drought breaks after rains",
             "country_code": "IR", "source_name": "y", "timestamp": None,
             "similarity": 0.85, "gate_status": "assigned"},
        ]

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _t: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_signal_matches_fn=signal_matches,
    ))

    evidence = plan["semantic_evidence"]
    assert len(evidence) == 2
    assert all(e["retrieval_lane"] == "semantic" for e in evidence)
    assert all(e["match_basis"] == "signal_headline" for e in evidence)
    # below-gate material is present AND labeled — the funnel rule
    assert any(e["gate_status"] == "below_gate" for e in evidence)


def test_signal_timeout_preserves_centroid_anchors_and_names_component_gap():
    async def no_threads(**kwargs):
        return []

    async def centroids():
        return TOPICS

    async def broken_signals(**kwargs):
        raise TimeoutError("ANN timeout")

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_signal_matches_fn=broken_signals,
    ))

    assert any(
        anchor.get("match_basis") == "member_centroid"
        for anchor in plan["anchors"]
    )
    assert any(
        gap.get("component") == "signal_headline"
        for gap in plan["coverage_gaps"]
    )


def test_centroid_timeout_preserves_atlas_and_signal_results():
    async def no_threads(**kwargs):
        return []

    async def broken_centroids():
        raise TimeoutError("centroid timeout")

    async def atlas_anchors():
        return [{
            "slug": "water-stress-drought",
            "label": "Water stress and drought",
            "anchor_vec": QUERY_VEC,
        }]

    async def signal_matches(**kwargs):
        return [{
            "signal_id": 7,
            "headline": "Iran reservoirs fall further",
            "similarity": 0.9,
            "gate_status": "assigned",
        }]

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=broken_centroids,
        fetch_atlas_anchors_fn=atlas_anchors,
        fetch_signal_matches_fn=signal_matches,
        substrate_min_centroids=80,
    ))

    assert any(
        anchor.get("match_basis") == "topic_description"
        for anchor in plan["anchors"]
    )
    assert plan["semantic_evidence"][0]["signal_id"] == 7
    centroid_gaps = [
        gap for gap in plan["coverage_gaps"]
        if gap.get("component") == "story_centroid"
    ]
    assert len(centroid_gaps) == 1
    assert "unavailable" in centroid_gaps[0]["note"].lower()


def test_atlas_timeout_preserves_centroid_and_signal_results():
    async def no_threads(**kwargs):
        return []

    async def centroids():
        return TOPICS

    async def broken_atlas():
        raise TimeoutError("atlas anchor timeout")

    async def signal_matches(**kwargs):
        return [{
            "signal_id": 8,
            "headline": "Iran drought pressure expands",
            "similarity": 0.89,
            "gate_status": "below_gate",
        }]

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_atlas_anchors_fn=broken_atlas,
        fetch_signal_matches_fn=signal_matches,
    ))

    assert any(
        anchor.get("match_basis") == "member_centroid"
        for anchor in plan["anchors"]
    )
    assert plan["semantic_evidence"][0]["signal_id"] == 8
    assert any(
        gap.get("component") == "topic_description"
        for gap in plan["coverage_gaps"]
    )


def test_signal_evidence_absent_without_embedder():
    intent = parse_research_intent("rain theft Iran")

    async def no_threads(**kwargs):
        return []

    plan = asyncio.run(discover_anchors(
        intent, hours=72,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _t: None,
        fetch_centroids_fn=lambda: None,  # never reached
        fetch_signal_matches_fn=lambda **k: None,  # never reached
    ))
    assert plan["semantic_evidence"] == []
    assert any(g.get("lane") == "semantic" for g in plan["coverage_gaps"])


def test_junk_headlines_filtered_and_deduped():
    """#223 remainder: malformed scraped titles never surface as evidence,
    and syndicated duplicate headlines collapse to one item."""
    from app.services.research_semantic import is_junk_headline
    assert is_junk_headline("Doc Iniaztwk5508793.Shtml")
    assert is_junk_headline("index.html")
    assert is_junk_headline("Untitled")
    assert is_junk_headline("12345 67890")  # no real words
    assert not is_junk_headline("Iran faces severe drought as reservoirs reach lows")
    assert not is_junk_headline("El dron ruso que golpeó a Rumania")
    # number-spelling bot template (Bluesky spam, 2026-07-04)
    assert is_junk_headline(
        "Digit: 5,250,037\nIn words: Five Million Two Hundred Fifty Thousand "
        "Thirty Seven\nअङ्कः ५२,५०,०३७"
    )
    assert is_junk_headline("In words: Twenty One Thousand and Five")
    # real headlines using those words stay
    assert not is_junk_headline("Minister explains the deal in words voters understand")
    assert not is_junk_headline("Digital economy grows five percent this year")


# ── W2b two-tier gate labels (L3 review 2026-07-05) ──────────────────────────

def test_gate_tier_for_two_tier_contract(monkeypatch):
    from app.services import research_semantic as rs
    monkeypatch.setattr(rs, "_EXT_THRESHOLDS", ({"election-legitimacy": 0.95}, 0.9))

    assert rs.gate_tier_for(True, 0.99, "election-legitimacy") == "verified"
    # clears the per-topic ~75%-precision threshold → extended
    assert rs.gate_tier_for(False, 0.96, "election-legitimacy") == "extended"
    # assigned but below both tiers
    assert rs.gate_tier_for(False, 0.50, "election-legitimacy") == "assigned"
    # unknown topic falls back to the global threshold
    assert rs.gate_tier_for(False, 0.92, "some-new-topic") == "extended"
    # no assignment at all
    assert rs.gate_tier_for(None, None, None) == "below_gate"


# ── Centroid substrate: the whole field, and a guard that can actually fire ──
# Both defects measured 2026-07-27/28 (docs/research/gold/2026-07-27-semantic-
# search-feasibility.md).


class _RecordingConn:
    """Minimal asyncpg stand-in that remembers the SQL it was handed."""

    def __init__(self, rows=None, value=None):
        self.rows = rows or []
        self.value = value
        self.queries: list[str] = []
        self.statements: list[str] = []

    async def fetch(self, query, *args, **kwargs):
        self.queries.append(query)
        return self.rows

    async def fetchval(self, query, *args, **kwargs):
        self.queries.append(query)
        return self.value

    async def execute(self, statement):
        self.statements.append(statement)


def test_centroid_fetch_does_not_slice_the_field_by_a_batch_stamp():
    """`last_seen` is a nightly BATCH stamp — measured on prod 2026-07-28,
    1,144 of 1,165 pool rows share one value (2,714/2,719 on 07-27). Ordering
    by it and taking 100 served a planner-arbitrary 3.7-8.6% of the field."""
    from app.services.research_semantic import (
        CENTROID_POOL_SCAN_CAP,
        fetch_topic_centroids,
    )

    conn = _RecordingConn(rows=[
        {"id": 5, "label": "Water stress", "centroid_vec": [0.1, 0.2],
         "agg_n_signals": 40},
    ])
    out = asyncio.run(fetch_topic_centroids(conn))

    sql = conn.queries[0]
    # NULLS LAST matters: DESC defaults to NULLS FIRST, which would rank
    # volume-unknown topics above every real one if the cap ever bound.
    assert "ORDER BY agg_n_signals DESC NULLS LAST, id DESC" in sql
    assert "last_seen" not in sql          # the batch stamp never orders again
    assert "LIMIT 100" not in sql
    # the cap is a blast-radius bound, set far above every measured pool
    assert CENTROID_POOL_SCAN_CAP >= 5000
    assert f"LIMIT {CENTROID_POOL_SCAN_CAP}" in sql
    assert out[0]["topic_id"] == 5 and out[0]["n_signals"] == 40


def test_pool_size_count_shares_the_scoring_query_predicate():
    """A health number measured over a different population is not a health
    number. Same WHERE, verbatim, or the guard is measuring something else."""
    from app.services.research_semantic import (
        _ACTIVE_CENTROID_WHERE,
        fetch_active_centroid_pool_size,
        fetch_topic_centroids,
    )

    count_conn = _RecordingConn(value=1165)
    total = asyncio.run(fetch_active_centroid_pool_size(count_conn))
    assert total == 1165

    rows_conn = _RecordingConn(rows=[])
    asyncio.run(fetch_topic_centroids(rows_conn))

    assert _ACTIVE_CENTROID_WHERE.strip() in count_conn.queries[0]
    assert _ACTIVE_CENTROID_WHERE.strip() in rows_conn.queries[0]
    assert "count(*)" in count_conn.queries[0]

    # no pool at all reads as zero, never as "healthy"
    assert asyncio.run(fetch_active_centroid_pool_size(_RecordingConn(value=None))) == 0


def test_substrate_guard_fires_on_the_true_pool_not_the_returned_slice():
    """The bug: the guard compared len(topics) while the fetch capped the list,
    so `100 < 80` was false by construction and a collapsed pool always
    reported healthy. Here the lane is handed MORE topics than the floor while
    the real substrate is below it — the guard must still fire."""
    async def no_threads(**kwargs):
        return []

    many_topics = [
        {"topic_id": i, "label": f"topic {i}",
         "centroid_vec": QUERY_VEC, "n_signals": 10}
        for i in range(120)          # > the 80 floor, as the old LIMIT allowed
    ]

    async def centroids():
        return many_topics

    async def true_pool_size():
        return 12                    # the substrate that actually exists

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_centroid_pool_size_fn=true_pool_size,
        substrate_min_centroids=80,
    ))

    thin = [g for g in plan["coverage_gaps"] if g.get("component") == "story_centroid"]
    assert len(thin) == 1
    assert thin[0]["centroid_pool_size"] == 12      # the pool, not the slice
    assert "12 active" in thin[0]["note"]
    assert "120" not in thin[0]["note"]
    # and the noisy centroid anchors are actually suppressed
    assert not any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])


def test_substrate_guard_stays_quiet_when_the_true_pool_is_healthy():
    """Mirror case: a capped/short returned list must NOT be read as a thin
    substrate now that the count is authoritative."""
    async def no_threads(**kwargs):
        return []

    async def centroids():
        return TOPICS                # only 3 rows returned

    async def true_pool_size():
        return 1165                  # prod pool, 2026-07-28

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_centroid_pool_size_fn=true_pool_size,
        substrate_min_centroids=80,
    ))

    assert not any(
        g.get("component") == "story_centroid" for g in plan["coverage_gaps"]
    )
    assert any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])


def test_pool_size_lookup_failure_is_itself_visible():
    async def no_threads(**kwargs):
        return []

    async def centroids():
        return TOPICS

    async def broken_pool_size():
        raise TimeoutError("count timed out")

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_centroid_pool_size_fn=broken_pool_size,
        substrate_min_centroids=80,
    ))

    assert any(
        g.get("component") == "story_centroid_pool_size"
        for g in plan["coverage_gaps"]
    )


# ── Signal lane: a timeout must never look like an empty corpus ─────────────


def test_ann_timeout_raises_a_named_degradation_not_an_empty_list():
    """probes=20 measured >100s under nightly load against a 6s budget. The
    old path let that surface as `[]`, which reads as 'the corpus holds
    nothing' — the one thing it does not mean."""
    from app.services.research_semantic import (
        SemanticSignalLaneTimeout,
        fetch_semantic_signal_matches,
    )

    class TimingOutConn(_RecordingConn):
        async def fetch(self, query, *args, **kwargs):
            raise asyncio.TimeoutError()

    conn = TimingOutConn()
    with pytest.raises(SemanticSignalLaneTimeout) as excinfo:
        asyncio.run(fetch_semantic_signal_matches(conn, QUERY_VEC, hours=24))

    assert excinfo.value.degraded_reason == "ann_timeout"
    # still a TimeoutError, so every existing degrade path keeps catching it
    assert isinstance(excinfo.value, TimeoutError)
    assert conn.statements == ["SET ivfflat.probes = 10"]


def test_timed_out_signal_lane_surfaces_a_degraded_marker_in_the_plan():
    from app.services.research_semantic import SemanticSignalLaneTimeout

    async def no_threads(**kwargs):
        return []

    async def centroids():
        return TOPICS

    async def timed_out_signals(**kwargs):
        raise SemanticSignalLaneTimeout("signal ANN lane exceeded 6s")

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"),
        hours=24,
        fetch_threads_fn=no_threads,
        fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_signal_matches_fn=timed_out_signals,
    ))

    assert plan["semantic_evidence"] == []
    gaps = [g for g in plan["coverage_gaps"] if g.get("component") == "signal_headline"]
    assert len(gaps) == 1
    assert gaps[0]["degraded_reason"] == "ann_timeout"
    assert "not a measured absence" in gaps[0]["note"]
    # the empty is reachable as a gap anchor, not just buried in the payload
    assert any(
        a["evidence_label"] == "gap" and "ann_timeout" in a["label"]
        for a in plan["anchors"]
    )
    # sibling bases are untouched by one lane's failure
    assert any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])


def test_unnamed_lane_failures_keep_the_original_gap_wording():
    """Regression guard: only failures that KNOW why they failed get the
    stronger wording; everything else still reports the exception class."""
    from app.services.research_anchor_discovery import _semantic_component_gap

    gap = _semantic_component_gap("signal_headline", ValueError("boom"))
    assert gap["degraded_reason"] == "ValueError"
    assert gap["note"] == "Semantic signal headline unavailable (ValueError)."
