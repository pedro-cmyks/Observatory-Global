"""Workbench article enrichment F1 — fetch + extract pinned pages.

Spec: docs/specs/2026-07-20-workbench-article-enrichment.md.

Pinned evidence URLs (5-50 per investigation, analyst-curated) are fetched
server-side, run through trafilatura, and cached in `pinned_articles` keyed by
sha1(url) — shared across users, no user data in the row. Partial yield is a
NORMAL product state (paywalls/bot walls/consent walls): every terminal status
is honest, never dressed as success.

Abuse posture (the endpoint is public; pins are anonymous localStorage):
  1. scheme gate — http/https only;
  2. SSRF gate — every hop's host must resolve to public IPs only (private/
     loopback/link-local/reserved rejected), redirects re-checked per hop,
     max 5 hops;
  3. known-domain gate — only domains observed in signals_v2 (48h) or
     historical_evidence_samples may be fetched. Interim trade (spec §1.2):
     exact-URL matching would need an index signals_v2 can't afford
     (churn/bloat history); domain gate + SSRF + per-IP rate limit is the
     honest v1. Fails CLOSED when the domain set can't be loaded.
No robots.txt parsing in v1: honest UA, tiny volume, curated news domains;
401/403 map to status 'robots'.

Frozen-evidence discipline: a terminal row is never overwritten (the UPDATE
carries `WHERE status='pending'`); `pending` rows older than 10 min are
re-eligible (a deploy can kill the background task — requeue at read time).
DNS-dead / 404 / 410 pages fall back to the Wayback Machine (labeled
via='wayback') — link rot is exactly what pin-time fetching preserves against.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import re
import time
from urllib.parse import urljoin, urlsplit

import aiohttp

from app import db

logger = logging.getLogger(__name__)


def _pool():
    # db.pool is assigned at app startup (main_v2); absent in unit tests/CLI.
    return getattr(db, "pool", None)

USER_AGENT = "AtlasResearch/1.0 (+https://observatorio-atlas.vercel.app; analyst pin enrichment)"
FETCH_TIMEOUT_S = 10
BODY_CAP_BYTES = 2 * 1024 * 1024
MAX_REDIRECT_HOPS = 5
MIN_OK_WORDS = 120           # below this a 200 reads as a wall, not an article
EXCERPT_WORDS = 60           # display/export-safe excerpt length (legal: never full text)
PENDING_STALE_S = 600        # pending older than this is re-eligible
CONCURRENCY = 3
_KNOWN_DOMAINS_TTL_S = 3600

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}

_sem = asyncio.Semaphore(CONCURRENCY)
_domain_locks: dict[str, asyncio.Lock] = {}
_known_domains_cache: dict = {"at": 0.0, "domains": None}

_KNOWN_DOMAINS_SQL = """
SELECT DISTINCT lower(substring(source_url FROM '://([^/]+)')) AS d
FROM signals_v2
WHERE created_at > now() - interval '48 hours'
  AND source_url LIKE 'http%'
UNION
SELECT DISTINCT lower(substring(source_url FROM '://([^/]+)')) AS d
FROM historical_evidence_samples
WHERE source_url LIKE 'http%'
"""


def url_hash(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


async def known_domains() -> frozenset | None:
    """Domains Atlas has actually observed (48h hot + archive samples).

    Cached in-process 1h; stale cache is served on DB failure; with no cache
    at all the gate FAILS CLOSED (caller rejects).
    """
    now = time.monotonic()
    cached = _known_domains_cache["domains"]
    if cached is not None and now - _known_domains_cache["at"] < _KNOWN_DOMAINS_TTL_S:
        return cached
    if _pool() is None:
        return cached
    try:
        async with _pool().acquire() as conn:
            rows = await conn.fetch(_KNOWN_DOMAINS_SQL)
        domains = frozenset(_strip_www(r["d"]) for r in rows if r["d"])
        _known_domains_cache.update(at=now, domains=domains)
        return domains
    except Exception as exc:  # pooler timeout, transient — serve stale if any
        logger.warning("known_domains query failed: %s", str(exc)[:200])
        return cached


def _domain_known(host: str, domains: frozenset) -> bool:
    h = _strip_www(host)
    if h in domains:
        return True
    # subdomain of a known domain (edition.cnn.com vs cnn.com)
    parts = h.split(".")
    for i in range(1, len(parts) - 1):
        if ".".join(parts[i:]) in domains:
            return True
    return False


async def _host_public(host: str) -> bool:
    """Resolve and require EVERY address to be public (SSRF gate)."""
    if not host:
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except OSError:
        return False
    addrs = {info[4][0] for info in infos}
    if not addrs:
        return False
    for a in addrs:
        try:
            ip = ipaddress.ip_address(a)
        except ValueError:
            return False
        if not ip.is_global or ip.is_multicast:
            return False
    return True


async def gate_url(url: str) -> tuple[bool, str]:
    """(allowed, reason). Applied to the ORIGINAL url before any fetch."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False, "invalid_url"
    if parts.scheme not in ("http", "https"):
        return False, "scheme"
    host = (parts.hostname or "").lower()
    if not host:
        return False, "invalid_url"
    domains = await known_domains()
    if domains is None:
        return False, "domain_set_unavailable"   # fail closed
    if not _domain_known(host, domains):
        return False, "domain_not_known"
    if not await _host_public(host):
        return False, "host_not_public"
    return True, "ok"


async def _fetch_raw(session: aiohttp.ClientSession, url: str) -> tuple[int, str, bytes, str]:
    """Manual redirect loop so every hop passes the SSRF gate.

    Returns (http_status, content_type, body, final_url). Raises on network
    errors; raises ValueError('unsafe_redirect') when a hop fails the gate.
    """
    cur = url
    for _ in range(MAX_REDIRECT_HOPS + 1):
        parts = urlsplit(cur)
        if parts.scheme not in ("http", "https") or not await _host_public((parts.hostname or "").lower()):
            raise ValueError("unsafe_redirect")
        async with session.get(cur, allow_redirects=False) as resp:
            if resp.status in _REDIRECT_STATUSES:
                loc = resp.headers.get("Location")
                if not loc:
                    return resp.status, "", b"", cur
                cur = urljoin(cur, loc)
                continue
            body = await resp.content.read(BODY_CAP_BYTES)
            ctype = (resp.headers.get("Content-Type") or "").lower()
            return resp.status, ctype, body, cur
    raise ValueError("too_many_redirects")


async def _wayback_lookup(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(
            "https://archive.org/wayback/available", params={"url": url}
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
        snap = (data.get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("available") and str(snap.get("status", "")).startswith("2"):
            u = snap.get("url") or ""
            return u.replace("http://web.archive.org", "https://web.archive.org") or None
    except Exception:
        return None
    return None


def _extract(body: bytes, ctype: str, url: str) -> dict | None:
    """trafilatura pass → {title, text, lang?} or None when nothing extracts."""
    if ctype and ("html" not in ctype and "xml" not in ctype and "text/plain" not in ctype):
        return {"unsupported": True}
    try:
        html_text = body.decode("utf-8", errors="replace")
    except Exception:
        return None
    try:
        import trafilatura
        raw = trafilatura.extract(
            html_text, url=url, output_format="json", with_metadata=True,
            include_comments=False, favor_precision=True,
        )
    except Exception as exc:
        logger.warning("trafilatura failed for %s: %s", url, str(exc)[:200])
        return None
    if not raw:
        return None
    try:
        doc = json.loads(raw)
    except Exception:
        return None
    text = (doc.get("text") or "").strip()
    if not text:
        return None
    return {
        "title": (doc.get("title") or "").strip() or None,
        "text": text,
        "lang": (doc.get("language") or None),
    }


def _excerpt(text: str) -> str:
    words = text.split()
    cut = " ".join(words[:EXCERPT_WORDS])
    return cut + ("…" if len(words) > EXCERPT_WORDS else "")


def classify_fetch(http_status: int, extracted: dict | None) -> tuple[str, str | None]:
    """Status machine → (status, fetch_error). Honest by construction."""
    if http_status in (401, 403):
        return "robots", f"http_{http_status}"
    if http_status == 402:
        return "paywall", "http_402"
    if http_status in (404, 410):
        return "error", f"http_{http_status}"
    if http_status >= 400:
        return "error", f"http_{http_status}"
    if extracted is None:
        return "paywall", "no_extractable_text"
    if extracted.get("unsupported"):
        return "unsupported", "non_html_content"
    words = len(extracted["text"].split())
    if words < MIN_OK_WORDS:
        return "paywall", f"thin_extract_{words}w"
    return "ok", None


async def process_url(url: str) -> None:
    """Worker: fetch → extract → persist. Never raises (fire-and-forget)."""
    h = url_hash(url)
    domain = host_of(url)
    lock = _domain_locks.setdefault(domain, asyncio.Lock())
    if len(_domain_locks) > 500:
        _domain_locks.clear()
    try:
        async with _sem, lock:
            timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
            headers = {"User-Agent": USER_AGENT, "Accept-Language": "en, es;q=0.8, *;q=0.5"}
            via = "live"
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                status_code: int | None = None
                body: bytes = b""
                ctype = ""
                err: str | None = None
                try:
                    status_code, ctype, body, _final = await _fetch_raw(session, url)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError) as exc:
                    err = type(exc).__name__
                # Dead page → Wayback fallback (link rot is the enemy).
                if err is not None or (status_code in (404, 410)):
                    wb = await _wayback_lookup(session, url)
                    if wb:
                        try:
                            status_code, ctype, body, _final = await _fetch_raw(session, wb)
                            via = "wayback"
                            err = None
                        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError) as exc:
                            err = err or type(exc).__name__
                if err is not None and status_code is None:
                    await _persist_terminal(h, status="error", http_status=None, via="live",
                                            fetch_error=err)
                    return
                extracted = _extract(body, ctype, url) if body else None
                status, fetch_error = classify_fetch(status_code or 0, extracted)
                row: dict = {"status": status, "http_status": status_code, "via": via,
                             "fetch_error": fetch_error}
                if status == "ok" and extracted:
                    text = extracted["text"]
                    row.update(
                        title=extracted.get("title"),
                        outlet=_strip_www(domain),
                        lang=extracted.get("lang"),
                        extracted_text=text,
                        excerpt=_excerpt(text),
                        word_count=len(text.split()),
                        content_hash=hashlib.sha1(text.encode("utf-8")).hexdigest(),
                    )
                await _persist_terminal(h, **row)
    except Exception as exc:  # never propagate out of a background task
        logger.warning("article fetch worker failed for %s: %s", url, str(exc)[:200])
        try:
            await _persist_terminal(h, status="error", http_status=None, via="live",
                                    fetch_error=f"worker_{type(exc).__name__}")
        except Exception:
            pass


async def _persist_terminal(h: str, *, status: str, http_status: int | None, via: str,
                            fetch_error: str | None = None, title: str | None = None,
                            outlet: str | None = None, lang: str | None = None,
                            extracted_text: str | None = None, excerpt: str | None = None,
                            word_count: int | None = None, content_hash: str | None = None) -> None:
    if _pool() is None:
        return
    async with _pool().acquire() as conn:
        # status='pending' guard: a terminal success is never overwritten.
        await conn.execute(
            """
            UPDATE pinned_articles
            SET status=$2, http_status=$3, via=$4, fetch_error=$5, title=$6,
                outlet=$7, lang=$8, extracted_text=$9, excerpt=$10,
                word_count=$11, content_hash=$12, fetched_at=now()
            WHERE url_hash=$1 AND status='pending'
            """,
            h, status, http_status, via, fetch_error, title, outlet,
            (lang or "")[:16] or None, extracted_text, excerpt, word_count, content_hash,
        )


async def enqueue_fetches(urls: list[str]) -> list[dict]:
    """Gate + register + spawn background fetches. Returns per-URL status.

    Response statuses: an existing row's status verbatim, 'queued' (new row,
    task spawned), or 'rejected' (+reason).
    """
    out: list[dict] = []
    seen: set[str] = set()
    for url in urls:
        url = (url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        h = url_hash(url)
        allowed, reason = await gate_url(url)
        if not allowed:
            out.append({"url": url, "status": "rejected", "reason": reason})
            continue
        if _pool() is None:
            out.append({"url": url, "status": "rejected", "reason": "db_unavailable"})
            continue
        async with _pool().acquire() as conn:
            inserted = await conn.fetchrow(
                """
                INSERT INTO pinned_articles (url_hash, url) VALUES ($1, $2)
                ON CONFLICT (url_hash) DO NOTHING
                RETURNING url_hash
                """,
                h, url,
            )
            if inserted:
                spawn = True
            else:
                # Existing row: requeue ONLY a stale pending (race-safe across
                # processes — the UPDATE's WHERE wins exactly once).
                requeued = await conn.fetchrow(
                    """
                    UPDATE pinned_articles SET created_at = now()
                    WHERE url_hash = $1 AND status = 'pending' AND fetched_at IS NULL
                      AND created_at < now() - make_interval(secs => $2)
                    RETURNING url_hash
                    """,
                    h, PENDING_STALE_S,
                )
                spawn = requeued is not None
        if spawn:
            asyncio.get_running_loop().create_task(process_url(url))
            out.append({"url": url, "status": "queued"})
        else:
            async with _pool().acquire() as conn:
                cur = await conn.fetchval(
                    "SELECT status FROM pinned_articles WHERE url_hash = $1", h)
            out.append({"url": url, "status": cur or "pending"})
    return out


_ARTICLE_STATE_FIELDS = (
    "url, status, via, http_status, title, outlet, lang, excerpt, word_count, "
    "fetch_error, fetched_at"
)


async def article_states(urls: list[str]) -> list[dict]:
    """Cached display states for a set of URLs. NEVER serves extracted_text
    (legal: excerpts only cross the API; full text is server-side substrate)."""
    hashes = {url_hash(u): u for u in urls if (u or "").strip()}
    if not hashes or _pool() is None:
        return []
    async with _pool().acquire() as conn:
        rows = await conn.fetch(
            f"SELECT url_hash, {_ARTICLE_STATE_FIELDS} FROM pinned_articles WHERE url_hash = ANY($1)",
            list(hashes.keys()),
        )
    out = []
    for r in rows:
        out.append({
            "url": r["url"], "status": r["status"], "via": r["via"],
            "http_status": r["http_status"], "title": r["title"],
            "outlet": r["outlet"], "lang": r["lang"], "excerpt": r["excerpt"],
            "word_count": r["word_count"], "fetch_error": r["fetch_error"],
            "fetched_at": r["fetched_at"].isoformat() + "Z" if r["fetched_at"] else None,
        })
    return out


async def full_texts_for(urls: list[str], *, cap_chars: int = 6000) -> dict[str, dict]:
    """Server-side consumer path (synthesize / F2 AI-read): url -> {text, title,
    outlet, fetched_at}. Full text never crosses the public API."""
    hashes = {url_hash(u): u for u in urls if (u or "").strip()}
    if not hashes or _pool() is None:
        return {}
    async with _pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT url_hash, url, title, outlet, extracted_text, fetched_at
            FROM pinned_articles
            WHERE url_hash = ANY($1) AND status = 'ok' AND extracted_text IS NOT NULL
            """,
            list(hashes.keys()),
        )
    out: dict[str, dict] = {}
    for r in rows:
        out[r["url"]] = {
            "text": (r["extracted_text"] or "")[:cap_chars],
            "title": r["title"], "outlet": r["outlet"],
            "fetched_at": r["fetched_at"].isoformat() + "Z" if r["fetched_at"] else None,
        }
    return out
