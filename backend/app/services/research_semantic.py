"""Semantic retrieval lane for research plans (Phase 1.5a, e5-base).

Query↔thread similarity against persisted `dynamic_topics.centroid_vec`
(768-dim running-mean `intfloat/multilingual-e5-base` centroids, written by
the local snapshot/lifecycle cron). The model is multilingual, so a Spanish
query can match a thread whose member headlines were Persian/Arabic/English —
this lane is the cross-language recall fix (spec Phase 1.5).

Deployment honesty (spec amendment territory):
- The embedding model runs where `sentence-transformers` is installed (the M1
  worker / local dev). The Fly API box does not ship torch; there the embedder
  is unavailable and the lane degrades to a visible coverage gap
  (`lane_unavailable`), following the Phase 1a degraded-lane pattern. Fly
  enablement (ONNX int8) and the persisted per-signal embedding store needed
  for full-corpus semantic retrieval are Phase 1.5b (own issue).
- Scope here is query↔thread. Query↔evidence over the full deduped corpus
  requires signal-level embeddings that are not persisted anywhere today.

Pure-ish: embedding + DB access are injected; cosine and candidate selection
are pure functions.
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any

logger = logging.getLogger(__name__)

EMBED_MODEL = "intfloat/multilingual-e5-base"

# e5 cosine similarities are compressed into a high band. The two match bases
# have different distributions (measured live 2026-06-10): member-headline
# centroids run hot (related ~0.80-0.95), topic label/description anchors run
# cooler (correct topic 0.80 vs off-topic floor ~0.71-0.75). Thresholds are
# per-basis; see tests/test_research_semantic.py::test_cross_language_real_model.
SEMANTIC_MIN_SIMILARITY = 0.80      # centroid basis: below = not a candidate
SEMANTIC_CONTEXT_SIMILARITY = 0.86  # centroid basis: above = context
ATLAS_MIN_SIMILARITY = 0.765        # description basis: below = not a candidate
ATLAS_CONTEXT_SIMILARITY = 0.79     # description basis: above = context
# Description-basis discrimination is weak (live spread for one query:
# correct topic 0.797, unrelated topics 0.769-0.783). A relative cut keeps
# only candidates close to the best match instead of everything over a floor.
ATLAS_TOP_MARGIN = 0.012
SEMANTIC_LANE_LIMIT = 8

_embed_fn = None  # lazy singleton; never loaded unless the lane is used


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def embedder_available() -> bool:
    if os.getenv("RESEARCH_SEMANTIC_DISABLED"):
        return False
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _build_embed_fn():
    """Same embedding path as the snapshot pipeline (scripts/emergent_poc.py
    `_build_embedder`): raw transformers, attention-mask mean pooling, L2
    normalize, max_length 96. MUST stay identical — query vectors are only
    comparable to `dynamic_topics.centroid_vec` if pooling matches."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    model = AutoModel.from_pretrained(EMBED_MODEL)
    model.eval()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    @torch.no_grad()
    def embed(texts: list[str]) -> list[list[float]]:
        enc = tok(texts, padding=True, truncation=True, max_length=96,
                  return_tensors="pt").to(device)
        hs = model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1).float()
        pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return [[float(x) for x in row] for row in pooled.cpu()]

    return embed


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed pre-prefixed texts ('query: ...' / 'passage: ...'). Returns None
    when the model stack is unavailable (Fly API box) — callers must treat
    None as a degraded lane, never an error."""
    global _embed_fn
    if not embedder_available():
        return None
    try:
        if _embed_fn is None:
            _embed_fn = _build_embed_fn()
        return _embed_fn(texts)
    except Exception as exc:
        logger.warning("semantic embed failed: %s", exc)
        return None


def embed_query(text: str) -> list[float] | None:
    vecs = embed_texts([f"query: {text}"])
    return vecs[0] if vecs else None


async def fetch_topic_centroids(conn: Any) -> list[dict[str, Any]]:
    """Active, non-roundup dynamic topics with centroids. Roundups are
    excluded per the do_not_promote_roundup guardrail — a grab-bag thread
    matching everything semantically is noise, not recall."""
    rows = await conn.fetch(
        """
        SELECT id, label, centroid_vec, agg_n_signals, last_seen
        FROM dynamic_topics
        WHERE state = 'active'
          AND is_roundup = FALSE
          AND centroid_vec IS NOT NULL
        ORDER BY last_seen DESC
        LIMIT 100
        """
    )
    return [
        {
            "topic_id": int(r["id"]),
            "label": r["label"],
            "centroid_vec": [float(x) for x in r["centroid_vec"]],
            "n_signals": int(r["agg_n_signals"] or 0),
        }
        for r in rows
    ]


def semantic_topic_candidates(
    query_vec: list[float],
    topics: list[dict[str, Any]],
    *,
    min_similarity: float = SEMANTIC_MIN_SIMILARITY,
    limit: int = SEMANTIC_LANE_LIMIT,
) -> list[dict[str, Any]]:
    """Pure ranking of topic centroids by cosine to the query vector."""
    scored = []
    for topic in topics:
        sim = cosine(query_vec, topic.get("centroid_vec") or [])
        if sim >= min_similarity:
            scored.append({
                "topic_id": topic["topic_id"],
                "label": topic["label"],
                "similarity": round(sim, 4),
                "n_signals": topic.get("n_signals", 0),
            })
    scored.sort(key=lambda c: c["similarity"], reverse=True)
    return scored[:limit]


def semantic_evidence_label(similarity: float, *, basis: str = "member_centroid") -> str:
    threshold = (ATLAS_CONTEXT_SIMILARITY if basis == "topic_description"
                 else SEMANTIC_CONTEXT_SIMILARITY)
    return "context" if similarity >= threshold else "weak_support"


# ── Atlas-topic anchor basis ─────────────────────────────────────────────────
# Atlas topics (the internal anchor taxonomy) have no member centroids, but
# their label+description embed well enough for cross-language query matching
# (Spanish query → English topic description, measured top-1 correct live).
# IMPORTANT: this is taxonomy similarity, NOT evidence — anchors built from it
# carry match_basis="topic_description" so the UI never presents it as found
# evidence (spec Product Principle).

_atlas_cache: dict[str, Any] = {"embedded": None, "loaded_at": 0.0}
_ATLAS_CACHE_TTL_SECONDS = 3600.0


async def fetch_atlas_topic_anchors(conn: Any) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT slug, label, description FROM atlas_topics WHERE is_active"
    )
    return [
        {"slug": r["slug"], "label": r["label"], "description": r["description"] or ""}
        for r in rows
    ]


def embed_atlas_anchors(topics: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Embed topic anchor texts; cached per process (taxonomy changes rarely)."""
    import time
    now = time.monotonic()
    cached = _atlas_cache["embedded"]
    if cached is not None and now - _atlas_cache["loaded_at"] < _ATLAS_CACHE_TTL_SECONDS:
        return cached
    vecs = embed_texts([f"passage: {t['label']}. {t['description']}" for t in topics])
    if vecs is None:
        return None
    embedded = [{**t, "anchor_vec": v} for t, v in zip(topics, vecs)]
    _atlas_cache["embedded"] = embedded
    _atlas_cache["loaded_at"] = now
    return embedded


def semantic_atlas_candidates(
    query_vec: list[float],
    embedded_topics: list[dict[str, Any]],
    *,
    min_similarity: float = ATLAS_MIN_SIMILARITY,
    limit: int = SEMANTIC_LANE_LIMIT,
) -> list[dict[str, Any]]:
    scored = []
    for topic in embedded_topics:
        sim = cosine(query_vec, topic.get("anchor_vec") or [])
        if sim >= min_similarity:
            scored.append({
                "slug": topic["slug"],
                "label": topic["label"],
                "similarity": round(sim, 4),
            })
    scored.sort(key=lambda c: c["similarity"], reverse=True)
    if scored:  # relative cut: only candidates near the best match survive
        top = scored[0]["similarity"]
        scored = [c for c in scored if c["similarity"] >= top - ATLAS_TOP_MARGIN]
    return scored[:limit]
