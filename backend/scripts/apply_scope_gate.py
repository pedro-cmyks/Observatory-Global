#!/usr/bin/env python3
"""Apply the persisted Atlas scope gate to assignments (Phase C inference).

Loads the trained gate (`train_scope_gate.py` output), embeds each
assignment's "headline | topic_label" with the SAME OpenAI model the gate
was trained on, scores it through the persisted scaler + logistic weights,
and applies the per-topic keep-threshold (>=90% precision), falling back to
the global threshold for thin topics. Output per assignment:
`gate_score` and `gate_kept` (keep vs abstain).

The gate calls NO LLM at inference — only an embedding + a dot product —
so it is cheap (~$0.00002/signal at text-embedding-3-small) and fast.
DeepSeek/Anthropic cannot substitute here: the weights live in the
OpenAI embedding vector space and DeepSeek has no embeddings API.

Embeddings come from `--embeddings` cache when present (free, for
validation against the training sample); otherwise they are fetched live
from OpenAI (`OPENAI_API_KEY`).

Modes:
  --eval   signals carry `is_evidence` consensus -> report kept-set
           precision + coverage (overall + per-topic) vs the gate's target.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase_b_scope_gate_probe as G  # noqa: E402

EMBED_BATCH = 512


def _load_gate(path: Path) -> dict[str, Any]:
    g = json.loads(path.read_text(encoding="utf-8"))
    g["_mean"] = np.asarray(g["scaler_mean"], dtype=np.float64)
    g["_std"] = np.asarray(g["scaler_std"], dtype=np.float64)
    g["_coef"] = np.asarray(g["lr_coef"], dtype=np.float64)
    g["_intercept"] = float(g["lr_intercept"])
    return g


def _embed_live(texts: list[str], model: str) -> np.ndarray:
    import openai
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    client = openai.OpenAI(api_key=key, timeout=60.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        chunk = texts[i : i + EMBED_BATCH]
        for attempt in range(1, 6):
            try:
                resp = client.embeddings.create(model=model, input=chunk)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 5:
                    raise
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
        print(f"  embedded {len(vecs)}/{len(texts)}", file=sys.stderr)
    return np.asarray(vecs, dtype=np.float64)


def _score(gate: dict[str, Any], emb: np.ndarray, atlas: np.ndarray) -> np.ndarray:
    X = np.hstack([emb, atlas])
    Xs = (X - gate["_mean"]) / gate["_std"]
    z = Xs @ gate["_coef"] + gate["_intercept"]
    return 1.0 / (1.0 + np.exp(-z))


def _keep(gate: dict[str, Any], score: float, slug: str | None) -> tuple[bool, float | None]:
    thr = gate["per_topic_threshold"].get(slug) if slug else None
    if thr is None:
        thr = gate["global_threshold"]
    if thr is None:  # abstain-mode topic with no usable threshold
        return False, None
    return bool(score >= thr), float(thr)


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Apply the persisted scope gate.")
    ap.add_argument("--gate", type=Path, default=base / "models/2026-05-29-scope-gate-v1.json")
    ap.add_argument("--signals", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl")
    ap.add_argument("--embeddings", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-openai-embeddings.jsonl",
                    help="Cached embeddings; if missing keys, fetched live from OpenAI.")
    ap.add_argument("--out", type=Path, default=base / "reports/phase-b/2026-05-29-scope-gate-decisions.jsonl")
    ap.add_argument("--eval", action="store_true", help="Report precision/coverage if is_evidence present.")
    ap.add_argument("--binary-only", action="store_true")
    args = ap.parse_args()

    gate = _load_gate(args.gate)
    model = gate["feature_spec"]["embedding_model"]

    rows = [json.loads(l) for l in args.signals.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.binary_only or args.eval:
        rows = [r for r in rows if r.get("is_evidence") in (0, 1)]

    keys = [(int(r["signal_id"]), r.get("assigned_topic_slug")) for r in rows]
    emb_map = G._load_embeddings(args.embeddings) if args.embeddings and args.embeddings.exists() else {}
    missing = [i for i, k in enumerate(keys) if k not in emb_map]
    if missing:
        texts = [f"{(rows[i].get('headline') or '').strip()} | {(rows[i].get('assigned_topic_label') or '').strip()}"
                 for i in missing]
        print(f"embedding {len(missing)} uncached rows live ({model})", file=sys.stderr)
        fresh = _embed_live(texts, model)
        for j, i in enumerate(missing):
            emb_map[keys[i]] = fresh[j]

    emb = np.vstack([emb_map[k] for k in keys])
    atlas = G._atlas_feats(rows)
    scores = _score(gate, emb, atlas)

    decisions = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for r, k, s in zip(rows, keys, scores):
            kept, thr = _keep(gate, float(s), k[1])
            d = {"signal_id": k[0], "assigned_topic_slug": k[1],
                 "gate_score": round(float(s), 5), "threshold": thr, "gate_kept": kept}
            decisions.append({**d, "is_evidence": r.get("is_evidence")})
            fh.write(json.dumps(d) + "\n")

    kept_n = sum(1 for d in decisions if d["gate_kept"])
    print(f"scored {len(decisions)} | kept {kept_n} ({kept_n/len(decisions):.1%}) -> {args.out}")

    if args.eval:
        ev = [d for d in decisions if d["is_evidence"] in (0, 1)]
        kept = [d for d in ev if d["gate_kept"]]
        tp = sum(1 for d in kept if d["is_evidence"] == 1)
        n_pos = sum(1 for d in ev if d["is_evidence"] == 1)
        prec = tp / len(kept) if kept else float("nan")
        cov = tp / n_pos if n_pos else float("nan")
        print(f"[eval] kept-set precision {prec:.4f} | evidence-coverage {cov:.4f} "
              f"| target {gate['target_precision']} (in-sample reproduction check)")


if __name__ == "__main__":
    main()
