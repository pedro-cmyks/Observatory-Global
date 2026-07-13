"""Multi-lane anchor discovery for the research workflow (Phase 1a).

Takes parsed research intent (``research_plan.parse_research_intent``) and
discovers openable anchors over surfaces that already exist: Narrative Threads,
country briefs, and public attention (trending searches). No ranking ledger,
no persistence, no LLM — those are Phase 1b/1.5/2.

Fetchers are injected so tests run without a database:
- ``fetch_threads_fn(hours, limit, country_codes)`` -> list of thread dicts
  (the ``thread_intelligence.fetch_threads`` shape).
- ``fetch_attention_fn(country_code, hours)`` -> list of trending keyword dicts
  (``{"keyword": str, "rank": int}``).

Evidence labels per spec Phase 1a acceptance:
- ``direct_evidence``: thread label/slug lexically matches the query itself.
- ``context``: matches only the axis expansion dictionary, or is a country /
  branch framing anchor.
- ``weak_support``: in geo scope but no lexical match (top threads only), or
  public-attention discussion (never verified evidence by default).
- ``gap``: marks missing coverage instead of hiding it.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.search_normalization import normalize_search_text
from app.services.research_plan import AXIS_TRIGGERS, COUNTRY_ALIASES

ThreadFetcher = Callable[..., Awaitable[list[dict[str, Any]]]]
AttentionFetcher = Callable[..., Awaitable[list[dict[str, Any]]]]

CONTRACT = "research-plan-v1"  # v1 (2026-07-05): two-tier gate labels, Kalman
# movement enrichment, R3 category passthrough, substrate-health guard.
# W2a: below this many active story centroids the member-centroid semantic
# basis runs in exactly the post-collapse noise regime measured in the F4 A/B
# (16-centroid pool → promiscuous matches). Suppress it HONESTLY (visible gap)
# instead of serving junk; the signal-headline + atlas bases don't depend on
# pool size and stay on. Router passes 80; tests default to 0 (off).
SUBSTRATE_MIN_CENTROIDS_DEFAULT = 80

# Human names for gap notes; falls back to the ISO code.
_COUNTRY_NAMES = {
    "IR": "Iran", "IQ": "Iraq", "IL": "Israel", "QA": "Qatar", "KW": "Kuwait",
    "BH": "Bahrain", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "JO": "Jordan", "CO": "Colombia", "US": "United States",
}

_QUERY_STOPWORDS = {
    "a", "about", "air", "an", "and", "around", "de", "del", "el", "en", "for",
    "how", "in", "la", "las", "los", "of", "on", "or", "regional", "sobre",
    "the", "to", "un", "una", "us", "what", "with", "y",
}

_GENERIC_CONTEXT_TOKENS = {"attack", "attacks", "strike", "strikes"}


def _norm_tokens(text: str) -> set[str]:
    return set(normalize_search_text(text or "").split())


def _thread_match_terms(thread: dict[str, Any]) -> set[str]:
    """Tokens a thread exposes for lexical matching: label + anchor slugs."""
    tokens = _norm_tokens(str(thread.get("label") or ""))
    for slug in thread.get("anchor_topics") or []:
        tokens |= set(normalize_search_text(str(slug).replace("-", " ")).split())
    return tokens


def _label_names_target_geo(label: str, geo_codes: list[str]) -> bool:
    normalized = normalize_search_text(label or "")
    tokens = set(normalized.split())
    for alias, code in COUNTRY_ALIASES.items():
        if code not in geo_codes:
            continue
        matched = alias in normalized if " " in alias else alias in tokens
        if matched:
            return True
    return False


def _expansion_tokens(intent: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for terms in (intent.get("expanded_terms") or {}).values():
        for term in terms:
            tokens |= _norm_tokens(term)
    return tokens - _QUERY_STOPWORDS


def _lexical_match(
    thread_tokens: set[str],
    query_tokens: set[str],
    expansion_tokens: set[str],
) -> tuple[str, list[str]]:
    """Classify an inspectable lexical relationship without single-token
    overclaiming.

    A lone generic overlap in a compound query (for example ``escalation`` in
    an Iran + infrastructure question) is recall, not direct evidence. It
    stays reachable as weak support. One-token queries can still match
    directly, while compound queries require at least two meaningful terms.
    """
    direct = sorted(thread_tokens & query_tokens)
    contextual = sorted(thread_tokens & expansion_tokens)
    direct_floor = 1 if len(query_tokens) == 1 else 2
    if direct and len(direct) >= direct_floor:
        return "direct_evidence", direct
    specific_context = set(contextual) - _GENERIC_CONTEXT_TOKENS
    if contextual and (specific_context or len(set(direct) | set(contextual)) >= 2):
        return "context", contextual
    return "weak_support", direct


def _semantic_component_gap(component: str, exc: Exception) -> dict[str, Any]:
    """Expose a failed semantic substrate without erasing healthy siblings."""
    return {
        "gap_type": "lane_degraded",
        "lane": "semantic",
        "component": component,
        "note": (
            f"Semantic {component.replace('_', ' ')} unavailable "
            f"({exc.__class__.__name__})."
        ),
    }


def _thread_anchor(
    thread: dict[str, Any],
    *,
    evidence_label: str,
    matched_terms: list[str],
    hours: int,
    country_code: str | None,
) -> dict[str, Any]:
    return {
        "anchor_type": "thread",
        "lane": "thread",
        "id": thread.get("thread_id"),
        "label": thread.get("label"),
        "evidence_label": evidence_label,
        "matched_terms": matched_terms,
        "signal_count": int(thread.get("signal_count") or 0),
        "source_count": int(thread.get("source_count") or 0),
        "changed_10h": int(thread.get("changed_10h") or 0),
        # W2d: R3 category lens passthrough (typer output on dynamic topics,
        # parent domain on atlas) — lets the plan group anchors by category.
        "category": thread.get("category"),
        "crisis_relevant": thread.get("crisis_relevant"),
        "coverage_countries": thread.get("top_countries") or [],
        "scope_basis": thread.get("scope_basis"),
        "subject_status": thread.get("subject_status"),
        "quality": thread.get("quality"),
        "confidence": thread.get("confidence"),
        "open": {
            "surface": "thread_detail",
            "params": {
                "thread_id": thread.get("thread_id"),
                "hours": hours,
                **({"country_code": country_code} if country_code else {}),
            },
        },
    }


async def discover_anchors(
    intent: dict[str, Any],
    *,
    hours: int,
    fetch_threads_fn: ThreadFetcher,
    fetch_attention_fn: AttentionFetcher | None = None,
    embed_query_fn: Callable[[str], list[float] | None] | None = None,
    fetch_centroids_fn: Callable[..., Awaitable[list[dict[str, Any]]]] | None = None,
    fetch_atlas_anchors_fn: Callable[..., Awaitable[list[dict[str, Any]] | None]] | None = None,
    fetch_signal_matches_fn: Callable[..., Awaitable[list[dict[str, Any]]]] | None = None,
    fetch_movement_fn: Callable[[list[str]], Awaitable[dict[str, dict[str, Any]]]] | None = None,
    substrate_min_centroids: int = 0,
) -> dict[str, Any]:
    """Discover anchors for parsed intent. Degrades lane-by-lane: a failing
    lane contributes a gap note, never an exception."""
    # Geo alias tokens ("iran") must not count as topical evidence: otherwise
    # every country-labeled thread becomes direct_evidence for any Iran query.
    geo_tokens = {tok for alias in COUNTRY_ALIASES for tok in alias.split()}
    query_tokens = (
        _norm_tokens(intent.get("main_intent") or "") - geo_tokens - _QUERY_STOPWORDS
    )
    expansion = _expansion_tokens(intent) - geo_tokens
    geo: list[str] = intent.get("geo_scope") or []
    axes: list[str] = intent.get("topic_axes") or []

    anchors: list[dict[str, Any]] = []
    semantic_evidence: list[dict[str, Any]] = []
    coverage_gaps: list[dict[str, Any]] = []
    seen_thread_ids: set[str] = set()
    thread_anchor_by_id: dict[str, dict[str, Any]] = {}
    axis_hit: dict[str, bool] = {axis: False for axis in axes}
    thread_universe_complete = True
    # Kept for contract compatibility. The complete-universe path below does
    # not omit discovered candidates; all weak material remains reachable.
    skipped_candidates: list[dict[str, Any]] = []

    # ── Country lane ─────────────────────────────────────────────────────
    for code in geo:
        anchors.append({
            "anchor_type": "country",
            "lane": "country",
            "id": f"country-{code.lower()}",
            "label": _COUNTRY_NAMES.get(code, code),
            "evidence_label": "context",
            "matched_terms": [],
            "open": {
                "surface": "country_brief",
                "params": {"country_code": code, "hours": hours},
            },
        })

    # ── Thread lane (country-scoped first, then global) ──────────────────
    scopes: list[str | None] = list(geo) or [None]
    if geo:
        scopes.append(None)  # global pass catches cross-border threads
    for scope in scopes:
        try:
            threads = await fetch_threads_fn(
                hours=hours,
                limit=None,
                country_codes=[scope] if scope else None,
            )
        except Exception as exc:  # degraded lane -> visible gap, not a 500
            thread_universe_complete = False
            coverage_gaps.append({
                "gap_type": "lane_degraded",
                "lane": "thread",
                "scope": scope,
                "note": f"Thread lane unavailable ({exc.__class__.__name__}); coverage unknown.",
            })
            continue

        for thread in threads:
            thread_id = str(thread.get("thread_id") or "")
            if not thread_id:
                continue
            thread_tokens = _thread_match_terms(thread)
            label, matched = _lexical_match(thread_tokens, query_tokens, expansion)
            explicit_geo = _label_names_target_geo(
                str(thread.get("label") or ""), geo,
            )
            if (
                label == "weak_support"
                and matched
                and explicit_geo
            ):
                label = "direct_evidence"
            elif label == "weak_support" and explicit_geo:
                contextual = sorted(thread_tokens & expansion)
                if contextual:
                    label, matched = "context", contextual
            existing = thread_anchor_by_id.get(thread_id)
            evidence_order = {"weak_support": 0, "context": 1, "direct_evidence": 2}
            if existing is not None:
                if evidence_order[label] > evidence_order[existing["evidence_label"]]:
                    existing["evidence_label"] = label
                    existing["matched_terms"] = matched
                    if scope:
                        existing["open"]["params"]["country_code"] = scope
                continue
            seen_thread_ids.add(thread_id)
            anchor = _thread_anchor(
                thread,
                evidence_label=label,
                matched_terms=matched,
                hours=hours,
                country_code=scope,
            )
            anchors.append(anchor)
            thread_anchor_by_id[thread_id] = anchor
            if label in ("direct_evidence", "context"):
                for axis in axes:
                    axis_tokens: set[str] = set(AXIS_TRIGGERS.get(axis, set()))
                    for term in (intent.get("expanded_terms") or {}).get(axis, []):
                        axis_tokens |= _norm_tokens(term)
                    if thread_tokens & axis_tokens:
                        axis_hit[axis] = True

    # ── Public-attention lane (discussion, never verified evidence) ──────
    if fetch_attention_fn is not None:
        for code in geo:
            try:
                items = await fetch_attention_fn(country_code=code, hours=hours)
            except Exception as exc:
                coverage_gaps.append({
                    "gap_type": "lane_degraded",
                    "lane": "public_attention",
                    "scope": code,
                    "note": f"Public-attention lane unavailable ({exc.__class__.__name__}).",
                })
                continue
            for item in items:
                keyword = str(item.get("keyword") or "")
                kw_tokens = _norm_tokens(keyword)
                matched = sorted(kw_tokens & (query_tokens | expansion))
                anchors.append({
                    "anchor_type": "public_attention",
                    "lane": "public_attention",
                    "id": f"attention-{code.lower()}-{normalize_search_text(keyword).replace(' ', '-')}",
                    "label": keyword,
                    "evidence_label": "weak_support",
                    "matched_terms": matched,
                    "open": {
                        "surface": "public_attention",
                        "params": {"country_code": code, "query": keyword, "hours": hours},
                    },
                })

    # ── Semantic lane (Phase 1.5a: query↔thread over e5 centroids) ───────
    if embed_query_fn is not None and fetch_centroids_fn is not None:
        from app.services.research_semantic import (
            semantic_evidence_label,
            semantic_topic_candidates,
        )
        import inspect
        query_vec = None
        try:
            query_vec = embed_query_fn(intent.get("main_intent") or "")
            if inspect.isawaitable(query_vec):
                query_vec = await query_vec
            if query_vec is None:
                coverage_gaps.append({
                    "gap_type": "lane_unavailable",
                    "lane": "semantic",
                    "note": (
                        "Semantic lane unavailable in this deployment "
                        "(embedding model not present); recall is lexical-only."
                    ),
                })
        except Exception as exc:
            coverage_gaps.append(_semantic_component_gap("query_embedding", exc))

        if query_vec is not None:
            topics: list[dict[str, Any]] = []
            centroids_available = True
            try:
                topics = await fetch_centroids_fn()
            except Exception as exc:
                centroids_available = False
                coverage_gaps.append(_semantic_component_gap("story_centroid", exc))

            # W2a substrate-health guard: a collapsed centroid pool makes the
            # member-centroid basis pure noise. Suppress it visibly; atlas and
            # signal-headline bases proceed independently.
            if (
                centroids_available
                and substrate_min_centroids
                and len(topics) < substrate_min_centroids
            ):
                coverage_gaps.append({
                    "gap_type": "lane_degraded",
                    "lane": "semantic",
                    "component": "story_centroid",
                    "note": (
                        f"Story-centroid pool is thin ({len(topics)} active, "
                        f"healthy ≥{substrate_min_centroids}); topic-level semantic "
                        "matches suppressed to avoid noise. Signal-headline "
                        "evidence below is unaffected."
                    ),
                })
                topics = []
            for cand in semantic_topic_candidates(query_vec, topics):
                thread_id = f"dynamic-topic-{cand['topic_id']}"
                if thread_id in seen_thread_ids:
                    existing = thread_anchor_by_id.get(thread_id)
                    if existing is not None:
                        existing["semantic_similarity"] = cand["similarity"]
                        existing["match_basis"] = "member_centroid"
                        existing["retrieval_lane"] = "thread+semantic"
                        semantic_label = semantic_evidence_label(cand["similarity"])
                        if (
                            existing["evidence_label"] == "weak_support"
                            and semantic_label == "context"
                            and (
                                not geo
                                or bool(set(existing.get("coverage_countries") or []) & set(geo))
                            )
                        ):
                            existing["evidence_label"] = "context"
                    continue
                seen_thread_ids.add(thread_id)
                anchors.append({
                    "anchor_type": "thread",
                    "lane": "semantic",
                    "retrieval_lane": "semantic",
                    "match_basis": "member_centroid",
                    "id": thread_id,
                    "label": cand["label"],
                    # With a geographic intent, an unscoped centroid is recall,
                    # not subject proof. It stays weak unless a lexical-lane
                    # candidate supplied matching coverage context above.
                    "evidence_label": (
                        "weak_support" if geo
                        else semantic_evidence_label(cand["similarity"])
                    ),
                    "matched_terms": [],
                    "semantic_similarity": cand["similarity"],
                    "signal_count": cand["n_signals"],
                    "open": {
                        "surface": "thread_detail",
                        "params": {"thread_id": thread_id, "hours": hours},
                    },
                })

            # Atlas-topic anchor basis: taxonomy similarity, NOT evidence.
            if fetch_atlas_anchors_fn is not None:
                from app.services.research_semantic import semantic_atlas_candidates
                from app.services.thread_intelligence import build_thread_id

                try:
                    embedded = await fetch_atlas_anchors_fn()
                    for cand in semantic_atlas_candidates(query_vec, embedded or []):
                        thread_id = build_thread_id(cand["slug"], geo)
                        if thread_id in seen_thread_ids:
                            continue
                        seen_thread_ids.add(thread_id)
                        anchors.append({
                            "anchor_type": "thread",
                            "lane": "semantic",
                            "retrieval_lane": "semantic",
                            "match_basis": "topic_description",
                            "id": thread_id,
                            "label": cand["label"],
                            # Taxonomy similarity is a navigation hint, never
                            # found evidence. Keep it inspectable but non-primary.
                            "evidence_label": "weak_support",
                            "matched_terms": [],
                            "semantic_similarity": cand["similarity"],
                            "open": {
                                "surface": "thread_detail",
                                "params": {
                                    "thread_id": thread_id,
                                    "hours": hours,
                                    **({"country_code": geo[0]} if geo else {}),
                                },
                            },
                        })
                except Exception as exc:
                    coverage_gaps.append(
                        _semantic_component_gap("topic_description", exc)
                    )

            # Signal-headline basis (#223 deliverable 2): full-corpus evidence
            # retrieval. It is independent from both anchor substrates.
            if fetch_signal_matches_fn is not None:
                try:
                    matches = await fetch_signal_matches_fn(
                        query_vec=query_vec, hours=hours,
                    )
                    for m in matches:
                        semantic_evidence.append({
                            **m,
                            "retrieval_lane": "semantic",
                            "match_basis": "signal_headline",
                        })
                except Exception as exc:
                    coverage_gaps.append(
                        _semantic_component_gap("signal_headline", exc)
                    )

    # ── Related-branch lane ───────────────────────────────────────────────
    for branch in intent.get("branches") or []:
        anchors.append({
            "anchor_type": "related_branch",
            "lane": "branch",
            "id": f"branch-{branch}",
            "label": branch.replace("-", " "),
            "evidence_label": "context",
            "matched_terms": [],
            "open": {
                "surface": "research_plan",
                "params": {"query": branch.replace("-", " "), "hours": hours},
            },
        })

    # ── Coverage gaps: axes with no thread evidence ───────────────────────
    for axis, hit in axis_hit.items():
        if not hit:
            geo_label = ", ".join(_COUNTRY_NAMES.get(c, c) for c in geo) or "the queried scope"
            coverage_gaps.append({
                "gap_type": "axis_no_thread",
                "axis": axis,
                "note": (
                    f"No coherent thread currently covers the '{axis}' axis for "
                    f"{geo_label}; available evidence is taxonomy-only or absent."
                ),
            })
    for code in geo:
        if not any(
            a["anchor_type"] == "thread" and a["open"]["params"].get("country_code") == code
            for a in anchors
        ):
            coverage_gaps.append({
                "gap_type": "country_no_threads",
                "country_code": code,
                "note": (
                    f"{_COUNTRY_NAMES.get(code, code)} has no country-scoped threads "
                    "matching this query in the window; signals may exist below the quality gate."
                ),
            })

    for gap in coverage_gaps:
        anchors.append({
            "anchor_type": "coverage_gap",
            "lane": gap.get("lane") or "gap",
            "id": f"gap-{gap['gap_type']}-{gap.get('axis') or gap.get('country_code') or gap.get('scope') or 'general'}",
            "label": gap["note"],
            "evidence_label": "gap",
            "matched_terms": [],
            "open": None,
        })

    # ── W2c movement enrichment (Kalman shared field #219) ───────────────
    # Display/reason enrichment ONLY: investigative_score keeps its
    # changed_10h lineage (the ranking calibration and the threads-panel
    # ordering both speak changed_10h; swapping the scale would silently
    # invalidate the 2026-06-10 calibration). Kalman rides along per anchor.
    thread_anchor_ids = [
        str(a["id"]) for a in anchors if a["anchor_type"] == "thread" and a.get("id")
    ]
    kalman: dict[str, dict[str, Any]] = {}
    if fetch_movement_fn is not None and thread_anchor_ids:
        try:
            kalman = await fetch_movement_fn(thread_anchor_ids) or {}
        except Exception:
            kalman = {}  # movement is enrichment — never degrades the plan
    for a in anchors:
        if a["anchor_type"] != "thread":
            continue
        m = kalman.get(str(a.get("id")))
        if m:
            a["movement"] = {**m, "source": "kalman-topic-movement"}
        else:
            a["movement"] = {"changed_10h": int(a.get("changed_10h") or 0), "source": "changed_10h"}

    # ── W2d category lens summary (R3) ────────────────────────────────────
    category_summary: dict[str, int] = {}
    for a in anchors:
        if a["anchor_type"] == "thread" and a.get("category"):
            category_summary[str(a["category"])] = category_summary.get(str(a["category"]), 0) + 1

    # ── Pin candidates + next steps ───────────────────────────────────────
    order = {"direct_evidence": 0, "context": 1, "weak_support": 2}
    pinnable = [
        a for a in anchors
        if a["anchor_type"] in ("thread", "country") and a["evidence_label"] != "gap"
    ]
    pinnable.sort(key=lambda a: (order.get(a["evidence_label"], 9), -int(a.get("signal_count") or 0)))
    pin_candidates = [a["id"] for a in pinnable]

    next_steps: list[str] = []
    if any(a["evidence_label"] == "direct_evidence" for a in anchors):
        next_steps.append("Open the direct-evidence threads and pin the ones that answer your subquestions.")
    if geo:
        next_steps.append("Open the country brief to compare who is covering this and from where.")
    for branch in intent.get("branches") or []:
        next_steps.append(f"Branch the investigation: search '{branch.replace('-', ' ')}'.")
    for gap in coverage_gaps:
        if gap["gap_type"] == "axis_no_thread":
            next_steps.append(
                f"The '{gap['axis']}' axis has no thread-level evidence yet — treat related claims as unverified."
            )

    return {
        "contract": CONTRACT,
        "intent": intent,
        "hours": hours,
        "anchors": anchors,
        "pin_candidates": pin_candidates,
        "coverage_gaps": coverage_gaps,
        "suggested_next_steps": next_steps,
        "skipped_candidates": skipped_candidates,
        "semantic_evidence": semantic_evidence,
        "category_summary": category_summary,
        "discovery_completion": {
            "thread_universe_complete": thread_universe_complete,
            "thread_candidate_ceiling": False,
        },
    }
