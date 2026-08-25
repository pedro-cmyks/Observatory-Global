#!/usr/bin/env python3
"""Corte-con-cuerpos MONÓTONO — el paso nocturno de zona gris (Step 2.7).

Prereg congelado: `docs/superpowers/specs/2026-08-24-court-bodies-monotone-
preregistration.md`. Origen: run 1 (KILL simétrico, 4/4 correcto hacia
rechazo, 0/2 hacia aceptación) → solo la dirección que ENDURECE escribe.

Transiciones PERMITIDAS (explícitas, congeladas):
    partial → failed | too_broad
    failed  → too_broad
    NULL/withheld → failed | too_broad   (primer sello jamás ablanda)
Todo lo demás (incluida cualquier flecha hacia entailed/partial) = no-op
ledgereado `softening_ignored`. Los topics `entailed` NUNCA entran a la
población. Reversión: --revert <ledger> restaura el estado previo fila a
fila. Kill-switch del runner: ATLAS_COURT_BODIES_MONOTONE.

Parámetros heredados SIN movimiento del run 1: ≤4 cuerpos/topic,
excerpt cap 500, prompt plano de la corte, DeepSeek temp 0.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys
import time

import aiohttp
import asyncpg

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND)

from scripts.m1_confirmation_calibration import load_db_url  # noqa: E402
from scripts.measure_court_with_bodies import (  # noqa: E402
    _RECEIPTS_URL_SQL, BODIES_PER_TOPIC, fetch_body, judge_bodies)

CAP_DEFAULT = 120
MODEL_MARK = "court-bodies-mono-v1"
# El ledger vive en el REPO canónico aunque el código corra desde la copia
# ALW (la primera noche escribió en ALW/docs por el path relativo — quirk
# corregido 2026-08-25; ese ledger fue copiado a mano al repo).
_REPO = os.environ.get("ATLAS_REPO_DIR", "/Users/pedro/ObservatorioGlobal")
_DOCS_ROOT = _REPO if os.path.isdir(os.path.join(_REPO, "docs")) \
    else os.path.join(_BACKEND, "..")
LEDGER_DIR = os.path.join(_DOCS_ROOT, "docs", "research", "label-court",
                          "bodies-monotone-ledger")

_POP_SQL = """
    SELECT d.id, d.label, d.label_status
    FROM dynamic_topics d
    WHERE d.state = 'active'
      AND COALESCE(d.is_junk, false) = false
      AND (d.label_status IN ('partial','failed') OR d.label_status IS NULL)
      AND EXISTS (SELECT 1 FROM topic_members tm
                  WHERE tm.topic_id = 'dynamic-topic-' || d.id
                    AND tm.role = 'evidence'
                    AND tm.engine_version = 'v1-compat'
                    AND COALESCE(tm.quarantined, false) = false)
    ORDER BY d.label_checked_at ASC NULLS FIRST
    LIMIT $1
"""

_ALLOWED = {
    ("partial", "failed"), ("partial", "too_broad"),
    ("failed", "too_broad"),
    (None, "failed"), (None, "too_broad"),
}


def monotone_applies(current: str | None, proposed: str | None) -> bool:
    """True solo para las transiciones endurecedoras congeladas del prereg."""
    if proposed is None:
        return False
    cur = current if current in ("partial", "failed", "too_broad",
                                 "entailed") else None
    return (cur, proposed) in _ALLOWED


async def run(args: argparse.Namespace) -> int:
    key = os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY missing")
    os.makedirs(LEDGER_DIR, exist_ok=True)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ledger_path = os.path.join(LEDGER_DIR, f"mono-{run_id}.jsonl")
    ledger = open(ledger_path, "a")
    stats = {"population": 0, "no_receipts": 0, "unfetchable": 0,
             "judged": 0, "hardened": 0, "softening_ignored": 0,
             "confirmed": 0, "errors": 0}
    t0 = time.monotonic()

    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                 timeout=30)
    try:
        pop = await conn.fetch(_POP_SQL, args.cap)
        stats["population"] = len(pop)
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for p in pop:
                dyn_id = int(p["id"])
                label = p["label"] or ""
                current = p["label_status"]
                tid = f"dynamic-topic-{dyn_id}"
                rows = await conn.fetch(_RECEIPTS_URL_SQL, tid, 8)
                receipts = [{"headline": html.unescape(r["headline"] or ""),
                             "source_url": r["source_url"]} for r in rows]
                entry = {"id": dyn_id, "label": label, "prior": current}
                if not receipts:
                    stats["no_receipts"] += 1
                    entry["outcome"] = "no_receipts"
                    ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    continue
                fetched = []
                for r in receipts:
                    if len(fetched) >= BODIES_PER_TOPIC:
                        break
                    if not r["source_url"]:
                        continue
                    out = await fetch_body(session, r["source_url"])
                    if out["status"] == "ok":
                        fetched.append({"headline": r["headline"],
                                        "excerpt": out["excerpt"]})
                if not fetched:
                    stats["unfetchable"] += 1
                    entry["outcome"] = "unfetchable"
                    ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    continue
                try:
                    verdict, reason, usage = await judge_bodies(
                        label, fetched, key)
                except Exception as exc:
                    stats["errors"] += 1
                    entry["outcome"] = f"judge_error:{exc!r}"[:120]
                    ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    continue
                stats["judged"] += 1
                entry.update(verdict_bodies=verdict, reason=reason,
                             bodies=len(fetched), usage=usage)
                if monotone_applies(current, verdict):
                    entry["outcome"] = "hardened"
                    entry["applied"] = bool(args.execute)
                    stats["hardened"] += 1
                    if args.execute:
                        await conn.execute(
                            "UPDATE dynamic_topics SET label_status=$1,"
                            " label_court_model=$2, label_checked_at=now()"
                            " WHERE id=$3", verdict, MODEL_MARK, dyn_id)
                elif verdict == current:
                    entry["outcome"] = "confirmed"
                    stats["confirmed"] += 1
                else:
                    entry["outcome"] = "softening_ignored"
                    stats["softening_ignored"] += 1
                ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
                ledger.flush()
    finally:
        await conn.close()
        ledger.close()
    stats["wall_s"] = round(time.monotonic() - t0, 1)
    stats["execute"] = bool(args.execute)
    stats["ledger"] = ledger_path
    print("[court-bodies-mono] " + json.dumps(stats, ensure_ascii=False))
    return 0


async def revert(path: str) -> int:
    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                 timeout=30)
    n = 0
    try:
        for line in open(path):
            d = json.loads(line)
            if d.get("outcome") == "hardened" and d.get("applied"):
                await conn.execute(
                    "UPDATE dynamic_topics SET label_status=$1,"
                    " label_court_model=NULL WHERE id=$2"
                    " AND label_court_model=$3",
                    d.get("prior"), int(d["id"]), MODEL_MARK)
                n += 1
    finally:
        await conn.close()
    print(f"[revert] {n} filas restauradas desde {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=CAP_DEFAULT)
    ap.add_argument("--execute", action="store_true",
                    help="escribe label_status (default: dry-run a ledger)")
    ap.add_argument("--revert", metavar="LEDGER",
                    help="restaura el estado previo de un ledger de corrida")
    args = ap.parse_args()
    if args.revert:
        return asyncio.run(revert(args.revert))
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
