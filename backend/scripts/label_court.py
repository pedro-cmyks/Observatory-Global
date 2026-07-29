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
        # 2026-07-29 GB2): an umbrella label names an EVENT FAMILY (aftermath,
        # tolls, rescues, responses of ONE event/story) OR a genuinely generic
        # bucket. Strict single-event entailment failed 34/36 umbrellas incl.
        # coherent ones — the right question is family membership, not
        # headline identity. Showing each CHILD's own served label alongside
        # its receipts (rather than a flat headline pool that erases which
        # receipt came from which child) gives the judge a second signal — BUT
        # GB2 (`docs/research/label-court/2026-07-29-gb2-blind-check.md`) found
        # the court was resolving label-vs-receipt conflicts the WRONG way:
        # 20% of sampled child labels were stale against their own served
        # receipts (dt-8172's children labeled "France Heat Wave Deaths" serve
        # receipts reading "300 mil evacuados" — literally the umbrella's own
        # claim), and the old prompt's "judge its LABEL first" instruction told
        # the judge to prefer the stale label. Rule 1 below inverts that. GB2
        # also confirmed the pre-registered roundup residual (rule 2) — but
        # named a DIFFERENT failure mode in the same sample (dt-8193 "Heat Wave
        # in Valencia" false-ENTAILED over Spain-wide alerts with no Valencia
        # receipt): leniency must not become blanket, so rule 3 keeps the
        # geography/subject specificity bar for labels that make a SPECIFIC
        # claim. Single-child umbrellas (GB2: 3/10 of its sample) are excluded
        # upstream in the SQL selection (main(), single_child_skip) — the
        # family question is vacuous with one child, so it never reaches here.
        children = family_children or []
        if children:
            blocks = []
            for c in children:
                child_lines = "\n".join(
                    f"      - {(r.get('headline') or '')[:160]}" for r in c.get("receipts", []))
                blocks.append(
                    f'  CHILD LABEL: "{c.get("child_label", "")}"\n'
                    f"{child_lines if child_lines else '      (no receipts)'}")
            body = "CHILD STORIES:\n" + "\n\n".join(blocks)
        else:
            body = f"HEADLINES:\n{lines}"
        return (
            "You are a strict fact-checker auditing the LABEL of a news-story "
            "FAMILY (an umbrella covering several child stories: one event's "
            "aftermath, casualty counts, rescues, responses, follow-ups — OR a "
            "genuinely generic category bucket, see rule 2) against its child "
            "stories, each shown with its OWN served label and a few receipt "
            "headlines.\n\n"
            f'FAMILY (UMBRELLA) LABEL: "{label}"\n\n{body}\n\n'
            "RULES:\n"
            "1. RECEIPTS OVER LABELS: child labels may be stale (frozen when "
            "the child was created, not refreshed as the story moved). When a "
            "child's receipts CONTRADICT its own label, judge by the "
            "RECEIPTS. The question is whether the umbrella label covers what "
            "the receipts report — not what a stale child label claims.\n"
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
            "repeat the specific detail.\n\n"
            "Do the MAJORITY of these child stories genuinely belong to the "
            "family this umbrella label names, applying the rules above? "
            "Reply ONLY with JSON:\n"
            '{"verdict": "entailed" | "partial" | "failed", "reason": "<one short sentence>"}\n'
            "- entailed: most children belong to the named family.\n"
            "- partial: the family is real but a large minority of children are unrelated.\n"
            "- failed: most children do NOT belong to the named family.")
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
              f"tokens in/out {tok_in}/{tok_out}{' · WRITTEN' if args.write else ' · DRY'}"
              f"{' · PROPOSALS APPLIED' if apply_proposals else ''}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
