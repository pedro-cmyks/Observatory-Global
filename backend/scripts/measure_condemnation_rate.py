#!/usr/bin/env python3
"""The condemnation-rate instrument — the pool-health alarm clock for gates 8-9.

Pre-registration (FROZEN, approved by Pedro: "congela el trigger en 15%"):
  docs/superpowers/specs/2026-08-03-condemnation-trigger-preregistration.md
Born from the 9th gate's KILL (`2026-08-03-label-adoption.md` §3): 39% of
eligibility-filtered near-neighbor identities carried receipts that do not
match their own labels. This script makes that measurement standalone,
repeatable every ~3 nights, and appends a ledger line so the trigger crosses
itself instead of being a "we'll see".

WHAT IT MEASURES
  Sample N=60 NEAR-NEIGHBOR identities — pool topics that are the best
  ELIGIBLE adoption candidate (cos >= MATCH_THRESHOLD 0.88) of at least one
  cluster on the latest fully-labelled snapshot, after the exact 9th-gate
  eligibility filters (not blob-confirmed, not label_status='failed', not
  is_junk, not umbrella, label non-empty). Judge each identity's OWN label
  against its OWN receipts (member cluster labels + surviving headlines) with
  the program's quote-gate protocol. Condemnation = the share that fails.

FROZEN TRIGGER
  rate <= 15%  ->  "TRIGGER: re-run gates 8-9" (the fidelity-locked harnesses
                   `measure_landing_predicate.py` then `measure_label_adoption.py`,
                   bars untouched).
  15% < rate <= 25% twice consecutively -> zone of interest: report the trend,
                   do NOT advance the trigger. The 15% does not move.

CONSERVATIVE COUNTING (frozen): a CONDEMNED verdict, an unparseable verdict,
and a SUPPORTED verdict whose reason stays ungrounded after one retry ALL
count as condemned — a judgment that cannot prove health never fires the
trigger early.

PROTOCOL DELTAS vs the 9th-gate baseline (stated, carried in the ledger's
`protocol` field): the baseline (seed 42, baseline:true) was measured through
the adoption sample's identical-label class with HYDRATED modal labels; this
standalone reads `dynamic_topics.label` + `centroid_vec` directly (the
identity's official label and persisted centroid — lighter, and arguably the
righter object for "does the identity's own label hold"). New seed per run
(default derived from the date): pool health is measured on the population,
never on the same 60 rows.

Cost: one snapshot read + one topic-table read + ~60 DeepSeek temp-0 calls
(~cents). Read-only prod. Mindful M1: run under `taskpolicy -b nice -n 19`;
never run while a snapshot chain owns the machine.

Usage:
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && taskpolicy -b nice -n 19 \
      /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_condemnation_rate            # seed = today's date
  ... --seed 12345                                    # explicit seed
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from scripts.project_dynamic_topics import MATCH_THRESHOLD  # noqa: E402
from scripts.simulate_used_t_removal import _unit_rows  # noqa: E402
from scripts.measure_consolidation_landing import (  # noqa: E402
    _DS_URL,
    mindful_gate,
)
from scripts.measure_landing_predicate import pool_topic_receipts  # noqa: E402
from scripts.label_court import _reason_quotes_a_receipt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / "docs" / "research" / "recall-229" / "condemnation-ledger.jsonl"
PREREG_PATH = ("docs/superpowers/specs/"
               "2026-08-03-condemnation-trigger-preregistration.md")

SAMPLE_N = 60                 # frozen (pre-registration)
TRIGGER_RATE = 0.15           # frozen; "no se negocia ni arriba ni abajo"
ZONE_HIGH = 0.25
MIN_RECEIPT_LINES = 2         # an identity with <2 receipt lines is unjudgeable;
                              # deterministically replaced from the shuffled rest


# ------------------------------------------------------------------ pure parts
def default_seed(today: dt.date | None = None) -> int:
    """New seed per run, derived from the date (YYYYMMDD as int) — pool health
    is measured on the population, never on the same 60 rows."""
    d = today or dt.date.today()
    return int(d.strftime("%Y%m%d"))


def parse_condemnation_verdict(text: str) -> tuple[str, str]:
    """Judge output -> (verdict, reason). verdict in {'supported', 'condemned',
    'unparseable'}; unparseable is counted as condemned by the caller (a
    judgment that cannot prove health never fires the trigger early)."""
    raw = (text or "").strip()
    body = raw
    if body.startswith("```"):
        body = body.strip("`")
        body = body[body.find("{"):] if "{" in body else body
    verdict = ""
    reason = ""
    try:
        obj = json.loads(body)
        if isinstance(obj, dict):
            verdict = str(obj.get("verdict", "")).strip().lower()
            reason = str(obj.get("reason", "")).strip()
    except (json.JSONDecodeError, ValueError):
        pass
    if verdict not in ("supported", "condemned"):
        low = raw.lower()
        for v in ("condemned", "supported"):
            if v in low:
                verdict = v
                break
    if verdict not in ("supported", "condemned"):
        return "unparseable", raw[:300]
    return verdict, (reason or raw[:300])


def condemned_for_ledger(verdict: str, grounded: bool) -> bool:
    """Frozen conservative rule: only a GROUNDED 'supported' clears an
    identity. CONDEMNED, unparseable, and ungrounded-supported all count."""
    return verdict != "supported" or not grounded


def trigger_status(rate: float, prev_rate: float | None) -> str:
    """The frozen trigger line + the zone-of-interest rule (two consecutive
    runs in (15%, 25%] = report the trend, never advance the trigger)."""
    if rate <= TRIGGER_RATE:
        return "TRIGGER: re-run gates 8-9"
    if rate <= ZONE_HIGH:
        if prev_rate is not None and TRIGGER_RATE < prev_rate <= ZONE_HIGH:
            return ("ZONE OF INTEREST (second consecutive run in 15-25%): "
                    "report the trend; the trigger does NOT advance")
        return "zone of interest (15-25%): watch the next run"
    return "no trigger"


def ledger_line(*, date: str, seed: int, n: int,
                condemned_ids: list[str], protocol: str,
                baseline: bool = False,
                extra: dict[str, Any] | None = None) -> dict[str, Any]:
    line = {
        "date": date, "seed": seed, "n": n,
        "condemned": len(condemned_ids),
        "rate": round(len(condemned_ids) / max(n, 1), 4),
        "condemned_ids": sorted(condemned_ids),
        "protocol": protocol,
    }
    if baseline:
        line["baseline"] = True
    if extra:
        line.update(extra)
    return line


def read_previous_rate(ledger_path: Path) -> float | None:
    if not ledger_path.exists():
        return None
    lines = [ln for ln in ledger_path.read_text().splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return float(json.loads(lines[-1]).get("rate"))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def append_ledger(ledger_path: Path, line: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def judge_prompt(topic: dict[str, Any], receipts: list[str]) -> str:
    rec = "\n".join(f"R{i+1}: {x}" for i, x in enumerate(receipts[:14]))
    return (
        "You are auditing a news-topic identity: does its OWN label match "
        "what it ACTUALLY holds?\n\n"
        f"IDENTITY label: \"{topic['label']}\" ({topic['identity_key']}, "
        f"state {topic['state']})\n"
        f"RECEIPTS (its member cluster labels + surviving headlines):\n{rec}\n\n"
        "SUPPORTED = the receipts substantially describe the story the label "
        "names. CONDEMNED = they do not: a grab-bag of unrelated stories, or "
        "a different story than the label claims. Your reason MUST include a "
        "short VERBATIM quoted excerpt copied exactly from the receipts above "
        "— this is mechanically checked. Reply ONLY JSON:\n"
        '{"verdict": "SUPPORTED" | "CONDEMNED", '
        '"reason": "<1-2 sentences with a verbatim quoted receipt excerpt>"}')


# ------------------------------------------------------------------ run
async def run(args: argparse.Namespace) -> int:
    import asyncpg
    import httpx
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not db or not key:
        raise SystemExit("DATABASE_URL and DEEPSEEK_API_KEY required")
    seed = args.seed if args.seed is not None else default_seed()
    rng = np.random.default_rng(seed)
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    try:
        mindful_gate("condemnation start")
        # latest fully-labelled snapshot (>=100 clusters, 0 NULL labels)
        snap = await conn.fetchrow(
            "SELECT snapshot_at FROM emergent_clusters "
            "WHERE centroid_vec IS NOT NULL GROUP BY snapshot_at "
            "HAVING count(*) >= 100 AND count(*) FILTER (WHERE label IS NULL) = 0 "
            "ORDER BY snapshot_at DESC LIMIT 1")
        if snap is None:
            raise SystemExit("no fully-labelled snapshot found")
        snap_at = snap["snapshot_at"]
        crows = await conn.fetch(
            "SELECT id, centroid_vec FROM emergent_clusters "
            "WHERE snapshot_at = $1 AND centroid_vec IS NOT NULL "
            "AND label IS NOT NULL", snap_at)
        # pool: the 9th gate's EXACT eligibility filters, on persisted rows
        trows = await conn.fetch(
            "SELECT id, identity_key, label, state, centroid_vec "
            "FROM dynamic_topics WHERE centroid_vec IS NOT NULL "
            "AND label IS NOT NULL AND label <> '' "
            "AND blob_confirmed_at IS NULL "
            "AND COALESCE(label_status,'') <> 'failed' "
            "AND NOT is_junk AND NOT COALESCE(is_umbrella, false)")
        print(f"[pool] snapshot {snap_at} clusters={len(crows)}; "
              f"eligible pool topics={len(trows)}")
        V = _unit_rows(np.stack([np.asarray(r["centroid_vec"], dtype=np.float64)
                                 for r in crows]))
        T = _unit_rows(np.stack([np.asarray(r["centroid_vec"], dtype=np.float64)
                                 for r in trows]))
        S = V @ T.T
        best = np.argmax(S, axis=1)
        bcos = S[np.arange(len(crows)), best]
        hits: dict[int, dict[str, Any]] = {}
        for k in range(len(crows)):
            if bcos[k] < MATCH_THRESHOLD:
                continue
            t = trows[int(best[k])]
            h = hits.setdefault(int(t["id"]), {
                "id": int(t["id"]), "identity_key": t["identity_key"],
                "label": t["label"], "state": t["state"],
                "clusters_naming": 0, "max_cos": 0.0})
            h["clusters_naming"] += 1
            h["max_cos"] = max(h["max_cos"], round(float(bcos[k]), 4))
        pop = list(hits.values())
        print(f"[pop] {len(pop)} distinct near-neighbor identities "
              f"(clusters with candidate: {int((bcos >= MATCH_THRESHOLD).sum())}"
              f"/{len(crows)})")
        order = rng.permutation(len(pop)).tolist()
        sample: list[dict[str, Any]] = []
        skipped_thin = 0
        for i in order:
            if len(sample) >= min(SAMPLE_N, len(pop)):
                break
            t = pop[i]
            rec = await pool_topic_receipts(conn, t["id"], set())
            if len(rec) < MIN_RECEIPT_LINES:
                skipped_thin += 1
                continue
            sample.append({**t, "receipts": rec})
        print(f"[sample] {len(sample)} identities (skipped {skipped_thin} with "
              f"< {MIN_RECEIPT_LINES} receipt lines)")

        judgments: list[dict[str, Any]] = []
        async with httpx.AsyncClient() as client:
            for t in sample:
                haystack = [{"headline": x} for x in t["receipts"]]
                prompt = judge_prompt(t, t["receipts"])
                attempts = []
                for attempt in range(2):
                    body = {"model": "deepseek-chat", "temperature": 0,
                            "messages": [{"role": "user",
                                          "content": prompt if attempt == 0 else
                                          prompt + "\n\nREMINDER: the reason "
                                          "failed the quote check; copy a "
                                          "verbatim excerpt (>= 6 chars, in "
                                          "quotes) from the receipts."}]}
                    r = await client.post(
                        _DS_URL, json=body, timeout=60.0,
                        headers={"Authorization": f"Bearer {key}"})
                    r.raise_for_status()
                    ans = r.json()["choices"][0]["message"]["content"]
                    verdict, reason = parse_condemnation_verdict(ans)
                    grounded = _reason_quotes_a_receipt(reason, haystack)
                    attempts.append({"verdict": verdict, "reason": reason,
                                     "grounded": grounded})
                    if grounded and verdict in ("supported", "condemned"):
                        break
                final = attempts[-1]
                is_condemned = condemned_for_ledger(final["verdict"],
                                                    final["grounded"])
                judgments.append({**{k: t[k] for k in
                                     ("id", "identity_key", "label", "state",
                                      "clusters_naming", "max_cos")},
                                  **final, "condemned": is_condemned})
                mark = "CONDEMNED" if is_condemned else "supported"
                print(f"  [{mark:9s}] dt-{t['id']:<6d} '{t['label'][:52]}' "
                      f"grounded={final['grounded']}")
                if is_condemned:
                    print(f"              {final['reason'][:180]}")

        condemned_ids = [j["identity_key"] for j in judgments if j["condemned"]]
        prev = read_previous_rate(LEDGER)
        line = ledger_line(
            date=dt.date.today().isoformat(), seed=seed, n=len(judgments),
            condemned_ids=condemned_ids,
            protocol="standalone-v1: dynamic_topics.label + persisted centroid; "
                     f"snapshot {snap_at.isoformat()}",
            extra={"snapshot": snap_at.isoformat(),
                   "population": len(pop), "skipped_thin": skipped_thin,
                   "judgments": [{k: j[k] for k in
                                  ("identity_key", "label", "verdict",
                                   "grounded", "condemned")}
                                 for j in judgments]})
        append_ledger(LEDGER, line)
        status = trigger_status(line["rate"], prev)
        print(f"\n[rate] {line['condemned']}/{line['n']} = "
              f"{100*line['rate']:.1f}% condemned (seed {seed}, prev "
              f"{'-' if prev is None else f'{100*prev:.1f}%'})")
        print(f"[trigger] {status}")
        print(f"[ledger] appended to {LEDGER}")
        return 0
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Condemnation-rate instrument (read-only; ~60 DeepSeek "
                    "calls; appends to the condemnation ledger).")
    ap.add_argument("--seed", type=int, default=None,
                    help="sampling seed (default: today's date as YYYYMMDD)")
    return ap.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
