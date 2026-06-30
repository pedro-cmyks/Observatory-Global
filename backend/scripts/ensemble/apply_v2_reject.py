"""Taxonomy revision — v2 reject stage (#204), additive, flag-gated, reversible.

Post-classifier reject: of the signals the lexical gate (`theme-hint-lex-v2`) KEPT,
demote the ones the v2 e5 gate scores as OUT_OF_SCOPE (the force-fit). Uses the e5
vector already persisted in `signal_embeddings` → $0 inference. NUMPY-ONLY scoring
(loads plain logistic weights from `v2_gate.json`, like the existing e5base scope
gate) — no sklearn/joblib, so it is portable to the M1 worker venv. Does NOT touch
the classifier; runs after it.

Honesty + safety:
  - DRY-RUN by default: prints the A/B (how many it would demote + spot-check) and
    writes nothing.
  - LIVE write requires BOTH `--apply` AND env `ATLAS_V2_GATE_ENABLED=true`.
  - Only DEMOTES (gate_kept true->false); never promotes. Tags `gate_model=
    v2-gate-e5-lr-1` + keeps `gate_score` so every demotion is attributable and
    reversible (no silent filtering — the reason is on the row).

Run (A/B):   python -m backend.scripts.ensemble.apply_v2_reject [--hours 24] [--threshold 0.5]
Run (live):  ATLAS_V2_GATE_ENABLED=true python -m backend.scripts.ensemble.apply_v2_reject --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg
import numpy as np

MODEL_PATH = "backend/models/v2_gate.json"
GATE_MODEL_TAG = "v2-gate-e5-lr-1"


def _parse_vec(txt: str) -> np.ndarray:
    return np.fromstring(txt.strip("[]"), sep=",", dtype=np.float32)


def _load_gate(path: str) -> tuple[np.ndarray, float]:
    g = json.load(open(path))
    return np.asarray(g["inscope_coef"], dtype=np.float64), float(g["inscope_intercept"])


async def run(hours: int, threshold: float, apply: bool) -> int:
    coef, intercept = _load_gate(MODEL_PATH)

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """SELECT a.signal_id, a.topic_id, s.headline, e.vec::text v
               FROM signal_topic_assignments a
               JOIN signal_embeddings e ON e.signal_id = a.signal_id
               JOIN signals_v2 s ON s.id = a.signal_id
               WHERE a.model_version='theme-hint-lex-v2' AND a.gate_kept = true
                 AND a.assigned_at > NOW() - ($1 || ' hours')::interval""",
            str(hours))
        if not rows:
            print(f"no embedded gate_kept assignments in {hours}h.")
            return 0
        X = np.vstack([_parse_vec(r["v"]) for r in rows]).astype(np.float64)
        p_inscope = 1.0 / (1.0 + np.exp(-(X @ coef + intercept)))  # numpy sigmoid
        reject = p_inscope < threshold

        n, nrej = len(rows), int(reject.sum())
        print(f"=== v2 reject A/B (theme-hint-lex-v2 gate_kept, {hours}h, thr={threshold}) ===")
        print(f"  embedded gate_kept: {n}")
        print(f"  would DEMOTE (force-fit, P(in-scope)<{threshold}): {nrej} ({100*nrej/n:.1f}%)")
        print(f"  remain kept: {n-nrej} ({100*(n-nrej)/n:.1f}%)")

        order = np.argsort(p_inscope)
        print("\n  10 lowest P(in-scope) among KEPT — the force-fit being demoted:")
        for i in order[:10]:
            print(f"    [{p_inscope[i]:.2f}] {(rows[i]['headline'] or '')[:76]}")
        print("\n  10 highest P(in-scope) among KEPT — correctly retained:")
        for i in order[::-1][:10]:
            print(f"    [{p_inscope[i]:.2f}] {(rows[i]['headline'] or '')[:76]}")

        if not apply:
            print("\n[DRY-RUN] no writes. Live: ATLAS_V2_GATE_ENABLED=true ... --apply")
            return 0
        if os.environ.get("ATLAS_V2_GATE_ENABLED", "").lower() != "true":
            print("\n[BLOCKED] --apply given but ATLAS_V2_GATE_ENABLED!=true. No writes.")
            return 2

        # LIVE: demote only the force-fit, tagged + reversible
        dem = [(rows[i]["signal_id"], rows[i]["topic_id"], float(p_inscope[i]))
               for i in range(n) if reject[i]]
        await conn.executemany(
            """UPDATE signal_topic_assignments
               SET gate_kept=false, gate_model=$3, gate_score=$4
               WHERE signal_id=$1 AND topic_id=$2 AND model_version='theme-hint-lex-v2'""",
            [(sid, tid, GATE_MODEL_TAG, sc) for sid, tid, sc in dem])
        print(f"\n[APPLIED] demoted {len(dem)} force-fit assignments "
              f"(gate_model={GATE_MODEL_TAG}, reversible).")
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--threshold", type=float,
                    default=float(os.environ.get("ATLAS_V2_GATE_THRESHOLD", "0.5")))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    return asyncio.run(run(args.hours, args.threshold, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
