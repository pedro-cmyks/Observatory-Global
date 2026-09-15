"""Story share-editorial — the quote-gated LinkedIn lede for ONE story.

Piece A v2 of the launch campaign (spec 2026-08-24-campana-lanzamiento §2.1):
Pedro judged the v1 kit "cero tratamiento editorial, solo una foto de datos
crudos". The fix is a 2-3 sentence lede in English, synthesized from the
CURATED receipts the analyst picked in the kit dialog — with the same honesty
machinery the product already trusts:

  * QUOTE GATE (article_read pattern): every sentence must cite one receipt
    and carry a VERBATIM quote from that receipt's headline. The quote is
    validated as a normalized substring at parse time — a sentence the model
    cannot ground is DROPPED, so a hallucinated claim is unrepresentable in
    the response. Zero surviving sentences is a legal, honest answer.
  * NUMBER GUARD: every digit run in a sentence must appear in the receipt it
    cites. The lede can never invent a count the coverage does not carry.
  * STATE MEDIA IS NEVER NEUTRAL (publication_synthesis rule 4a, enforced
    mechanically here, not hoped): a sentence resting on a state-media receipt
    must name the outlet in the sentence itself, or it is dropped.

One LLM call per generation through the insight chain (Anthropic→DeepSeek,
cost-ledgered via surface="story-share-editorial"); the router caches the
successful result in Redis so regenerating the same curated set never re-pays.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.services.article_read import _extract_json, _norm  # shared, test-frozen
from app.services.insight_llm import generate_insight

logger = logging.getLogger("atlas.story_editorial")

PROMPT_VERSION = "share-editorial-v2"  # v2: standalone-sentence rule + orphan gate
MAX_RECEIPTS = 4
MAX_SENTENCES = 3
# A quote shorter than this is too easy to satisfy by accident ("the", a bare
# name) — unless it IS the whole headline, which is as grounded as it gets.
MIN_QUOTE_CHARS = 12
LLM_SURFACE = "story-share-editorial"


@dataclass
class EditorialReceipt:
    headline: str
    outlet: str | None = None
    lang: str | None = None
    country: str | None = None
    # Resolved by the ROUTER: client tier flag OR the server-side name
    # classifier (source_tiers) — the server never trusts the client alone
    # to decide an outlet is NOT state media.
    state_media: bool = False


_EDITORIAL_SYSTEM = """You are the editor of Atlas, a narrative-intelligence system that measures \
world news coverage. Write the lede for ONE measured story, in English, from \
the numbered receipt headlines provided — and from nothing else.

HARD RULES:
1. 2-3 sentences of tight news prose. No hashtags, no emoji, no hype, no \
first person. EVERY sentence must stand on its own: no pronouns or \
definite references ("The denial", "This", "He", "It") that depend on \
another sentence — a sentence may be removed by the fact-check and the \
rest must still read.
2. EVERY sentence must be supported by one receipt: put a VERBATIM quote \
(exact characters, in the receipt's original language) from that receipt's \
headline in the "quote" field, with the receipt number. A sentence you cannot \
back with a verbatim quote is forbidden — omit it instead.
3. Do not invent numbers, causes, outcomes, or context beyond the headlines. \
Any number you write must appear in the receipt the sentence cites.
4. STATE MEDIA IS NEVER NEUTRAL: when a sentence rests on a receipt tagged \
[STATE MEDIA], attribute the claim to that outlet by name in the sentence \
itself (e.g. "..., according to RT.").
5. Receipts may be in any language; the lede is always English.
6. Output STRICT JSON only, no prose around it:
{"sentences": [{"text": "...", "quote": "...", "receipt": 1}]}"""


def build_editorial_user_prompt(label: str, receipts: list[EditorialReceipt]) -> str:
    lines = [f"Story label: {label}", "", "Receipts:"]
    for i, r in enumerate(receipts, start=1):
        meta = " · ".join(p for p in ((r.lang or "").strip(), (r.outlet or "").strip(), (r.country or "").strip()) if p)
        tag = " [STATE MEDIA]" if r.state_media else ""
        lines.append(f"[{i}] ({meta}) {r.headline.strip()}{tag}" if meta else f"[{i}] {r.headline.strip()}{tag}")
    lines.append("")
    lines.append("Write the lede.")
    return "\n".join(lines)


def _digit_runs(s: str) -> set[str]:
    return set(re.findall(r"\d+", s))


def _outlet_tokens(outlet: str | None) -> list[str]:
    """Referenceable name tokens for the state-attribution check: lowercase
    alphanumeric tokens of the outlet name minus bare TLD noise. 'russian.rt.com'
    -> ['russian', 'rt']."""
    if not outlet:
        return []
    toks = [t for t in re.split(r"[^a-z0-9]+", outlet.lower()) if len(t) >= 2]
    # A purely numeric token ("24" of 24.kg) would satisfy the check whenever
    # the sentence carries that NUMBER — a name reference must carry a letter.
    return [
        t for t in toks
        if not t.isdigit() and t not in {"com", "net", "org", "www", "co", "info", "news"}
    ]


def _attribution_ok(text: str, outlet: str | None) -> bool:
    toks = _outlet_tokens(outlet)
    if not toks:
        # No referenceable name to demand — cannot enforce, do not fake it.
        return True
    low = text.lower()
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in toks)


# A sentence that opens by pointing back ("The denial follows…", "This…",
# "He…") reads as nonsense once the sentence it points to is dropped by the
# gate (measured 2026-09-14 on dt-277: France24 sentence dropped, Repubblica
# sentence left opening with "The denial follows a Haaretz revelation…").
_DEFINITE_OPENER = re.compile(
    r"^the\s+(?:denial|claim|move|decision|report|response|statement|remark|"
    r"announcement|accusation|warning|deal|meeting|talks|vote|ban|lawsuit|suit|"
    r"revelation|figure|number|incident|plan|ruling|order|comments?|remarks)\b",
    re.IGNORECASE,
)
_PRONOUN_OPENER = re.compile(
    r"^(?:this|that|these|those|he|she|it|they|his|her|its|their|such|both|"
    r"neither|meanwhile|however|in\s+response|in\s+turn|as\s+a\s+result|"
    r"the\s+(?:former|latter))\b",
    re.IGNORECASE,
)


def _opens_with_anaphora(text: str, *, after_drop: bool) -> bool:
    """A pronoun/connector opener always depends on a prior sentence. A
    definite "The <event-noun>…" opener is fine as a lede's first line ("The
    strike killed two…") but reads as orphaned right after a drop."""
    t = text.strip()
    if _PRONOUN_OPENER.match(t):
        return True
    return after_drop and bool(_DEFINITE_OPENER.match(t))


def validate_editorial(parsed: dict | None, receipts: list[EditorialReceipt]) -> dict:
    """The gate. Returns {"sentences": [...], "dropped": n} — kept sentences
    carry {text, quote, receipt(1-based)}. Zero kept is legal.

    Orphan rule: a sentence opening with a pronoun/connector ("This…",
    "He…", "Meanwhile…") always depends on another one and is dropped; a
    definite "The <event-noun>…" opener is dropped only when the sentence
    right before it fell — it depended on the one that fell."""
    kept: list[dict] = []
    dropped = 0
    raw = parsed.get("sentences") if isinstance(parsed, dict) else None
    if not isinstance(raw, list):
        return {"sentences": [], "dropped": 0}
    previous_dropped = False
    for item in raw:
        if len(kept) >= MAX_SENTENCES:
            break
        if not isinstance(item, dict):
            dropped += 1
            previous_dropped = True
            continue
        text = str(item.get("text") or "").strip()
        quote = str(item.get("quote") or "").strip()
        ref = item.get("receipt")
        if not text or not quote or not isinstance(ref, int) or not (1 <= ref <= len(receipts)):
            dropped += 1
            previous_dropped = True
            continue
        receipt = receipts[ref - 1]
        head_norm = _norm(receipt.headline)
        quote_norm = _norm(quote)
        # Quote gate: verbatim substring; substantial, or the whole headline.
        if not quote_norm or quote_norm not in head_norm:
            dropped += 1
            previous_dropped = True
            continue
        if len(quote_norm) < MIN_QUOTE_CHARS and quote_norm != head_norm:
            dropped += 1
            previous_dropped = True
            continue
        # Number guard: every digit run in the sentence must exist in the
        # cited headline — a count the coverage does not carry cannot print.
        if not _digit_runs(text) <= _digit_runs(receipt.headline):
            dropped += 1
            previous_dropped = True
            continue
        # State media never neutral — attribution enforced, not hoped.
        if receipt.state_media and not _attribution_ok(text, receipt.outlet):
            dropped += 1
            previous_dropped = True
            continue
        if _opens_with_anaphora(text, after_drop=previous_dropped):
            dropped += 1
            previous_dropped = True
            continue
        kept.append({"text": text, "quote": quote, "receipt": ref})
        previous_dropped = False
    return {"sentences": kept, "dropped": dropped}


async def run_share_editorial(
    label: str,
    receipts: list[EditorialReceipt],
    *,
    session_id: str | None = None,
) -> dict:
    """One chain call → parse → gate. Returns the response body minus the
    router's envelope fields (cache/contract/story): {lede, sentences,
    dropped, provider, error}. `lede` is None with an error code when the
    chain failed or nothing survived the gate — never a fabricated line."""
    receipts = receipts[:MAX_RECEIPTS]
    user = build_editorial_user_prompt(label, receipts)
    text, provider, error, _usage = await generate_insight(
        _EDITORIAL_SYSTEM,
        user,
        max_tokens=700,
        surface=LLM_SURFACE,
        session_id=session_id,
    )
    if text is None:
        return {"lede": None, "sentences": [], "dropped": 0, "provider": provider, "error": error or "insight_unavailable"}
    parsed = _extract_json(text)
    gated = validate_editorial(parsed, receipts)
    if not gated["sentences"]:
        logger.info("share-editorial quote gate dropped everything (dropped=%s, provider=%s)", gated["dropped"], provider)
        return {"lede": None, "sentences": [], "dropped": gated["dropped"], "provider": provider, "error": "quote_gate_failed"}
    lede = " ".join(s["text"] for s in gated["sentences"])
    return {"lede": lede, "sentences": gated["sentences"], "dropped": gated["dropped"], "provider": provider, "error": None}
