#!/usr/bin/env python3
"""Score Atlas topic assignments with the scope gate (Phase C production).

Runs LOCALLY (off-iCloud mlvenv: asyncpg + torch + transformers), the same
machine + cadence as the atlas-classifier cron. For each
`theme-hint-lex-v2` assignment it:
  1. embeds "query: headline | topic_label" with the gate's local
     multilingual encoder (e5-base, MPS) — $0/signal,
  2. scores [embedding || atlas_confidence || atlas_matched_terms] through
     the persisted scaler + logistic weights,
  3. applies the per-topic keep-threshold (global fallback),
  4. writes gate_score / gate_kept / gate_model back to
     signal_topic_assignments.

Idempotent / resume-safe: scores only rows with gate_score IS NULL unless
--rescore. Incremental use: --window-hours 0.5 in the cron after
backfill_lexicon_topics.py. Backfill: --window-hours 0 (all joinable).

Env: DATABASE_URL (Supabase pooler). Feature extraction MUST match the
training corpus (build_consensus_corpus.py): atlas_matched_terms =
len(evidence['matched_terms']).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path("docs/research/atlas-paper/phase-1-validation")
DEFAULT_GATE = BASE / "models/2026-05-29-scope-gate-v1-e5base.json"
SELECT_SQL = """
    SELECT a.signal_id, a.topic_id, t.slug, t.label,
           s.headline, a.confidence, a.evidence
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s   ON s.id = a.signal_id
    WHERE a.method = 'lexicon'
      AND a.model_version = 'theme-hint-lex-v2'
      AND s.headline IS NOT NULL
      AND ($1::boolean OR a.gate_score IS NULL)
      AND ($2::int = 0 OR a.assigned_at > NOW() - ($2::int * INTERVAL '1 hour'))
    ORDER BY a.assigned_at DESC
    LIMIT $3
"""
UPDATE_SQL = """
    UPDATE signal_topic_assignments
       SET gate_score = $3, gate_kept = $4, gate_model = $5
     WHERE signal_id = $1 AND topic_id = $2
       AND method = 'lexicon' AND model_version = 'theme-hint-lex-v2'
"""


def _load_gate(path: Path) -> dict[str, Any]:
    g = json.loads(path.read_text(encoding="utf-8"))
    g["_mean"] = np.asarray(g["scaler_mean"], dtype=np.float64)
    g["_std"] = np.asarray(g["scaler_std"], dtype=np.float64)
    g["_coef"] = np.asarray(g["lr_coef"], dtype=np.float64)
    g["_intercept"] = float(g["lr_intercept"])
    return g


def _matched_terms(evidence: Any) -> float:
    ev = evidence
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except json.JSONDecodeError:
            return 0.0
    if isinstance(ev, dict):
        mt = ev.get("matched_terms")
        if isinstance(mt, list):
            return float(len(mt))
    return 0.0


def _build_embedder(model_name: str):
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    def embed(texts: list[str]) -> np.ndarray:
        out_vecs = []
        with torch.no_grad():
            for i in range(0, len(texts), 64):
                batch = texts[i : i + 64]
                enc = tok(batch, padding=True, truncation=True, max_length=96,
                          return_tensors="pt").to(device)
                hs = model(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).float()
                pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                out_vecs.append(pooled.cpu().numpy())
        return np.vstack(out_vecs)

    return embed, device


def _score_and_decide(gate: dict[str, Any], emb: np.ndarray, conf: np.ndarray,
                      mt: np.ndarray, slugs: list[str]) -> tuple[np.ndarray, list[bool]]:
    X = np.hstack([emb, conf.reshape(-1, 1), mt.reshape(-1, 1)])
    Xs = (X - gate["_mean"]) / gate["_std"]
    z = Xs @ gate["_coef"] + gate["_intercept"]
    scores = 1.0 / (1.0 + np.exp(-z))
    per_topic = gate["per_topic_threshold"]
    g_thr = gate["global_threshold"]
    kept: list[bool] = []
    for s, slug in zip(scores, slugs):
        thr = per_topic.get(slug, g_thr)
        if thr is None:
            thr = g_thr
        kept.append(bool(thr is not None and s >= thr))
    return scores, kept


async def run(args: argparse.Namespace) -> None:
    import asyncpg

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)

    gate = _load_gate(args.gate)
    embed, device = _build_embedder(gate["feature_spec"]["embedding_model"])
    print(f"gate {args.gate_id} | encoder {gate['feature_spec']['embedding_model']} on {device}",
          file=sys.stderr)

    conn = await asyncpg.connect(db)
    total = 0
    try:
        while True:
            rows = await conn.fetch(SELECT_SQL, args.rescore, args.window_hours, args.batch)
            if not rows:
                break
            texts = [f"query: {(r['headline'] or '').strip()} | {(r['label'] or '').strip()}" for r in rows]
            emb = embed(texts)
            conf = np.array([float(r["confidence"]) for r in rows])
            mt = np.array([_matched_terms(r["evidence"]) for r in rows])
            slugs = [r["slug"] for r in rows]
            scores, kept = _score_and_decide(gate, emb, conf, mt, slugs)
            await conn.executemany(UPDATE_SQL, [
                (r["signal_id"], r["topic_id"], float(sc), bool(k), args.gate_id)
                for r, sc, k in zip(rows, scores, kept)
            ])
            total += len(rows)
            kept_n = sum(kept)
            print(f"  scored {total} (+{len(rows)}, kept {kept_n})", file=sys.stderr)
            if args.rescore or len(rows) < args.batch:
                # in --rescore mode the NULL filter never shrinks the pool; one pass only
                if args.rescore:
                    break
    finally:
        await conn.close()
    print(json.dumps({"scored": total, "gate_id": args.gate_id}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="Score atlas assignments with the scope gate.")
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--gate-id", default="atlas-scope-gate-v1-e5base")
    ap.add_argument("--window-hours", type=int, default=0, help="0 = all joinable; else recent window.")
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--rescore", action="store_true", help="Re-score even rows that already have a score.")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
