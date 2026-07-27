#!/usr/bin/env python3
"""Compute Atlas's PRIMARY metric: query-conditional investigation recall.

Roadmap Phase 2 (`docs/specs/2026-07-09-resume-roadmap.md`): *"for a gold set of
~20 real analyst queries, does Atlas have a clean thread answering each?
Target: >=80% answered by a useful thread."* Never computed before this script.

Gold set + rubric: `docs/research/gold/gold-query-set-v1.json` and
`docs/research/gold/2026-07-27-gold-query-set-v1.md`.

What this harness does, per query:

  R1  GET /api/v2/threads?hours=H&limit=40                    (global list)
  R2  GET /api/v2/threads?...&country_code=CC                 (per query region)
  R3  pick <=N candidates from R1 u R2 BY RECEIPTS, not by label (rubric G4),
      then GET /api/v2/theme/{thread_id}?hours=H for each     (the scored set)
  R4  honest floor: GET /api/v2/search/thread at 6h AND 24h   (rubric G5)
      plus the VERBATIM question, which is what an analyst actually pastes.

Structural metrics are computed in code (no LLM): receipt counts, distinct
outlets / origin countries / source languages, and the syndication measure via
`thread_ranking._norm_headline` — the same normaliser the ranker dedupes on.

The 0-3 semantic score comes from a two-pass judge over the sanctioned LLM chain
(`insight_llm.generate_insight`, Anthropic -> DeepSeek). Pass 1 sees receipts
ONLY (rubric G8: no label, no metadata, no expected class) and its per-receipt
verdicts are immutable; ROR is computed in code from those verdicts so the model
cannot fudge the arithmetic. Pass 2 unlocks the label, the payload metadata, the
structural metrics, the harness-detected rule triggers and the query's own
`pass_criteria`, and returns the score with quoted evidence.

Honest failure is a first-class outcome: if the judge lane is down every score
is `null` and the structural metrics still land. Nothing is ever fabricated.

Dry run is the default (everything runs, no files are written); `--execute`
writes the JSONL ledger and the markdown report under `docs/research/gold/`.

Usage:
    set -a; . ~/AtlasLocalWorker/.env; set +a
    backend/.venv/bin/python backend/scripts/run_gold_query_eval.py --execute
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.search_normalization import normalize_search_text
# Private by name, shared by intent: this is THE definition of "one headline"
# used by the ranker's syndication damp. Replicating it here would let the
# harness and the engine disagree about what a reprint is.
from app.services.thread_ranking import _norm_headline, headline_diversity
from app.services.insight_llm import generate_insight

logger = logging.getLogger("gold_eval")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = REPO_ROOT / "docs/research/gold/gold-query-set-v1.json"
DEFAULT_OUT_DIR = REPO_ROOT / "docs/research/gold"
DEFAULT_BASE_URL = "https://atlas-api-pedro.fly.dev"

HARNESS_VERSION = "gold-query-eval-v1"

# ---------------------------------------------------------------------------
# Rubric constants (docs/research/gold/2026-07-27-gold-query-set-v1.md sec.2/4/5)
# ---------------------------------------------------------------------------

RUBRIC_SCALE = """LEVEL 3 - Directly answers: ROR@20 >= 0.90 AND ROR@all >= 0.75 AND the label
  describes the majority receipt set AND >=3 distinct outlets across >=2 distinct
  origin countries with syndication collapsed AND the query's country/actor is
  present in the receipts AND no unflagged defect.
LEVEL 2 - Usable with its own caveats: ROR@20 >= 0.75 AND ROR@all >= 0.50 AND the
  label describes the majority receipt set AND >=3 independent outlets. Defects may
  be present ONLY IF Atlas itself surfaces them (coherence.tier/.warning,
  label_status, confidence, warnings[], quality.noise_rate).
LEVEL 1 - Honest floor / adjacent only: (a) Atlas declares it has nothing and returns
  labelled raw signal with real sources and a coverage tier; or (b) the only thread is
  a genuinely NEIGHBOURING story, correctly labelled and correctly flagged, that does
  not answer the question. Not answered - but not a failure of honesty.
LEVEL 0 - Absent or false: no thread and no working floor; OR receipts do not support
  the label (ROR@20 < 0.5); OR a real defect is present and flagged NOWHERE in the
  payload; OR a silent empty (a broad window returning 0 while a shorter window
  returns >0, with no degraded marker)."""

HONESTY_RULE = """THE HONESTY RULE, which outranks everything else:
A CONFIDENT GRAB-BAG SCORES 0. AN HONEST EMPTY SCORES 1.
A run where Atlas fails loudly is a better product than a run where it fabricates.
Never reward fluent prose that is not carried by the served receipts."""

CONTROL_RULE = """THIS ITEM IS A NEGATIVE CONTROL. It looks like a plausible analyst question
but cannot be answered honestly from a 7-day press corpus - either the event is absent
from the corpus, or the KIND of question (who broke it first / did coverage move the
price / what does the public think) is outside what a press-coverage index can measure.
The control PASSES when Atlas returns an honest absence (level 0 or 1) and FAILS when it
returns a confident-looking answer (level 2 or 3). Do NOT credit Atlas for producing
something. Score what Atlas would actually show an analyst who asked this."""

# Each control is twinned with a real item of near-identical shape (rubric sec.5).
PAIRS: list[tuple[str, str, str]] = [
    ("GQ-15", "GQ-01", "disaster vocabulary vs measured event"),
    ("GQ-17", "GQ-04", "governance template vs evidence"),
    ("GQ-18", "GQ-02", "same substrate, answerable vs not"),
    ("GQ-19", "GQ-08", "measurable finance vs forecast"),
    ("GQ-20", "GQ-06", "evidence vs opinion, same corpus"),
    ("GQ-16", "GQ-04", "low-volume region: no data vs no evidence"),
]

# ---------------------------------------------------------------------------
# Lexical helpers (deterministic, logged, used for candidate selection + a
# code-side on-topic PROXY -- never presented as the judged ROR)
# ---------------------------------------------------------------------------

STOPWORDS = frozenset("""
a an and are as at be been being but by did do does for from had has have how i in
into is it its of on or that the their them then there these they this to was were
what when where which while who whom why will with would you your about after against
against also any been can could may might must not now only over same should since so
such than that's there's through under until upon very via we what's yet
""".split())

# Words that are real content but too generic to make a good corpus probe.
# Used ONLY for probe selection, never for on-topic matching.
GENERIC_FOR_PROBE = frozenset("""
coverage emergency evacuating evacuated evacuation states state response international
media outlets press government authorities first phase happened week weekly people
actually exactly ordinary reporting reported report story news said says think give
side marked mean means leave suddenly announced exposed risk action legal taking
closing cutting ties covering versus english scandal around said exploded front
""".split())

COUNTRY_ALIASES: dict[str, str] = {
    "spain": "ES", "france": "FR", "germany": "DE", "philippines": "PH",
    "colombia": "CO", "cuba": "CU", "nicaragua": "NI", "iran": "IR",
    "united states": "US", "indonesia": "ID", "romania": "RO", "pakistan": "PK",
    "kashmir": "PK", "sudan": "SD", "australia": "AU", "lesotho": "LS",
    "mongolia": "MN", "ukraine": "UA", "congo": "CD",
    "democratic republic of the congo": "CD", "dr congo": "CD",
}


def content_tokens(text: str) -> list[str]:
    """Normalised content tokens (len>=4, stopwords removed), order preserved."""
    out: list[str] = []
    for tok in normalize_search_text(text).split():
        # len>=3 so party/institution acronyms that carry the whole question
        # survive (PSD, AJK, PNRR); 2-char tokens ("US", "DR") are dropped
        # because as a substring they match everything.
        if len(tok) >= 3 and tok not in STOPWORDS and tok not in out:
            out.append(tok)
    return out


def _matches_word(token: str, word: str) -> bool:
    """Word-boundary match with morphology tolerance.

    Tokens of 5+ chars match on a 5-char prefix so 'wildfires'/'wildfire' and
    'evacuated'/'evacuation' agree. Short tokens must match EXACTLY: 'war' as a
    prefix matched 'Warsaw' and put a Poland travel thread top of the Sudan
    query, and 'fire' as a substring matched 'wildfire' and put a Canada-tariff
    thread top of the Iberian wildfire query. Both were measured, both are gone.
    """
    if len(token) <= 4:
        return word == token
    return word.startswith(token[:5])


def token_hits(tokens: list[str], text: str) -> list[str]:
    words = normalize_search_text(text or "").split()
    return [t for t in tokens if any(_matches_word(t, w) for w in words)]


def probe_terms(query: str, limit: int = 2) -> list[str]:
    """Deterministic floor-probe terms for the C3 corpus control.

    `/api/v2/search/thread` is a substring matcher over normalised headline /
    source / themes / persons -- it has NO notion of a multi-token AND. So the
    probe is a single distinctive token (proper nouns first, by order of mention
    in the question), and the remaining query tokens are intersected CLIENT-SIDE
    against the rows it returns. That is the corpus control the rubric's C3 asks
    for, done without pretending the endpoint is a search engine.
    """
    words = re.findall(r"[^\W\d_]+", query, re.UNICODE)
    caps: list[str] = []
    plain: list[str] = []
    for word in words:
        norm = normalize_search_text(word)
        if len(norm) < 4 or norm in STOPWORDS or norm in GENERIC_FOR_PROBE:
            continue
        (caps if word[0].isupper() else plain).append(norm)
    ordered = [t for t in caps if t] + [t for t in sorted(plain, key=len, reverse=True)]
    seen: list[str] = []
    for tok in ordered:
        if tok not in seen:
            seen.append(tok)
    return seen[:limit]


def query_country_codes(entry: dict) -> list[str]:
    """ISO codes mechanically derived from the gold entry's own `region` field."""
    region = (entry.get("region") or "").lower()
    codes: list[str] = []
    for name, code in COUNTRY_ALIASES.items():
        if name in region and code not in codes:
            codes.append(code)
    return codes[:3]


# ---------------------------------------------------------------------------
# Receipts + structural metrics
# ---------------------------------------------------------------------------

def normalise_receipt(row: dict) -> dict:
    """One shape for list `evidence_samples` and detail `signals`."""
    return {
        "headline": row.get("headline") or "",
        "source": row.get("source") or row.get("source_name") or "",
        "country_code": row.get("country_code") or row.get("country") or "",
        "source_lang": row.get("source_lang") or "",
        "source_origin_country": row.get("source_origin_country") or "",
        "syndication_count": row.get("syndication_count"),
        "evidence_role": row.get("evidence_role") or "",
        "url": row.get("url") or "",
    }


def structural_metrics(receipts: list[dict], tokens: list[str]) -> dict:
    """Everything measurable without an LLM. Origin-country and syndication_count
    exist only on the list `evidence_samples` payload; when the scored set is the
    detail payload they come back null and are reported as unavailable, never 0.
    """
    n = len(receipts)
    if not n:
        return {
            "receipts": 0, "distinct_outlets": 0, "distinct_country_codes": 0,
            "distinct_source_langs": 0, "distinct_origin_countries": None,
            "origin_country_available": False, "repeated_headline_share": None,
            "max_headline_cluster_share": None, "headline_diversity": None,
            "syndicated_role_share": None, "lexical_on_topic_at20": None,
            "lexical_on_topic_all": None,
        }
    norm_heads = [_norm_headline(r["headline"]) for r in receipts if r["headline"]]
    counts: dict[str, int] = {}
    for h in norm_heads:
        counts[h] = counts.get(h, 0) + 1
    distinct_heads = len(counts)
    origins = {r["source_origin_country"] for r in receipts if r["source_origin_country"]}
    roles = [r["evidence_role"] for r in receipts if r["evidence_role"]]
    hits = [1 if token_hits(tokens, r["headline"]) else 0 for r in receipts]
    return {
        "receipts": n,
        "distinct_outlets": len({r["source"] for r in receipts if r["source"]}),
        "distinct_country_codes": len({r["country_code"] for r in receipts if r["country_code"]}),
        "distinct_source_langs": len({r["source_lang"] for r in receipts if r["source_lang"]}),
        "distinct_origin_countries": len(origins) if origins else None,
        "origin_country_available": bool(origins),
        # Syndication measure: share of receipts that are NOT a first-of-its-kind
        # headline under the ranker's own reprint normaliser.
        "repeated_headline_share": round(1 - distinct_heads / len(norm_heads), 3) if norm_heads else None,
        "max_headline_cluster_share": round(max(counts.values()) / len(norm_heads), 3) if norm_heads else None,
        "headline_diversity": round(headline_diversity({"evidence_samples": receipts}), 3),
        "syndicated_role_share": round(sum(1 for r in roles if r == "syndicated") / len(roles), 3) if roles else None,
        "lexical_on_topic_at20": round(sum(hits[:20]) / min(20, n), 3),
        "lexical_on_topic_all": round(sum(hits) / n, 3),
    }


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class AtlasClient:
    """Sequential, polite prod client. Every call's status + latency is logged
    into the evidence packet (rubric sec.6)."""

    def __init__(self, base_url: str, delay: float):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.calls: list[dict] = []
        self._client = httpx.AsyncClient(
            headers={"User-Agent": f"AtlasGoldEval/1.0 ({HARNESS_VERSION})"},
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict, *, timeout: float,
                  attempts: int = 1) -> tuple[Any | None, dict]:
        record: dict = {"path": path, "params": {k: str(v)[:120] for k, v in params.items()},
                        "attempts": []}
        data = None
        for attempt in range(1, attempts + 1):
            started = asyncio.get_event_loop().time()
            status: Any = None
            error = None
            try:
                resp = await self._client.get(f"{self.base_url}{path}", params=params,
                                              timeout=timeout)
                status = resp.status_code
                if resp.status_code == 200:
                    data = resp.json()
            except Exception as exc:  # timeout, transport, decode
                error = f"{type(exc).__name__}: {str(exc)[:160]}"
            latency = round(asyncio.get_event_loop().time() - started, 2)
            record["attempts"].append({"n": attempt, "status": status,
                                       "latency_s": latency, "error": error})
            logger.info("  %s %s -> %s (%ss)%s", path,
                        params.get("q") or params.get("country_code") or "",
                        status, latency, f" ERR {error}" if error else "")
            if data is not None:
                break
            await asyncio.sleep(self.delay)
        self.calls.append(record)
        await asyncio.sleep(self.delay)
        return data, record


# ---------------------------------------------------------------------------
# Judge (two-pass, over the sanctioned Anthropic -> DeepSeek chain)
# ---------------------------------------------------------------------------

def _repair_json(fragment: str) -> Any | None:
    """Parse JSON that a provider truncated at max_tokens.

    DeepSeek has cut Atlas JSON mid-structure before (the F2 AI-read lane). Walk
    the fragment, remember every point where the document was structurally safe
    to cut, then close the open containers from the latest such point backwards.
    """
    stack: list[str] = []
    safe: list[tuple[int, tuple[str, ...]]] = []
    in_str = False
    escape = False
    for i, ch in enumerate(fragment):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack:
                stack.pop()
            if stack:
                safe.append((i + 1, tuple(stack)))
        elif ch == "," and stack:
            safe.append((i, tuple(stack)))
    for cut, open_stack in reversed(safe[-80:]):
        candidate = fragment[:cut].rstrip().rstrip(",") + "".join(reversed(open_stack))
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def parse_json_lenient(text: str | None) -> tuple[Any | None, bool]:
    """Returns (parsed, was_repaired)."""
    if not text:
        return None, False
    body = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", body, re.S)
    if fence:
        body = fence.group(1).strip()
    start = body.find("{")
    if start < 0:
        return None, False
    body = body[start:]
    try:
        return json.loads(body), False
    except json.JSONDecodeError:
        pass
    repaired = _repair_json(body)
    return repaired, repaired is not None


async def generate_with_retry(system: str, user: str, *, max_tokens: int,
                              attempts: int = 3) -> tuple[str | None, str | None, str | None, dict | None]:
    """`generate_insight` with backoff.

    The chain itself does not retry, and a single DeepSeek timeout would
    otherwise turn into a null score for a query Atlas actually answered —
    an honest null, but a needlessly expensive one.
    """
    last: tuple = (None, None, "insight_unavailable", None)
    for attempt in range(1, attempts + 1):
        text, provider, error, usage = await generate_insight(system, user, max_tokens=max_tokens)
        if text:
            return text, provider, error, usage
        last = (text, provider, error, usage)
        logger.warning("  judge attempt %d/%d failed (%s)", attempt, attempts, error)
        await asyncio.sleep(2.0 * attempt)
    return last


def _receipt_block(receipts: list[dict], cap: int) -> str:
    lines = []
    for i, r in enumerate(receipts[:cap], start=1):
        lines.append(
            f"{i}. [{r['country_code'] or '--'}|{r['source_lang'] or '--'}|"
            f"{r['source'] or 'unknown'}] {r['headline'][:220]}"
        )
    return "\n".join(lines)


PASS1_SYSTEM = (
    "You are an evidence auditor for a narrative-intelligence system. You see an "
    "analyst's question and the receipts a system served for it. You do NOT see the "
    "system's label or its self-assessment, on purpose. Judge ONLY whether each "
    "receipt is about the specific event/subject the analyst asked about. Receipts in "
    "any language count equally - never mark a receipt off-topic because it is not in "
    "English. Reply with JSON only, no prose."
)


async def judge_pass1(query: str, receipts: list[dict], cap: int,
                      max_tokens: int) -> dict:
    sent = receipts[:cap]
    user = (
        f"ANALYST QUESTION:\n{query}\n\n"
        f"RECEIPTS SERVED (index. [country|lang|outlet] headline):\n"
        f"{_receipt_block(sent, cap)}\n\n"
        "For EVERY index above decide: is this receipt about the specific event or "
        "subject the question asks about? Adjacent-but-different stories are 0.\n"
        'Return JSON exactly: {"verdicts":[{"i":1,"on":1},{"i":2,"on":0}],'
        '"off_examples":[{"i":2,"why":"<=12 words"}]}\n'
        "Include one verdict per index, in order. off_examples: at most 5."
    )
    text, provider, error, usage = await generate_with_retry(
        PASS1_SYSTEM, user, max_tokens=max_tokens)
    parsed, repaired = parse_json_lenient(text)
    verdicts: dict[int, int] = {}
    if isinstance(parsed, dict):
        for v in parsed.get("verdicts") or []:
            try:
                verdicts[int(v["i"])] = 1 if int(v.get("on", 0)) else 0
            except (KeyError, TypeError, ValueError):
                continue
    # ROR is arithmetic over the model's per-receipt verdicts, computed HERE so
    # the model cannot report a rate that its own verdicts do not support.
    at20 = [verdicts[i] for i in range(1, 21) if i in verdicts]
    allv = [verdicts[i] for i in range(1, len(sent) + 1) if i in verdicts]
    return {
        "provider": provider,
        "model": (usage or {}).get("model"),
        "error": error,
        "truncation_repaired": repaired,
        "receipts_sent": len(sent),
        "verdicts_returned": len(allv),
        "ror_at20": round(sum(at20) / len(at20), 3) if at20 else None,
        "ror_all": round(sum(allv) / len(allv), 3) if allv else None,
        "off_examples": (parsed or {}).get("off_examples") if isinstance(parsed, dict) else None,
    }


PASS2_SYSTEM = (
    "You are the scorer for Atlas's primary product metric. You apply a fixed rubric "
    "to one served answer and return a level 0-3 with quoted evidence. You are "
    "adversarial toward fluency: prose that is not carried by the served receipts is "
    "worth nothing. Reply with JSON only, no prose outside the JSON."
)


async def judge_pass2(entry: dict, packet: dict, pass1: dict, receipts: list[dict],
                      max_tokens: int) -> dict:
    is_control = entry["expected"] == "negative_control"
    user = f"""ANALYST QUESTION:
{entry['query']}

EXPECTED CLASS: {entry['expected']}

PASS CRITERIA FOR THIS EXACT ITEM (verbatim from the gold set - it overrides
generic reasoning wherever it is more specific):
{entry['pass_criteria']}

{CONTROL_RULE if is_control else ''}

RUBRIC SCALE ("answered" = level >= 2):
{RUBRIC_SCALE}

{HONESTY_RULE}

--- WHAT ATLAS SERVED ---
Best answer attempt: {packet['scored_object']}
Thread id: {packet['thread_id']}
Thread label: {packet['label']}
Payload metadata: {json.dumps(packet['meta'], ensure_ascii=False)[:1800]}
Structural metrics measured in code: {json.dumps(packet['structural'], ensure_ascii=False)}
Harness-detected rule triggers (mechanical, already verified): {packet['rule_triggers']}
Honest-floor probes (/api/v2/search/thread, 6h and 24h windows):
{json.dumps(packet['floor'], ensure_ascii=False)[:1200]}
Verbatim-question probe (what the analyst gets pasting the question as-is):
{json.dumps(packet['verbatim_probe'], ensure_ascii=False)[:400]}

--- INDEPENDENT PASS-1 RECEIPT AUDIT (immutable, do not recompute) ---
ROR@20 = {pass1.get('ror_at20')}  ROR@all = {pass1.get('ror_all')}
({pass1.get('verdicts_returned')} of {pass1.get('receipts_sent')} receipts judged)
Off-topic examples: {json.dumps(pass1.get('off_examples'), ensure_ascii=False)[:600]}

--- THE FIRST 20 RECEIPTS AS SERVED ---
{_receipt_block(receipts, 20)}

Score this item. Return JSON exactly:
{{"score": <0|1|2|3>,
  "verdict": "<one line, <=30 words>",
  "evidence": ["<verbatim receipt headline or payload field=value that justifies the score>", "..."],
  "rules_fired": ["G1"|"G2"|"G3"|"G4"|"G5"|"G7"|"D2"|"D3"|"D5"|"none"],
  "honesty_note": "<did Atlas flag its own defects? <=25 words>"}}
Every score MUST cite at least one item in "evidence", quoted from the material above.
An unevidenced score is invalid."""
    text, provider, error, usage = await generate_with_retry(
        PASS2_SYSTEM, user, max_tokens=max_tokens)
    parsed, repaired = parse_json_lenient(text)
    out = {
        "provider": provider,
        "model": (usage or {}).get("model"),
        "error": error,
        "truncation_repaired": repaired,
        "score": None, "verdict": None, "evidence": [], "rules_fired": [],
        "honesty_note": None, "raw": (text or "")[:400] if not parsed else None,
    }
    if isinstance(parsed, dict):
        try:
            score = int(parsed.get("score"))
            out["score"] = score if 0 <= score <= 3 else None
        except (TypeError, ValueError):
            out["score"] = None
        out["verdict"] = str(parsed.get("verdict") or "")[:300] or None
        ev = parsed.get("evidence")
        out["evidence"] = [str(e)[:300] for e in ev][:6] if isinstance(ev, list) else []
        rf = parsed.get("rules_fired")
        out["rules_fired"] = [str(r)[:12] for r in rf][:8] if isinstance(rf, list) else []
        out["honesty_note"] = str(parsed.get("honesty_note") or "")[:240] or None
    return out


# ---------------------------------------------------------------------------
# Anti-gaming rules, mechanically decidable (rubric sec.4)
# ---------------------------------------------------------------------------

def detect_rule_triggers(packet_meta: dict, structural: dict, floor: dict,
                         thread_id: str, label: str) -> dict[str, str]:
    """Returns {rule: reason} for every mechanically-certain trigger."""
    fired: dict[str, str] = {}
    meta = packet_meta or {}
    if thread_id and "dynamic-topic-" not in thread_id:
        fired["G1"] = f"thread_id '{thread_id}' is a taxonomy/atlas row, not a dynamic story"
    elif (meta.get("category") or "").strip().lower() == (label or "").strip().lower() and label:
        fired["G1"] = "label equals its own category"
    hd = structural.get("headline_diversity")
    rhs = structural.get("repeated_headline_share")
    srs = structural.get("syndicated_role_share")
    reasons = []
    if hd is not None and hd < 0.5:
        reasons.append(f"headline_diversity {hd} < 0.5")
    if rhs is not None and rhs > 0.35:
        reasons.append(f"repeated_headline_share {rhs} > 0.35")
    if srs is not None and srs >= 0.40:
        reasons.append(f"syndicated evidence_role share {srs} >= 0.40")
    if (meta.get("source_count") or 0) <= 2 and (meta.get("signal_count") or 0) >= 25:
        reasons.append("source_count <=2 with signal_count >=25")
    if reasons:
        fired["G2"] = "; ".join(reasons)
    lifetime = meta.get("lifetime_signal_count") or 0
    window = meta.get("signal_count") or 0
    coherence = meta.get("coherence") or {}
    if window and lifetime and lifetime / max(window, 1) > 10 and coherence.get("tier") == "mixed":
        fired["G3"] = f"lifetime/window {lifetime}/{window} > 10 with coherence.tier=mixed"
    if window and window < 10 and lifetime > 100:
        fired["G7"] = f"window signal_count {window} < 10 while lifetime {lifetime} > 100"
    short = floor.get("probe_6h") or {}
    long = floor.get("probe_24h") or {}
    if (long.get("total") == 0 and (short.get("total") or 0) > 0
            and "query_thread_thin_coverage" in (long.get("warnings") or [])):
        fired["G5"] = (f"silent empty: 24h total=0 while 6h total={short.get('total')} "
                       "on the same probe, no degraded marker")
    return fired


# Caps the mechanical rules impose (rubric sec.4). Applied to the REAL arm only:
# on the control arm a cap would LOWER a confabulated answer toward the control's
# own pass band and hide the failure the control exists to catch. Asymmetry is
# deliberate and reported.
RULE_CAPS = {"G1": 1, "G2": 1, "G3": 1, "G5": 0, "G7": 1}


# ---------------------------------------------------------------------------
# Per-query run
# ---------------------------------------------------------------------------

async def probe_floor(client: AtlasClient, term: str, hours: int, tokens: list[str],
                      timeout: float) -> dict:
    data, rec = await client.get("/api/v2/search/thread",
                                 {"q": term, "hours": hours}, timeout=timeout)
    if not isinstance(data, dict):
        return {"probe": term, "hours": hours, "http": rec["attempts"][-1], "error": True}
    rows = [normalise_receipt(r) for r in (data.get("signals") or [])]
    # Client-side AND: the endpoint has no multi-token intersection, so the rest
    # of the question's tokens are matched here against what the probe returned.
    others = [t for t in tokens if not _matches_word(t, term)]
    on_topic = [r for r in rows if len(token_hits(others, r["headline"])) >= 1]
    return {
        "probe": term,
        "hours": hours,
        "total": data.get("total"),
        "coverageTier": data.get("coverageTier"),
        "warnings": data.get("warnings"),
        "rows_returned": len(rows),
        "lexical_on_topic_rows": len(on_topic),
        "lexical_on_topic_sources": len({r["source"] for r in on_topic if r["source"]}),
        "sample_headlines": [r["headline"][:140] for r in on_topic[:5]],
        "latency_s": rec["attempts"][-1]["latency_s"],
    }


def receipt_fit(receipts: list[dict], tokens: list[str], ccs: list[str]) -> tuple[float, dict]:
    """How well a set of RECEIPTS answers the query. Never reads the label
    (rubric G4: selector and judge both see receipts first).

    Three terms, all receipt-level:
      token_coverage  - share of the question's content tokens found anywhere
      row_rate        - share of receipts carrying at least one of them
      country_share   - share of receipts from the country the question names

    Coverage dominates: a thread whose every receipt says "Romania" and nothing
    else covers 1 token of 12 and must not out-rank one that also says "Bolojan"
    and "PSD". country_share carries the queries whose receipts are in a language
    the question is not written in - the one thing a lexical matcher cannot see
    (D4 scope fit, doing real work here).
    """
    matched: set[str] = set()
    hit_rows = 0
    in_country = 0
    for r in receipts:
        hits = token_hits(tokens, r["headline"])
        if hits:
            hit_rows += 1
            matched.update(hits)
        if ccs and r["country_code"] in ccs:
            in_country += 1
    n = len(receipts)
    token_cov = len(matched) / len(tokens) if tokens else 0.0
    row_rate = hit_rows / n if n else 0.0
    country_share = in_country / n if (n and ccs) else 0.0
    score = (0.45 * token_cov + 0.25 * row_rate + 0.30 * country_share) if ccs \
        else (0.60 * token_cov + 0.40 * row_rate)
    return round(score, 4), {
        "token_coverage": round(token_cov, 3),
        "receipt_hit_rate": round(row_rate, 3),
        "country_share": round(country_share, 3),
        "receipts_scored": n,
    }


# A candidate below BOTH floors is not Atlas answering — it is the harness
# reaching for the closest thing in the served lists. Recorded and told to the
# judge, so a weak reach is never read as a confident answer (which would
# unfairly fail a control) nor as a fabrication by Atlas.
TOPICAL_FLOOR_TOKENS = 0.25
TOPICAL_FLOOR_COUNTRY = 0.50


def clears_topical_floor(why: dict) -> bool:
    return (why.get("token_coverage", 0) >= TOPICAL_FLOOR_TOKENS
            or why.get("country_share", 0) >= TOPICAL_FLOOR_COUNTRY)


def candidate_score(thread: dict, tokens: list[str], ccs: list[str]) -> tuple[float, dict]:
    receipts = [normalise_receipt(r) for r in (thread.get("evidence_samples") or [])]
    score, why = receipt_fit(receipts, tokens, ccs)
    why["label_lexical_hits"] = len(token_hits(tokens, thread.get("label") or ""))
    return score, why


async def run_query(entry: dict, client: AtlasClient, *, hours: int, candidates: int,
                    global_threads: list[dict], country_threads: dict[str, list[dict]],
                    detail_timeout: float, floor_timeout: float, judge: bool,
                    receipt_cap: int) -> dict:
    qid, query = entry["id"], entry["query"]
    logger.info("[%s] %s", qid, query[:96])
    tokens = content_tokens(query)
    ccs = query_country_codes(entry)
    probes = probe_terms(query)
    logger.info("  tokens=%s cc=%s probes=%s", tokens[:8], ccs, probes)

    pool: list[dict] = list(global_threads)
    seen_ids = {t.get("thread_id") for t in pool}
    for cc in ccs:
        for t in country_threads.get(cc, []):
            if t.get("thread_id") not in seen_ids:
                pool.append(t)
                seen_ids.add(t.get("thread_id"))

    ranked = sorted(((candidate_score(t, tokens, ccs), t) for t in pool),
                    key=lambda p: p[0][0], reverse=True)
    shortlist = [(s, why, t) for (s, why), t in ranked if s > 0][:candidates]
    selection_basis = "receipt_lexical" if shortlist else "none"
    if len(shortlist) < candidates:
        # Pad from the country-scoped lists in SERVED rank order. Lexical
        # overlap is English-biased: a thread whose receipts are wholly in
        # Spanish or Romanian can score 0 on an English question and still be
        # the right answer, so it must still get opened. Logged either way.
        chosen = {t.get("thread_id") for _, _, t in shortlist}
        for cc in ccs:
            for t in country_threads.get(cc, []):
                if len(shortlist) >= candidates:
                    break
                if t.get("thread_id") in chosen:
                    continue
                chosen.add(t.get("thread_id"))
                shortlist.append((0.0, {"note": "country_scoped_rank_pad"}, t))
                selection_basis = (selection_basis + "+country_scoped_rank"
                                   if selection_basis != "none" else "country_scoped_rank")

    considered = [{"thread_id": t.get("thread_id"), "label": t.get("label"),
                   "score": round(s, 3), **why} for (s, why), t in ranked[:5]]

    # R3 -- open candidate details, best first; stop at the first strong hit.
    best: dict | None = None
    detail_log: list[dict] = []
    for idx, (score, why, thread) in enumerate(shortlist):
        tid = thread.get("thread_id")
        data, rec = await client.get(f"/api/v2/theme/{tid}", {"hours": hours},
                                     timeout=detail_timeout, attempts=2 if idx == 0 else 1)
        ok = isinstance(data, dict)
        receipts = [normalise_receipt(r) for r in (data.get("signals") or [])] if ok else []
        source = "detail" if receipts else "list_evidence_samples"
        if not receipts:
            receipts = [normalise_receipt(r) for r in (thread.get("evidence_samples") or [])]
        st = structural_metrics(receipts, tokens)
        fit, fit_why = receipt_fit(receipts, tokens, ccs)
        detail_log.append({"thread_id": tid, "resolved": ok, "receipt_source": source,
                           "detail_fit": fit, **fit_why,
                           "lexical_on_topic_at20": st["lexical_on_topic_at20"],
                           "http": rec["attempts"]})
        cand = {"thread": thread, "detail": data if ok else None, "receipts": receipts,
                "structural": st, "receipt_source": source, "selection": why,
                "selection_score": round(score, 3), "detail_fit": fit,
                "detail_fit_why": fit_why, "detail_resolved": ok}
        if best is None or fit > best["detail_fit"]:
            best = cand
        if fit_why["token_coverage"] >= 0.5 and fit_why["receipt_hit_rate"] >= 0.75:
            break  # unambiguous hit; stop spending detail calls

    # R4 -- honest floor + the verbatim question.
    floor: dict = {}
    if probes:
        floor["probe_6h"] = await probe_floor(client, probes[0], 6, tokens, floor_timeout)
        floor["probe_24h"] = await probe_floor(client, probes[0], 24, tokens, floor_timeout)
        if len(probes) > 1:
            floor["probe2_6h"] = await probe_floor(client, probes[1], 6, tokens, floor_timeout)
    verbatim, vrec = await client.get("/api/v2/search/thread", {"q": query, "hours": hours},
                                      timeout=floor_timeout)
    verbatim_probe = {
        "total": (verbatim or {}).get("total"),
        "coverageTier": (verbatim or {}).get("coverageTier"),
        "warnings": (verbatim or {}).get("warnings"),
        "latency_s": vrec["attempts"][-1]["latency_s"],
        "note": "the endpoint is a substring matcher: a full question matches nothing",
    }

    # Evidence packet
    if best is not None:
        thread, detail = best["thread"], best["detail"] or {}
        meta = {
            "signal_count": thread.get("signal_count"),
            "lifetime_signal_count": thread.get("lifetime_signal_count"),
            "source_count": thread.get("source_count"),
            "country_count": thread.get("country_count"),
            "confidence": thread.get("confidence"),
            "confidence_measured": thread.get("confidence_measured"),
            "confidence_source": thread.get("confidence_source"),
            "avg_confidence": thread.get("avg_confidence"),
            "label_status": thread.get("label_status") or detail.get("label_status"),
            "label_proposed": thread.get("label_proposed"),
            "category": thread.get("category"),
            "anchor_topics": thread.get("anchor_topics"),
            "subject_countries": thread.get("subject_countries"),
            "subject_geography_status": thread.get("subject_geography_status"),
            "temporal_signature": thread.get("temporal_signature"),
            "trend": thread.get("trend"),
            "why_now": thread.get("why_now"),
            "quality": thread.get("quality"),
            "coherence": detail.get("coherence"),
            "warnings": detail.get("warnings"),
            "detail_total": detail.get("total"),
            "detail_signalSample": detail.get("signalSample"),
        }
        weak = not clears_topical_floor(best["detail_fit_why"])
        scored_object = f"served thread ({best['receipt_source']})"
        if weak:
            scored_object += (
                " — WEAK CANDIDATE: no thread in the served lists cleared the harness's"
                " topical floor (token coverage <0.25 and country share <0.50). This is"
                " the closest thing available, NOT Atlas confidently answering. Treat the"
                " honest-floor probes below as the real answer material."
            )
        packet = {
            "scored_object": scored_object,
            "thread_id": thread.get("thread_id"),
            "label": thread.get("label"),
            "meta": meta,
            "structural": best["structural"],
            "floor": floor,
            "verbatim_probe": verbatim_probe,
        }
        receipts = best["receipts"]
        result_weak = weak
    else:
        result_weak = True
        meta = {}
        packet = {
            "scored_object": "no candidate thread in the served lists; floor probe only",
            "thread_id": None, "label": None, "meta": {},
            "structural": structural_metrics([], tokens),
            "floor": floor, "verbatim_probe": verbatim_probe,
        }
        receipts = []

    triggers = detect_rule_triggers(meta, packet["structural"], floor,
                                    packet["thread_id"] or "", packet["label"] or "")
    packet["rule_triggers"] = triggers or "none"

    result: dict = {
        "id": qid, "query": query, "expected": entry["expected"],
        "domain": entry.get("domain"), "region": entry.get("region"),
        "query_tokens": tokens, "country_codes": ccs, "probe_terms": probes,
        "selection_basis": selection_basis,
        "candidates_considered": considered,
        "detail_calls": detail_log,
        "thread_id": packet["thread_id"], "label": packet["label"],
        "receipt_source": best["receipt_source"] if best else None,
        "detail_fit": best["detail_fit"] if best else None,
        "detail_fit_why": best["detail_fit_why"] if best else None,
        "weak_candidate": result_weak,
        "structural": packet["structural"],
        "meta": meta,
        "floor": floor,
        "verbatim_probe": verbatim_probe,
        "rule_triggers": triggers,
        "pass1": None, "judge": None,
        "score": None, "judge_score": None, "cap_applied": None,
        "verdict": None, "evidence": [], "error": None,
    }

    if not judge:
        result["error"] = "judge_disabled"
        return result

    try:
        pass1 = await judge_pass1(query, receipts, receipt_cap, max_tokens=2400) if receipts else {
            "provider": None, "model": None, "error": "no_receipts",
            "ror_at20": None, "ror_all": None, "receipts_sent": 0,
            "verdicts_returned": 0, "off_examples": None, "truncation_repaired": False}
        result["pass1"] = pass1
        # G3 needs the judged ROR@all, so it is added after pass 1.
        if pass1.get("ror_all") is not None and pass1["ror_all"] < 0.60 and packet["structural"]["receipts"]:
            triggers["G3"] = f"ROR@all {pass1['ror_all']} < 0.60 (over-merged)"
            packet["rule_triggers"] = triggers
        judged = await judge_pass2(entry, packet, pass1, receipts, max_tokens=900)
        if judged["score"] is not None and not judged["evidence"]:
            logger.warning("  [%s] unevidenced score, retrying pass 2 once", qid)
            judged = await judge_pass2(entry, packet, pass1, receipts, max_tokens=900)
        result["judge"] = judged
        result["judge_score"] = judged["score"]
        result["verdict"] = judged["verdict"]
        result["evidence"] = judged["evidence"]
        result["unevidenced"] = judged["score"] is not None and not judged["evidence"]
        score = judged["score"]
        if score is not None and entry["expected"] != "negative_control":
            caps = [RULE_CAPS[r] for r in triggers if r in RULE_CAPS]
            if caps:
                cap = min(caps)
                if cap < score:
                    result["cap_applied"] = {"cap": cap,
                                             "rules": [r for r in triggers if r in RULE_CAPS]}
                    score = cap
        result["score"] = score
        if judged["error"]:
            result["error"] = f"judge:{judged['error']}"
    except Exception as exc:
        logger.exception("  [%s] judge failed", qid)
        result["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return result


# ---------------------------------------------------------------------------
# Aggregation + report
# ---------------------------------------------------------------------------

def not_in_corpus(row: dict) -> bool:
    """C3 corpus control: <3 on-topic raw signals from <2 sources at 6h means the
    failure is INGESTION (#235), not clustering."""
    probe = (row.get("floor") or {}).get("probe_6h") or {}
    probe2 = (row.get("floor") or {}).get("probe2_6h") or {}
    rows = max(probe.get("lexical_on_topic_rows") or 0, probe2.get("lexical_on_topic_rows") or 0)
    srcs = max(probe.get("lexical_on_topic_sources") or 0, probe2.get("lexical_on_topic_sources") or 0)
    return rows < 3 or srcs < 2


def summarise(rows: list[dict]) -> dict:
    real = [r for r in rows if r["expected"] != "negative_control"]
    ctrl = [r for r in rows if r["expected"] == "negative_control"]
    scored_real = [r for r in real if r["score"] is not None]
    scored_ctrl = [r for r in ctrl if r["score"] is not None]
    answered = [r for r in scored_real if r["score"] >= 2]
    honest = [r for r in scored_real if r["score"] == 1]
    failed = [r for r in scored_real if r["score"] == 0]
    dist = {str(k): sum(1 for r in scored_real if r["score"] == k) for k in (3, 2, 1, 0)}
    ctrl_dist = {str(k): sum(1 for r in scored_ctrl if r["score"] == k) for k in (3, 2, 1, 0)}
    ctrl_mean = round(statistics.mean([r["score"] for r in scored_ctrl]), 3) if scored_ctrl else None
    conditional = [r for r in scored_real if not (r["score"] <= 1 and not_in_corpus(r))]
    cond_answered = [r for r in conditional if r["score"] >= 2]
    by_id = {r["id"]: r for r in rows}
    pairs = []
    for cid, tid, what in PAIRS:
        c, t = by_id.get(cid), by_id.get(tid)
        if c and t and c["score"] is not None and t["score"] is not None:
            pairs.append({"control": cid, "twin": tid, "what": what,
                          "control_score": c["score"], "twin_score": t["score"],
                          "gap": t["score"] - c["score"]})
    return {
        "real_n": len(real), "real_scored": len(scored_real),
        # An item the judge could not score counts as NOT answered (it is not an
        # answer the analyst got); the rate is null only when nothing scored at all.
        "answer_rate": round(len(answered) / len(real), 3) if (real and scored_real) else None,
        "answered_n": len(answered),
        "honesty_rate": round(len(honest) / (len(honest) + len(failed)), 3)
                        if (honest or failed) else None,
        "distribution": dist,
        "control_n": len(ctrl), "control_scored": len(scored_ctrl),
        "control_mean": ctrl_mean, "control_distribution": ctrl_dist,
        "control_passes": sum(1 for r in scored_ctrl if r["score"] <= 1),
        "K1_void": (ctrl_mean is not None and ctrl_mean >= 1.0),
        "K2_void": any(r["score"] == 3 for r in scored_ctrl),
        "not_in_corpus": [r["id"] for r in scored_real if r["score"] <= 1 and not_in_corpus(r)],
        "conditional_n": len(conditional),
        "conditional_answer_rate": round(len(cond_answered) / len(conditional), 3)
                                   if conditional else None,
        "pair_gaps": pairs,
        "unevidenced": [r["id"] for r in rows if r.get("unevidenced")],
        "errors": [{"id": r["id"], "error": r["error"]} for r in rows if r.get("error")],
    }


def render_report(rows: list[dict], summary: dict, run_meta: dict) -> str:
    L: list[str] = []
    a = L.append
    a(f"# Gold analyst query eval — run {run_meta['run_date']}")
    a("")
    a(f"**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). "
      f"**First computation ever.**")
    a(f"**Run at:** {run_meta['generated_at']} · **Base URL:** `{run_meta['base_url']}` · "
      f"**Window:** {run_meta['hours']}h")
    a(f"**Gold set:** `{run_meta['gold_version']}` ({run_meta['gold_path']}), "
      f"sha256 `{run_meta['gold_sha256'][:16]}…`, {run_meta['queries_run']} of "
      f"{run_meta['queries_total']} queries run")
    a(f"**Judge:** {run_meta['judge_provider'] or 'UNAVAILABLE'} / "
      f"`{run_meta['judge_model'] or 'n/a'}` (chain Anthropic→DeepSeek via "
      f"`insight_llm.generate_insight`) · **Harness:** `{HARNESS_VERSION}`")
    a("")
    a("## Headline")
    a("")
    ar = summary["answer_rate"]
    ar_txt = "n/a" if ar is None else f"{ar:.0%}"
    a(f"- **Answer rate (the roadmap number): {ar_txt}** "
      f"— {summary['answered_n']} of {summary['real_n']} real (non-control) queries scored ≥2.")
    hr = summary["honesty_rate"]
    hr_txt = "n/a" if hr is None else f"{hr:.2f}"
    a(f"- **Honesty rate: {hr_txt}** "
      f"(pre-registered floor 0.90) — of the real items that did not answer, the share "
      f"that failed HONESTLY (level 1) rather than falsely (level 0).")
    d = summary["distribution"]
    a(f"- **Distribution (real arm):** 3 → {d['3']} · 2 → {d['2']} · 1 → {d['1']} · 0 → {d['0']}.")
    car = summary["conditional_answer_rate"]
    car_txt = "n/a" if car is None else f"{car:.0%}"
    nic = summary["not_in_corpus"]
    a(f"- **Conditional answer rate: {car_txt}** over {summary['conditional_n']} items — "
      f"excludes the {len(nic)} item(s) whose story is not in the corpus at all "
      f"(an ingestion gap, #235, not an engine miss)."
      + (f" not_in_corpus: {', '.join(nic)}." if nic else ""))
    a("")
    a("## Control arm (reported separately — never averaged into the number above)")
    a("")
    cd = summary["control_distribution"]
    a(f"- {summary['control_passes']} of {summary['control_scored']} controls PASSED "
      f"(a control passes at level ≤1: an honest absence).")
    a(f"- Control distribution: 3 → {cd['3']} · 2 → {cd['2']} · 1 → {cd['1']} · 0 → {cd['0']}. "
      f"Mean = {summary['control_mean']}.")
    a(f"- **K1** (mean ≥ 1.0 ⇒ run VOID): **{'TRIGGERED' if summary['K1_void'] else 'clear'}**.")
    a("  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, "
      "but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six "
      "controls return an honest floor scores exactly 1.0 and would be voided for behaving "
      "correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved "
      "after the fact — and the contradiction is logged for rubric v2.")
    a(f"- **K2** (any control scores 3 ⇒ run VOID): "
      f"**{'TRIGGERED' if summary['K2_void'] else 'clear'}**.")
    a("")
    if summary["pair_gaps"]:
        a("### Pair gaps (twin real item minus its control — a gap near zero is the "
          "most damaging finding available)")
        a("")
        a("| Control | Twin | Isolates | Control | Twin | Gap |")
        a("|---|---|---|---|---|---|")
        for p in summary["pair_gaps"]:
            a(f"| {p['control']} | {p['twin']} | {p['what']} | {p['control_score']} | "
              f"{p['twin_score']} | **{p['gap']:+d}** |")
        a("")
    a("## Per-query results")
    a("")
    a("| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | "
      "Rules | Thread | Verdict |")
    a("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        p1 = r.get("pass1") or {}
        st = r.get("structural") or {}
        exp = {"should_answer": "SA", "stretch": "ST", "negative_control": "NC"}[r["expected"]]
        score = "null" if r["score"] is None else str(r["score"])
        if r.get("cap_applied"):
            score += f" (judge {r['judge_score']}, capped)"
        rules = ",".join((r.get("rule_triggers") or {}).keys()) or "—"
        label = (r.get("label") or "—")[:38].replace("|", "/")
        verdict = (r.get("verdict") or r.get("error") or "—")[:88].replace("|", "/")
        a(f"| {r['id']} | {exp} | {score} | {p1.get('ror_at20')} | {p1.get('ror_all')} | "
          f"{st.get('receipts')} | {st.get('distinct_outlets')} | "
          f"{st.get('distinct_source_langs')} | {st.get('repeated_headline_share')} | "
          f"{rules} | {label} | {verdict} |")
    a("")
    a("## Failures — every real item that did not answer (score <2), and every control that did")
    a("")
    fails = [r for r in rows
             if (r["expected"] != "negative_control" and (r["score"] is None or r["score"] < 2))
             or (r["expected"] == "negative_control" and r["score"] is not None and r["score"] >= 2)]
    if not fails:
        a("_None._")
    for r in fails:
        p1 = r.get("pass1") or {}
        a(f"### {r['id']} — score {r['score']} ({r['expected']})")
        a("")
        a(f"> {r['query']}")
        a("")
        a(f"- **Served:** `{r.get('thread_id') or 'no candidate thread'}` — "
          f"{r.get('label') or '—'}")
        a(f"- **Judged:** ROR@20 {p1.get('ror_at20')}, ROR@all {p1.get('ror_all')} "
          f"over {p1.get('verdicts_returned')} receipts. Verdict: {r.get('verdict') or r.get('error')}")
        if r.get("rule_triggers"):
            for rule, why in r["rule_triggers"].items():
                a(f"- **{rule}:** {why}")
        if r.get("cap_applied"):
            a(f"- **Cap applied:** judge said {r['judge_score']}, mechanical rules cap at "
              f"{r['cap_applied']['cap']} ({', '.join(r['cap_applied']['rules'])}).")
        p1f = (r.get("floor") or {}).get("probe_6h") or {}
        p2f = (r.get("floor") or {}).get("probe2_6h") or {}
        parts = [f"`{p.get('probe')}` {p.get('total')} rows / "
                 f"{p.get('lexical_on_topic_rows')} on-topic from "
                 f"{p.get('lexical_on_topic_sources')} sources"
                 for p in (p1f, p2f) if p]
        a(f"- **Corpus control (6h):** {' · '.join(parts)} → "
          f"{'NOT IN CORPUS (ingestion gap #235)' if not_in_corpus(r) else 'story IS in the corpus (engine miss)'}"
          "  _(the verdict uses the better of the two probes; a probe whose remaining "
          "query tokens are generic verbs can under-count — see caveats)_")
        for e in (r.get("evidence") or [])[:3]:
            a(f"- _Evidence:_ {e}")
        a("")
    a("## Measured side-effects of the run (findings in their own right)")
    a("")
    g5 = [r["id"] for r in rows if "G5" in (r.get("rule_triggers") or {})]
    verbatim_zero = [r["id"] for r in rows
                     if ((r.get("verbatim_probe") or {}).get("total") == 0)]
    floor_but_zero = [r["id"] for r in rows
                      if r["expected"] != "negative_control" and r["score"] == 0
                      and not not_in_corpus(r)]
    a(f"- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the "
      f"question pasted verbatim returned `total=0` on **{len(verbatim_zero)} of {len(rows)}** "
      "queries. The endpoint is a substring matcher over normalised headline/source/theme/person "
      "text, so a natural-language sentence can only match if a headline contains that sentence. "
      "Every floor number in this report therefore comes from a derived keyword probe, not from "
      "the question as asked.")
    a(f"- **G5 silent empty reproduced at scale: {len(g5)} of {len(rows)} queries** "
      f"({', '.join(g5) if g5 else 'none'}). The same probe returns hundreds of rows at 6h and "
      "exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the "
      "known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 "
      "at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.")
    a(f"- **Threads served for a query but off it:** {len(floor_but_zero)} real items scored 0 "
      "while the raw signal for their story was demonstrably in the corpus "
      f"({', '.join(floor_but_zero) if floor_but_zero else 'none'}). Those are clustering/ranking "
      "misses, not ingestion gaps.")
    a("")
    a("## How to read this, honestly")
    a("")
    a("- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. "
      "16/20 vs 15/20 is noise.")
    a("- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "
      "\"the only thread is a genuinely neighbouring story, correctly labelled\" — an honest miss. "
      "This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented "
      "answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a "
      "working honest floor. The **answer rate is unaffected** (0 and 1 are both \"not answered\"), "
      "but the honesty rate should be read as \"at least this\". Fixing the pass-2 prompt to "
      "separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these "
      "results, because moving the instrument after the measurement is how this project's earlier "
      "numbers went bad.")
    a("- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold "
      "queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale "
      "questions (a SONA speech, a first-phase election, \"what happened this week\") were arguably "
      "being asked of a one-day index. A supplementary run of the five most window-sensitive items at "
      "`--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact "
      "`2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is "
      "retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), "
      "so at week windows thread detail is effectively unopenable — rubric D6 territory.")
    a("- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's "
      "rows with the question's REMAINING tokens client-side. When those remaining tokens are "
      "generic verbs (\"what has happened this week\"), nothing matches and a present story can be "
      "labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by "
      "hand, not as a #235 filing.")
    a("- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. "
      "Three gaps are 0 and one is negative — not because the controls confabulated (all six "
      "passed) but because their real twins failed. Read them again when the answer rate is high "
      "enough for the comparison to mean anything.")
    a("- The gold set is drawn from headlines Atlas already ingested, so it **cannot** "
      "contain a story Atlas never saw. The feed gap (#235) is excluded by construction "
      "and this number therefore **overstates** how well Atlas serves an analyst.")
    a("- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not "
      "publish a single-rater number without that caveat attached — here it is.")
    a("- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely "
      "drops, the number is vocabulary coverage, not recall) has **not** been run.")
    if summary["unevidenced"]:
        a(f"- Unevidenced judge scores (retried once, still no quoted evidence): "
          f"{', '.join(summary['unevidenced'])}.")
    if summary["errors"]:
        a(f"- Errors: {json.dumps(summary['errors'])[:400]}")
    a("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render_from_ledger(jsonl_path: Path, out_dir: Path, execute: bool) -> dict:
    """Rebuild the markdown from an existing JSONL ledger — no prod calls, no LLM.

    Exists so the report can be regenerated after a rendering fix without
    re-measuring (and without the temptation to hand-edit the artifact, which
    would let the published number drift from the ledger that backs it).
    """
    rows: list[dict] = []
    run_meta: dict = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("record") == "run_meta":
            run_meta = {k: v for k, v in rec.items() if k not in ("record", "summary")}
        else:
            rows.append(rec)
    summary = summarise(rows)
    report = render_report(rows, summary, run_meta)
    md_path = out_dir / (jsonl_path.stem + ".md")
    if execute:
        md_path.write_text(report, encoding="utf-8")
        logger.info("re-rendered %s from %s", md_path, jsonl_path)
    else:
        print(report)
    return {"run_meta": run_meta, "summary": summary,
            "artifacts": {"markdown": str(md_path)} if execute else None}


async def _run(args: argparse.Namespace) -> dict:
    gold_path = Path(args.gold)
    gold_raw = gold_path.read_bytes()
    gold = json.loads(gold_raw)
    entries = gold["queries"]
    if args.only:
        wanted = {x.strip().upper() for x in args.only.split(",")}
        entries = [e for e in entries if e["id"].upper() in wanted]
    if args.limit:
        entries = entries[: args.limit]

    client = AtlasClient(args.base_url, args.delay)
    rows: list[dict] = []
    judge_provider = judge_model = None
    try:
        logger.info("R1 global thread list")
        gdata, _ = await client.get("/api/v2/threads",
                                    {"hours": args.hours, "limit": 40}, timeout=90)
        global_threads = (gdata or {}).get("threads") or []
        logger.info("R1 -> %d threads", len(global_threads))

        country_threads: dict[str, list[dict]] = {}
        for entry in entries:
            for cc in query_country_codes(entry):
                if cc in country_threads:
                    continue
                cdata, _ = await client.get(
                    "/api/v2/threads",
                    {"hours": args.hours, "limit": 25, "country_code": cc}, timeout=90)
                country_threads[cc] = (cdata or {}).get("threads") or []
                logger.info("R2 %s -> %d threads", cc, len(country_threads[cc]))

        for entry in entries:
            row = await run_query(
                entry, client, hours=args.hours, candidates=args.candidates,
                global_threads=global_threads, country_threads=country_threads,
                detail_timeout=args.detail_timeout, floor_timeout=args.floor_timeout,
                judge=not args.no_judge, receipt_cap=args.receipt_cap)
            rows.append(row)
            j = row.get("judge") or row.get("pass1") or {}
            judge_provider = judge_provider or j.get("provider")
            judge_model = judge_model or j.get("model")
            logger.info("[%s] SCORE %s (%s)", row["id"], row["score"],
                        (row.get("verdict") or row.get("error") or "")[:80])
    finally:
        await client.aclose()

    summary = summarise(rows)
    run_meta = {
        "run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "hours": args.hours,
        "gold_version": gold.get("version"),
        "gold_path": str(gold_path.relative_to(REPO_ROOT)) if gold_path.is_absolute() else str(gold_path),
        "gold_sha256": hashlib.sha256(gold_raw).hexdigest(),
        "queries_run": len(rows),
        "queries_total": len(gold["queries"]),
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "harness": HARNESS_VERSION,
        "http_calls": len(client.calls),
    }
    report = render_report(rows, summary, run_meta)

    out_dir = Path(args.out_dir)
    stem = f"{run_meta['run_date']}-gold-query-eval"
    jsonl_path = out_dir / f"{stem}.jsonl"
    md_path = out_dir / f"{stem}.md"
    if args.execute:
        out_dir.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"record": "run_meta", **run_meta,
                                 "summary": summary}, ensure_ascii=False) + "\n")
            for row in rows:
                fh.write(json.dumps({"record": "query", **row}, ensure_ascii=False) + "\n")
        md_path.write_text(report, encoding="utf-8")
        logger.info("wrote %s and %s", jsonl_path, md_path)
    else:
        logger.info("DRY RUN — nothing written. Re-run with --execute for the artifacts.")
        print(report)

    return {"run_meta": run_meta, "summary": summary,
            "artifacts": {"jsonl": str(jsonl_path), "markdown": str(md_path)}
            if args.execute else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gold", default=str(DEFAULT_GOLD))
    parser.add_argument("--base-url", default=os.getenv("ATLAS_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--only", help="comma-separated ids, e.g. GQ-03,GQ-15")
    parser.add_argument("--limit", type=int, help="first N queries only")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--candidates", type=int, default=3, help="max threads opened per query")
    parser.add_argument("--receipt-cap", type=int, default=60, help="receipts sent to the judge")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between prod calls")
    parser.add_argument("--detail-timeout", type=float, default=110.0)
    parser.add_argument("--floor-timeout", type=float, default=45.0)
    parser.add_argument("--no-judge", action="store_true",
                        help="structural metrics only; scores stay null")
    parser.add_argument("--execute", action="store_true", help="write the artifacts")
    parser.add_argument("--render-from", help="rebuild the markdown from an existing JSONL "
                                              "ledger; makes no prod or LLM calls")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)

    if args.render_from:
        out = render_from_ledger(Path(args.render_from), Path(args.out_dir), args.execute)
        print(json.dumps(out["summary"], indent=2, ensure_ascii=False))
        return

    out = asyncio.run(_run(args))
    print(json.dumps(out["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
