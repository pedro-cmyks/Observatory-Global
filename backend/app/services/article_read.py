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
from app.services.article_fetch import (
    article_sources,
    full_texts_for,
    host_of,
    url_hash,
)
from app.services.insight_llm import generate_insight
from app.services.thread_ranking import _norm_headline as _wire_norm

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
    "('according to', officials said, etc.); max 6 claims (pick the most "
    "load-bearing), 8 actors, 5 gaps; keep \"text\" fields short; answer in the "
    "article's own language for quotes, English for everything else."
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
            pass
    if start == -1:
        return None
    # Truncation repair: a max_tokens cutoff leaves a dangling object. Walk back
    # to each complete object boundary and try closing the arrays/root. Claims
    # already parsed survive; the cut-off tail is lost, never invented.
    body = text[start:]
    ends = [m.end() for m in re.finditer(r"\}\s*(?=,|\]|$)", body)]
    for cut in reversed(ends[-40:]):
        frag = body[:cut]
        for closer in ("]}", "]}]}", "}]}", "]}}"):
            try:
                return json.loads(frag + closer)
            except Exception:
                continue
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
        _READ_SYSTEM, user, max_tokens=2400, surface="workbench-ai-read",
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


# ── Source independence (Council R3 P1) ──────────────────────────────────────
# Corroboration is only real between INDEPENDENT sources — two syndicated copies
# of one wire story (same AP/Reuters/AAP body, different mastheads) are one
# source, not two, and must not inflate confidence on the surface built to
# establish it. Reuse the measured syndication signal (thread_ranking's
# masthead-strip) plus a same-outlet and byte-identical-body check. Only
# cross-origin agreement corroborates; same-wire agreement is labeled honestly.

# Two-level public suffixes we actually see in news ccTLDs. NOT a full public-
# suffix list — just enough to fold edition.cnn.com→cnn.com without collapsing a
# whole .com.au wire family (katherinetimes.com.au ≠ blayneychronicle.com.au)
# into one root (those are separated by the wire-headline signal instead).
_TWO_LEVEL_TLDS = frozenset({
    "com.au", "net.au", "org.au", "co.uk", "org.uk", "co.nz", "com.br",
    "com.mx", "co.za", "com.tr", "co.in", "co.jp", "com.cn", "com.sg",
    "com.cy", "com.ph", "com.ng", "co.ke", "com.pk", "com.co", "com.ua",
})


def _registrable(host: str) -> str:
    """Registrable domain from an outlet host. Folds subdomains
    (edition.cnn.com→cnn.com) so two pages of one masthead read as one source,
    but keeps distinct .com.au wire-family domains distinct."""
    host = (host or "").strip().lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    if ".".join(parts[-2:]) in _TWO_LEVEL_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def source_signature(url: str, meta: dict | None) -> dict:
    """Independence signature for one source article: registrable outlet root,
    masthead-stripped wire headline (the thread_ranking signal), and the
    extracted-body hash. Falls back to the URL host when outlet metadata is
    absent (defensive — a with-claims article is normally status='ok')."""
    meta = meta or {}
    outlet = (meta.get("outlet") or "").strip() or host_of(url)
    return {
        "outlet_root": _registrable(outlet),
        "wire_sig": _wire_norm(str(meta.get("title") or "")),
        "content_hash": (str(meta.get("content_hash") or "").strip() or None),
    }


_INDEPENDENCE_LABEL = {
    "independent": "2 independent sources",
    "same_outlet": "same outlet — not independent",
    "same_wire": "2 outlets, 1 wire source",
    "same_primary_source": "2 outlets, 1 primary source (attributed)",
    "shared_quotes": "2 outlets, same underlying quotes",
}


def articles_independent(a: dict, b: dict) -> tuple[bool, str]:
    """Are two source articles independent for corroboration? Returns
    (independent, reason). Byte-identical body OR identical masthead-stripped
    headline = one wire copy; same registrable outlet = one source; a shared
    ATTRIBUTED primary or a shared quote set = one voice rewritten; otherwise
    cross-origin = independent."""
    ah, bh = a.get("content_hash"), b.get("content_hash")
    if ah and bh and ah == bh:
        return False, "same_wire"          # identical extracted body = one wire copy
    ar_, br_ = a.get("outlet_root") or "", b.get("outlet_root") or ""
    if ar_ and ar_ == br_:
        return False, "same_outlet"        # two pages, one masthead
    aw, bw = a.get("wire_sig") or "", b.get("wire_sig") or ""
    if aw and aw == bw:
        return False, "same_wire"          # syndicated: headline identical bar the masthead stamp
    if same_primary_source(a, b):
        return False, "same_primary_source"
    if quote_overlap(a.get("quotes") or [], b.get("quotes") or []) \
            >= QUOTE_OVERLAP_SAME_PRIMARY:
        return False, "shared_quotes"
    return True, "independent"


# ── Corroborate-v2 R2: paraphrase/attribution independence ───────────────────
# The C-N18 witness: three REWRITES of one Haaretz report — different bodies,
# different headlines, so content_hash/wire_sig/outlet_root all pass — whose
# own quotes say "According to Haaretz". Byte-identity catches syndication;
# this catches DERIVATION. Layer 1 is regex over the claims' verbatim quotes
# (cheap, pre-embedding); layer 2 is quote-text overlap. Precision-first:
# attribution to non-media actors (officials, police, ministries) never fires.

_ATTRIBUTION_RES = [
    re.compile(r"\b[Aa]ccording to (?:the )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    re.compile(r"\b(?:[Ff]irst )?[Rr]eported by (?:the )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    re.compile(r"\b(?:as )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3}) (?:first )?reported\b"),
    re.compile(r"\b[Cc]it(?:ing|ed by) ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"),
    # es
    re.compile(r"\b[Ss]egún (?:el diario |la agencia |el portal )?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    re.compile(r"\b[Ii]nformó ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    re.compile(r"\bcitando a ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
    # de / fr
    re.compile(r"\b[Ww]ie ([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2}) berichtet"),
    re.compile(r"\b[Ss]elon (?:le |la |l')?([A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,2})"),
]

# Attributed names that are NOT a press outlet — attribution to these is
# normal sourcing, not derivation. Lowercased containment check.
_NON_MEDIA_ATTRIBUTION = frozenset({
    "officials", "official", "authorities", "police", "army", "military",
    "government", "ministry", "witnesses", "residents", "sources", "experts",
    "analysts", "doctors", "hospital", "hospitals", "un", "united nations",
    "who", "spokesperson", "spokesman", "spokeswoman", "president",
    "prime minister", "el gobierno", "las autoridades", "la policía",
    "testigos", "fuentes",
})


def attributed_outlet(quotes: list[str]) -> str | None:
    """Most-frequent MEDIA name the quotes attribute their content to, or
    None. Normalized lowercase (matches against outlet_root by containment)."""
    from collections import Counter
    names: Counter[str] = Counter()
    for q in quotes or []:
        for rx in _ATTRIBUTION_RES:
            for m in rx.finditer(q or ""):
                name = re.sub(r"\s+", " ", m.group(1)).strip(" .,'’-").lower()
                if not name or len(name) < 3:
                    continue
                if any(nm in name or name in nm for nm in _NON_MEDIA_ATTRIBUTION):
                    continue
                names[name] += 1
    if not names:
        return None
    return names.most_common(1)[0][0]


QUOTE_OVERLAP_SAME_PRIMARY = 0.6
_MIN_QUOTE_CHARS = 40   # short quotes collide by chance


def _norm_quote(q: str) -> str:
    return re.sub(r"[^\w\s]", "", re.sub(r"\s+", " ", (q or "").lower())).strip()


def quote_overlap(quotes_a: list[str], quotes_b: list[str]) -> float:
    """Share of one article's substantial quotes contained in the other's
    (normalized substring, either direction, over the smaller set). Two
    'independent' accounts built from the same quote set = one primary."""
    na = [_norm_quote(q) for q in quotes_a or [] if len(_norm_quote(q)) >= _MIN_QUOTE_CHARS]
    nb = [_norm_quote(q) for q in quotes_b or [] if len(_norm_quote(q)) >= _MIN_QUOTE_CHARS]
    if not na or not nb:
        return 0.0
    small, big = (na, nb) if len(na) <= len(nb) else (nb, na)
    hits = sum(1 for q in small if any(q in o or o in q for o in big))
    return hits / len(small)


def same_primary_source(a: dict, b: dict) -> bool:
    """Both derive from the same named outlet, or one derives from the
    OTHER's masthead (site B attributing to Haaretz vs haaretz.com itself)."""
    da, db_ = a.get("derivative_of"), b.get("derivative_of")
    if da and db_ and da == db_:
        return True
    if da and da in (b.get("outlet_root") or ""):
        return True
    if db_ and db_ in (a.get("outlet_root") or ""):
        return True
    return False


def _quotes_by_url(table: dict[str, dict]) -> dict[str, list[str]]:
    """Every claim's verbatim quote, grouped by article. The cross-read table
    already carries the quote-gated text, so the attribution/overlap signals
    read it there — no caller has to plumb quotes into the signatures."""
    by_url: dict[str, list[str]] = {}
    for c in table.values():
        url = c.get("url")
        if url:
            by_url.setdefault(url, []).append(str(c.get("quote") or ""))
    return by_url


def _with_quotes(sig: dict, quotes: list[str] | None) -> dict:
    """Signature + the article's own quotes and the outlet they attribute to.
    Kept out of source_signature because attribution is a property of the READ
    (the claims), not of the fetched page metadata. Never mutates the caller's
    signature; a signature that already carries quotes is left alone."""
    if sig.get("quotes") is not None:
        return sig
    qs = list(quotes or [])
    return {**sig, "quotes": qs, "derivative_of": attributed_outlet(qs)}


# ── Cross-read ───────────────────────────────────────────────────────────────

_CROSS_CACHE: dict[str, tuple[float, dict]] = {}
_CROSS_TTL_S = 900


def build_cross_input(
    readings: dict[str, dict], sources: dict[str, dict] | None = None
) -> tuple[str, dict[str, dict]]:
    """Claims across articles, each with a stable id 'c<n>'. Returns (prompt
    user text, id -> {url, outlet, text, quote}) — the table findings resolve
    against. `sources` (url -> {outlet, title, ...}) carries the outlet name for
    display; independence is gated separately in validate_cross."""
    sources = sources or {}
    table: dict[str, dict] = {}
    lines: list[str] = []
    n = 0
    for url, r in readings.items():
        outlet = (sources.get(url, {}).get("outlet") or "").strip() or host_of(url)
        outlet_line = f"ARTICLE: {url}"
        claim_lines = []
        for c in r.get("claims", []):
            n += 1
            cid = f"c{n}"
            table[cid] = {"url": url, "outlet": outlet, "text": c["text"],
                          "quote": c["quote"],
                          "attribution": c.get("attribution", "asserted")}
            claim_lines.append(f"  [{cid}] ({c.get('attribution','asserted')}) {c['text']}\n"
                               f"        quote: \"{c['quote']}\"")
        if claim_lines:
            lines.append(outlet_line)
            lines.extend(claim_lines)
    lines.append("\nWhich claims corroborate each other and which are in tension?")
    return "\n".join(lines), table


def validate_cross(
    parsed: dict, table: dict[str, dict], sigs: dict[str, dict] | None = None
) -> list[dict]:
    """Findings referencing unknown claim ids — or a claim paired with itself /
    its own article — are dropped. Kind is closed-vocabulary.

    SOURCE-INDEPENDENCE GATE (Council R3 P1): a 'corroboration' whose two
    articles are NOT independent (syndicated copies of one wire story, or two
    pages of one masthead) is relabeled 'shared_source' — the claims agree, but
    that is one source echoing itself, not two sources converging. Every
    corroboration/shared_source finding carries an `independence` block so the
    distinction is honest ('2 independent sources' vs '2 outlets, 1 wire
    source'). Tensions are left untouched.

    R2 extends the gate past byte-identity to DERIVATION: each signature is
    enriched with its article's own quotes (off `table`) and the media outlet
    those quotes attribute to, so three rewrites of one report read as one
    voice instead of independent corroboration."""
    sigs = sigs or {}
    quotes_by_url = _quotes_by_url(table)
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
        finding = {
            "kind": kind,
            "a": {"id": a, **table[a]},
            "b": {"id": b, **table[b]},
            "note": str(f.get("note") or "")[:400],
        }
        if kind == "corroboration":
            ua, ub = table[a]["url"], table[b]["url"]
            sa = _with_quotes(sigs.get(ua) or source_signature(ua, None), quotes_by_url.get(ua))
            sb = _with_quotes(sigs.get(ub) or source_signature(ub, None), quotes_by_url.get(ub))
            indep, reason = articles_independent(sa, sb)
            finding["independence"] = {
                "independent": indep,
                "reason": reason,
                "label": _INDEPENDENCE_LABEL[reason],
            }
            if not indep:
                # honest: the quotes align, but it is one source, not corroboration
                finding["kind"] = "shared_source"
        out.append(finding)
    return out


async def cross_read(urls: list[str]) -> dict:
    """Corroboration/tension map over the quote-backed claims of a pin set.
    Labeled possible-tension; the quotes travel with every finding so the
    analyst verifies in one glance."""
    readings = await read_articles(urls)
    with_claims = {u: r for u, r in readings.items() if r.get("claims")}
    base = {
        "contract": "workbench-cross-read-v1",
        "prompt_version": PROMPT_VERSION,
        "articles_read": len(readings),
        "articles_with_claims": len(with_claims),
        "findings": [],
        "independent_corroborations": 0,
        "shared_source_findings": 0,
        "note": ("AI READ — possible corroborations/tensions over quote-backed claims only; "
                 "corroboration counts INDEPENDENT sources (syndicated wire copies of one "
                 "story are labeled 'same source'); verify the quotes"),
    }
    if len(with_claims) < 2:
        return {**base, "reason": "fewer than two articles with quote-backed claims"}
    key = "|".join(sorted(url_hash(u) for u in with_claims)) + "::" + PROMPT_VERSION
    hit = _CROSS_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _CROSS_TTL_S:
        return hit[1]
    # Source metadata (outlet/title/content_hash) for the independence gate.
    sources = await article_sources(list(with_claims.keys()))
    sigs = {u: source_signature(u, sources.get(u)) for u in with_claims}
    user, table = build_cross_input(with_claims, sources)
    raw, provider, error, usage = await generate_insight(
        _CROSS_SYSTEM, user, max_tokens=900, surface="workbench-cross-read",
    )
    if not raw:
        return {**base, "reason": error or "insight_unavailable"}
    parsed = _extract_json(raw) or {}
    findings = validate_cross(parsed, table, sigs)
    payload = {
        **base,
        "findings": findings,
        "independent_corroborations": sum(1 for f in findings if f["kind"] == "corroboration"),
        "shared_source_findings": sum(1 for f in findings if f["kind"] == "shared_source"),
        "model": (usage or {}).get("model") or provider,
    }
    _CROSS_CACHE[key] = (time.monotonic(), payload)
    return payload
