"""Workbench AI-read F2 — grounded per-article reading + cross-read.

Spec: docs/specs/2026-07-20-workbench-article-enrichment.md §5.

The Workbench is the sanctioned LLM surface (synthesize / corroborate /
insight); this extends it from headlines to the FETCHED BODY. Discipline:

- QUOTE GATE (spec decision 3): every claim MUST carry a verbatim quote from
  the article text. Quotes are validated as substrings (whitespace/curly-quote
  normalized) at parse time — a claim whose quote does not appear in the text
  is DROPPED, silently making hallucinated claims unrepresentable. Cross-read
  compares only quote-backed claims and labels findings "possible tension —
  verify quotes"; it never asserts contradiction as fact.
- CACHE: readings persist in ai_readings keyed by (url_hash, prompt_version) —
  regenerating a dossier or reopening an investigation never re-pays inference.
- BOUNDARY: investigation-scoped. Nothing here writes the Atlas engine
  substrate (no topic assignment, no member writes).
- Chain: insight_llm.generate_insight (Anthropic → DeepSeek), cost-ledgered
  under surfaces 'workbench-ai-read' / 'workbench-cross-read'.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from app import db
from app.services.article_fetch import full_texts_for, url_hash
from app.services.insight_llm import generate_insight

logger = logging.getLogger(__name__)

PROMPT_VERSION = "read-v1"
MAX_CLAIMS = 8
MAX_ACTORS = 10
MAX_QUOTE_CHARS = 350
TEXT_CAP_CHARS = 6000
READ_CONCURRENCY = 3

_READ_SYSTEM = (
    "You read ONE news article and output STRICT JSON only (no prose, no "
    "fences). Schema:\n"
    '{"claims":[{"text":"one-sentence claim the article makes","quote":"VERBATIM '
    'span from the article (max ~40 words) that backs the claim","attribution":'
    '"asserted"|"attributed","attributed_to":"who, when attribution=attributed, else null"}],'
    '"actors":[{"name":"...","kind":"person"|"org"|"state"|"group","role":"few words"}],'
    '"numbers":[{"value":"...","what":"..."}],'
    '"gaps":["something a reader would want that the article does NOT say"]}\n'
    "HARD RULES: quotes must be EXACT verbatim substrings of the supplied text "
    "— never paraphrase inside \"quote\"; a claim without a verbatim quote is "
    "forbidden — omit it; use ONLY the supplied text, never outside knowledge; "
    "distinguish what the outlet ASSERTS from what it ATTRIBUTES to sources "
    "('according to', officials said, etc.); max 8 claims, 10 actors, 6 gaps; "
    "answer in the article's own language for quotes, English for everything else."
)

_CROSS_SYSTEM = (
    "You compare quote-backed claims extracted from SEVERAL news articles an "
    "analyst pinned. Output STRICT JSON only:\n"
    '{"findings":[{"kind":"corroboration"|"tension","a":"<claim id>","b":"<claim id>",'
    '"note":"1-2 plain sentences naming what aligns or diverges"}]}\n'
    "HARD RULES: use ONLY the supplied claims and their quotes — never outside "
    "knowledge; reference claims ONLY by their given ids; report a tension only "
    "when the quotes actually point different ways (numbers, actors, causality, "
    "framing) — topical overlap alone is neither; if nothing aligns or diverges, "
    'return {"findings":[]}; max 8 findings.'
)


def _norm(s: str) -> str:
    """Whitespace + typographic-quote normalization for verbatim checking."""
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def validate_reading(parsed: dict, article_text: str) -> dict:
    """Enforce the quote gate + caps. Returns the surviving reading (possibly
    with zero claims — an honest empty read, never an invented one)."""
    text_norm = _norm(article_text)
    claims = []
    dropped = 0
    for c in (parsed.get("claims") or [])[: MAX_CLAIMS * 2]:
        if not isinstance(c, dict):
            continue
        quote = str(c.get("quote") or "").strip()
        claim_text = str(c.get("text") or "").strip()
        if not quote or not claim_text or len(quote) > MAX_QUOTE_CHARS:
            dropped += 1
            continue
        if _norm(quote) not in text_norm:
            dropped += 1          # hallucinated / paraphrased quote → claim dies
            continue
        attribution = c.get("attribution")
        if attribution not in ("asserted", "attributed"):
            attribution = "asserted"
        claims.append({
            "text": claim_text[:400],
            "quote": quote,
            "attribution": attribution,
            "attributed_to": (str(c.get("attributed_to"))[:120]
                              if attribution == "attributed" and c.get("attributed_to") else None),
        })
        if len(claims) >= MAX_CLAIMS:
            break
    actors = []
    for a in (parsed.get("actors") or [])[:MAX_ACTORS]:
        if not isinstance(a, dict):
            continue
        name = str(a.get("name") or "").strip()
        if len(name) < 3 or name.isdigit():
            continue
        kind = a.get("kind") if a.get("kind") in ("person", "org", "state", "group") else "person"
        actors.append({"name": name[:120], "kind": kind, "role": str(a.get("role") or "")[:160]})
    numbers = [
        {"value": str(n.get("value"))[:60], "what": str(n.get("what"))[:160]}
        for n in (parsed.get("numbers") or [])[:8]
        if isinstance(n, dict) and n.get("value")
    ]
    gaps = [str(g)[:200] for g in (parsed.get("gaps") or [])[:6] if str(g).strip()]
    return {"claims": claims, "actors": actors, "numbers": numbers, "gaps": gaps,
            "dropped_claims": dropped}


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _pool():
    return getattr(db, "pool", None)


async def _cached_readings(hashes: list[str]) -> dict[str, dict]:
    if not hashes or _pool() is None:
        return {}
    async with _pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT url_hash, model, reading, created_at FROM ai_readings "
            "WHERE url_hash = ANY($1) AND prompt_version = $2",
            hashes, PROMPT_VERSION,
        )
    out = {}
    for r in rows:
        reading = r["reading"]
        if isinstance(reading, str):
            try:
                reading = json.loads(reading)
            except Exception:
                continue
        out[r["url_hash"]] = {**reading, "model": r["model"],
                              "read_at": r["created_at"].isoformat() + "Z"}
    return out


async def _store_reading(h: str, model: str, reading: dict) -> None:
    if _pool() is None:
        return
    async with _pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO ai_readings (url_hash, prompt_version, model, reading) "
            "VALUES ($1, $2, $3, $4::jsonb) ON CONFLICT (url_hash, prompt_version) DO NOTHING",
            h, PROMPT_VERSION, model, json.dumps(reading),
        )


async def _read_one(url: str, art: dict) -> tuple[str, dict | None]:
    text = (art.get("text") or "")[:TEXT_CAP_CHARS]
    if not text:
        return url, None
    user = f"TITLE: {art.get('title') or '(untitled)'}\nOUTLET: {art.get('outlet') or 'unknown'}\n\nARTICLE TEXT:\n{text}"
    raw, provider, error, usage = await generate_insight(
        _READ_SYSTEM, user, max_tokens=1400, surface="workbench-ai-read",
    )
    if not raw:
        logger.warning("ai-read unavailable for %s: %s", url, error)
        return url, None
    parsed = _extract_json(raw)
    if not parsed:
        return url, None
    reading = validate_reading(parsed, text)
    model = (usage or {}).get("model") or provider or "unknown"
    await _store_reading(url_hash(url), model, reading)
    return url, {**reading, "model": model, "read_at": None}


async def read_articles(urls: list[str]) -> dict[str, dict]:
    """url -> reading for every url with fetched text. Cache-first; misses run
    through the LLM chain (bounded concurrency) and persist. Absent text or a
    dead chain = absent entry (honest absence, never a fabricated read)."""
    urls = [u for u in dict.fromkeys(urls) if (u or "").strip()][:64]
    if not urls:
        return {}
    hashes = {url_hash(u): u for u in urls}
    cached = await _cached_readings(list(hashes.keys()))
    out = {hashes[h]: r for h, r in cached.items()}
    misses = [u for u in urls if u not in out]
    if not misses:
        return out
    texts = await full_texts_for(misses, cap_chars=TEXT_CAP_CHARS)
    sem = asyncio.Semaphore(READ_CONCURRENCY)

    async def guarded(u: str):
        async with sem:
            try:
                return await _read_one(u, texts[u])
            except Exception as exc:
                logger.warning("ai-read failed for %s: %s", u, str(exc)[:200])
                return u, None

    results = await asyncio.gather(*(guarded(u) for u in misses if u in texts))
    for u, reading in results:
        if reading is not None:
            out[u] = reading
    return out


# ── Cross-read ───────────────────────────────────────────────────────────────

_CROSS_CACHE: dict[str, tuple[float, dict]] = {}
_CROSS_TTL_S = 900


def build_cross_input(readings: dict[str, dict]) -> tuple[str, dict[str, dict]]:
    """Claims across articles, each with a stable id 'c<n>'. Returns (prompt
    user text, id -> {url, text, quote}) — the table findings resolve against."""
    table: dict[str, dict] = {}
    lines: list[str] = []
    n = 0
    for url, r in readings.items():
        outlet_line = f"ARTICLE: {url}"
        claim_lines = []
        for c in r.get("claims", []):
            n += 1
            cid = f"c{n}"
            table[cid] = {"url": url, "text": c["text"], "quote": c["quote"],
                          "attribution": c.get("attribution", "asserted")}
            claim_lines.append(f"  [{cid}] ({c.get('attribution','asserted')}) {c['text']}\n"
                               f"        quote: \"{c['quote']}\"")
        if claim_lines:
            lines.append(outlet_line)
            lines.extend(claim_lines)
    lines.append("\nWhich claims corroborate each other and which are in tension?")
    return "\n".join(lines), table


def validate_cross(parsed: dict, table: dict[str, dict]) -> list[dict]:
    """Findings referencing unknown claim ids — or a claim paired with itself /
    its own article — are dropped. Kind is closed-vocabulary."""
    out = []
    for f in (parsed.get("findings") or [])[:8]:
        if not isinstance(f, dict):
            continue
        a, b = str(f.get("a") or ""), str(f.get("b") or "")
        kind = f.get("kind")
        if kind not in ("corroboration", "tension") or a not in table or b not in table or a == b:
            continue
        if table[a]["url"] == table[b]["url"]:
            continue   # intra-article agreement is trivia, not corroboration
        out.append({
            "kind": kind,
            "a": {"id": a, **table[a]},
            "b": {"id": b, **table[b]},
            "note": str(f.get("note") or "")[:400],
        })
    return out


async def cross_read(urls: list[str]) -> dict:
    """Corroboration/tension map over the quote-backed claims of a pin set.
    Labeled possible-tension; the quotes travel with every finding so the
    analyst verifies in one glance."""
    readings = await read_articles(urls)
    with_claims = {u: r for u, r in readings.items() if r.get("claims")}
    base = {
        "contract": "workbench-cross-read-v0",
        "prompt_version": PROMPT_VERSION,
        "articles_read": len(readings),
        "articles_with_claims": len(with_claims),
        "findings": [],
        "note": "AI READ — possible corroborations/tensions over quote-backed claims only; verify the quotes",
    }
    if len(with_claims) < 2:
        return {**base, "reason": "fewer than two articles with quote-backed claims"}
    key = "|".join(sorted(url_hash(u) for u in with_claims)) + "::" + PROMPT_VERSION
    hit = _CROSS_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _CROSS_TTL_S:
        return hit[1]
    user, table = build_cross_input(with_claims)
    raw, provider, error, usage = await generate_insight(
        _CROSS_SYSTEM, user, max_tokens=900, surface="workbench-cross-read",
    )
    if not raw:
        return {**base, "reason": error or "insight_unavailable"}
    parsed = _extract_json(raw) or {}
    payload = {**base, "findings": validate_cross(parsed, table),
               "model": (usage or {}).get("model") or provider}
    _CROSS_CACHE[key] = (time.monotonic(), payload)
    return payload
