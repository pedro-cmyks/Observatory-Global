"""Phase 1.5a — semantic lane (query↔thread over e5 centroids).

Spec acceptance:
- A query with no lexical match surfaces related anchors labeled
  retrieval_lane=semantic.
- Cross-language: Spanish query matches a thread built from Persian/English
  headlines (real-model test, skipped where sentence-transformers is absent —
  run it on the M1: `.venv` may lack torch; use mlvenv or install locally).
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
    assert anchor["id"] == "water-stress-drought--ir"  # country-scoped thread id
    assert anchor["open"]["params"]["country_code"] == "IR"
    assert not any("sports" in a["id"] for a in semantic)


def _torch_available() -> bool:
    import importlib.util
    return bool(importlib.util.find_spec("torch")
                and importlib.util.find_spec("transformers"))


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
