"""External-depth lane (#161) — DOC 2.0 as query-time evidence enrichment.

Probe verdict (docs/research/doc20/2026-07-06-doc20-probe.md): valuable
EXACTLY where Atlas is thin (Armenia fixture: 21/39 new verifiable articles
in 8 languages); marginal where the firehose covers; latency 16-35s and a
fragile query parser → this lane is ON-DEMAND only, simple keyword queries,
hard timeout, cached, degrades to an honest gap. Never a firehose.

Every result is labeled `external` + `unverified` and carries the #217
credibility tier — external evidence ships WITH its receipts.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import urllib.parse
from typing import Any

from app.services.source_tiers import tier_payload

logger = logging.getLogger(__name__)

DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT_SECONDS = 25.0  # measured p50 ~16-35s; beyond this = honest gap
_CACHE_TTL = 1800.0
_MAX_RECORDS = 40

_cache: dict[str, tuple[float, dict | None]] = {}

_STOP = {
    "the", "and", "in", "of", "on", "for", "a", "an", "to", "at",
    "updates", "update", "news", "coverage", "crisis", "situation",
}


def build_query(label: str, country: str | None = None) -> str:
    """DOC 2.0's parser is fragile with OR-groups (probe: 0 results on a
    valid-looking OR query) — emit the SIMPLEST form: significant label
    tokens, space-joined (implicit AND)."""
    toks = [t for t in re.findall(r"[A-Za-zÀ-ÿ]{3,}", label.lower())
            if t not in _STOP][:5]
    q = " ".join(toks)
    if country and len(q.split()) < 4 and country.lower() not in q:
        q = f"{q} {country}".strip()
    return q


async def fetch_external_depth(
    label: str,
    country: str | None = None,
    known_urls: set[str] | None = None,
) -> dict | None:
    """Returns {items, query, fetched_at, source: 'gdelt-doc-2.0'} or None
    (lane unavailable — caller renders the gap, never an error)."""
    query = build_query(label, country)
    if not query:
        return None
    now = time.time()
    hit = _cache.get(query)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]

    params = urllib.parse.urlencode({
        "query": query, "mode": "artlist", "format": "json",
        "maxrecords": _MAX_RECORDS, "timespan": "3d", "sort": "hybridrel",
    })
    url = f"{DOC_URL}?{params}"

    def _get() -> bytes:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "atlas/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as r:
            return r.read()

    try:
        body = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _get),
            timeout=_TIMEOUT_SECONDS + 2,
        )
        arts = json.loads(body).get("articles", [])
    except Exception as exc:  # noqa: BLE001 — any failure = honest gap
        logger.warning("external depth lane unavailable (%s): %s", query, exc)
        _cache[query] = (now, None)  # negative-cache the flaky window too
        return None

    known = known_urls or set()
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for a in arts:
        u = a.get("url") or ""
        title = (a.get("title") or "").strip()
        tkey = title.lower()[:80]
        if not title or u in known or tkey in seen_titles:
            continue
        seen_titles.add(tkey)
        dom = urllib.parse.urlparse(u).netloc.removeprefix("www.")
        items.append({
            "title": title[:200],
            "url": u,
            "domain": dom,
            "language": (a.get("language") or "").lower() or None,
            "seendate": a.get("seendate"),
            "verified": False,
            "lane": "external",
            "credibility": tier_payload(dom),
        })
    result = {
        "source": "gdelt-doc-2.0",
        "query": query,
        "items": items[:25],
        "already_known_excluded": sum(1 for a in arts
                                      if (a.get("url") or "") in known),
        "fetched_at": now,
    }
    _cache[query] = (now, result)
    return result
