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

CONTRACT = "research-plan-v0"
THREAD_LANE_LIMIT = 24
WEAK_SUPPORT_CAP = 3
PIN_CANDIDATE_CAP = 6

# Human names for gap notes; falls back to the ISO code.
_COUNTRY_NAMES = {
    "IR": "Iran", "IQ": "Iraq", "IL": "Israel", "QA": "Qatar", "KW": "Kuwait",
    "BH": "Bahrain", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "JO": "Jordan", "CO": "Colombia", "US": "United States",
}


def _norm_tokens(text: str) -> set[str]:
    return set(normalize_search_text(text or "").split())


def _thread_match_terms(thread: dict[str, Any]) -> set[str]:
    """Tokens a thread exposes for lexical matching: label + anchor slugs."""
    tokens = _norm_tokens(str(thread.get("label") or ""))
    for slug in thread.get("anchor_topics") or []:
        tokens |= set(normalize_search_text(str(slug).replace("-", " ")).split())
    return tokens


def _expansion_tokens(intent: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for terms in (intent.get("expanded_terms") or {}).values():
        for term in terms:
            tokens |= _norm_tokens(term)
    return tokens


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
) -> dict[str, Any]:
    """Discover anchors for parsed intent. Degrades lane-by-lane: a failing
    lane contributes a gap note, never an exception."""
    # Geo alias tokens ("iran") must not count as topical evidence: otherwise
    # every country-labeled thread becomes direct_evidence for any Iran query.
    geo_tokens = {tok for alias in COUNTRY_ALIASES for tok in alias.split()}
    query_tokens = _norm_tokens(intent.get("main_intent") or "") - geo_tokens
    expansion = _expansion_tokens(intent) - geo_tokens
    geo: list[str] = intent.get("geo_scope") or []
    axes: list[str] = intent.get("topic_axes") or []

    anchors: list[dict[str, Any]] = []
    semantic_evidence: list[dict[str, Any]] = []
    coverage_gaps: list[dict[str, Any]] = []
    seen_thread_ids: set[str] = set()
    axis_hit: dict[str, bool] = {axis: False for axis in axes}
    # Honest ledger input (spec: No Silent Filtering): every thread candidate
    # the lanes considered but did not anchor, with a reason code.
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
                limit=THREAD_LANE_LIMIT,
                country_codes=[scope] if scope else None,
            )
        except Exception as exc:  # degraded lane -> visible gap, not a 500
            coverage_gaps.append({
                "gap_type": "lane_degraded",
                "lane": "thread",
                "scope": scope,
                "note": f"Thread lane unavailable ({exc.__class__.__name__}); coverage unknown.",
            })
            continue

        weak_used = 0
        for thread in threads:
            thread_id = str(thread.get("thread_id") or "")
            if not thread_id or thread_id in seen_thread_ids:
                continue
            thread_tokens = _thread_match_terms(thread)
            direct = sorted(thread_tokens & query_tokens)
            contextual = sorted(thread_tokens & expansion)
            if direct:
                label, matched = "direct_evidence", direct
            elif contextual:
                label, matched = "context", contextual
            elif scope and weak_used < WEAK_SUPPORT_CAP:
                label, matched = "weak_support", []
                weak_used += 1
            else:
                skipped_candidates.append({
                    "candidate_id": thread_id,
                    "label": thread.get("label"),
                    "lane": "thread",
                    "scope": scope,
                    "reason_code": (
                        "weak_support_cap_reached" if scope else "no_intent_match"
                    ),
                })
                continue
            seen_thread_ids.add(thread_id)
            anchors.append(_thread_anchor(
                thread,
                evidence_label=label,
                matched_terms=matched,
                hours=hours,
                country_code=scope,
            ))
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
                if not matched:
                    skipped_candidates.append({
                        "candidate_id": f"attention-{code.lower()}-{normalize_search_text(keyword).replace(' ', '-')}",
                        "label": keyword,
                        "lane": "public_attention",
                        "scope": code,
                        "reason_code": "no_intent_match",
                    })
                    continue
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
            else:
                topics = await fetch_centroids_fn()
                for cand in semantic_topic_candidates(query_vec, topics):
                    thread_id = f"dynamic-topic-{cand['topic_id']}"
                    if thread_id in seen_thread_ids:
                        continue  # lexical lanes already anchored it
                    seen_thread_ids.add(thread_id)
                    anchors.append({
                        "anchor_type": "thread",
                        "lane": "semantic",
                        "retrieval_lane": "semantic",
                        "match_basis": "member_centroid",
                        "id": thread_id,
                        "label": cand["label"],
                        "evidence_label": semantic_evidence_label(cand["similarity"]),
                        "matched_terms": [],
                        "semantic_similarity": cand["similarity"],
                        "signal_count": cand["n_signals"],
                        "open": {
                            "surface": "thread_detail",
                            "params": {"thread_id": thread_id, "hours": hours},
                        },
                    })

                # Atlas-topic anchor basis: taxonomy similarity, NOT evidence.
                # Reaches country threads that have no member centroid (e.g. a
                # Spanish query matching the English water-stress description).
                if fetch_atlas_anchors_fn is not None:
                    from app.services.research_semantic import semantic_atlas_candidates
                    from app.services.thread_intelligence import build_thread_id
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
                            "evidence_label": semantic_evidence_label(
                                cand["similarity"], basis="topic_description"
                            ),
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
                # Signal-headline basis (#223 deliverable 2): full-corpus
                # evidence retrieval. These are evidence ITEMS, not anchors —
                # each labeled with retrieval lane + gate status so below-gate
                # material is reachable but never presented as curated.
                if fetch_signal_matches_fn is not None:
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
            coverage_gaps.append({
                "gap_type": "lane_degraded",
                "lane": "semantic",
                "note": f"Semantic lane unavailable ({exc.__class__.__name__}).",
            })

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

    # ── Pin candidates + next steps ───────────────────────────────────────
    order = {"direct_evidence": 0, "context": 1, "weak_support": 2}
    pinnable = [
        a for a in anchors
        if a["anchor_type"] in ("thread", "country") and a["evidence_label"] != "gap"
    ]
    pinnable.sort(key=lambda a: (order.get(a["evidence_label"], 9), -int(a.get("signal_count") or 0)))
    pin_candidates = [a["id"] for a in pinnable[:PIN_CANDIDATE_CAP]]

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
    }
