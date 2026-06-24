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


def _embed_remote(texts: list[str]) -> list[list[float]] | None:
    """Embed via the internal embed service (nlp_worker hosts the model on
    Fly — see enrichment/embed_service.py). Private 6PN URL via
    EMBED_SERVICE_URL; returns None on any failure (lane degrades)."""
    base = os.getenv("EMBED_SERVICE_URL")
    if not base:
        return None
    import json
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{base.rstrip('/')}/embed",
            data=json.dumps({"texts": texts}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # 30s default: the atlas-anchor batch (~30 texts) takes >10s on Fly
        # shared CPU; on success the caller caches it per process, so the
        # cost is paid once per deploy, not per request.
        timeout = float(os.getenv("EMBED_SERVICE_TIMEOUT_SECONDS", "30"))
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = json.loads(res.read())
        vectors = payload.get("vectors")
        return vectors if isinstance(vectors, list) and vectors else None
    except Exception as exc:
        logger.warning("remote embed failed: %s", exc)
        return None


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed pre-prefixed texts ('query: ...' / 'passage: ...').

    Provider chain: local torch (M1 dev / nlp_worker) → internal embed
    service (Fly api box with EMBED_SERVICE_URL set) → None. Callers must
    treat None as a degraded lane, never an error."""
    global _embed_fn
    if embedder_available():
        try:
            if _embed_fn is None:
                _embed_fn = _build_embed_fn()
            return _embed_fn(texts)
        except Exception as exc:
            logger.warning("semantic embed failed: %s", exc)
            return None
    return _embed_remote(texts)


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


# ── Signal-headline basis (full-corpus retrieval, #223 deliverable 2) ───────
# pgvector ANN over signal_embeddings (halfvec/768, migration 054). Every hit
# carries its gate status so below-gate material is query-reachable but
# labeled (Pipeline Funnel Principle). Distances: cosine distance = 1 - sim.

# Re-measured 2026-06-11 on the ~100K-embedding corpus: relevant-query tops
# sit at 0.84-0.86 (genuine on-topic matches); the 0.82 floor admitted
# malformed-headline junk ("Doc Inia*.Shtml" at 0.822) and weak
# same-language affinity. 0.84 cuts the junk band while keeping the
# measured relevant cluster.
SIGNAL_MIN_SIMILARITY = 0.84
SIGNAL_LANE_LIMIT = 12

# Malformed scraped titles pollute the embedding corpus and match anything
# ("Doc Iniaztwk5508793.Shtml"). Filter at write AND query time.
import re as _re
_JUNK_HEADLINE = _re.compile(r"\.s?html?|^doc\s|^untitled", _re.IGNORECASE)


def is_junk_headline(headline: str | None) -> bool:
    if not headline:
        return True
    if _JUNK_HEADLINE.search(headline):
        return True
    words = [w for w in headline.split() if any(c.isalpha() for c in w)]
    return len(words) < 3  # needs at least three real words to be a headline


async def fetch_semantic_signal_matches(
    conn: Any,
    query_vec: list[float],
    *,
    hours: int,
    limit: int = SIGNAL_LANE_LIMIT,
    min_similarity: float = SIGNAL_MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    vec_literal = "[" + ",".join(f"{x:.5f}" for x in query_vec) + "]"
    rows = await conn.fetch(
        f"""
        SELECT s.id, s.headline, s.country_code, s.source_name, s.timestamp,
               1 - (e.vec <=> $1::halfvec) AS similarity,
               EXISTS (SELECT 1 FROM signal_topic_assignments sta
                       WHERE sta.signal_id = s.id) AS has_topic
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
        ORDER BY e.vec <=> $1::halfvec
        LIMIT {int(limit * 3)}
        """,
        vec_literal,
    )
    import html as _html
    matches = []
    seen_headlines: set[str] = set()
    for r in rows:
        sim = float(r["similarity"])
        if sim < min_similarity:
            continue
        headline = _html.unescape(r["headline"] or "")
        if is_junk_headline(headline):
            continue
        # query-side dedup (#223): syndicated copies of the same headline can
        # all carry embeddings (the writer dedupes per run, not across runs)
        dedup_key = headline.strip().lower()
        if dedup_key in seen_headlines:
            continue
        seen_headlines.add(dedup_key)
        matches.append({
            "signal_id": int(r["id"]),
            # stored headlines are HTML-entity-encoded (known serialize bug)
            "headline": headline,
            "country_code": r["country_code"],
            "source_name": r["source_name"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "similarity": round(sim, 4),
            # gate status per Pipeline Funnel Principle: reachable, labeled
            "gate_status": "assigned" if r["has_topic"] else "below_gate",
        })
        if len(matches) >= limit:
            break
    return matches


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


# ---------------------------------------------------------------------------
# Semantic thread membership (#214/#162 follow-up, 2026-06-24).
#
# The lexicon topic classifier (`theme-hint-lex-v2`) is English-keyed: in a
# 168h window 1,722 Spanish / 832 Persian / 667 Arabic signals were ingested
# but only 5 / 0 / 0 received a topic assignment, so non-English voice could
# never reach a thread as gated evidence (gate_recall_by_language report,
# docs/research/nlp-coverage/2026-06-24). The scope gate was never the bottleneck
# — there was nothing in the pipe to ungate.
#
# Fix: route topic membership for the un-lexicon'd corpus through the existing
# multilingual e5 embeddings (signal_embeddings, migration 054) against the
# thread's running-mean centroid (dynamic_topics.centroid_vec). Read-path,
# language-agnostic, $0, reuses the ANN already built for research.
#
# Conservative initial floor: centroid↔signal cosine. Centroids run hotter than
# label anchors (members cluster tight) but the running mean drifts, so 0.82 is
# chosen between the research centroid floor (0.80) and the signal-headline floor
# (0.84) — pending a measured re-calibration on labeled members.
THREAD_MEMBER_MIN_SIMILARITY = 0.82
THREAD_MEMBER_LIMIT = 12


def build_semantic_members(
    raw_rows: list[dict[str, Any]],
    *,
    exclude_ids: set[int] | None = None,
    min_similarity: float = THREAD_MEMBER_MIN_SIMILARITY,
    limit: int = THREAD_MEMBER_LIMIT,
) -> list[dict[str, Any]]:
    """Pure filter/label of centroid-ANN rows into thread member items.

    Each raw row is a dict with: id, headline, country_code, source_name,
    source_url, timestamp(isoformat or None), sentiment, source_lang,
    similarity, has_topic. Applies the similarity floor, junk-headline filter,
    cross-syndication headline dedup, and the lexicon-already-shown exclusion,
    then labels each survivor. Honest provenance: every item is tagged
    retrieval=semantic_member with its gate_status so the surface never presents
    a semantic neighbour as gated evidence.
    """
    import html as _html

    excl = exclude_ids or set()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in raw_rows:
        sid = int(r["id"])
        if sid in excl:
            continue
        sim = float(r["similarity"])
        if sim < min_similarity:
            continue
        headline = _html.unescape(r.get("headline") or "")
        if is_junk_headline(headline):
            continue
        key = headline.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "signal_id": sid,
            "headline": headline,
            "country_code": r.get("country_code"),
            "source_name": r.get("source_name"),
            "source_url": r.get("source_url"),
            "timestamp": r.get("timestamp"),
            "sentiment": float(r["sentiment"]) if r.get("sentiment") is not None else None,
            "source_lang": r.get("source_lang") or "xx",
            "similarity": round(sim, 4),
            "retrieval": "semantic_member",
            "gate_status": "assigned" if r.get("has_topic") else "below_gate",
        })
        if len(out) >= limit:
            break
    return out


async def fetch_semantic_thread_members(
    conn: Any,
    topic_id: int,
    *,
    hours: int,
    exclude_ids: list[int] | None = None,
    limit: int = THREAD_MEMBER_LIMIT,
    min_similarity: float = THREAD_MEMBER_MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    """Signals semantically inside a dynamic topic, via centroid ANN.

    Surfaces the non-English / un-lexicon'd voice the English lexicon never
    assigned. Empty list when the topic has no centroid or no embeddings exist
    yet (fresh signals embed on the nightly cron) — caller degrades silently.
    """
    centroid_row = await conn.fetchrow(
        "SELECT centroid_vec FROM dynamic_topics "
        "WHERE id = $1 AND centroid_vec IS NOT NULL",
        topic_id,
    )
    if not centroid_row:
        return []
    centroid = [float(x) for x in centroid_row["centroid_vec"]]
    vec_literal = "[" + ",".join(f"{x:.5f}" for x in centroid) + "]"
    excl = exclude_ids or []
    rows = await conn.fetch(
        f"""
        SELECT s.id, s.headline, s.country_code, s.source_name, s.source_url,
               s.timestamp, s.sentiment,
               COALESCE(NULLIF(s.source_lang, ''), 'xx') AS source_lang,
               1 - (e.vec <=> $1::halfvec) AS similarity,
               EXISTS (SELECT 1 FROM signal_topic_assignments sta
                       WHERE sta.signal_id = s.id) AS has_topic
        FROM signal_embeddings e
        JOIN signals_v2 s ON s.id = e.signal_id
        WHERE s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND NOT (s.id = ANY($2::bigint[]))
        ORDER BY e.vec <=> $1::halfvec
        LIMIT {int(limit * 4)}
        """,
        vec_literal,
        excl,
    )
    raw = [
        {
            "id": r["id"],
            "headline": r["headline"],
            "country_code": r["country_code"],
            "source_name": r["source_name"],
            "source_url": r["source_url"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "sentiment": r["sentiment"],
            "source_lang": r["source_lang"],
            "similarity": r["similarity"],
            "has_topic": r["has_topic"],
        }
        for r in rows
    ]
    return build_semantic_members(
        raw, exclude_ids=set(excl), min_similarity=min_similarity, limit=limit
    )
