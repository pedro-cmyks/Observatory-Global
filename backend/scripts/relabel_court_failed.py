"""Relabel the court-FAILED topics FROM their own receipts (#204, Pedro 2026-07-18).

The Label Court measured 84.4% of active labels asserting things their receipts
don't support. This pass regenerates each failed topic's label from the SAME
decoded receipts the court judged (DeepSeek one-liner, ~cents for 731), then
resets label_status so the nightly court re-judges the new label — the
before/after pass-rate is the measured outcome. A regenerated label equal to
the current one (whitespace/case-insensitive) is a NO-OP: the failed stamp
stays, ledger reason='relabel_no_change' (GB2 incidental, 2026-07-29).

Display-only: identity, membership, centroids untouched. REVERSIBLE: every
change is appended to docs/research/label-court/<date>-relabel-ledger.jsonl
as {topic_id, old, new}; reverting = replaying the ledger backwards
(scripts/revert via psql UPDATE ... SET label=old).

CLASS F LIVELOCK FIX (2026-07-30, docs/research/label-court/2026-07-29-gb5-
blind-check.md): the 30-min runner pairs this script with label_court.py —
court judges NULL->failed, this script rewrites the label and resets
label_status->NULL, court re-judges, ... For an umbrella whose family is
genuinely incoherent, NO regenerated label can pass, so the pair never
converges. Measured: 154 umbrella judgments over 43 rows in one day, 23 rows
judged more than once, dt-8222 judged 12 times, dt-8235 cycled 5 distinct
labels across 7 judgments. Two independent brakes, both keyed on
`label_updated_at` (migration 055, already set by every write below — no
migration needed) and this script's own ledger (already the durable,
restart-surviving record the GB5 brief pointed at):
  - COOLDOWN: a topic relabeled within the last 24h is skipped entirely (SQL
    WHERE clause — cheap, no per-row ledger read needed).
  - CAP: a topic already attempted >=3 times in the trailing 7 days is
    skipped and STAYS on its current (failed, honestly chipped) label rather
    than churning a 4th time — "a family no label can describe is an
    over-merge, not a labeling problem" (GB5). The count is read from this
    script's OWN ledger files (glob the trailing 7 daily files, count entries
    for the topic_id) rather than a new DB column, since GB5 explicitly named
    the ledger as an acceptable, already-durable mechanism and this pass adds
    no migration.

Run (repo root, M1 env):
  python -m backend.scripts.relabel_court_failed --dry-run --limit 10
  python -m backend.scripts.relabel_court_failed --write
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

# Dual-mode import: the cron invokes this as `backend.scripts.relabel_court_failed`
# (repo root cwd); pytest imports it as `scripts.relabel_court_failed` (backend cwd).
try:
    from backend.scripts.label_court import (
        _receipts_for, _umbrella_receipts_for, _LEDGER_DIR,
    )
    from backend.scripts.label_hygiene import is_placeholder_label
except ModuleNotFoundError:
    from scripts.label_court import (  # type: ignore[no-redef]
        _receipts_for, _umbrella_receipts_for, _LEDGER_DIR,
    )
    from scripts.label_hygiene import is_placeholder_label  # type: ignore[no-redef]

_DS_URL = "https://api.deepseek.com/chat/completions"
_LABEL_MODEL = "relabel-court-v1/deepseek-chat"

# GB5 Class F defaults: cheap, tunable via CLI, not env (this script has
# always been CLI-flag configured, not env-gated like label_court.py).
_DEFAULT_COOLDOWN_HOURS = 24
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_ATTEMPTS_WINDOW_DAYS = 7

# Candidates: unchanged from before, PLUS the cooldown — a topic relabeled
# within the cooldown window is not even fetched, so it can never burn an API
# call or a ledger line this cycle. label_updated_at is nullable (never
# refreshed = NULL, migration 055) so a topic that has never been relabeled
# is always a candidate regardless of the cooldown.
# TF-3b (2026-07-31): court-failed REVIVED candidates join — without this they
# are immortal (never promoted: court_blocked; never relabeled: not active;
# never re-tried: label_status not NULL). The loop closes here:
# failed -> relabel (resets label_status via the court-column upsert) ->
# fresh trial -> entailed -> promotes.
_RELABEL_CANDIDATES_SQL = (
    "SELECT id, label, is_umbrella FROM dynamic_topics "
    "WHERE (state='active' OR (state='candidate' AND revived_at IS NOT NULL)) "
    "AND label_status='failed' AND label IS NOT NULL "
    "AND (label_updated_at IS NULL OR label_updated_at < now() - $2::interval) "
    "ORDER BY agg_n_signals DESC LIMIT $1"
)


def _relabel_attempts_last_n_days(topic_id: int, now: datetime, *,
                                   days: int = _DEFAULT_ATTEMPTS_WINDOW_DAYS) -> int:
    """Count REAL relabel attempts (ledger entries that represent an actual
    DeepSeek call, whether it changed the label or reproduced it) for this
    topic across the trailing `days` days' ledger files. Reads from DISK so
    the count survives a process restart — this script runs as a fresh
    process every 30-min cron cycle, so an in-memory counter would reset
    every time and never actually cap anything. Cooldown/cap SKIP entries
    are NOT attempts (nothing was tried) and are excluded, so a capped topic
    cannot inflate its own count further while parked."""
    count = 0
    for d in range(days):
        day = (now - timedelta(days=d)).date()
        led = _LEDGER_DIR / f"{day.isoformat()}-relabel-ledger.jsonl"
        if not led.exists():
            continue
        with led.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("topic_id") != topic_id:
                    continue
                if entry.get("reason") in ("relabel_cooldown_24h", "relabel_capped_7d"):
                    continue
                count += 1
    return count


def relabel_prompt(receipts: list[dict]) -> str:
    lines = "\n".join(f"- {(r.get('headline') or '')[:160]}" for r in receipts)
    return (
        "These headlines belong to one news cluster. Write a concise LABEL "
        "(4-8 words, headline style, English, keep proper nouns/places) that "
        "accurately describes the MAJORITY of them. Never claim more than the "
        "headlines support; if they span one event's aftermath, name the "
        "event. Reply with ONLY the label text, nothing else.\n\n"
        f"HEADLINES:\n{lines}"
    )


def clean_generated_label(text: str) -> str | None:
    """Judge output -> a servable label, or None when unusable."""
    lab = (text or "").strip().strip('"').strip("'").strip()
    # strip a leading "Label:" the model sometimes adds
    if lab.lower().startswith("label:"):
        lab = lab[6:].strip()
    lab = lab.rstrip(".")
    if not lab or len(lab) < 8 or len(lab) > 90:
        return None
    if is_placeholder_label(lab):
        return None
    return lab


def is_label_unchanged(old: str | None, new: str | None) -> bool:
    """True when the proposed relabel reproduces the current label
    (whitespace runs collapsed + case folded for the comparison only)."""
    if not old or not new:
        return False
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip().casefold()
    return norm(old) == norm(new)


async def _ds_label(receipts: list[dict], key: str) -> tuple[str | None, dict]:
    import httpx
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user", "content": relabel_prompt(receipts)}]}
    async with httpx.AsyncClient() as c:
        r = await c.post(_DS_URL, json=body,
                         headers={"Authorization": f"Bearer {key}"}, timeout=40.0)
        r.raise_for_status()
        payload = r.json()
    u = payload.get("usage") or {}
    usage = {"in": u.get("prompt_tokens", 0) or 0, "out": u.get("completion_tokens", 0) or 0}
    return clean_generated_label(payload["choices"][0]["message"]["content"]), usage


async def main() -> None:
    ap = argparse.ArgumentParser(description="Relabel court-failed topics from their receipts.")
    ap.add_argument("--limit", type=int, default=0, help="0=all failed")
    ap.add_argument("--receipts", type=int, default=8)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cooldown-hours", type=float, default=_DEFAULT_COOLDOWN_HOURS,
                    help="GB5 Class F: skip a topic relabeled within this many hours")
    ap.add_argument("--max-attempts", type=int, default=_DEFAULT_MAX_ATTEMPTS,
                    help="GB5 Class F: cap relabel attempts per topic within --attempts-window-days")
    ap.add_argument("--attempts-window-days", type=int, default=_DEFAULT_ATTEMPTS_WINDOW_DAYS,
                    help="GB5 Class F: the trailing window the attempt cap is counted over")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not db or not key:
        print("DATABASE_URL + DEEPSEEK_API_KEY required", file=sys.stderr); sys.exit(2)

    conn = await asyncpg.connect(db)
    now = datetime.now(timezone.utc)
    _LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    ledger = _LEDGER_DIR / f"{now.date().isoformat()}-relabel-ledger.jsonl"
    relabeled = skipped = failed = unchanged = capped = 0
    tok_in = tok_out = 0
    try:
        limit = args.limit or 1_000_000
        cooldown = timedelta(hours=args.cooldown_hours)
        rows = await conn.fetch(_RELABEL_CANDIDATES_SQL, limit, cooldown)
        print(f"{len(rows)} court-failed topics to relabel "
              f"(cooldown={args.cooldown_hours}h, cap={args.max_attempts}/"
              f"{args.attempts_window_days}d)", flush=True)
        with ledger.open("a", encoding="utf-8") as led:
            for r in rows:
                dyn_id = r["id"]

                # GB5 Class F cap: a topic already attempted >= max_attempts
                # times in the trailing window stops being relabeled — its
                # current failed stamp stands (honest chip) instead of
                # burning another DeepSeek call the pair cannot converge on.
                attempts = _relabel_attempts_last_n_days(
                    dyn_id, now, days=args.attempts_window_days)
                if attempts >= args.max_attempts:
                    capped += 1
                    print(f"  dt-{dyn_id}: CAPPED ({attempts} attempts in "
                          f"{args.attempts_window_days}d >= {args.max_attempts}) — "
                          f"label stands, failed stamp kept", flush=True)
                    led.write(json.dumps({
                        "topic_id": dyn_id, "old": r["label"], "new": None,
                        "reason": "relabel_capped_7d", "attempts": attempts,
                        "at": now.isoformat()}, ensure_ascii=False) + "\n")
                    continue

                if r["is_umbrella"]:
                    receipts = await _umbrella_receipts_for(conn, dyn_id, args.receipts)
                else:
                    receipts = await _receipts_for(conn, f"dynamic-topic-{dyn_id}", dyn_id,
                                                   args.receipts)
                if len(receipts) < 3:
                    skipped += 1
                    continue
                try:
                    new_label, usage = await _ds_label(receipts, key)
                except Exception as ex:  # noqa: BLE001 — one API hiccup ≠ abort
                    print(f"  dt-{dyn_id}: API error ({str(ex)[:60]})", flush=True)
                    failed += 1
                    continue
                tok_in += usage["in"]; tok_out += usage["out"]
                if not new_label:
                    failed += 1
                    continue
                if is_label_unchanged(r["label"], new_label):
                    # GB2 incidental finding (2026-07-29): regenerating the SAME
                    # string that just failed must not clear the court stamp —
                    # the next pass would re-fail it, cycling stamps off nightly.
                    unchanged += 1
                    print(f"  dt-{dyn_id}: unchanged {(r['label'] or '')[:48]!r} "
                          "— keeping court stamp", flush=True)
                    led.write(json.dumps({"topic_id": dyn_id, "old": r["label"],
                                          "new": new_label,
                                          "reason": "relabel_no_change",
                                          "at": now.isoformat()},
                                         ensure_ascii=False) + "\n")
                    continue
                print(f"  dt-{dyn_id}: {(r['label'] or '')[:38]!r} -> {new_label[:48]!r}",
                      flush=True)
                led.write(json.dumps({"topic_id": dyn_id, "old": r["label"],
                                      "new": new_label, "at": now.isoformat()},
                                     ensure_ascii=False) + "\n")
                if args.write:
                    # New label + reset the verdict so the court re-judges it.
                    await conn.execute(
                        "UPDATE dynamic_topics SET label=$2, label_updated_at=$3, "
                        "label_model=$4, label_status=NULL, label_checked_at=NULL, "
                        "label_proposed=NULL WHERE id=$1",
                        dyn_id, new_label, now, _LABEL_MODEL)
                relabeled += 1
    finally:
        await conn.close()
    print(f"\nRELABEL DONE: {relabeled} relabeled · {unchanged} unchanged(stamp kept) · "
          f"{capped} capped(livelock guard) · {skipped} skipped(<3 receipts) · "
          f"{failed} failed · tokens {tok_in}/{tok_out}"
          f"{' · WRITTEN' if args.write else ' · DRY'}\nledger: {ledger}")


if __name__ == "__main__":
    asyncio.run(main())
