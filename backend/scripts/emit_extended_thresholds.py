#!/usr/bin/env python
"""Emit backend/app/data/scope_gate_extended_thresholds.json (two-tier serving).

Mechanical step of the retrain playbook (docs/state/handoff-playbooks.md):
after retraining the gate at the VERIFIED target (0.90), re-run
train_scope_gate with --target-precision 0.75 --out /tmp/gate75.json, then
run this to convert that run's .calibration.json into the serving file the
API reads (themes.py EXTENDED tier). Previously this conversion was done
ad-hoc in-session; this script makes it reproducible.

Usage:
  python backend/scripts/emit_extended_thresholds.py \
      --calibration /tmp/gate75.calibration.json \
      --gate-id atlas-scope-gate-v4-mega2 \
      [--out backend/app/data/scope_gate_extended_thresholds.json]

Then deploy the API (./scripts/deploy-fly-api.sh) — app/data ships in the
Docker image (models/ does NOT).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", required=True,
                    help=".calibration.json from a --target-precision 0.75 run")
    ap.add_argument("--gate-id", required=True,
                    help="MUST match the deployed gate_model id (cron GATE_ID)")
    ap.add_argument("--verified-target", type=float, default=0.90)
    ap.add_argument("--out", default="backend/app/data/scope_gate_extended_thresholds.json")
    args = ap.parse_args()

    calib = json.load(open(args.calibration))
    ext_target = float(calib.get("target_precision", 0.75))
    if abs(ext_target - 0.75) > 1e-6:
        print(f"WARN: calibration target is {ext_target}, expected 0.75 — "
              "did you run train_scope_gate with --target-precision 0.75?")

    per_topic = {}
    for slug, e in calib["per_topic"].items():
        thr = e.get("threshold")
        if thr is not None:
            per_topic[slug] = round(float(thr), 5)
        # abstain topics get NO extended threshold: the serving layer then
        # has no extended tier for them — honest, not a silent fallback.

    out = {
        "gate_id": args.gate_id,
        "target_precision_verified": args.verified_target,
        "target_precision_extended": ext_target,
        "global_threshold": round(float(calib["global_operating_point"]["threshold"]), 5),
        "per_topic_threshold": per_topic,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}: {len(per_topic)} topics, "
          f"global {out['global_threshold']}, gate {args.gate_id}")
    print("NEXT: ./scripts/deploy-fly-api.sh (app/data ships in the image)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
