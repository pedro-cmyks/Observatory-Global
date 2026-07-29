"""LABEL COURT (#204/#224, council Move 1) — catch the mislabeled thread.

For every ACTIVE dynamic topic, put its SERVED label on trial against its own
receipts (topic_members evidence headlines): a DeepSeek temp-0 entailment judge
answers "does this label accurately describe the majority of these receipts?"
-> verdict entailed | partial | failed. On `failed` (the dt-320
"17-Year-Old British Teen Fall" label sitting over Greek traffic-accident news
class) it proposes a receipt-derived NEUTRAL label.

Writes (migration 080): dynamic_topics.label_status / label_checked_at /
label_court_model / label_proposed. The proposal NEVER auto-replaces the served
label unless ATLAS_LABEL_COURT_APPLY=on (default OFF) — the court flags, humans
(or a later gate) decide. Every failure is appended to a JSONL ledger under
docs/research/label-court/ as labeler training data (#204 gold is starved).

UMBRELLA LANE (2026-07-29, identity-three-levers Lever B1): the biggest served
rows are umbrellas (migration 058, is_umbrella=true — the front-page lane
after the R2 label-fold), and they carry no verdict by construction until this
lane runs. An umbrella gets a FAMILY question instead of a headline-identity
one: for each CHILD (bounded <=10, biggest-first), show its own served label +
up to 3 decoded receipt headlines, and ask whether the majority of children
genuinely belong to the family the umbrella label names — a child's own label
is often the tell (a "Belgian shooting" child under a "Venezuela Earthquake"
umbrella) even before its receipts are read. Gated by `ATLAS_COURT_UMBRELLAS`
(default OFF): while off, the trial is `is_umbrella=false` only — today's cron
keeps judging the story lane and never touches umbrellas. Flip it on (ALW
`.env`) only after the pre-registered gate GB (>=8/10 blind hand-check
agreement on a sample of umbrella verdicts) has passed. `--only-umbrellas`
scopes an ad-hoc manual pass to umbrella rows regardless of the env gate (used
for the one-off GB input run — it does not touch the cron flag).

CONTAMINATION FIX (2026-07-29, GB blind-check `docs/research/label-court/
2026-07-29-gb-blind-check.md`): the first umbrella run's 36 verdicts were
VOID. `_RECEIPTS_SQL` had no `engine_version` or `quarantined` filter, so
`topic_members` rows from the experimental `unified-v2` construction (F3,
never cut over — rebuilt nightly, always-fresh timestamps) crowded the SERVED
`v1-compat` evidence out of the `ORDER BY max(timestamp) DESC LIMIT k`
window. The court was judging receipts users never saw — dose-response was
monotonic (failed umbrellas 85.9% non-served receipts vs 50% for partial).
Fixed: bind `engine_version` to `topic_members_engine_version()` (never a
hardcoded literal, so this can't drift from the F4 cutover var again),
exclude `quarantined` rows, and order by `tm.assigned_at` (served-evidence
freshness) instead of `s.timestamp` (immune to nightly-rebuild timestamp
churn on rows the product never serves). HYPOTHESIS for the next audit: the
blind-spot audit's "court over-strictness" finding (13/15 sampled `partial`
verdicts read fine to a human) may be the SAME contamination on the STORY
lane — this fix applies there too (`_receipts_for` is shared), worth
re-running that audit post-fix rather than assuming it was calibration only.

CALIBRATION FIX (2026-07-29, GB2 round-2 blind-check `docs/research/
label-court/2026-07-29-gb2-blind-check.md`): scored 6/10 (contamination
confirmed gone — the round-1 pathology of judging unserved evidence did not
recur). Three separable, genuine calibration gaps, NOT contamination:
(1) labels-over-receipts inversion — 20% of sampled child labels were stale
against their own served receipts, and the OLD prompt's "judge its LABEL
first" line told the judge to trust the stale label over the receipts that
contradicted it (dt-8172's children labeled "France Heat Wave Deaths" serve
receipts reading "300 mil evacuados" — literally the umbrella's own claim).
(2) the pre-registered roundup residual, confirmed once more (a generic
"global heatwaves" label over Italy+UK+Russia regional heatwaves was failed
for not being literally global). (3) single-child umbrellas (3/10 of GB2's
sample) make the family question vacuous. GB2 ALSO named the caution that
must bound any fix: the residual is NOT monotone strictness — dt-8193 "Heat
Wave in Valencia" was false-ENTAILED over Spain-wide alerts with no Valencia
receipt, so a blanket-lenience fix would trade one error for another. Fixed:
the family prompt now states RULES 1-3 explicitly (receipts-over-labels;
generic buckets honestly covering generic families are entailed; but a
SPECIFIC label — place/actor/figure/count/concrete-action — still needs a
receipt that supports that specific claim, not just an adjacent or broader
family) and `_SINGLE_CHILD_SKIP_SQL` excludes one-child umbrellas from the
family trial entirely (falls through to the story lane's judgment instead).

Serving reads label_status only (additive). Reversible: NULL the four columns.

Run (repo root, M1 env, off-peak — DeepSeek, ~cents):
  python -m backend.scripts.label_court --dry-run --limit 20   # inspect
  python -m backend.scripts.label_court --write                # all active
  ATLAS_COURT_UMBRELLAS=on python -m backend.scripts.label_court \
      --write --only-umbrellas                                 # GB input run
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

# `app.*` lives under backend/ — this script is invoked both as
# `backend.scripts.label_court` (repo root, cwd for the ALW runner) and as
# `scripts.label_court` (backend/ as pytest rootdir, `app` already on
# sys.path via pythonpath=.). The explicit insert makes the first case work
# without relying on cwd; harmless / idempotent in the second. Same pattern
# as scripts/measure_court_enforcement.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.thread_intelligence import topic_members_engine_version  # noqa: E402

_DS_URL = "https://api.deepseek.com/chat/completions"
_COURT_MODEL = "label-court-v0/deepseek-chat"
_LEDGER_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "label-court"

_VALID = ("entailed", "partial", "failed")

# Receipts for a topic's trial: distinct evidence headlines, SERVED-freshest
# first. Scoped to the engine_version the product actually serves ($3, bound
# to topic_members_engine_version() — never a hardcoded literal, see the
# module docstring's 2026-07-29 contamination note) and excludes quarantined
# members (migration 087 / audit_topic_blackholes.py — off-centroid, already
# hidden from users). Ordered by tm.assigned_at (when THIS engine_version
# attached the member) rather than s.timestamp (the signal's own timestamp,
# which a nightly-rebuilt experimental lane can refresh independently of
# whether it's served) — assigned_at is immune to that churn.
_RECEIPTS_SQL = """
    SELECT s.headline, s.country_code
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1 AND tm.role = 'evidence'
      AND tm.engine_version = $3
      AND COALESCE(tm.quarantined, false) = false
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code
    ORDER BY max(tm.assigned_at) DESC
    LIMIT $2
"""
# Fallback for topics whose typed membership has not been projected yet
# (topic_members is behind): the emergent sample the snapshot always carries.
# NOT a topic_members query (dynamic_topic_members/emergent_clusters instead)
# — no engine_version or quarantined column exists on this path, so the
# 2026-07-29 contamination fix does not apply here. If this fallback is ever
# repointed at topic_members, it must gain the same two filters.
_RECEIPTS_FALLBACK_SQL = """
    SELECT s.headline, s.country_code
    FROM dynamic_topic_members dtm
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])) AS sid
    JOIN signals_v2 s ON s.id = sid
    WHERE dtm.dynamic_topic_id = $1
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code
    ORDER BY max(s.timestamp) DESC
    LIMIT $2
"""


def parse_verdict(text: str) -> tuple[str, str]:
    """Judge output -> (verdict, reason). Tolerant: accepts bare word or JSON.

    Unknown / unparseable defaults to 'partial' (never silently 'entailed' —
    an unreadable judgment must not clear a label)."""
    raw = (text or "").strip()
    verdict = ""
    reason = ""
    # Try JSON first ({"verdict": "...", "reason": "..."}), tolerating fences.
    body = raw
    if body.startswith("```"):
        body = body.strip("`")
        body = body[body.find("{"):] if "{" in body else body
    try:
        obj = json.loads(body)
        if isinstance(obj, dict):
            verdict = str(obj.get("verdict", "")).strip().lower()
            reason = str(obj.get("reason", "")).strip()
    except (json.JSONDecodeError, ValueError):
        pass
    if verdict not in _VALID:
        low = raw.lower()
        # bare-word / embedded verdict
        for v in _VALID:
            if v in low:
                verdict = v
                break
    if verdict not in _VALID:
        return "partial", raw[:200]
    return verdict, (reason or raw[:200])


# GB3 quote-gate (2026-07-29, docs/research/label-court/
# 2026-07-29-gb3-blind-check.md): mirrors the AI-read quote-gate pattern
# (article_read.py — every claim must carry a verbatim quote from the fetched
# text, validated as a substring at parse; quoteless claims are DROPPED).
# Applied here to the umbrella family lane: GB3 caught the court fabricating
# an absence ("none mention a Michigan visit" — a receipt literally reads
# "Trump defends his tariffs during Michigan visit") and citing CHILD LABELS
# as if they were evidence. Forcing the reason to ground itself in a verbatim
# receipt excerpt, and mechanically checking that grounding, makes both
# failure modes self-detecting instead of silently shipping a stamp.
#
# TWO quote styles are accepted, not just the double-quote the prompt asks
# for: DeepSeek frequently reaches for single quotes around a receipt excerpt
# (observed live, dt-8130/8093/etc.) — very likely to dodge escaping a
# receipt that itself contains double quotes inside a JSON string value. That
# is reasonable model behaviour, not a defect, so the parser accommodates it.
# Single-quote spans need lookaround, not just a length floor: a straight/
# curly apostrophe (contractions, possessives — "Trump's", "world's") is
# lexically identical to a single quote mark, and a NAIVE ['‘](.{20,}?)['’]
# pattern was observed live mis-pairing an incidental possessive apostrophe
# (e.g. "…stories' receipts report that…") as the OPENING quote, capturing
# the wrong span entirely and missing the real quoted excerpt that followed.
# Real opening quotes are preceded by non-word chars (space/punctuation) and
# followed immediately by non-space; real closing quotes are preceded by
# non-space and NOT followed by a word char (a possessive apostrophe always
# IS). Once that lookaround disambiguates opening/closing from apostrophes,
# the same 6-char floor as the double-quote pattern is safe — a plain length
# floor was the wrong tool (it rejected genuine short quotes like 'Typhoon
# Noul', observed live on dt-8105, while a NAIVE unguarded apostrophe pairing
# is what needed the real fix). The REAL safety net either way is the
# containment check below, not the regex: a spurious capture that isn't an
# actual receipt substring simply returns False.
_DOUBLE_QUOTE_PATTERN = re.compile(r'["“]([^"“”]{6,}?)["”]')
_SINGLE_QUOTE_PATTERN = re.compile(r"(?<!\w)['‘](?=\S)([^'‘’]{6,}?)(?<=\S)['’](?!\w)")


def _normalize_for_quote_match(text: str) -> str:
    """Collapse whitespace + casefold so a model's lightly-retyped quote
    (extra space, different case) still matches the receipt it cites. Also
    strips leading/trailing punctuation — observed live: the model closes a
    quote with a trailing period INSIDE the quote marks ('…de París.') that
    the receipt itself doesn't carry ('…de París'), which is a formatting
    habit (American quote-punctuation convention), not a fabricated quote;
    without stripping it the containment check below fails on an otherwise
    exact excerpt."""
    t = re.sub(r"\s+", " ", (text or "")).strip().casefold()
    return t.strip(".,;:!?\"'“”‘’")


def _reason_quotes_a_receipt(reason: str, receipts: list[dict]) -> bool:
    """True iff `reason` contains a quoted substring (double OR single
    quotes, straight or curly — see the length-floor rationale above) that
    actually appears in at least one receipt headline. False means the
    verdict is UNGROUNDED — the reason cites nothing checkable (a label
    paraphrase, an unquoted assertion, or a fabricated quote) and the caller
    must withhold the verdict (never write label_status) rather than trust
    it."""
    reason = reason or ""
    quotes = _DOUBLE_QUOTE_PATTERN.findall(reason) + _SINGLE_QUOTE_PATTERN.findall(reason)
    if not quotes:
        return False
    haystacks = [_normalize_for_quote_match(r.get("headline") or "") for r in receipts]
    for q in quotes:
        needle = _normalize_for_quote_match(q)
        if len(needle) < 6:
            continue
        if any(needle in h for h in haystacks if h):
            return True
    return False


def _dominant_geo(country_codes: list[str]) -> str:
    codes = [c for c in country_codes if c and c.upper() != "XX"]
    if not codes:
        return "Global"
    return Counter(codes).most_common(1)[0][0]


# cross-language stopwords (EN/ES/IT/PT/FR/DE + common CJK/Greek/Cyrillic glue)
_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "after", "over", "into",
    "amid", "says", "said", "new", "not", "but", "has", "have", "will", "was",
    "are", "per", "para", "con", "una", "che", "del", "della", "der", "die",
    "und", "les", "des", "pour", "dans", "sur", "για", "και", "στο", "στη",
    "στην", "της", "του", "the", "news", "video", "live", "watch", "update",
}
# a usable token: ≥4 letters (any script), NOT a bare number/date, NOT a
# lingering entity-escape fragment (x3c4…) after html.unescape can't resolve it.
_ESCAPE_FRAG = re.compile(r"^x[0-9a-f]{2,4}$", re.I)


def build_neutral_label(receipts: list[dict]) -> str:
    """Receipt-derived neutral label: '<dominant-geo>: <subject> — from N receipts'.

    Subject = the most frequent salient token across headlines (a cheap, honest
    stand-in until a real receipt-summarizer runs); geo = the modal country
    code. Never asserts a narrative the receipts don't support. Headlines are
    HTML-entity-decoded first (the same &#xNNNN; soup the frontend decodes —
    without it the tokens come out as 'x3c4x3bf' escape fragments)."""
    n = len(receipts)
    geo = _dominant_geo([r.get("country_code") or "" for r in receipts])
    toks: Counter = Counter()
    for r in receipts:
        text = html.unescape(r.get("headline") or "")
        for w in text.split():
            wl = "".join(ch for ch in w if ch.isalnum())
            if len(wl) < 4:
                continue
            if wl.isdigit() or _ESCAPE_FRAG.match(wl):
                continue
            if wl.lower() in _STOP:
                continue
            toks[wl] += 1
    subject = ", ".join(w for w, _ in toks.most_common(3)) if toks else "mixed reports"
    return f"{geo}: {subject} — from {n} receipts"


def _judge_prompt(label: str, receipts: list[dict], *, family: bool = False,
                  family_children: list[dict] | None = None) -> str:
    lines = "\n".join(f"- {(r.get('headline') or '')[:160]}" for r in receipts)
    if family:
        # Umbrella bar (2026-07-18, sharpened 2026-07-29 Lever B1, recalibrated
        # 2026-07-29 GB2, GB3): an umbrella label names an EVENT FAMILY
        # (aftermath, tolls, rescues, responses of ONE event/story) OR a
        # genuinely generic bucket. Strict single-event entailment failed
        # 34/36 umbrellas incl. coherent ones — the right question is family
        # membership, not headline identity.
        #
        # GB2 (docs/research/label-court/2026-07-29-gb2-blind-check.md, 6/10):
        # the court read stale CHILD LABELS over receipts (dt-8172's children
        # labeled "France Heat Wave Deaths" serve receipts reading "300 mil
        # evacuados" — literally the umbrella's own claim) and stamped
        # single-child "families" where the question is vacuous. Fixed with
        # rules 1-3 below + _SINGLE_CHILD_SKIP_SQL (main()).
        #
        # GB3 (docs/research/label-court/2026-07-29-gb3-blind-check.md, 7/10,
        # ONE remaining mechanism, ZERO false-entailments): rule 1 said
        # "receipts over labels" but the block still LED with `CHILD LABEL:
        # "…"` — the most salient token the judge sees per child — so the
        # judge kept dismissing children BY THEIR LABEL (dt-3433's child `383`
        # "Romania Demands Drone Reprogramming" serves "Russians hit a foreign
        # vessel with a drone in the Black Sea" — the label's own SHIPS
        # clause, verbatim — counted AGAINST the label; dt-8111's court reason
        # asserted "none mention a Michigan visit" while child `3996`
        # literally serves "Trump defends his tariffs during Michigan visit"
        # — a fabricated absence). Two structural fixes: (a) demote the
        # label — receipts now print FIRST in each child block, the label
        # prints AFTER, marked "may be stale"; (b) the reason must QUOTE a
        # receipt verbatim (see `_reason_quotes_a_receipt` below) — a reason
        # that only cites labels, or asserts an absence a receipt contradicts,
        # is now mechanically detectable and the verdict is withheld (never
        # stamped) rather than trusted. GB3 also measured 0/33 partial — the
        # scale had collapsed to binary because nothing steered the judge
        # toward it; rule 4 gives `partial` an explicit trigger for compound
        # labels (dt-8168 "Wildfires…Japan": 6/7 children verbatim-support the
        # wildfire clause, but "Quake Hits Japan" has no receipt anywhere).
        children = family_children or []
        if children:
            blocks = []
            for c in children:
                child_lines = "\n".join(
                    f"      - {(r.get('headline') or '')[:160]}" for r in c.get("receipts", []))
                blocks.append(
                    f"  RECEIPTS:\n"
                    f"{child_lines if child_lines else '      (no receipts)'}\n"
                    f'  (label, may be stale — do not treat as evidence): '
                    f'"{c.get("child_label", "")}"')
            body = "CHILD STORIES:\n" + "\n\n".join(blocks)
        else:
            body = f"HEADLINES:\n{lines}"
        return (
            "You are a strict fact-checker auditing the LABEL of a news-story "
            "FAMILY (an umbrella covering several child stories: one event's "
            "aftermath, casualty counts, rescues, responses, follow-ups — OR a "
            "genuinely generic category bucket, see rule 2) against its child "
            "stories. Each child is shown RECEIPTS FIRST, then its own served "
            "label (which may be stale — judge by the receipts).\n\n"
            f'FAMILY (UMBRELLA) LABEL: "{label}"\n\n{body}\n\n'
            "RULES:\n"
            "1. RECEIPTS OVER LABELS: a child's label is shown LAST and may be "
            "stale (frozen when the child was created, not refreshed as the "
            "story moved). Read each child's RECEIPTS first. When a child's "
            "receipts CONTRADICT its own label, judge by the RECEIPTS, never "
            "by the label. The question is whether the umbrella label covers "
            "what the receipts report — not what a stale child label claims — "
            "and a child is NOT disqualified just because its label sounds "
            "off-topic if its receipts are on-topic.\n"
            "2. GENERIC BUCKETS ARE HONEST: a generic label honestly covering "
            "a generic family counts as entailed — 'Daily Earthquake Updates' "
            "over several distinct earthquakes IS honest, and regional "
            "instances under a broader regional label are covered "
            "('European heatwaves' covers Italy and UK heatwaves). Do not "
            "fail a roundup label merely for containing more than one "
            "instance of the thing it announces.\n"
            "3. SPECIFIC LABELS STILL NEED A MATCHING RECEIPT: rule 2 never "
            "relaxes specificity. If the label names a SPECIFIC place, actor, "
            "figure, casualty count, or concrete action (a city, a named "
            "person, a death toll, a blockade), AT LEAST ONE receipt SOMEWHERE "
            "in the family must actually support THAT specific claim — a "
            "family that is merely adjacent, broader, or a plausible-sounding "
            "generalization of it, with NO receipt anywhere naming the "
            "specific detail, is not enough. This is a check on the WHOLE "
            "family, not a per-child requirement: once one receipt supports "
            "the specific claim, another child still belongs if it covers the "
            "SAME broader event, even if that child's own receipts don't "
            "repeat the specific detail.\n"
            "4. COMPOUND LABELS GET PARTIAL, NOT FAILED: if the label makes "
            "TWO OR MORE separate claims (e.g. 'X and Y', 'X; Z hits W') and "
            "the majority of children strongly support ONE of those claims "
            "while another claim has no supporting receipt anywhere, the "
            "verdict is PARTIAL — the dominant, well-receipted clause earns "
            "that much even though the secondary clause is unsupported. Only "
            "call FAILED when the majority of children support NONE of the "
            "label's claims.\n\n"
            "Do the MAJORITY of these child stories genuinely belong to the "
            "family this umbrella label names, applying the rules above? "
            "Your REASON MUST ground whatever it claims IS supported with at "
            "least one short VERBATIM quoted excerpt, copied EXACTLY, from "
            "one of the RECEIPTS above — never from a child label, never a "
            "paraphrase. This applies even when you also note something that "
            "is UNSUPPORTED (e.g. a compound label's secondary clause, rule "
            "4): quoting the label's own unsupported clause to name the gap "
            "is fine, but it does NOT by itself ground the verdict — you "
            "must ALSO quote a receipt for whatever part you say IS "
            "supported. Never write an unquoted assertion that nothing "
            "supports a claim if a receipt above contradicts it — quote that "
            "receipt instead. "
            "Reply ONLY with JSON:\n"
            '{"verdict": "entailed" | "partial" | "failed", '
            '"reason": "<one short sentence with a verbatim quoted receipt excerpt>"}\n'
            "- entailed: most children belong to the named family.\n"
            "- partial: the family is real but a large minority of children are unrelated, OR the "
            "label is compound and only its dominant clause is receipted (rule 4).\n"
            "- failed: most children do NOT belong to the named family (or, for a compound label, "
            "NONE of its claims are supported).")
    return (
        "You are a strict fact-checker auditing a news-cluster LABEL against the "
        "actual headlines assigned to it.\n\n"
        f'LABEL: "{label}"\n\nHEADLINES:\n{lines}\n\n'
        "Does the LABEL accurately describe the MAJORITY of these headlines? "
        "Judge on subject and geography, not vibe. Reply ONLY with JSON:\n"
        '{"verdict": "entailed" | "partial" | "failed", "reason": "<one short sentence>"}\n'
        "- entailed: the label fits most headlines.\n"
        "- partial: the label fits some but a large minority are off-topic.\n"
        "- failed: the label does NOT describe most headlines (wrong subject or "
        "wrong country).")


async def _ds_judge(label: str, receipts: list[dict], key: str, *,
                    family: bool = False,
                    family_children: list[dict] | None = None) -> tuple[str, str, dict]:
    import httpx
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user",
                          "content": _judge_prompt(label, receipts, family=family,
                                                   family_children=family_children)}]}
    async with httpx.AsyncClient() as c:
        r = await c.post(_DS_URL, json=body,
                         headers={"Authorization": f"Bearer {key}"}, timeout=40.0)
        r.raise_for_status()
        payload = r.json()
    ans = payload["choices"][0]["message"]["content"]
    verdict, reason = parse_verdict(ans)
    u = payload.get("usage") or {}
    usage = {"input_tokens": u.get("prompt_tokens", 0) or 0,
             "output_tokens": u.get("completion_tokens", 0) or 0}
    return verdict, reason, usage


async def _receipts_for(conn, topic_id: str, dyn_id: int, k: int) -> list[dict]:
    # Bound, not hardcoded (2026-07-29 contamination fix) — follows the same
    # F4 cutover var thread_intelligence.py's serving reads follow, so the
    # court can never again drift onto an engine_version the product doesn't
    # serve.
    engine_version = topic_members_engine_version()
    rows = await conn.fetch(_RECEIPTS_SQL, topic_id, k, engine_version)
    if not rows:
        rows = await conn.fetch(_RECEIPTS_FALLBACK_SQL, dyn_id, k)
    # DECODE before the judge reads (2026-07-18): headlines arrive
    # HTML-entity-encoded (&#x395;… soup) — an undecoded Greek/Russian receipt
    # is unreadable to the judge, so non-Latin topics were failing for
    # ILLEGIBILITY, not label truth. The neutral-label builder already
    # decoded; the judge must see the same text.
    return [{"headline": html.unescape(r["headline"] or ""),
             "country_code": r["country_code"]} for r in rows]


# Umbrellas have no direct members — their receipts are the union of their
# CHILDREN's (2026-07-18: the label-fold moved the served front page to
# umbrella rows, so a court that skips umbrellas never touches what users
# actually see; the damp was a no-op on the list that matters).
_CHILD_IDS_SQL = "SELECT id FROM dynamic_topics WHERE parent_id = $1 AND state='active'"


async def _umbrella_receipts_for(conn, umbrella_id: int, k: int) -> list[dict]:
    # NOTE: kept for relabel_court_failed.py (imports this by name) — the flat,
    # un-labeled receipt pool it uses to regenerate a neutral label. The court's
    # own family TRIAL uses the richer _umbrella_family_for below.
    child_rows = await conn.fetch(_CHILD_IDS_SQL, umbrella_id)
    out: list[dict] = []
    seen: set[str] = set()
    # Spread the receipt budget across children so one big child can't be the
    # whole trial — an umbrella label must describe the FAMILY.
    per_child = max(2, k // max(1, len(child_rows)))
    for cr in child_rows:
        cid = int(cr["id"])
        for r in await _receipts_for(conn, f"dynamic-topic-{cid}", cid, per_child):
            key = (r["headline"] or "")[:80]
            if key and key not in seen:
                seen.add(key)
                out.append(r)
        if len(out) >= k:
            break
    return out[:k]


# Lever B1 (2026-07-29): the family TRIAL wants each child's own LABEL next to
# its receipts, bounded so the prompt stays cheap — biggest children first (a
# 40-child umbrella showing all of them would swamp the prompt and the budget).
_UMBRELLA_MAX_CHILDREN = 10
_UMBRELLA_RECEIPTS_PER_CHILD = 3

_CHILD_LABELS_RANKED_SQL = """
    SELECT id, label FROM dynamic_topics
    WHERE parent_id = $1 AND state = 'active' AND label IS NOT NULL
    ORDER BY agg_n_signals DESC NULLS LAST
    LIMIT $2
"""


async def _umbrella_family_for(conn, umbrella_id: int,
                               per_child: int = _UMBRELLA_RECEIPTS_PER_CHILD,
                               max_children: int = _UMBRELLA_MAX_CHILDREN) -> list[dict]:
    """Family fixture for the umbrella court question: per CHILD (bounded to
    `max_children`, biggest-first), its own served label + up to `per_child`
    decoded receipt headlines. Keeping receipts grouped under the child that
    carries them — instead of the flat pool `_umbrella_receipts_for` builds —
    lets the judge see a child whose LABEL ALONE reveals it does not belong
    (e.g. a "Belgian shooting" child under a "Venezuela Earthquake" umbrella),
    not just headlines stripped of which child served them."""
    child_rows = await conn.fetch(_CHILD_LABELS_RANKED_SQL, umbrella_id, max_children)
    family: list[dict] = []
    for cr in child_rows:
        cid = int(cr["id"])
        receipts = await _receipts_for(conn, f"dynamic-topic-{cid}", cid, per_child)
        family.append({"child_id": cid, "child_label": cr["label"] or "", "receipts": receipts})
    return family


def _flatten_family_receipts(family: list[dict]) -> list[dict]:
    """Union of every child's receipts, deduped by headline prefix — the flat
    list the neutral-label proposal and the failure ledger both expect."""
    out: list[dict] = []
    seen: set[str] = set()
    for child in family:
        for r in child.get("receipts", []):
            key = (r.get("headline") or "")[:80]
            if key and key not in seen:
                seen.add(key)
                out.append(r)
    return out


def _umbrella_clause(*, only_umbrellas: bool, umbrellas_enabled: bool) -> str:
    """SQL WHERE-fragment deciding whether umbrella rows enter the trial.

    Priority: --only-umbrellas (explicit, ad-hoc — e.g. the GB hand-check
    input run) beats the env gate. Otherwise ATLAS_COURT_UMBRELLAS decides:
    off (default) = umbrellas excluded, the story lane runs exactly as before
    Lever B1; on = both lanes (story + umbrella family) are tried."""
    if only_umbrellas:
        return "AND is_umbrella = true "
    if umbrellas_enabled:
        return ""
    return "AND is_umbrella = false "


# GB2 (2026-07-29, docs/research/label-court/2026-07-29-gb2-blind-check.md):
# the family question — "do the children belong to the family the label
# names?" — is VACUOUS for an umbrella with exactly one active child (3/10 of
# GB2's blind sample); there is nothing for the family to disagree with, yet
# the court still stamped a verdict on all three. Correlated subquery counts
# active, labeled children of each candidate row (the bare "dynamic_topics"
# table name is usable as its own range-variable from inside the aliased "c"
# subquery — no outer alias needed); a single-child umbrella is EXCLUDED from
# this trial entirely (label_status stays whatever it was, typically NULL) —
# it falls through to the STORY lane's judgment of its lone child instead of
# being tried as a family of one. No-op for non-umbrella rows (short-circuits
# on `is_umbrella = false`).
_SINGLE_CHILD_SKIP_SQL = (
    "AND (is_umbrella = false OR (SELECT count(*) FROM dynamic_topics c "
    "WHERE c.parent_id = dynamic_topics.id AND c.state = 'active' "
    "AND c.label IS NOT NULL) >= 2) "
)

# Invariant companion to the skip above: a row judged BEFORE this fix shipped
# (or one whose children later merged/retired down to one) can carry a STALE
# family-lane verdict that this trial will now never touch again (GB2's
# dt-8193 "Heat Wave in Valencia" — false-ENTAILED under the old prompt,
# excluded from re-judgment by the skip, and left standing unless swept).
# "Single-child umbrellas keep NULL" must be an invariant, not an accident of
# when the skip landed — clear the stamp so a wrong stale verdict never
# outlives the fix that was supposed to remove it. Idempotent; no-op once
# clean.
_SINGLE_CHILD_CLEANUP_SQL = (
    "UPDATE dynamic_topics SET label_status=NULL, label_checked_at=NULL, "
    "label_court_model=NULL, label_proposed=NULL "
    "WHERE state='active' AND is_umbrella = true AND label_status IS NOT NULL "
    "AND (SELECT count(*) FROM dynamic_topics c WHERE c.parent_id = dynamic_topics.id "
    "AND c.state = 'active' AND c.label IS NOT NULL) < 2"
)

# GB3 quote-gate write path (2026-07-29): "mark the verdict unchecked" means
# an ACTIVE reset, not merely skipping the write — otherwise a row that
# already carries a STALE stamp from an earlier (less-scrutinized) pass keeps
# displaying that old verdict forever, which is exactly the "front page
# stamped on an ungrounded reason" outcome the gate exists to prevent. Same
# four columns as the ordinary write, same reversibility.
_WITHHOLD_CLEAR_SQL = (
    "UPDATE dynamic_topics SET label_status=NULL, label_checked_at=NULL, "
    "label_court_model=NULL, label_proposed=NULL WHERE id=$1"
)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Label Court: try each active topic's label vs its receipts.")
    ap.add_argument("--limit", type=int, default=0, help="only the top-N served topics (0=all active)")
    ap.add_argument("--receipts", type=int, default=8, help="headlines per trial")
    ap.add_argument("--write", action="store_true", help="write verdicts to dynamic_topics")
    ap.add_argument("--dry-run", action="store_true", help="judge + print, no write (default if --write absent)")
    ap.add_argument("--only-unchecked", action="store_true",
                    help="incremental: only topics with label_status IS NULL")
    ap.add_argument("--only-umbrellas", action="store_true",
                    help="scope the trial to umbrella (family) rows only, regardless of "
                         "ATLAS_COURT_UMBRELLAS — for ad-hoc manual passes (e.g. the GB "
                         "hand-check input run); never touches the cron gate")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("DEEPSEEK_API_KEY required", file=sys.stderr); sys.exit(2)
    apply_proposals = os.environ.get("ATLAS_LABEL_COURT_APPLY", "off").lower() == "on"
    # Lever B1 kill-switch (2026-07-29, default OFF): while off, umbrellas are
    # excluded from the trial entirely — the story lane keeps riding the cron
    # unaffected. Flip on only after gate GB (>=8/10 blind hand-check
    # agreement) passes. --only-umbrellas bypasses this for a scoped manual
    # run without touching the switch itself.
    umbrellas_enabled = os.environ.get("ATLAS_COURT_UMBRELLAS", "off").lower() == "on"

    conn = await asyncpg.connect(db)
    checked_at = datetime.now(timezone.utc)
    try:
        limit = args.limit or 1_000_000
        unchecked = "AND label_status IS NULL " if args.only_unchecked else ""
        umbrella_clause = _umbrella_clause(only_umbrellas=args.only_umbrellas,
                                           umbrellas_enabled=umbrellas_enabled)
        print(f"umbrella lane: {'ON (only-umbrellas)' if args.only_umbrellas else ('ON' if umbrellas_enabled else 'off')}")
        #
        # Ordering (2026-07-20, council R2 N2): the INCREMENTAL pass judges
        # NEWEST-PROMOTED first (id DESC). The 30-min cadence exists so a topic
        # that promotes and serves gets its stamp within one cycle — ordering a
        # bounded pass by lifetime agg_n_signals would stamp the old backlog
        # (~800 legacy actives) before today's served leads, leaving the fold
        # unstamped for hours. Full (non-incremental) runs keep biggest-first.
        order = "id DESC" if args.only_unchecked else "agg_n_signals DESC"
        rows = await conn.fetch(
            "SELECT id, label, is_umbrella FROM dynamic_topics "
            "WHERE state='active' AND label IS NOT NULL "
            f"{unchecked}"
            f"{umbrella_clause}"
            f"{_SINGLE_CHILD_SKIP_SQL}"
            f"ORDER BY {order} LIMIT $1", limit)
        if not rows:
            print("no active topics to try"); return

        dist: Counter = Counter()
        tok_in = tok_out = 0
        failures = []
        ungrounded = 0
        for r in rows:
            dyn_id = r["id"]
            topic_id = f"dynamic-topic-{dyn_id}"
            label = r["label"]
            is_umbrella = bool(r["is_umbrella"])
            family_children: list[dict] | None = None
            if is_umbrella:
                family_children = await _umbrella_family_for(conn, dyn_id)
                receipts = _flatten_family_receipts(family_children)
            else:
                receipts = await _receipts_for(conn, topic_id, dyn_id, args.receipts)
            if len(receipts) < 2:
                print(f"  dt-{dyn_id}: SKIP (only {len(receipts)} receipts) — {label[:50]}")
                continue
            verdict, reason, usage = await _ds_judge(label, receipts, key,
                                                     family=is_umbrella,
                                                     family_children=family_children)
            tok_in += usage["input_tokens"]; tok_out += usage["output_tokens"]

            # GB3 quote-gate (2026-07-29): a family verdict whose reason is
            # not grounded in a verbatim receipt quote is WITHHELD — not
            # counted, not ledgered as a failure, and label_status is never
            # written (stays whatever it already was, i.e. "unchecked"/NULL
            # if this is the first pass). This is the umbrella lane's own
            # defect-detector: GB3 caught reasons that cited child labels or
            # fabricated an absence a receipt contradicted, and both are
            # mechanically undetectable without this check.
            if is_umbrella and not _reason_quotes_a_receipt(reason, receipts):
                ungrounded += 1
                print(f"  ? dt-{dyn_id} [umbrella] [UNGROUNDED verdict={verdict}, withheld] "
                      f"{label[:40]} — reason lacked a verbatim receipt quote: {reason[:80]!r}")
                if args.write:
                    # Active reset (not a skip): a stale stamp from an
                    # earlier pass must not keep showing once THIS pass finds
                    # it ungrounded — "unchecked" has to mean unchecked.
                    await conn.execute(_WITHHOLD_CLEAR_SQL, dyn_id)
                continue

            dist[verdict] += 1
            proposed = build_neutral_label(receipts) if verdict == "failed" else None
            mark = {"entailed": "✓", "partial": "~", "failed": "✗"}[verdict]
            tag = " [umbrella]" if is_umbrella else ""
            extra = f"  ->PROPOSE: {proposed}" if proposed else ""
            print(f"  {mark} dt-{dyn_id}{tag} [{verdict}] {label[:46]}{extra}")
            if verdict == "failed":
                failures.append({
                    "topic_id": topic_id, "served_label": label,
                    "verdict": verdict, "reason": reason, "proposed": proposed,
                    "receipts": [x["headline"] for x in receipts],
                    "checked_at": checked_at.isoformat(),
                    "lane": "umbrella" if is_umbrella else "story",
                    **({"family": [{"child_id": c["child_id"], "child_label": c["child_label"]}
                                   for c in family_children]} if family_children else {}),
                })
            if args.write:
                new_label = label
                if proposed and apply_proposals:
                    new_label = proposed
                await conn.execute(
                    "UPDATE dynamic_topics SET label_status=$2, label_checked_at=$3, "
                    "label_court_model=$4, label_proposed=$5, label=$6 WHERE id=$1",
                    dyn_id, verdict, checked_at, _COURT_MODEL, proposed, new_label)

        # Sweep stale single-child verdicts (see _SINGLE_CHILD_CLEANUP_SQL) —
        # only meaningful when umbrellas are in scope at all, and only on a
        # write pass (a dry-run must not mutate the DB).
        if args.write and (args.only_umbrellas or umbrellas_enabled):
            cleared = await conn.execute(_SINGLE_CHILD_CLEANUP_SQL)
            print(f"single-child cleanup: {cleared}")

        # ledger: failures are #204 training data
        if failures:
            _LEDGER_DIR.mkdir(parents=True, exist_ok=True)
            led = _LEDGER_DIR / f"{checked_at.date().isoformat()}-label-court-failures.jsonl"
            with led.open("a", encoding="utf-8") as f:
                for x in failures:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
            print(f"\nledger += {len(failures)} failures -> {led}")

        total = sum(dist.values())
        print(f"\nLABEL COURT DONE: {total} tried · "
              f"entailed {dist['entailed']} · partial {dist['partial']} · failed {dist['failed']} · "
              f"ungrounded/withheld {ungrounded} · "
              f"tokens in/out {tok_in}/{tok_out}{' · WRITTEN' if args.write else ' · DRY'}"
              f"{' · PROPOSALS APPLIED' if apply_proposals else ''}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
