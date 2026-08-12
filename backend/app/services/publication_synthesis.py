"""Grounded publication synthesis — one cited mini-article from frozen evidence.

Extracted from the dossier router so BOTH the L3 dossier endpoint and the L1
daily edition (its lead story) produce the same cited prose, and so the headless
M1 daily builder can call it without importing the HTTP framework. No FastAPI.
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.services.insight_llm import generate_insight


class SynthEvidenceItem(BaseModel):
    # Structured frozen evidence — the citation table for the mini-article. The
    # server numbers these [1..N] in the prompt and resolves the model's [n]
    # markers back against THIS table (never trusting an echoed citation list).
    headline: str
    source: str | None = None
    date: str | None = None
    url: str | None = None
    # State-controlled/affiliated outlet (signals_v2.is_state_media). Surfaced to
    # the model (the evidence line is tagged) and carried onto the resolved
    # citation so the front page never presents state media as neutral (R3 P0).
    is_state_media: bool = False


class SynthPin(BaseModel):
    label: str
    type: str | None = None
    evidence: list[str] = Field(default_factory=list)  # frozen headlines (may carry "— source")
    # Structured variant of `evidence` (preferred when present) — enables the
    # authoritative numbered-receipts table. Legacy `evidence` strings still work.
    evidence_items: list[SynthEvidenceItem] = Field(default_factory=list)
    note: str | None = None
    # Server-side low-coherence flag on the pin's thread (a conflated black-hole
    # whose evidence is a mix of unrelated events).
    low_coherence: bool = False


class SynthConnectionNode(BaseModel):
    # Per-pin connectedness from the MEASURED relation graph — which pins are the
    # confirmed spine and which are merely topically adjacent.
    label: str
    connectedness: str | None = None   # confirmed | text-linked | coverage-context | similar-only | isolated
    confirmed_with: list[str] = Field(default_factory=list)  # distinctive shared-actor partners
    contextual_with: list[str] = Field(default_factory=list)  # same coverage country; never proof
    similar_with: list[str] = Field(default_factory=list)    # semantic-only partners
    text_mentions: list[str] = Field(default_factory=list)   # verbatim evidence-text mentions of another pin


class SynthConnection(BaseModel):
    # grounded | text-linked | context-only | similar-only | split | isolated
    state: str | None = None
    nodes: list[SynthConnectionNode] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)     # "A ↔ B — shared actor X"
    countries: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    press: int = 0
    public: int = 0
    bridges: list[str] = Field(default_factory=list)    # unpinned stories nearby
    lens_note: str | None = None


class SynthTension(BaseModel):
    # One MEASURED cross-read tension (workbench-cross-read-v1, kind='tension'):
    # two quote-backed claims from different articles that disagree. The prose
    # may never assert either side as settled — see apply_tension_guard.
    a_quote: str
    a_outlet: str | None = None
    b_quote: str
    b_outlet: str | None = None
    note: str | None = None


class SynthesizeRequest(BaseModel):
    title: str = ""
    pins: list[SynthPin] = Field(..., min_length=1)
    connection: SynthConnection | None = None
    gaps: list[str] = Field(default_factory=list)
    # Measured cross-read tensions for THIS pin set (optional — absent on the
    # daily-edition path and on a first report run, present once the analyst has
    # cross-read the sources).
    tensions: list[SynthTension] = Field(default_factory=list)


_SYNTH_SYSTEM = (
    "You are a news-desk editor writing a PUBLISHABLE STANDALONE mini-article from "
    "an analyst's pinned evidence. A stranger reading ONLY your article must "
    "understand the story AND must NOT be misled into thinking loosely-related pins "
    "form one confirmed narrative. You are given the pinned stories with their "
    "frozen evidence headlines — each NUMBERED '[n]' and possibly ending "
    "'— <outlet>, <YYYY-MM-DD>' — a MEASURED connection verdict, and PER-PIN "
    "connectedness. Rules:\n"
    "0. ARTICLE FORM WITH RECEIPTS. Write a dated lede (1-2 sentences answering "
    "who/what/when/where from the DATED evidence) and a short body (2-4 short "
    "paragraphs). EVERY factual claim in the lede and body must end with the "
    "inline citation marker(s) '[n]' of the numbered evidence line(s) supporting "
    "it (e.g. 'ordered the cutoff [2]', multiple allowed '[1][4]'). You may cite "
    "ONLY the supplied numbered evidence — never outside knowledge, never a number "
    "that was not supplied. A sentence you cannot back with a supplied [n] does "
    "not belong in the body. If the evidence is THIN, write a SHORTER body — never "
    "pad, never generalize to fill space.\n"
    "1. GROUND everything in the supplied evidence — never invent facts, numbers, "
    "actors, events, dates, or outcomes that are not in the headlines.\n"
    "2. LEAD WITH THE CONFIRMED SPINE. Build the through-line ONLY from pins whose "
    "per-pin connectedness is 'confirmed' (they share a distinctive actor); name "
    "that actor. A pin marked 'similar-only' shares NO verified actor "
    "with the others — it is topically or linguistically adjacent, NOT confirmed "
    "connected. You MUST explicitly bracket such a pin: say it is 'topically "
    "adjacent, not confirmed connected — possibly an artifact of shared language/"
    "topic', and do NOT weave it into the main narrative as if the link were proven. "
    "Even when the overall state is 'grounded', a single confirmed edge does not make "
    "every pin part of one story. If the state is 'split' or 'isolated', say the pins "
    "do not form one story.\n"
    "2a. COVERAGE CONTEXT IS NOT A STORY LINK. A pin marked 'coverage-context' only "
    "shares a country appearing in coverage with another pin. That country is NOT "
    "verified as the shared subject, identity, coordination, or cause. Keep it out "
    "of the confirmed spine and describe it only as navigation context.\n"
    "2b. TEXT MENTIONS OVERRIDE 'no link' CLAIMS. A pin may carry evidence-text "
    "mentions ('evidence text mentions …'): its headline TEXT references another "
    "pinned story even though entity extraction found no shared actor. Describe such "
    "a pin exactly that way — 'isolated by entity extraction, but its evidence text "
    "references <term> — verify' — and NEVER write 'no evidence links them' or "
    "'isolated, unconnected' about a pin that carries a text mention. A 'text-linked' "
    "connectedness is weaker than 'confirmed' but stronger than 'similar-only'.\n"
    "2c. GLASS BOX ON LINK NAMES. When naming WHAT links two pins, quote ONLY the "
    "exact measured tokens handed to you (shared actor names, contextual coverage "
    "countries, or mention "
    "terms in 'links' / per-pin connectedness). Never substitute, embellish, or "
    "infer different actor names for a link, even if they read more naturally.\n"
    "3. CHECK EVIDENCE-TO-LABEL FIT. For each pin, verify its evidence headlines "
    "actually name the actors or place in the pin's OWN label. If a pin's bullets do "
    "NOT support its label (they describe unrelated actors/events — a conflated or "
    "mis-labelled thread), or the pin is flagged LOW-COHERENCE, do NOT narrate its "
    "content as if it were about the label: flag that pin as UNRELIABLE (state that "
    "its evidence does not match its label) and exclude it from the finding.\n"
    "4. DO NOT ASSERT CONTESTED OUTCOMES AS FACT. Election results, concessions, "
    "inaugurations, and transfers of power are claims, not givens. Do NOT state one "
    "as settled fact unless an evidence headline DIRECTLY states it happened. "
    "Attribute contested or single-sourced outcomes to their source ('reported by "
    "<outlet>', 'per <outlet>') and prefer hedged phrasing ('reportedly', 'is said "
    "to') when a headline announces rather than confirms. Surface a date if a "
    "headline carries one (evidence lines may end '— <outlet>, <YYYY-MM-DD>'); date "
    "contested outcomes with it; if outcomes are undated, say the timing is unclear.\n"
    "4a. STATE MEDIA IS NEVER NEUTRAL. An evidence line tagged '[STATE MEDIA]' is a "
    "state-controlled or state-affiliated outlet. NEVER state its claim as neutral "
    "established fact: attribute it to the outlet ('according to <outlet>, Russian "
    "state media', 'per state broadcaster <outlet>') and, when it is the ONLY source "
    "for a figure or claim, say the claim is reported by state media and not "
    "independently corroborated. If a claim is carried by BOTH a state-media line and "
    "an independent line, you may state it and cite both. A lede or figure resting "
    "solely on '[STATE MEDIA]' citations MUST carry the state-media attribution in the "
    "same sentence — never present it bare.\n"
    "4b. NEVER SETTLE A MEASURED TENSION. When 'MEASURED CROSS-READ TENSIONS' are "
    "supplied, two read sources DISAGREE on that point. Do NOT assert either side "
    "as established fact: attribute both ('<outlet> says X, while <outlet> says Y') "
    "or say the point is contested. A sentence asserting one side unqualified will "
    "be downgraded server-side to 'reported (uncorroborated)' with the opposing "
    "quote attached — write it attributed the first time.\n"
    "5. SURFACE THE NON-OBVIOUS insight visible only across pins (a self-declared "
    "alignment, a coverage asymmetry, an actor bridging two CONFIRMED stories) — but "
    "only over the confirmed spine, never over a bracketed or unreliable pin.\n"
    "6. UNKNOWNS — 'what we don't know'. 2-4 short bullet-style sentences naming "
    "what is missing or unproven: missing voices (no public/forum signal, absent "
    "languages/origins), unverified or single-sourced claims, undated outcomes, "
    "pins frozen metadata-only (no evidence captured), isolated or text-linked-only "
    "pins (with their verify caveat). When a 'coverage lens' note is supplied, one "
    "unknown MUST carry it (the evidence leans one language/origin — say so).\n"
    "Output STRICT JSON only, no prose around it: "
    '{"headline": "<=14 words, the confirmed finding", '
    '"lede": "1-2 sentences, dated, who/what/when/where, with [n] markers", '
    '"body": ["2-4 short paragraphs, every claim ending with its [n] marker(s)"], '
    '"unknowns": ["2-4 sentences"]}.'
)


# Legacy folded evidence string "headline — outlet, YYYY-MM-DD" (the frontend
# folds attribution into the string; structured evidence_items are preferred).
_LEGACY_EVIDENCE_RE = re.compile(
    r"^(?P<headline>.+?)\s+—\s+(?:(?P<source>.+?),\s+)?(?P<date>\d{4}-\d{2}-\d{2})$"
)


def _citation_table(req: SynthesizeRequest) -> list[dict]:
    """Global numbered receipts [1..N] across pins, in prompt order. This table
    is AUTHORITATIVE: the model's [n] markers resolve against it — an echoed or
    invented citation can never enter the response."""
    table: list[dict] = []
    for pin_i, p in enumerate(req.pins):
        if p.evidence_items:
            items = [
                {"headline": e.headline, "source": e.source, "date": e.date,
                 "url": e.url, "is_state_media": e.is_state_media}
                for e in p.evidence_items
            ]
        else:
            items = []
            for h in p.evidence:
                m = _LEGACY_EVIDENCE_RE.match(h)
                if m:
                    items.append({"headline": m.group("headline"),
                                  "source": m.group("source"),
                                  "date": m.group("date"), "url": None,
                                  "is_state_media": False})
                else:
                    items.append({"headline": h, "source": None, "date": None,
                                  "url": None, "is_state_media": False})
        for it in items:
            table.append({"n": len(table) + 1, "pin": p.label, "pin_i": pin_i, **it})
    return table


def _synth_user(req: SynthesizeRequest, article_texts: dict | None = None) -> str:
    """article_texts: url -> {text, outlet, fetched_at} from pinned_articles
    (Workbench enrichment F1). An excerpt rides UNDER its evidence line with the
    SAME [n] — the excerpt is the same source as its headline, never a new
    receipt number."""
    article_texts = article_texts or {}
    parts: list[str] = []
    if req.title:
        parts.append(f"Investigation title: {req.title}")
    table = _citation_table(req)
    by_pin: dict[int, list[dict]] = {}
    for row in table:
        by_pin.setdefault(row["pin_i"], []).append(row)
    parts.append("\nPINNED STORIES + frozen evidence (numbered — cite as [n]):")
    for i, p in enumerate(req.pins, 1):
        flag = " [⚠ LOW-COHERENCE thread — evidence may be a conflated mix]" if p.low_coherence else ""
        parts.append(f"{i}. {p.label}" + (f" [{p.type}]" if p.type else "") + flag)
        rows = by_pin.get(i - 1, [])
        if not rows:
            parts.append("   (metadata only — no frozen evidence captured for this pin)")
        for row in rows:
            attribution = ""
            if row["source"] or row["date"]:
                bits = [b for b in (row["source"], row["date"]) if b]
                attribution = " — " + ", ".join(bits)
            state_tag = " [STATE MEDIA]" if row.get("is_state_media") else ""
            parts.append(f"   [{row['n']}] {row['headline']}{attribution}{state_tag}")
            art = article_texts.get(row["url"] or "")
            if art and art.get("text"):
                fetched = (art.get("fetched_at") or "")[:10]
                parts.append(
                    f"       full text of [{row['n']}] (fetched {fetched or 'earlier'}): "
                    f"\"{art['text'][:600].strip()}\""
                )
        if p.note:
            parts.append(f"   note: {p.note}")
    c = req.connection
    if c:
        parts.append("\nMEASURED CONNECTION VERDICT:")
        parts.append(f"  state: {c.state or 'unknown'}")
        if c.nodes:
            parts.append("  per-pin connectedness (from the measured relation graph):")
            for nd in c.nodes:
                line = f"    - {nd.label}: {nd.connectedness or 'unknown'}"
                if nd.confirmed_with:
                    line += " — confirmed link (distinctive shared actor) to " + ", ".join(nd.confirmed_with[:6])
                if nd.contextual_with:
                    line += " — coverage-country context only (not subject identity or causality) with " + ", ".join(nd.contextual_with[:6])
                if nd.similar_with:
                    line += " — similarity-only proximity to " + ", ".join(nd.similar_with[:6])
                parts.append(line)
                for tm in nd.text_mentions[:4]:
                    parts.append(f"      · {tm}")
        if c.links:
            parts.append("  links: " + " | ".join(c.links[:8]))
        if c.countries:
            parts.append("  countries touched: " + ", ".join(c.countries[:10]))
        if c.languages:
            parts.append("  coverage languages: " + ", ".join(c.languages[:8]))
        parts.append(f"  press signals: {c.press} · public/forum signals: {c.public}")
        if c.lens_note:
            parts.append(f"  coverage lens: {c.lens_note}")
        if c.bridges:
            parts.append("  nearby unpinned stories (bridges): " + " | ".join(c.bridges[:6]))
    if req.tensions:
        parts.append("\nMEASURED CROSS-READ TENSIONS (two read sources disagree — "
                     "never assert either side as settled; attribute both):")
        for t in req.tensions[:6]:
            parts.append(f"  - {t.note or 'claims in tension'}")
            parts.append(f"      A: “{t.a_quote[:240]}”" + (f" — {t.a_outlet}" if t.a_outlet else ""))
            parts.append(f"      B: “{t.b_quote[:240]}”" + (f" — {t.b_outlet}" if t.b_outlet else ""))
    if req.gaps:
        parts.append("\nKNOWN GAPS (from the frozen report):")
        for g in req.gaps[:6]:
            parts.append(f"  - {g}")
    return "\n".join(parts)


# ── measured-tension guard ────────────────────────────────────────────────────
# Frank test 2026-08-12: the cross-read measured a real editorial discrepancy
# (naharnet "Russia has yet to officially comment" vs algemeiner "Russia's
# Foreign Ministry said … would boost ties") and the synthesis asserted the
# second side flatly — "the report contradicts itself and only the buried
# section is right". The prompt rule above asks the model not to; THIS is the
# enforcement, deterministic and after the fact.
#
# WHAT IS BUILT (honest scope): this is lexical, not semantic. A sentence is
# treated as asserting one side of a flagged pair when it carries at least one
# content term EXCLUSIVE to that side plus ≥3 terms of the pair overall, carries
# NO term exclusive to the other side (prose that already presents both sides is
# doing the right thing), and is not already attributed/hedged. Such a sentence
# keeps its text and gains, before its terminal punctuation, the honesty clause
# "— reported (uncorroborated): …" naming the opposing quote and outlet. It is
# never dropped: dropping would lose the finding the analyst most needs.
_TENSION_STOPWORDS = frozenset({
    "about", "after", "again", "against", "also", "another", "been", "before",
    "being", "between", "both", "could", "does", "doing", "during", "each",
    "from", "have", "having", "here", "into", "just", "like", "more", "most",
    "much", "must", "only", "other", "over", "same", "should", "since", "some",
    "such", "than", "that", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "until", "very", "were", "what", "when",
    "where", "which", "while", "will", "with", "would", "your", "shall", "might",
    "still", "into", "onto", "upon", "including", "however", "although",
})
_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Already-honest phrasings: an attributed or hedged sentence is not an
# unqualified assertion, so the guard leaves it alone.
_HEDGE_RE = re.compile(
    r"\b(?:according to|reportedly|reported by|per\s+[a-z0-9.-]+\.[a-z]{2,}|is said to|"
    r"was said to|claims?|claimed|alleged(?:ly)?|uncorroborated|unconfirmed|contested|"
    r"disputed|denies|denied|yet to|has not|have not|did not|no comment)\b",
    re.IGNORECASE,
)
# A sentence ends on .!? only when the next thing is a new sentence (or the end)
# — so "According to algemeiner.com, …" stays ONE sentence and keeps its hedge.
_SENT_END_RE = re.compile(r"[.!?]+(?=\s+[A-Z“\"(]|\s*$)")
_TERMINAL_RE = re.compile(r"([.!?]+)(\s*)$")
_TENSION_MIN_OVERLAP = 3
_TENSION_QUOTE_CHARS = 200


def _split_sentences(text: str) -> list[str]:
    """Sentences with their trailing whitespace kept, so "".join() is lossless."""
    out: list[str] = []
    start = 0
    for m in _SENT_END_RE.finditer(text or ""):
        end = m.end()
        while end < len(text) and text[end].isspace():
            end += 1
        out.append(text[start:end])
        start = end
    if start < len(text or ""):
        out.append(text[start:])
    return out


def _tension_tokens(text: str) -> set[str]:
    return {
        t for t in _TOKEN_RE.findall((text or "").lower())
        if len(t) >= 4 and t not in _TENSION_STOPWORDS
    }


def _tension_marker(quote: str, outlet: str | None) -> str:
    trimmed = " ".join((quote or "").split())[:_TENSION_QUOTE_CHARS].rstrip(" .,;:")
    attribution = f" ({outlet})" if outlet else ""
    return (" — reported (uncorroborated): the cross-read measured a contrary "
            f"account, “{trimmed}”{attribution}")


def apply_tension_guard(
    texts: list[str], tensions: list[SynthTension],
) -> tuple[list[str], list[dict]]:
    """Downgrade every sentence that asserts one side of a MEASURED cross-read
    tension without attribution. Pure. Returns (guarded texts, ledger)."""
    if not tensions or not texts:
        return texts, []
    pairs = []
    for t in tensions:
        ta, tb = _tension_tokens(t.a_quote), _tension_tokens(t.b_quote)
        if not ta or not tb:
            continue
        pairs.append((t, ta, tb, ta - tb, tb - ta))
    if not pairs:
        return texts, []

    out: list[str] = []
    ledger: list[dict] = []
    for text in texts:
        rebuilt: list[str] = []
        for sentence in _split_sentences(text or ""):
            if not sentence.strip():
                rebuilt.append(sentence)
                continue
            tokens = _tension_tokens(sentence)
            marked = sentence
            for t, ta, tb, only_a, only_b in pairs:
                if len(tokens & (ta | tb)) < _TENSION_MIN_OVERLAP:
                    continue
                hits_a, hits_b = bool(tokens & only_a), bool(tokens & only_b)
                if hits_a == hits_b:
                    continue          # both sides present (honest) or neither side named
                if _HEDGE_RE.search(sentence):
                    continue          # already attributed / hedged
                counter_quote = t.a_quote if hits_b else t.b_quote
                counter_outlet = t.a_outlet if hits_b else t.b_outlet
                marker = _tension_marker(counter_quote, counter_outlet)
                m = _TERMINAL_RE.search(marked)
                if m:
                    marked = marked[:m.start()] + marker + m.group(1) + m.group(2)
                else:
                    marked = marked.rstrip() + marker
                ledger.append({
                    "sentence": sentence.strip(),
                    "counter_quote": counter_quote,
                    "counter_outlet": counter_outlet,
                    "note": t.note,
                })
                break                 # one downgrade per sentence
            rebuilt.append(marked)
        out.append("".join(rebuilt))
    return out, ledger


def _extract_json(text: str) -> dict | None:
    """Lenient — providers sometimes fence the JSON or add a sentence around it."""
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


_CITE_RE = re.compile(r"\[(\d{1,3})\]")


def _as_paragraphs(v) -> list[str] | None:
    """body/unknowns arrive as a list of strings or a single string — normalize
    to a clean list of non-empty paragraphs."""
    if isinstance(v, str):
        v = [s for s in re.split(r"\n{2,}|\n(?=- )", v)]
    if not isinstance(v, list):
        return None
    out = [str(s).strip().lstrip("- ").strip() for s in v if str(s).strip()]
    return out or None


def _resolve_citations(texts: list[str], table: list[dict]) -> list[dict]:
    """[n] markers found in the article, resolved against the AUTHORITATIVE
    numbered table (first-appearance order; out-of-range ns dropped). The model
    never gets to invent a receipt."""
    by_n = {row["n"]: row for row in table}
    seen: list[int] = []
    for t in texts:
        for m in _CITE_RE.finditer(t):
            n = int(m.group(1))
            if n in by_n and n not in seen:
                seen.append(n)
    return [
        {"n": n, "headline": by_n[n]["headline"], "source": by_n[n]["source"],
         "date": by_n[n]["date"], "url": by_n[n]["url"], "pin": by_n[n]["pin"],
         "is_state_media": bool(by_n[n].get("is_state_media"))}
        for n in seen
    ]


async def synthesize_publication_article(req: SynthesizeRequest) -> dict:
    """One grounded LLM pass → publishable mini-article {headline, lede, body,
    unknowns, citations}; legacy {headline, synthesis, gap} passthrough when the
    model answers in the old shape. Reused by the L3 dossier endpoint and the L1
    daily edition (its lead story) so both produce the same cited prose."""
    contract = "dossier-synthesis-v2"
    empty = {"contract": contract, "headline": None, "lede": None, "body": None,
             "unknowns": None, "citations": None, "synthesis": None, "gap": None,
             "tension_downgrades": None}
    # Workbench enrichment F1: pull cached full texts for the evidence URLs and
    # feed excerpts under their [n] lines. Best-effort — synthesis never fails
    # on the enrichment substrate being absent (fresh deploy, table missing, db
    # down): it degrades to headlines-only exactly as before.
    article_texts: dict = {}
    try:
        from app.services.article_fetch import full_texts_for
        urls = [row["url"] for row in _citation_table(req) if row.get("url")]
        if urls:
            article_texts = await full_texts_for(urls)
    except Exception:
        article_texts = {}
    empty["full_text_used"] = len(article_texts)   # honesty: how many receipts had full text
    text, provider, error, _usage = await generate_insight(
        _SYNTH_SYSTEM, _synth_user(req, article_texts), max_tokens=1200, surface="dossier-synthesis",
    )
    if not text:
        return {**empty, "provider": None, "error": error or "insight_unavailable"}
    parsed = _extract_json(text)
    if not parsed:
        # non-JSON reply — still useful; hand the prose back as the legacy synthesis.
        return {**empty, "synthesis": text.strip(), "provider": provider, "error": None}
    lede = (parsed.get("lede") or "").strip() or None
    body = _as_paragraphs(parsed.get("body"))
    if lede or body:
        unknowns = _as_paragraphs(parsed.get("unknowns"))
        # The prose may not settle a tension the cross-read MEASURED — enforced
        # after the pass, never left to the model's compliance.
        guarded, downgrades = apply_tension_guard(
            ([lede] if lede else []) + (body or []), req.tensions)
        if lede:
            lede, guarded = guarded[0], guarded[1:]
        body = guarded or None
        citations = _resolve_citations(
            ([lede] if lede else []) + (body or []), _citation_table(req))
        return {
            **empty,
            "headline": (parsed.get("headline") or None),
            "lede": lede,
            "body": body,
            "unknowns": unknowns,
            "citations": citations or None,
            "tension_downgrades": downgrades or None,
            "provider": provider,
            "error": None,
        }
    # Legacy shape — frontend falls back to the old renderer.
    return {
        **empty,
        "headline": (parsed.get("headline") or None),
        "synthesis": (parsed.get("synthesis") or None),
        "gap": (parsed.get("gap") or None),
        "provider": provider,
        "error": None,
    }
