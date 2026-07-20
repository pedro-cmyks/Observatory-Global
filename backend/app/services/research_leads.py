"""Workbench LEADS lane F2.5 — body entities interrogate Atlas.

Spec: docs/specs/2026-07-20-workbench-article-enrichment.md §5b.

Information-model rule: the fetched body NEVER writes the engine substrate —
it QUERIES it. Entities the article bodies reveal (that no headline named)
are matched against what Atlas already measured; each hit is a pinnable lead
carrying its verbatim body quote-context + measured thread hits. Honest by
construction: no bare "related", every lead shows its basis.

Discipline (the #234 rarity lesson, applied twice):
- investigation-DF gate: an entity present in most of the pinned bodies is
  the investigation's own subject, not a lead;
- ubiquity gate: an entity matching more than MAX_THREAD_HITS threads is a
  trump-class actor — matching everything relates nothing. Skipped, counted
  in `suppressed` (no silent filtering).
"""
from __future__ import annotations

import logging

import unicodedata

from app import db
from app.services.article_read import read_articles
from app.services.thread_intelligence import (
    _PERSON_TOPIC_SLUGS_SQL,
    fetch_threads,
)
from app.utils import _is_valid_person

logger = logging.getLogger(__name__)

CONTRACT = "workbench-leads-v0"
POOL_HOURS = 48
POOL_LIMIT = 40
MAX_ENTITIES = 12          # gated entities looked up per call
MAX_THREAD_HITS = 12       # above this = ubiquitous actor, suppressed
MAX_LEADS = 10
DF_MIN_ARTICLES = 3        # investigation-DF gate needs ≥3 read articles to act


def _pool_conn():
    return getattr(db, "pool", None)


def _fold(s: str) -> str:
    """Diacritic-fold + lowercase (Nicușor → nicusor). Cross-language press
    spells the same actor differently; leads must not miss on an ș."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _cp(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _name_matches(a: str, b: str) -> bool:
    """Fold-aware match with transliteration tolerance
    (Zelenski/Zelenskyy/Zelensky). Exact/substring first; else the SURNAME
    (last token) must share a ≥6-char prefix AND, when both carry a first
    name, the first tokens must share ≥3 — a single shared common word
    ("actor", "ministry") never glues two distinct names."""
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return False
    if fa in fb or fb in fa:
        return True
    ta, tb = fa.split(), fb.split()
    if _cp(ta[-1], tb[-1]) < 6:
        return False
    if len(ta) > 1 and len(tb) > 1:
        return _cp(ta[0], tb[0]) >= 3
    return True


def _thread_matches(thread: dict, entity_name: str, matching_slugs: set[str]) -> bool:
    """Fold/variant-aware version of the #234 thread_matches_person semantics:
    dynamic/emergent threads match on top_entities; atlas threads match
    precisely via the persons-array slug set."""
    for e in (thread.get("top_entities") or []):
        if _name_matches(str(e), entity_name):
            return True
    tid = str(thread.get("thread_id", ""))
    if tid.startswith("dynamic-topic-") or tid.startswith("emergent-cluster-"):
        return False
    return any(str(s).lower() in matching_slugs for s in (thread.get("anchor_topics") or []))


def gather_entities(readings: dict[str, dict]) -> list[dict]:
    """Body actors → gated lead candidates with their best quote-context.

    Skips kind=state (a country matches half the pool — too broad to be a
    lead) and persons that fail the shared person gate. Dedupes by lowercase
    name keeping the first (url, role, quote) context seen.
    """
    seen: dict[str, dict] = {}
    n_articles = len(readings)
    for url, r in readings.items():
        quote_by_claim = [c.get("quote") for c in r.get("claims", []) if c.get("quote")]
        for a in r.get("actors", []):
            name = (a.get("name") or "").strip()
            kind = a.get("kind") or "person"
            if len(name) < 3 or kind == "state":
                continue
            if kind == "person" and not _is_valid_person(name):
                continue
            key = name.lower()
            e = seen.get(key)
            if e is None:
                # quote context: first claim quote from the same article that
                # mentions the actor; else the actor's role line.
                quote = next((q for q in quote_by_claim if name.lower() in q.lower()), None)
                seen[key] = {"name": name, "kind": kind, "role": a.get("role") or "",
                             "source_url": url, "quote": quote, "df": 1}
            else:
                e["df"] += 1
    out = []
    for e in seen.values():
        # investigation-DF gate: present in most bodies = the subject itself.
        if n_articles >= DF_MIN_ARTICLES and e["df"] > n_articles / 2:
            e["suppressed"] = "investigation_subject"
        out.append(e)
    return out


def _base_ids(raw_ids: list[str]) -> set[str]:
    """Normalize pinned anchor/thread ids for exclusion matching."""
    out = set()
    for r in raw_ids:
        s = str(r or "").strip().lower()
        if not s:
            continue
        out.add(s)
        if "--" in s:                       # slug--cc → slug
            out.add(s.split("--", 1)[0])
    return out


async def find_leads(urls: list[str], pinned_ids: list[str] | None = None) -> dict:
    """Body entities → measured Atlas thread hits, excluding what is already
    pinned. One pool fetch total; one slugs query per gated entity."""
    readings = await read_articles(urls)
    candidates = gather_entities(readings)
    suppressed = [{"name": c["name"], "reason": c["suppressed"]}
                  for c in candidates if c.get("suppressed")]
    lookups = [c for c in candidates if not c.get("suppressed")][:MAX_ENTITIES]
    base = {
        "contract": CONTRACT,
        "articles_read": len(readings),
        "entities_considered": len(candidates),
        "leads": [],
        "suppressed": suppressed,
        "basis": "actor from fetched article body → measured membership in current Atlas threads; body never writes the engine",
    }
    if not lookups:
        return base
    try:
        pool_threads = await fetch_threads(hours=POOL_HOURS, limit=POOL_LIMIT)
    except Exception as exc:
        logger.warning("leads thread pool fetch failed: %s", str(exc)[:200])
        return {**base, "reason": "thread_pool_unavailable"}
    excluded = _base_ids(pinned_ids or [])
    leads = []
    for ent in lookups:
        person_lower = ent["name"].lower()
        matching_slugs: set[str] = set()
        if ent["kind"] == "person" and _pool_conn() is not None:
            try:
                async with _pool_conn().acquire() as conn:
                    rows = await conn.fetch(_PERSON_TOPIC_SLUGS_SQL, POOL_HOURS, person_lower)
                matching_slugs = {str(r["slug"]).lower() for r in rows}
            except Exception as exc:
                logger.warning("leads slugs query failed for %s: %s", ent["name"], str(exc)[:160])
        hits = []
        for t in pool_threads:
            try:
                if _thread_matches(t, ent["name"], matching_slugs):
                    tid = str(t.get("thread_id") or "")
                    slug = str((t.get("anchor_topics") or [""])[0] or "").lower()
                    if tid.lower() in excluded or (slug and slug in excluded):
                        continue
                    hits.append({
                        "thread_id": tid,
                        "label": t.get("label") or t.get("title"),
                        "signal_count": t.get("signal_count"),
                    })
            except Exception:
                continue
        if not hits:
            continue
        if len(hits) > MAX_THREAD_HITS:
            suppressed.append({"name": ent["name"], "reason": f"ubiquitous_{len(hits)}_threads"})
            continue
        leads.append({
            "entity": ent["name"], "kind": ent["kind"], "role": ent["role"],
            "quote": ent["quote"], "source_url": ent["source_url"],
            "threads": sorted(hits, key=lambda h: -(h.get("signal_count") or 0))[:6],
            "thread_count": len(hits),
        })
    # rarest first — the single-thread actor is the investigative one.
    leads.sort(key=lambda l: (l["thread_count"], -(l["threads"][0].get("signal_count") or 0)))
    return {**base, "leads": leads[:MAX_LEADS], "suppressed": suppressed}
