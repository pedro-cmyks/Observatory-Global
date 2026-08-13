"""Grounded publication synthesis — one cited mini-article from frozen evidence.

Extracted from the dossier router so BOTH the L3 dossier endpoint and the L1
daily edition (its lead story) produce the same cited prose, and so the headless
M1 daily builder can call it without importing the HTTP framework. No FastAPI.
"""
from __future__ import annotations

import json
import re
import unicodedata

from pydantic import BaseModel, Field

from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.insight_llm import generate_insight
from app.services.subject_geography import resolve_gazetteer_place


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


class SynthMarketReceipt(BaseModel):
    # One SERVED descriptive market instrument (markets-descriptive-v0: the
    # world basket + a country's own instruments). It is a RECEIPT, never a
    # relation: it says what a price did, never that news moved it. Carried so
    # prose asserting a market DIRECTION can be checked against the measurable
    # (X3-A) — the scorecard's only "Atlas said the opposite" claim.
    symbol: str
    label: str
    asset_class: str | None = None      # equity-index|equity-single|fx|rate|energy|metal|…
    role: str | None = None             # currency|index|champion|export-commodity
    country_code: str | None = None
    last_close: float | None = None
    last_close_at: str | None = None    # ISO date of the close the change is measured at
    # Net % change of the LAST SESSION (last close vs the prior close). None
    # when the price is pending or the series is too short — an absent
    # measurement is never read as "no move".
    change_pct: float | None = None


class SynthesizeRequest(BaseModel):
    title: str = ""
    pins: list[SynthPin] = Field(..., min_length=1)
    connection: SynthConnection | None = None
    gaps: list[str] = Field(default_factory=list)
    # Measured cross-read tensions for THIS pin set (optional — absent on the
    # daily-edition path and on a first report run, present once the analyst has
    # cross-read the sources).
    tensions: list[SynthTension] = Field(default_factory=list)
    # Served market receipts in scope for this story (world basket + the
    # subject countries' own instruments). Optional: with none supplied a
    # market-direction claim is still downgraded — as uncorroborated, never as
    # contradicted.
    markets: list[SynthMarketReceipt] = Field(default_factory=list)


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
    "4c. NEVER INVENT A MARKET DIRECTION. Do NOT write that stocks, shares, an "
    "index, a currency, bonds or a commodity rose, fell, rallied or plunged unless "
    "an evidence headline says so or a 'SERVED MARKET RECEIPTS' line measures it — "
    "and when a receipt measures it, use the receipt's own figure. A market "
    "direction is never a mood: an aid pledge or a rescue is not evidence that "
    "prices went up. An unbacked direction is downgraded server-side to 'reported "
    "(uncorroborated)'.\n"
    "4d. NEVER INVENT A PLACE. Name a city, town or region ONLY when an evidence "
    "line (headline or full text) names it. If you know only the country, say the "
    "COUNTRY ('in Colombia') — never substitute its capital or largest city as a "
    "stand-in. An unbacked city is rewritten server-side to the country.\n"
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
    if req.markets:
        parts.append("\nSERVED MARKET RECEIPTS (descriptive — a level and its last-session "
                     "change; NEVER evidence that news moved a price):")
        for m in req.markets[:12]:
            chg = f"{m.change_pct:+.2f}% last session" if m.change_pct is not None else "no measured change"
            level = f"{m.last_close:g}" if m.last_close is not None else "pending"
            asof = f" as of {m.last_close_at}" if m.last_close_at else ""
            parts.append(f"  - {m.label} ({m.symbol}): {level}, {chg}{asof}")
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


# ── market-direction guard (X3-A) ─────────────────────────────────────────────
# Veracity scorecard 2026-08-13, claim 6 — the ONE place in twelve fact-checked
# claims where Atlas asserted the OPPOSITE of the measurable: the Colombia
# edition's prose had Colombian stocks rising ("aid + resilience" → optimism)
# while COLCAP closed -0.51% and bonds fell. Evidence was clean; the SYNTHESIS
# invented the direction.
#
# The rule, in the tension guard's discipline: a sentence asserting that a
# market moved must carry a receipt. The receipt may be MEASURED (a served
# instrument) or REPORTED (a cited evidence headline that says it). With
# neither, the sentence keeps its text and gains the same "reported
# (uncorroborated)" clause — the finding is never dropped.
#
# HONEST SCOPE — where this guard abstains, and why:
#   * FX and RATE receipts never settle a direction. An FX quote carries no
#     declared convention (USD/COP falling IS the peso strengthening) and a
#     bond quote confuses price with yield ("bonds fell" / "yields rose" are
#     the same event). Such a claim is uncorroborated, NEVER "contradicted".
#   * A sentence naming BOTH directions is describing a mix — left alone.
#   * An already attributed/hedged sentence is left alone (shared _HEDGE_RE).
#   * Lexical, not semantic: it fires on a market SUBJECT plus a DIRECTION verb
#     in the same sentence, so "the death toll rose" can never trip it.
_MARKET_UP_RE = re.compile(
    r"\b(?:rise|rises|rising|rose|risen|rally|rallies|rallied|rallying|rebound|"
    r"rebounds|rebounded|climb|climbs|climbed|climbing|gain|gains|gained|surge|"
    r"surges|surged|jump|jumps|jumped|soar|soars|soared|advance|advances|advanced|"
    r"advancing|higher|firmer|strengthen|strengthens|strengthened|appreciate|"
    r"appreciates|appreciated|up)\b"
    r"|\b(?:al alza|en alza|al?\s?repunte)\b"
    r"|\b(?:sube|suben|subió|subieron|subiendo|repunt\w*|avanz\w*|apreci\w*|"
    r"fortalec\w*|gana|ganó|ganaron|ganancias)\b",
    re.IGNORECASE,
)
_MARKET_DOWN_RE = re.compile(
    r"\b(?:fall|falls|fell|fallen|falling|drop|drops|dropped|dropping|plunge|"
    r"plunges|plunged|slide|slides|slid|slip|slips|slipped|sink|sinks|sank|sunk|"
    r"tumble|tumbles|tumbled|slump|slumps|slumped|decline|declines|declined|"
    r"lower|weaken|weakens|weakened|depreciate|depreciates|depreciated|retreat|"
    r"retreats|retreated|selloff|sell-off|down)\b"
    r"|\b(?:a la baja|en baja)\b"
    r"|\b(?:cae|caen|cayó|cayeron|cayendo|ca[ií]da|desplom\w*|retroced\w*|pierde|"
    r"perdió|perdieron|pérdidas|perdidas|debilit\w*|baja|bajan|bajó|bajaron)\b",
    re.IGNORECASE,
)
# subject key → (pattern, instrument roles, instrument asset classes)
_MARKET_SUBJECTS: tuple[tuple[str, re.Pattern, frozenset, frozenset], ...] = (
    ("equities", re.compile(
        r"\b(?:stocks?|shares?|equit(?:y|ies)|bourses?|index|indexes|indices|"
        r"acciones|bolsas?|burs[áa]til(?:es)?|[íi]ndices?)\b", re.IGNORECASE),
     frozenset({"index", "champion"}),
     frozenset({"equity-index", "equity-etf", "equity-single"})),
    ("currency", re.compile(
        r"\b(?:currenc(?:y|ies)|exchange rate|forex|tipo de cambio|divisas?|"
        r"moneda|peso|dollar|d[óo]lar|euro|yen|lira|rupee|rupia)\b", re.IGNORECASE),
     frozenset({"currency"}), frozenset({"fx", "fx-index"})),
    ("bonds", re.compile(
        r"\b(?:bonds?|bonos?|yields?|rendimientos?|treasur(?:y|ies)|deuda)\b",
        re.IGNORECASE),
     frozenset(), frozenset({"rate", "rates"})),
    ("oil", re.compile(r"\b(?:oil|crude|brent|wti|petr[óo]leo|crudo)\b", re.IGNORECASE),
     frozenset(), frozenset({"energy"})),
    ("metals", re.compile(r"\b(?:gold|silver|copper|oro|plata|cobre)\b", re.IGNORECASE),
     frozenset(), frozenset({"metal"})),
    # "markets rose" in everyday prose means equities — deliberately NOT a
    # match-anything bucket, which would let an unrelated instrument moving the
    # right way corroborate a claim about something else.
    ("markets", re.compile(r"\b(?:markets?|mercados?)\b", re.IGNORECASE),
     frozenset({"index", "champion"}),
     frozenset({"equity-index", "equity-etf", "equity-single"})),
)
# Quote conventions these classes do NOT declare — they can never settle a
# direction claim (see HONEST SCOPE above).
_MARKET_AMBIGUOUS_CLASSES = frozenset({"fx", "fx-index", "rate", "rates"})
# Label words that identify no instrument on their own.
_MARKET_NAME_STOP = frozenset({
    "index", "indices", "fund", "etf", "stock", "stocks", "share", "shares",
    "front", "month", "crude", "spot", "futures", "dollar", "peso", "euro",
    "yen", "bond", "bonds", "note", "notes", "year", "market", "markets",
    "price", "prices", "front-month", "composite", "general",
})
_MARKET_FLAT_EPS = 0.05                  # |change| under this is "no move", not a direction
_MARKET_TERSE_MARKER = " (uncorroborated)"


def _market_name_tokens(label: str, symbol: str) -> set[str]:
    toks = {t for t in _TOKEN_RE.findall((label or "").lower())
            if len(t) >= 4 and t not in _MARKET_NAME_STOP}
    sym = (symbol or "").lower()
    if len(sym) >= 4 and sym not in _MARKET_NAME_STOP:
        toks.add(sym)
    return toks


def _market_subject_keys(sentence: str) -> set[str]:
    return {key for key, pattern, _r, _c in _MARKET_SUBJECTS if pattern.search(sentence)}


def _market_claim_direction(sentence: str) -> int | None:
    """+1 / -1, or None when the sentence names no direction or names both."""
    up, down = bool(_MARKET_UP_RE.search(sentence)), bool(_MARKET_DOWN_RE.search(sentence))
    if up == down:
        return None
    return 1 if up else -1


def _market_named(sentence: str,
                  markets: list[SynthMarketReceipt]) -> list[SynthMarketReceipt]:
    """Instruments this sentence names outright ("Ecopetrol", "COLCAP") — the
    strongest subject signal there is, and one that needs no subject lexicon."""
    lowered = sentence.lower()
    return [m for m in markets
            if any(t in lowered for t in _market_name_tokens(m.label, m.symbol))]


def _market_matches(sentence: str, keys: set[str],
                    markets: list[SynthMarketReceipt]) -> list[SynthMarketReceipt]:
    """Instruments this sentence is about — named outright, else by subject class."""
    named = _market_named(sentence, markets)
    if named:
        return named
    out: list[SynthMarketReceipt] = []
    for key, _p, roles, classes in _MARKET_SUBJECTS:
        if key not in keys:
            continue
        for m in markets:
            if m in out:
                continue
            if (m.role or "") in roles or (m.asset_class or "") in classes:
                out.append(m)
    return out


def _market_sign(m: SynthMarketReceipt) -> int | None:
    """The measured direction of a receipt, or None when it cannot settle one."""
    if (m.asset_class or "").lower() in _MARKET_AMBIGUOUS_CLASSES:
        return None
    if m.change_pct is None:
        return None
    if abs(m.change_pct) < _MARKET_FLAT_EPS:
        return 0
    return 1 if m.change_pct > 0 else -1


def _cited_support(sentence: str, claim: int,
                   cited_headlines: dict[int, str] | None) -> bool:
    """A cited evidence headline that itself reports the same move. The claim
    then HAS a receipt — reported rather than measured — so it stands."""
    if not cited_headlines:
        return False
    for m in _CITE_RE.finditer(sentence):
        headline = cited_headlines.get(int(m.group(1)))
        if not headline:
            continue
        if _market_subject_keys(headline) and _market_claim_direction(headline) == claim:
            return True
    return False


def _market_marker(worst: SynthMarketReceipt | None) -> str:
    if worst is None:
        return (" — reported (uncorroborated): no market receipt in this edition "
                "measures that move")
    asof = f" ({worst.last_close_at})" if worst.last_close_at else ""
    return (f" — reported (uncorroborated): the served market receipt measures "
            f"{worst.label} {worst.change_pct:+.2f}% at its last close{asof}")


def apply_market_direction_guard(
    texts: list[str],
    markets: list[SynthMarketReceipt] | None,
    *,
    cited_headlines: dict[int, str] | None = None,
    terse: bool = False,
) -> tuple[list[str], list[dict]]:
    """Downgrade every sentence asserting a market DIRECTION that no receipt
    carries. Pure. Returns (guarded texts, ledger).

    `terse=True` is the headline form: the ≤14-word headline gets the short
    "(uncorroborated)" stamp instead of the full clause, so a downgraded lede
    can never sit under a headline still asserting the move.
    """
    if not texts:
        return texts, []
    markets = list(markets or [])

    out: list[str] = []
    ledger: list[dict] = []
    for text in texts:
        rebuilt: list[str] = []
        for sentence in _split_sentences(text or ""):
            if not sentence.strip():
                rebuilt.append(sentence)
                continue
            keys = _market_subject_keys(sentence)
            named = _market_named(sentence, markets)
            claim = _market_claim_direction(sentence) if (keys or named) else None
            if claim is None or _HEDGE_RE.search(sentence):
                rebuilt.append(sentence)
                continue
            matched = named or _market_matches(sentence, keys, markets)
            measurable = [(m, s) for m in matched if (s := _market_sign(m)) is not None]
            if measurable:
                if any(sign == claim for _m, sign in measurable):
                    rebuilt.append(sentence)          # the receipt corroborates it
                    continue
                worst = max(measurable, key=lambda pair: abs(pair[0].change_pct))[0]
                basis = "contradicted"
            else:
                if _cited_support(sentence, claim, cited_headlines):
                    rebuilt.append(sentence)          # the press reported the move
                    continue
                worst, basis = None, "uncorroborated"
            marker = _MARKET_TERSE_MARKER if terse else _market_marker(worst)
            m = _TERMINAL_RE.search(sentence)
            if m:
                marked = sentence[:m.start()] + marker + m.group(1) + m.group(2)
            else:
                marked = sentence.rstrip() + marker
            ledger.append({
                "sentence": sentence.strip(),
                "claim": "up" if claim == 1 else "down",
                "subjects": sorted(keys),
                "basis": basis,
                "symbol": worst.symbol if worst else None,
                "label": worst.label if worst else None,
                "change_pct": worst.change_pct if worst else None,
                "as_of": worst.last_close_at if worst else None,
            })
            rebuilt.append(marked)
        out.append("".join(rebuilt))
    return out, ledger


# ── capital-as-proxy geography guard (X3-B) ───────────────────────────────────
# Veracity scorecard claim 1: two testers read two variants of the same lead —
# one correct ("Chocó"), one false ("epicenter near Bogotá"). The epicenter was
# San José del Palmar, Chocó, ~240 km WEST of Bogotá (USGS), and the receipts
# under the story were correct. No code maps a country to its capital; the city
# entered through the generative lede, which had no city-vs-receipt check.
#
# THE RULE: a city appears only when a receipt carries it. Degraded geography
# names the COUNTRY ("in Colombia") and never a stand-in city.
#
# HONEST SCOPE: it fires only on a LOCATION PREPOSITION followed by a
# Title-Case place the GeoNames gazetteer resolves (`resolve_gazetteer_place`,
# cities ≥15k + admin-1, country names and the leader/demonym lexicons
# excluded). A place the gazetteer does not carry (San José del Palmar) is left
# untouched rather than guessed at, and the longest captured phrase is resolved
# WHOLE — never by prefix, which would file that Chocó town in Costa Rica.
_GEO_PREP_ES = ("cerca de", "en las afueras de", "a las afueras de", "en")
_GEO_TITLE_WORD = r"[A-ZÀ-ÖØ-Þ][\w'’À-ſ-]*"
_GEO_PLACE_RE = re.compile(
    r"(?P<prep>\b(?:in|at|near|outside|around|close to|just outside|"
    r"on the outskirts of|cerca de|en las afueras de|a las afueras de|en)\s+)"
    r"(?P<place>" + _GEO_TITLE_WORD + r"(?:\s+(?:de|del|la|las|los|el|of|the)\s+"
    + _GEO_TITLE_WORD + r"|\s+" + _GEO_TITLE_WORD + r"){0,3}"
    # the ONE comma tail that is unambiguously part of the place name, so the
    # rewrite never leaves an orphan ("in the United States, D.C.")
    r"(?:,\s*D\.?\s?C\.?)?)"
)
_GEO_DC_TAIL_RE = re.compile(r",\s*D\.?\s?C\.?$")
# Title-Case words that are never part of a place name — trimmed off the tail so
# "in Cali Tuesday" still resolves "Cali".
_GEO_TRAILING_STOP = frozenset({
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "lunes", "martes",
    "miércoles", "miercoles", "jueves", "viernes", "sábado", "sabado", "domingo",
})
# Country names that read as "the <name>" in running prose.
_GEO_THE_COUNTRIES = frozenset({
    "United States", "United Kingdom", "United Arab Emirates", "Netherlands",
    "Philippines", "Bahamas", "Gambia", "Maldives", "Marshall Islands",
    "Solomon Islands", "Czech Republic", "Dominican Republic",
    "Central African Republic", "Democratic Republic of the Congo",
    "Republic of the Congo", "Ivory Coast",
})


def _fold(text: str) -> str:
    """Accent- and case-insensitive fold, so a receipt spelling "Choco" still
    carries the prose's "Chocó"."""
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", text or "")
        if not unicodedata.combining(c)
    )
    return stripped.casefold()


def _geo_country_phrase(code: str) -> str | None:
    name = ISO_COUNTRY_NAMES.get(code)
    if not name:
        return None
    return f"the {name}" if name in _GEO_THE_COUNTRIES else name


def apply_geography_guard(
    texts: list[str], receipt_texts: list[str] | None,
) -> tuple[list[str], list[dict]]:
    """Rewrite every located CITY the receipts do not carry down to its country.
    Pure. Returns (guarded texts, ledger). A no-op without a receipt corpus —
    with nothing to check against, the guard refuses to rewrite geography."""
    corpus = [t for t in (receipt_texts or []) if t and str(t).strip()]
    if not texts or not corpus:
        return texts, []
    haystack = _fold(" \n ".join(str(t) for t in corpus))

    out: list[str] = []
    ledger: list[dict] = []
    for text in texts:
        def _replace(m: re.Match) -> str:
            prep = m.group("prep")
            place = _GEO_DC_TAIL_RE.sub("", m.group("place").strip()).rstrip(".,;:!?")
            words = place.split()
            while words and _fold(words[-1]) in _GEO_TRAILING_STOP:
                words.pop()
            place = " ".join(words)
            if not place:
                return m.group(0)
            code = resolve_gazetteer_place(place)
            if not code:
                return m.group(0)                     # unresolvable → never guessed
            if _fold(place) in haystack:
                return m.group(0)                     # a receipt carries the city
            country = _geo_country_phrase(code)
            if not country:
                return m.group(0)
            spanish = prep.strip().lower().startswith(_GEO_PREP_ES)
            # Spanish prose keeps the Spanish preposition; the country name stays
            # in the ISO English form the rest of the payload uses (and drops the
            # article, which does not carry across).
            replacement = ("en " + (ISO_COUNTRY_NAMES.get(code) or country)
                           if spanish else "in " + country)
            tail = m.group("place")[len(m.group("place").rstrip()):]
            ledger.append({
                "place": place,
                "country": ISO_COUNTRY_NAMES.get(code),
                "country_code": code,
                "replaced_with": replacement,
            })
            return replacement + tail

        out.append(_GEO_PLACE_RE.sub(_replace, text or ""))
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
             "tension_downgrades": None, "market_downgrades": None,
             "geography_downgrades": None}
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
        table = _citation_table(req)
        # The prose may not settle a tension the cross-read MEASURED, may not
        # invent a market direction, and may not invent a place — all three
        # enforced after the pass, never left to the model's compliance.
        guarded, downgrades = apply_tension_guard(
            ([lede] if lede else []) + (body or []), req.tensions)
        # Receipt corpus for the geography check: the frozen headlines plus any
        # fetched full text riding under them. Pin labels are NOT receipts (a
        # label is itself generated — the mislabel class).
        receipt_corpus = [row["headline"] for row in table] + [
            str(art.get("text") or "") for art in article_texts.values()
        ]
        # The two X3 guards also cover `unknowns` — it is prose the reader reads,
        # so an invented city or market move there is the same defect.
        body_n = len(body or [])
        prose = guarded + (unknowns or [])
        prose, market_downgrades = apply_market_direction_guard(
            prose, req.markets,
            cited_headlines={row["n"]: row["headline"] for row in table},
        )
        prose, geography_downgrades = apply_geography_guard(prose, receipt_corpus)
        head = 0
        if lede:
            lede, head = prose[0], 1
        body = prose[head:head + body_n] or None
        unknowns = prose[head + body_n:] or None
        headline = (parsed.get("headline") or None)
        if headline:
            # Same two guards on the headline: a downgraded lede must never sit
            # under a headline still asserting the move, and an invented city in
            # ≤14 words is the variant a reader quotes.
            (headline,), headline_geo = apply_geography_guard([headline], receipt_corpus)
            (headline,), headline_market = apply_market_direction_guard(
                [headline], req.markets, terse=True)
            market_downgrades += headline_market
            geography_downgrades += headline_geo
        citations = _resolve_citations(
            ([lede] if lede else []) + (body or []), table)
        return {
            **empty,
            "headline": headline,
            "lede": lede,
            "body": body,
            "unknowns": unknowns,
            "citations": citations or None,
            "tension_downgrades": downgrades or None,
            "market_downgrades": market_downgrades or None,
            "geography_downgrades": geography_downgrades or None,
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
