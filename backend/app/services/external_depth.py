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
# A FAILED window cools down for seconds, not half an hour. The old code
# negative-cached every failure for the full 1800s, so one transient timeout
# made the lane read "unavailable" on every re-run for 30 minutes — the
# 1-in-4 reliability the fresh Frank test measured (docs/research/gold/
# 2026-08-12-frank-test-fresh.md §3a). Successes still cache long.
_FAIL_CACHE_TTL = 60.0
_MAX_RECORDS = 40

_cache: dict[str, tuple[float, dict]] = {}

# DOC 2.0 hard rate limit: ONE request per 5 seconds per IP (the API answers
# excess requests with an HTML notice, not JSON — measured on the P0.6b
# corroboration fixture: concurrent gather → 3 of 6 queries rejected). All
# fetches in this process serialize through this throttle, INCLUDING the
# concurrent per-pin queries of the dossier corroboration lane: `asyncio.gather`
# starts them together, this lock releases them 5.1s apart.
_RATE_INTERVAL_S = 5.1
_rate_lock: asyncio.Lock | None = None
_last_fire = 0.0


async def throttle() -> None:
    """Release at most one DOC 2.0 request per `_RATE_INTERVAL_S`, process-wide.

    Public because the per-claim lane (corroboration.doc20_fetch_status) shares
    it: two lanes each honoring their own limit would still break the API's.
    """
    global _rate_lock, _last_fire
    if _rate_lock is None:
        _rate_lock = asyncio.Lock()
    async with _rate_lock:
        wait = _RATE_INTERVAL_S - (time.monotonic() - _last_fire)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_fire = time.monotonic()


# Back-compat alias — older call sites imported the private name.
_throttle = throttle

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


def _build_getter(url: str):
    """The blocking fetch, as a factory so tests can replace the network
    without patching urllib globally. Returns (http_status, body)."""

    def _get() -> tuple[int, bytes]:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "atlas/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    return _get


async def fetch_external_depth_status(
    label: str,
    country: str | None = None,
    known_urls: set[str] | None = None,
    *,
    timespan: str = "3d",
    raw_query: str | None = None,
) -> dict:
    """The fetch WITH its outcome named:

        {"status": "ok" | "throttled" | "down" | "skipped", "result": dict|None}

    `ok` covers a measured zero (`items: []`) — "nobody covered this" is an
    answer. `throttled` is the DOC 2.0 rate limit (HTTP 429, or the free tier's
    HTML over-limit notice served with a 200). `down` is timeout/DNS/5xx. The
    dossier lane needs the distinction: a throttled pin must not read the same
    as a pin whose story genuinely has no web coverage.
    """
    query = raw_query if raw_query is not None else build_query(label, country)
    if not query:
        return {"status": "skipped", "result": None}
    now = time.time()
    cache_key = f"{query}|{timespan}"
    hit = _cache.get(cache_key)
    if hit:
        cached_status = hit[1].get("status")
        ttl = _CACHE_TTL if cached_status == "ok" else _FAIL_CACHE_TTL
        if now - hit[0] < ttl:
            return hit[1]

    params = urllib.parse.urlencode({
        "query": query, "mode": "artlist", "format": "json",
        "maxrecords": _MAX_RECORDS, "timespan": timespan, "sort": "hybridrel",
    })
    url = f"{DOC_URL}?{params}"
    _get = _build_getter(url)

    try:
        await throttle()   # DOC 2.0: 1 req / 5s per IP, else an HTML notice
        status_code, body = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _get),
            timeout=_TIMEOUT_SECONDS + 2,
        )
    except Exception as exc:  # noqa: BLE001 — timeout / DNS / refused
        logger.warning("external depth lane down (%s): %s", query, str(exc)[:120])
        out = {"status": "down", "result": None}
        _cache[cache_key] = (now, out)
        return out

    if status_code == 429:
        logger.warning("external depth lane throttled (%s)", query)
        out = {"status": "throttled", "result": None}
        _cache[cache_key] = (now, out)
        return out
    if status_code >= 500:
        out = {"status": "down", "result": None}
        _cache[cache_key] = (now, out)
        return out
    try:
        # Over-limit responses come back as HTML or plain text, not JSON —
        # that IS the free tier's throttle tell, not a generic failure.
        arts = json.loads(body).get("articles", [])
    except Exception:  # noqa: BLE001
        logger.warning("external depth lane throttled (non-JSON body) (%s)", query)
        out = {"status": "throttled", "result": None}
        _cache[cache_key] = (now, out)
        return out

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
    out = {"status": "ok", "result": result}
    _cache[cache_key] = (now, out)
    return out


async def fetch_external_depth(
    label: str,
    country: str | None = None,
    known_urls: set[str] | None = None,
    *,
    timespan: str = "3d",
    raw_query: str | None = None,
) -> dict | None:
    """Returns {items, query, fetched_at, source: 'gdelt-doc-2.0'} or None
    (lane unavailable — caller renders the gap, never an error).

    Back-compat façade over `fetch_external_depth_status` for callers that only
    need "did it answer?" (#161 theme-detail depth). Callers that must tell a
    THROTTLED lane from a story with no coverage use the status form."""
    out = await fetch_external_depth_status(
        label, country, known_urls, timespan=timespan, raw_query=raw_query)
    return out.get("result")
