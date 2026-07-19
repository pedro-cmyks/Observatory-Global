"""Relabel the court-FAILED topics FROM their own receipts (#204, Pedro 2026-07-18).

The Label Court measured 84.4% of active labels asserting things their receipts
don't support. This pass regenerates each failed topic's label from the SAME
decoded receipts the court judged (DeepSeek one-liner, ~cents for 731), then
resets label_status so the nightly court re-judges the new label — the
before/after pass-rate is the measured outcome.

Display-only: identity, membership, centroids untouched. REVERSIBLE: every
change is appended to docs/research/label-court/<date>-relabel-ledger.jsonl
as {topic_id, old, new}; reverting = replaying the ledger backwards
(scripts/revert via psql UPDATE ... SET label=old).

Run (repo root, M1 env):
  python -m backend.scripts.relabel_court_failed --dry-run --limit 10
  python -m backend.scripts.relabel_court_failed --write
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

from backend.scripts.label_court import (
    _receipts_for, _umbrella_receipts_for, _LEDGER_DIR,
)
from backend.scripts.label_hygiene import is_placeholder_label

_DS_URL = "https://api.deepseek.com/chat/completions"
_LABEL_MODEL = "relabel-court-v1/deepseek-chat"


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
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not db or not key:
        print("DATABASE_URL + DEEPSEEK_API_KEY required", file=sys.stderr); sys.exit(2)

    conn = await asyncpg.connect(db)
    now = datetime.now(timezone.utc)
    _LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    ledger = _LEDGER_DIR / f"{now.date().isoformat()}-relabel-ledger.jsonl"
    relabeled = skipped = failed = 0
    tok_in = tok_out = 0
    try:
        limit = args.limit or 1_000_000
        rows = await conn.fetch(
            "SELECT id, label, is_umbrella FROM dynamic_topics "
            "WHERE state='active' AND label_status='failed' AND label IS NOT NULL "
            "ORDER BY agg_n_signals DESC LIMIT $1", limit)
        print(f"{len(rows)} court-failed topics to relabel", flush=True)
        with ledger.open("a", encoding="utf-8") as led:
            for r in rows:
                dyn_id = r["id"]
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
    print(f"\nRELABEL DONE: {relabeled} relabeled · {skipped} skipped(<3 receipts) · "
          f"{failed} failed · tokens {tok_in}/{tok_out}"
          f"{' · WRITTEN' if args.write else ' · DRY'}\nledger: {ledger}")


if __name__ == "__main__":
    asyncio.run(main())
