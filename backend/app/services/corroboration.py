"""Web-corroboration lane (roadmap v2.1 P0.6b) — pure math + search, no LLM.

Productizes the manual corroboration run (docs/research/flagship/
2026-07-11-nato-ankara-marquee.md §WEB CORROBORATION): for each dossier pin,
1-2 focused web-search queries → gathered article titles → SOURCE-INDEPENDENCE
weighting (the G2 rule): near-identical headlines (syndicated wire) collapse to
ONE source; independently-operated outlets are counted, never raw articles.

Search executor = the existing #161 external-depth lane (GDELT DOC 2.0 —
free, no key, credibility-tiered). This module owns only the MATH so it stays
unit-testable without a network: query building, syndication clustering,
independence counting, status assignment.

Statuses emitted by the math: 'established' (≥3 independent outlets) |
'unverified' (<3, or the pin's search lane was unavailable) |
'not_applicable' (metadata-only context with no frozen evidence claim).
'contested' is part of the dossier-corroboration-v1 contract but is NOT emitted
by v1 math — stance detection is not a token count; it stays reserved (a
client-supplied lane or a future stance pass may set it).
"""
from __future__ import annotations

import re
from typing import Any

# G2 thresholds — documented in the payload meta so the section is glass-box.
ESTABLISHED_MIN_OUTLETS = 3
SYNDICATION_JACCARD = 0.6      # title token-set overlap ≥ this = same wire copy
MAX_QUERIES_PER_PIN = 2
MAX_CITATIONS_PER_PIN = 5

_STOP = {
    "the", "and", "in", "of", "on", "for", "a", "an", "to", "at", "with",
    "over", "after", "amid", "during", "between", "against", "under",
    "updates", "update", "news", "coverage", "crisis", "situation", "talks",
    "story", "stories", "report", "reports", "reported", "reporting",
    "latest", "live", "heard", "said", "says", "according",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zà-ÿ0-9]{3,}", (text or "").lower())
            if t not in _STOP]


def build_pin_queries(
    label: str,
    actors: list[str] | None = None,
    evidence: list[str] | None = None,
) -> list[str]:
    """Build focused queries from the synthetic label and frozen receipts.

    DOC 2.0's implicit-AND parser is fragile, so each query stays short. The
    thread label remains the primary query. A frozen evidence headline is the
    first fallback because it carries the event wording that actually appeared
    in coverage; measured actors fill the fallback slot only when no distinct
    receipt query is available.
    """
    queries: list[str] = []
    label_toks = _tokens(label)[:5]
    if label_toks:
        queries.append(" ".join(label_toks))

    for receipt in (evidence or []):
        # Frontend attribution is appended as ``headline — outlet, date``.
        # Search only the frozen headline; domains/dates would overconstrain the
        # implicit-AND query and reproduce the false negative this fallback
        # exists to prevent.
        headline = re.split(r"\s+—\s+", receipt or "", maxsplit=1)[0]
        headline_toks = _tokens(headline)
        # Put the label/evidence overlap first (usually the place or actor),
        # then add three concrete headline terms. Four implicit-AND tokens are
        # specific enough to describe the event without reproducing the
        # over-constrained five-token timeout measured against DOC 2.0.
        shared = [t for t in headline_toks if t in label_toks]
        receipt_only = [t for t in headline_toks if t not in shared]
        q = " ".join(dict.fromkeys([*shared, *receipt_only]))
        q = " ".join(q.split()[:4])
        if q and q not in queries:
            queries.append(q)
        if len(queries) >= MAX_QUERIES_PER_PIN:
            return queries

    for a in (actors or [])[:3]:
        a_toks = _tokens(a)
        if not a_toks:
            continue
        # actor + the label's leading token anchors the actor to the story
        anchor = label_toks[0] if label_toks else ""
        q = " ".join(dict.fromkeys([*a_toks, anchor])).strip()
        if q and q not in queries:
            queries.append(q)
        if len(queries) >= MAX_QUERIES_PER_PIN:
            break
    return queries[:MAX_QUERIES_PER_PIN]


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_syndicated(articles: list[dict]) -> list[list[dict]]:
    """Greedy near-identical-title clustering. Each cluster ≈ one wire story
    (or one genuinely distinct account). Input dicts need `title`; order is
    preserved (first member = representative)."""
    clusters: list[tuple[frozenset, list[dict]]] = []
    for art in articles:
        tset = frozenset(_tokens(art.get("title") or ""))
        placed = False
        for cset, members in clusters:
            if _jaccard(tset, cset) >= SYNDICATION_JACCARD:
                members.append(art)
                placed = True
                break
        if not placed:
            clusters.append((tset, [art]))
    return [members for _, members in clusters]


def independence(articles: list[dict]) -> dict[str, Any]:
    """The G2 rule as a number. Cluster near-identical titles; each cluster
    collapses to its representative's outlet; count DISTINCT outlets across
    representatives. 20 reprints of one wire story = 1; CNBC+Time+ABC each
    writing their own = 3. Articles need `title` + `outlet` (domain)."""
    clusters = cluster_syndicated(articles)
    rep_outlets: list[str] = []
    citations: list[dict] = []
    for members in clusters:
        rep = members[0]
        outlet = (rep.get("outlet") or "").lower()
        if outlet and outlet not in rep_outlets:
            rep_outlets.append(outlet)
            citations.append(rep)
    return {
        "independent_outlets": len(rep_outlets),
        "total_articles": len(articles),
        "syndicated_clusters": sum(1 for m in clusters if len(m) > 1),
        "citations": citations,   # one per independent outlet, input order
    }


def pin_status(
    independent_outlets: int,
    search_available: bool,
    *,
    applicable: bool = True,
) -> tuple[str, str]:
    """(status, note) from the independence count — glass-box, no judgment."""
    if not applicable:
        return (
            "not_applicable",
            "metadata-only context pin — no frozen evidence claim to corroborate",
        )
    if not search_available:
        return ("unverified",
                "web-search lane unavailable — corroboration not measured")
    if independent_outlets >= ESTABLISHED_MIN_OUTLETS:
        return ("established",
                f"{independent_outlets} independently-operated outlets "
                "(syndicated copies collapsed)")
    if independent_outlets == 0:
        return ("unverified", "no matching web coverage found in the window")
    return ("unverified",
            f"only {independent_outlets} independent outlet(s) — "
            "insufficient corroboration; treat as single-sourced")
