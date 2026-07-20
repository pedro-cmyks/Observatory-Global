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

import json
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


# ─────────────────────────────────────────────────────────────────────────────
# CORROBORATION LANE (council Phase 3a) — query-time verdicts over TWO corpora.
#
# The P0.6b math above answers "how many independent outlets cover this pin?".
# This lane answers a sharper question the council named the publish-blocker
# (Marcos): "does an OFFICIAL/WIRE or full-history source CORROBORATE — or
# CONTRADICT — the specific claim in this receipt?".
#
# Two unified corpora, both spanning MONTHS (not the 8-day hot window):
#   basis=doc20         → GDELT DOC 2.0 query-time (free, no key, throttles)
#   basis=atlas_hot     → signal_embeddings (semantic, last ~8 days)
#   basis=atlas_archive → historical_evidence_samples (text, May-3 → present)
#
# HONESTY (Marcos's requirement): when DOC 2.0 throttles/errors, the response
# says so explicitly via source_status and STILL serves the Atlas-corpus
# matches labelled by basis — never silently returns fewer results as if the
# answer were complete. Relation is MATH (figure comparison + term/semantic
# overlap), never an LLM stance guess — stance beyond figure conflict stays
# out of scope (same discipline as the reserved 'contested' status above).
# ─────────────────────────────────────────────────────────────────────────────

import asyncio as _asyncio
import logging as _logging
import urllib.parse as _urlparse

_log = _logging.getLogger(__name__)

Relation = str  # 'corroborates' | 'contradicts' | 'context'

# Relation thresholds — glass-box, echoed in the payload meta.
FIGURE_MATCH_TOLERANCE = 0.01   # |a-b|/max ≤ this = same figure = corroborates
SAME_EVENT_TERM_RECALL = 0.40   # ≥ this share of claim terms present = same event
CORROBORATE_TERM_RECALL = 0.50  # ≥ this (and no figure conflict) = corroborates
SAME_EVENT_SIMILARITY = 0.86    # semantic sim ≥ this = same event (hot lane)

# International wire agencies / official bodies — mirrors the frontend
# claimLedger.ts OFFICIAL_SOURCE_TOKENS so backend + client agree on what
# "official source present" means (the contested-figure caveat).
_OFFICIAL_SOURCE_TOKENS = (
    "reuters", "associated press", "afp", "agence france", "efe", "bloomberg",
    "anadolu", "tass", "xinhua", "kyodo", "yonhap", "pa media",
    "press association", "dpa", "pti", "ians", "ap news", "reliefweb",
    "united nations", "u.n.", "who ", "world health", "government",
)

# Numbers that are almost never a death-toll / magnitude claim — years and
# small counts that would create noisy figure "contradictions".
_FIGURE_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?")


def extract_figure(text: str | None) -> float | None:
    """First thousands-grouped or plain number → float, else None. Mirrors
    claimLedger.ts extractFigure so a headline's toll parses identically on
    both ends of the wire."""
    if not text:
        return None
    m = _FIGURE_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def is_official_source(source: str | None) -> bool:
    """True when the source name reads as an international wire / official body.
    Word-boundary for the two-letter agencies so 'AP' hits, 'Apple' doesn't."""
    s = (source or "").strip().lower()
    if not s:
        return False
    if re.search(r"\bap\b", s) or re.search(r"\bafp\b", s):
        return True
    return any(tok in s for tok in _OFFICIAL_SOURCE_TOKENS)


def extract_claim_terms(
    headline: str,
    *,
    country: str | None = None,
) -> dict[str, Any]:
    """Turn a claim headline into the search substrate: significant tokens +
    a DOC 2.0 implicit-AND query (short — the parser is fragile, see
    external_depth.build_query). Country is appended only when the query is
    short enough to stay specific without over-constraining."""
    toks = _tokens(headline)
    # Preserve first-seen order but drop dups.
    ordered = list(dict.fromkeys(toks))
    query_toks = ordered[:5]
    query = " ".join(query_toks)
    if country and len(query_toks) < 4 and country.lower() not in query.lower():
        query = f"{query} {country.lower()}".strip()
    return {"terms": ordered, "query": query.strip()}


def term_recall(claim_terms: list[str], candidate_text: str | None) -> float:
    """Share of the claim's distinctive terms present in the candidate. 0..1.
    Recall (not Jaccard) because a candidate headline may add many words; what
    matters is whether it restates the claim's terms."""
    if not claim_terms:
        return 0.0
    cand = set(_tokens(candidate_text or ""))
    if not cand:
        return 0.0
    hit = sum(1 for t in set(claim_terms) if t in cand)
    return hit / len(set(claim_terms))


def figure_relation(claim_figure: float | None,
                    candidate_figure: float | None) -> Relation | None:
    """Figure-level relation, or None when a figure is missing on either side.
    Within tolerance = corroborates; materially different = contradicts."""
    if claim_figure is None or candidate_figure is None:
        return None
    hi = max(abs(claim_figure), abs(candidate_figure))
    if hi == 0:
        return "corroborates"
    if abs(claim_figure - candidate_figure) / hi <= FIGURE_MATCH_TOLERANCE:
        return "corroborates"
    return "contradicts"


def classify_relation(
    claim_terms: list[str],
    claim_figure: float | None,
    candidate_headline: str | None,
    *,
    similarity: float | None = None,
) -> Relation:
    """MATH relation for one candidate against the claim. A candidate is the
    SAME EVENT when it restates enough claim terms OR (hot lane) is semantically
    close. Same-event + a conflicting figure = contradicts; same-event with a
    matching or absent figure = corroborates; everything weaker = context
    (related coverage, not a restatement). No stance model — honest by
    construction."""
    recall = term_recall(claim_terms, candidate_headline)
    same_event = recall >= SAME_EVENT_TERM_RECALL or (
        similarity is not None and similarity >= SAME_EVENT_SIMILARITY
    )
    cand_figure = extract_figure(candidate_headline)
    fig_rel = figure_relation(claim_figure, cand_figure)
    if same_event and fig_rel == "contradicts":
        return "contradicts"
    if fig_rel == "corroborates" and same_event:
        return "corroborates"
    if recall >= CORROBORATE_TERM_RECALL or (
        similarity is not None and similarity >= SAME_EVENT_SIMILARITY
    ):
        return "corroborates"
    return "context"


def _domain(url: str | None) -> str:
    return _urlparse.urlparse(url or "").netloc.removeprefix("www.")


def normalize_match(
    *,
    basis: str,
    source: str | None,
    url: str | None,
    country: str | None,
    date: str | None,
    snippet: str | None,
    relation: Relation,
    similarity: float | None = None,
) -> dict[str, Any]:
    """One unified corroboration row. `snippet` is the candidate headline (the
    only text these corpora carry) — kept so the dossier can show WHAT the
    corroborating source said."""
    return {
        "basis": basis,
        "source": source,
        "url": url,
        "country": country,
        "date": date,
        "snippet": snippet,
        "relation": relation,
        "official": is_official_source(source),
        "similarity": round(similarity, 4) if similarity is not None else None,
    }


def dedup_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse the three corpora on url OR normalized headline. First writer
    wins, but a later duplicate from a HIGHER-trust basis (doc20/archive carry
    official wires; hot carries the same story) never displaces the first — we
    keep insertion order and merely drop repeats. Contradictions are preserved
    (a contradicting row with a distinct url survives)."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[dict[str, Any]] = []
    for m in matches:
        url = (m.get("url") or "").strip().lower()
        title = re.sub(r"\s+", " ", (m.get("snippet") or "").strip().lower())[:120]
        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        out.append(m)
    return out


def citation_verdict(matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact per-receipt verdict the dossier renders next to a Citation.
    Counts corroborating / contradicting / official-among-corroborating. Answers
    the claim ledger's 'official source missing' question: is any corroborating
    source a wire/official body?"""
    corr = [m for m in matches if m.get("relation") == "corroborates"]
    contra = [m for m in matches if m.get("relation") == "contradicts"]
    official_corr = sum(1 for m in corr if m.get("official"))
    n_corr, n_contra = len(corr), len(contra)
    if n_contra and n_contra >= n_corr:
        status = "contradicted"
    elif n_corr:
        status = "corroborated"
    else:
        status = "uncorroborated"

    parts: list[str] = []
    if n_corr:
        official_note = (f", incl. {official_corr} official/wire"
                         if official_corr else ", none official/wire")
        parts.append(f"corroborated by {n_corr} source(s){official_note}")
    if n_contra:
        parts.append(f"contradicted by {n_contra}")
    if not parts:
        parts.append("no corroborating coverage found in the queried corpora")
    return {
        "status": status,
        "corroborating": n_corr,
        "contradicting": n_contra,
        "official_corroborating": official_corr,
        "note": "; ".join(parts),
    }


# ── corpus query builders (pure — testable without a DB) ─────────────────────

COLD_LANE_LIMIT = 40
HOT_LANE_LIMIT = 20


def build_cold_corpus_query(
    terms: list[str],
    *,
    country: str | None = None,
    limit: int = COLD_LANE_LIMIT,
) -> tuple[str, list[Any]]:
    """SQL + params for the FULL-HISTORY archive text lane
    (historical_evidence_samples, May-3 → present). ILIKE-ANY over the claim's
    distinctive terms (OR-match for recall); Python then scores term overlap and
    assigns the relation. Country filter optional. Pure: returns (sql, params)
    so the query shape is unit-tested without a live database."""
    patterns = [f"%{t}%" for t in terms[:6] if t]
    sql = """
        SELECT headline, source_url, source_name, country_code, day,
               topic_slug, sentiment
        FROM historical_evidence_samples
        WHERE headline IS NOT NULL
          AND headline ILIKE ANY($1)
          AND ($2::text IS NULL OR country_code = $2)
        ORDER BY day DESC
        LIMIT $3
    """
    return sql, [patterns, country, int(limit)]


def rows_to_archive_matches(
    rows: list[dict[str, Any]],
    claim_terms: list[str],
    claim_figure: float | None,
) -> list[dict[str, Any]]:
    """Turn cold-lane DB rows into unified matches, keeping only rows that
    restate the claim (same-event term recall) — an ILIKE OR-match alone is too
    loose. Pure."""
    import html as _html
    out: list[dict[str, Any]] = []
    for r in rows:
        headline = _html.unescape((r.get("headline") or "").strip())
        if not headline:
            continue
        recall = term_recall(claim_terms, headline)
        if recall < SAME_EVENT_TERM_RECALL:
            continue
        relation = classify_relation(claim_terms, claim_figure, headline)
        day = r.get("day")
        out.append(normalize_match(
            basis="atlas_archive",
            source=r.get("source_name") or _domain(r.get("source_url")),
            url=r.get("source_url"),
            country=r.get("country_code"),
            date=day.isoformat() if hasattr(day, "isoformat") else (
                str(day) if day else None),
            snippet=headline,
            relation=relation,
        ))
    return out


def articles_to_doc20_matches(
    articles: list[dict[str, Any]],
    claim_terms: list[str],
    claim_figure: float | None,
) -> list[dict[str, Any]]:
    """DOC 2.0 artlist articles → unified matches. Pure (no network)."""
    out: list[dict[str, Any]] = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        relation = classify_relation(claim_terms, claim_figure, title)
        url = a.get("url")
        out.append(normalize_match(
            basis="doc20",
            source=a.get("domain") or _domain(url),
            url=url,
            country=(a.get("sourcecountry") or "").upper() or None,
            date=a.get("seendate"),
            snippet=title,
            relation=relation,
        ))
    return out


def rows_to_hot_matches(
    matches: list[dict[str, Any]],
    claim_terms: list[str],
    claim_figure: float | None,
) -> list[dict[str, Any]]:
    """signal_embeddings semantic matches (research_semantic.fetch_semantic_
    signal_matches output) → unified matches, using each hit's similarity as the
    same-event signal. Pure."""
    out: list[dict[str, Any]] = []
    for m in matches:
        headline = (m.get("headline") or "").strip()
        if not headline:
            continue
        sim = m.get("similarity")
        relation = classify_relation(
            claim_terms, claim_figure, headline, similarity=sim)
        ts = m.get("timestamp")
        out.append(normalize_match(
            basis="atlas_hot",
            source=m.get("source_name"),
            # source_url now carried through fetch_semantic_signal_matches
            # (council R3 P1: hot-lane corroboration used to emit url:null =
            # zero clickable receipts on the surface built to deliver them).
            url=m.get("source_url"),
            country=m.get("country_code"),
            date=ts[:10] if isinstance(ts, str) else None,
            snippet=headline,
            relation=relation,
            similarity=sim,
        ))
    return out


# ── DOC 2.0 fetch WITH explicit status (honest degraded mode) ────────────────

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_DOC20_TIMEOUT = 25.0

# #260 DOC 2.0 cache + backoff. Positive cache holds ONLY status=="ok"
# payloads (a throttle notice must never be replayed as an answer); the
# cooldown marker is a short negative cache set after a 429/notice so
# repeated dossier renders stop hammering GDELT while it is throttling us.
# source_status still reports "throttled" honestly during the cooldown —
# the marker changes traffic, never the story we tell.
DOC20_CACHE_TTL = 6 * 3600      # seconds — ok payloads
DOC20_COOLDOWN_TTL = 120        # seconds — negative marker after a throttle
_DOC20_CACHE_PREFIX = "doc20:v1:"
_DOC20_COOLDOWN_KEY = "doc20:cooldown:v1"


def doc20_cache_key(query: str, timespan: str = "1m") -> str:
    """Versioned key over sha1(query|timespan) — stable across processes."""
    import hashlib
    digest = hashlib.sha1(f"{query}|{timespan}".encode("utf-8")).hexdigest()
    return f"{_DOC20_CACHE_PREFIX}{digest}"


def _resolve_doc20_cache() -> Any | None:
    """Best-effort app-level Redis. None outside the API process (scripts,
    unit tests) or when Redis is down — the lane degrades to no-cache."""
    try:
        from app.main_v2 import app as _app
        return getattr(_app.state, "redis", None)
    except Exception:  # noqa: BLE001 — import/app-state failure = no cache
        return None


async def doc20_cache_lookup(cache: Any, key: str) -> dict[str, Any] | None:
    """Pre-flight cache check: cached ok payload → {"...", "cache": "hit"};
    active cooldown → honest throttled response with cache: "cooldown";
    neither (or any cache error) → None (caller does the network fetch)."""
    if cache is None:
        return None
    try:
        cached = await cache.get(key)
        if cached:
            payload = json.loads(cached)
            payload["cache"] = "hit"
            return payload
        if await cache.get(_DOC20_COOLDOWN_KEY):
            return {"status": "throttled", "articles": [], "cache": "cooldown"}
    except Exception as exc:  # noqa: BLE001 — cache is best-effort
        _log.warning("doc20 cache lookup failed: %s", str(exc)[:120])
    return None


async def doc20_cache_store(cache: Any, key: str,
                            result: dict[str, Any]) -> None:
    """Post-fetch cache write: ok → positive cache (6h); throttled → set the
    short cooldown marker. 'down' is cached as nothing — a network blip must
    not suppress the next attempt."""
    if cache is None:
        return
    try:
        status = result.get("status")
        if status == "ok":
            await cache.setex(key, DOC20_CACHE_TTL, json.dumps(
                {"status": "ok", "articles": result.get("articles", [])}))
        elif status == "throttled":
            await cache.setex(_DOC20_COOLDOWN_KEY, DOC20_COOLDOWN_TTL, "1")
    except Exception as exc:  # noqa: BLE001 — cache is best-effort
        _log.warning("doc20 cache store failed: %s", str(exc)[:120])


async def doc20_fetch_status(
    query: str,
    *,
    timespan: str = "1m",
    maxrecords: int = 40,
    cache: Any | None = None,
) -> dict[str, Any]:
    """Fetch DOC 2.0 and CLASSIFY the outcome so the caller can be honest:
      {"status": "ok"|"throttled"|"down", "articles": [...],
       "cache": "hit"|"miss"|"cooldown"}.
    Non-JSON body (the free tier answers over-limit with an HTML notice) →
    'throttled'; HTTP 429 → 'throttled'; timeout/refused/other → 'down'.
    Shares the external_depth per-process 1-req/5s throttle so this lane never
    trips the rate limit on top of the depth lane. Responses are Redis-cached
    (#260): ok payloads 6h; a throttle sets a 120s cooldown marker so we stop
    hammering while throttled. No Redis → straight to the network."""
    if not query:
        return {"status": "down", "articles": [], "cache": "miss"}

    if cache is None:
        cache = _resolve_doc20_cache()
    key = doc20_cache_key(query, timespan)
    cached = await doc20_cache_lookup(cache, key)
    if cached is not None:
        return cached
    params = _urlparse.urlencode({
        "query": query, "mode": "artlist", "format": "json",
        "maxrecords": maxrecords, "timespan": timespan, "sort": "hybridrel",
    })
    url = f"{DOC_URL}?{params}"

    def _get() -> tuple[int, bytes]:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "atlas/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=_DOC20_TIMEOUT) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    try:
        # Reuse the external-depth global throttle when available.
        try:
            from app.services.external_depth import _throttle
            await _throttle()
        except Exception:  # noqa: BLE001 — throttle is best-effort
            pass
        status_code, body = await _asyncio.wait_for(
            _asyncio.get_event_loop().run_in_executor(None, _get),
            timeout=_DOC20_TIMEOUT + 2,
        )
    except Exception as exc:  # noqa: BLE001 — timeout / refused / DNS
        _log.warning("doc20 corroboration lane down (%s): %s", query, str(exc)[:120])
        return {"status": "down", "articles": [], "cache": "miss"}

    result = _classify_doc20(status_code, body)
    await doc20_cache_store(cache, key, result)
    result["cache"] = "miss"
    return result


def _classify_doc20(status_code: int, body: bytes) -> dict[str, Any]:
    """Pure: (HTTP status, body) → {"status": ok|throttled|down, "articles"}.
    Extracted so the JSON-parse path (a 200 with a real JSON body — the
    publishable success case) is unit-testable without a live fetch; the panel
    gate caught a NameError here that the orchestrator-level mocks skipped."""
    if status_code == 429:
        return {"status": "throttled", "articles": []}
    if status_code >= 500:
        return {"status": "down", "articles": []}
    try:
        articles = json.loads(body).get("articles", [])
    except (json.JSONDecodeError, AttributeError, ValueError, TypeError):
        # Over-limit HTML/text notice, not JSON — the free tier's throttle tell.
        return {"status": "throttled", "articles": []}
    return {"status": "ok", "articles": articles}


# ── orchestrator ─────────────────────────────────────────────────────────────

async def corroborate_claim(
    *,
    headline: str,
    figure: float | None = None,
    country: str | None = None,
    published_date: str | None = None,
    conn: Any | None = None,
    embed_fn: Any | None = None,
    hot_fetch: Any | None = None,
    doc20_fetch: Any | None = None,
    hot_hours: int = 192,
) -> dict[str, Any]:
    """Corroborate ONE claim across DOC 2.0 ∪ atlas_hot ∪ atlas_archive.

    Every corpus is best-effort and independently reported in `source_status`.
    A throttled/down DOC 2.0 NEVER suppresses the Atlas matches — the response
    is explicit about what was and wasn't reached (Marcos's honest-degraded
    requirement). All I/O is injectable so the contract is unit-tested offline:
      * doc20_fetch(query) -> {"status", "articles"}
      * hot_fetch(query_vec) -> list[semantic match dict]  (needs embed_fn+conn)
      * conn -> asyncpg-style connection for the cold archive lane
    """
    parsed = extract_claim_terms(headline, country=country)
    terms, query = parsed["terms"], parsed["query"]
    if figure is None:
        figure = extract_figure(headline)

    source_status: dict[str, str] = {
        "doc20": "not_queried",
        "atlas_hot": "not_queried",
        "atlas_archive": "not_queried",
    }
    matches: list[dict[str, Any]] = []

    # ── DOC 2.0 (query-time external) ──
    fetcher = doc20_fetch or doc20_fetch_status
    try:
        doc = await fetcher(query)
    except Exception as exc:  # noqa: BLE001
        _log.warning("doc20 fetch raised: %s", str(exc)[:120])
        doc = {"status": "down", "articles": []}
    source_status["doc20"] = doc.get("status", "down")
    doc20_cache = doc.get("cache")  # "hit"|"miss"|"cooldown"|None (injected)
    matches += articles_to_doc20_matches(
        doc.get("articles", []) or [], terms, figure)

    # ── atlas_hot (semantic over signal_embeddings) ──
    if conn is not None and embed_fn is not None and query:
        try:
            query_vec = await _maybe_await(embed_fn(f"query: {headline}"))
            if query_vec:
                hf = hot_fetch or _default_hot_fetch
                hot = await hf(conn, query_vec, hot_hours)
                matches += rows_to_hot_matches(hot or [], terms, figure)
                source_status["atlas_hot"] = "ok"
            else:
                source_status["atlas_hot"] = "unavailable"
        except Exception as exc:  # noqa: BLE001
            _log.warning("atlas_hot lane unavailable: %s", str(exc)[:120])
            source_status["atlas_hot"] = "unavailable"

    # ── atlas_archive (text over historical_evidence_samples) ──
    if conn is not None and terms:
        try:
            sql, params = build_cold_corpus_query(terms, country=country)
            rows = await conn.fetch(sql, *params)
            row_dicts = [dict(r) for r in rows]
            matches += rows_to_archive_matches(row_dicts, terms, figure)
            source_status["atlas_archive"] = "ok"
        except Exception as exc:  # noqa: BLE001
            _log.warning("atlas_archive lane unavailable: %s", str(exc)[:120])
            source_status["atlas_archive"] = "unavailable"

    matches = dedup_matches(matches)
    corroborating = [m for m in matches if m["relation"] == "corroborates"]
    contradicting = [m for m in matches if m["relation"] == "contradicts"]
    context = [m for m in matches if m["relation"] == "context"]

    return {
        "contract": "corroboration-v1",
        "claim": {
            "headline": headline,
            "figure": figure,
            "country": country,
            "published_date": published_date,
            "query": query,
            "terms": terms[:8],
        },
        "source_status": source_status,
        "corroborating": corroborating,
        "contradicting": contradicting,
        "context": context,
        "verdict": citation_verdict(matches),
        "meta": {
            "figure_match_tolerance": FIGURE_MATCH_TOLERANCE,
            "same_event_term_recall": SAME_EVENT_TERM_RECALL,
            "corroborate_term_recall": CORROBORATE_TERM_RECALL,
            "same_event_similarity": SAME_EVENT_SIMILARITY,
            "cache": doc20_cache,
        },
    }


async def _maybe_await(value: Any) -> Any:
    if _asyncio.iscoroutine(value):
        return await value
    return value


async def _default_hot_fetch(conn: Any, query_vec: list[float],
                             hours: int) -> list[dict[str, Any]]:
    """Bridge to research_semantic's ANN lane over signal_embeddings."""
    from app.services.research_semantic import fetch_semantic_signal_matches
    return await fetch_semantic_signal_matches(
        conn, query_vec, hours=hours, limit=HOT_LANE_LIMIT)
