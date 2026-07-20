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

Serving reads label_status only (additive). Reversible: NULL the four columns.

Run (repo root, M1 env, off-peak — DeepSeek, ~cents):
  python -m backend.scripts.label_court --dry-run --limit 20   # inspect
  python -m backend.scripts.label_court --write                # all active
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

_DS_URL = "https://api.deepseek.com/chat/completions"
_COURT_MODEL = "label-court-v0/deepseek-chat"
_LEDGER_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "label-court"

_VALID = ("entailed", "partial", "failed")

# Receipts for a topic's trial: distinct evidence headlines, freshest first.
_RECEIPTS_SQL = """
    SELECT s.headline, s.country_code
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1 AND tm.role = 'evidence'
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code
    ORDER BY max(s.timestamp) DESC
    LIMIT $2
"""
# Fallback for topics whose typed membership has not been projected yet
# (topic_members is behind): the emergent sample the snapshot always carries.
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


def _judge_prompt(label: str, receipts: list[dict], *, family: bool = False) -> str:
    lines = "\n".join(f"- {(r.get('headline') or '')[:160]}" for r in receipts)
    if family:
        # Umbrella bar (2026-07-18): an umbrella label names an EVENT FAMILY
        # (aftermath, tolls, rescues, responses of ONE event/story). Strict
        # single-event entailment failed 34/36 umbrellas incl. coherent ones —
        # the right question is family membership, not headline identity.
        return (
            "You are a strict fact-checker auditing the LABEL of a news-story "
            "FAMILY (one event/story with its aftermath, casualty counts, "
            "rescues, responses, follow-ups) against headlines drawn from "
            "across the family.\n\n"
            f'FAMILY LABEL: "{label}"\n\nHEADLINES:\n{lines}\n\n'
            "Do the MAJORITY of these headlines belong to the single event/"
            "story family this label names? Follow-ups and different angles of "
            "the SAME event count as belonging. Unrelated events or wrong "
            "geography do not. Reply ONLY with JSON:\n"
            '{"verdict": "entailed" | "partial" | "failed", "reason": "<one short sentence>"}\n'
            "- entailed: most headlines belong to the named family.\n"
            "- partial: the family is real but a large minority are unrelated.\n"
            "- failed: most headlines do NOT belong to the named family.")
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
                    family: bool = False) -> tuple[str, str, dict]:
    import httpx
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user",
                          "content": _judge_prompt(label, receipts, family=family)}]}
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
    rows = await conn.fetch(_RECEIPTS_SQL, topic_id, k)
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


async def main() -> None:
    ap = argparse.ArgumentParser(description="Label Court: try each active topic's label vs its receipts.")
    ap.add_argument("--limit", type=int, default=0, help="only the top-N served topics (0=all active)")
    ap.add_argument("--receipts", type=int, default=8, help="headlines per trial")
    ap.add_argument("--write", action="store_true", help="write verdicts to dynamic_topics")
    ap.add_argument("--dry-run", action="store_true", help="judge + print, no write (default if --write absent)")
    ap.add_argument("--only-unchecked", action="store_true",
                    help="incremental: only topics with label_status IS NULL")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr); sys.exit(2)
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("DEEPSEEK_API_KEY required", file=sys.stderr); sys.exit(2)
    apply_proposals = os.environ.get("ATLAS_LABEL_COURT_APPLY", "off").lower() == "on"

    conn = await asyncpg.connect(db)
    checked_at = datetime.now(timezone.utc)
    try:
        limit = args.limit or 1_000_000
        unchecked = "AND label_status IS NULL " if args.only_unchecked else ""
        # Umbrellas INCLUDED (2026-07-18): the label-fold made the served
        # front page umbrella-first — a court that skips them never judges
        # the labels users actually see. Their receipts come from children.
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
            if r["is_umbrella"]:
                receipts = await _umbrella_receipts_for(conn, dyn_id, args.receipts)
            else:
                receipts = await _receipts_for(conn, topic_id, dyn_id, args.receipts)
            if len(receipts) < 2:
                print(f"  dt-{dyn_id}: SKIP (only {len(receipts)} receipts) — {label[:50]}")
                continue
            verdict, reason, usage = await _ds_judge(label, receipts, key,
                                                     family=bool(r["is_umbrella"]))
            tok_in += usage["input_tokens"]; tok_out += usage["output_tokens"]
            dist[verdict] += 1
            proposed = build_neutral_label(receipts) if verdict == "failed" else None
            mark = {"entailed": "✓", "partial": "~", "failed": "✗"}[verdict]
            extra = f"  ->PROPOSE: {proposed}" if proposed else ""
            print(f"  {mark} dt-{dyn_id} [{verdict}] {label[:46]}{extra}")
            if verdict == "failed":
                failures.append({
                    "topic_id": topic_id, "served_label": label,
                    "verdict": verdict, "reason": reason, "proposed": proposed,
                    "receipts": [x["headline"] for x in receipts],
                    "checked_at": checked_at.isoformat(),
                })
            if args.write:
                new_label = label
                if proposed and apply_proposals:
                    new_label = proposed
                await conn.execute(
                    "UPDATE dynamic_topics SET label_status=$2, label_checked_at=$3, "
                    "label_court_model=$4, label_proposed=$5, label=$6 WHERE id=$1",
                    dyn_id, verdict, checked_at, _COURT_MODEL, proposed, new_label)

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
