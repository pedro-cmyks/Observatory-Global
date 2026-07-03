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


def _is_openai(model_name: str) -> bool:
    return model_name.startswith("text-embedding-")


def _text_for(model_name: str, headline: str, label: str) -> str:
    """Match the gate's TRAINING text exactly. e5 was trained on the
    'query: ' retrieval prefix; the OpenAI gate on the bare 'headline | label'
    (train_scope_gate._texts). Mismatching the prefix silently corrupts scores."""
    h, t = (headline or "").strip(), (label or "").strip()
    return f"query: {h} | {t}" if not _is_openai(model_name) else f"{h} | {t}"


def _build_openai_embedder(model_name: str):
    """Live OpenAI embeddings for the OpenAI-space gate (v1). ~$0.00002/signal."""
    import openai

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    client = openai.OpenAI(api_key=key, timeout=60.0)

    def embed(texts: list[str]) -> np.ndarray:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), 512):
            chunk = texts[i : i + 512]
            for attempt in range(1, 6):
                try:
                    resp = client.embeddings.create(model=model_name, input=chunk)
                    break
                except Exception:  # noqa: BLE001 — retry transient API/network errors
                    if attempt == 5:
                        raise
                    import time
                    time.sleep(2.0 * attempt)
            vecs.extend(d.embedding for d in resp.data)
        return np.asarray(vecs, dtype=np.float64)

    return embed, "openai"


def _build_embedder(model_name: str):
    if _is_openai(model_name):
        return _build_openai_embedder(model_name)
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
    model_name = gate["feature_spec"]["embedding_model"]
    embed, device = _build_embedder(model_name)
    print(f"gate {args.gate_id} | encoder {model_name} on {device}"
          + (" | DRY-RUN (no writes)" if args.dry_run else ""), file=sys.stderr)

    conn = await asyncpg.connect(db)
    total = 0
    per_topic: dict[str, list[int]] = {}  # slug -> [kept, n] (dry-run report)
    try:
        while True:
            rows = await conn.fetch(SELECT_SQL, args.rescore, args.window_hours, args.batch)
            if not rows:
                break
            texts = [_text_for(model_name, r["headline"], r["label"]) for r in rows]
            emb = embed(texts)
            conf = np.array([float(r["confidence"]) for r in rows])
            mt = np.array([_matched_terms(r["evidence"]) for r in rows])
            slugs = [r["slug"] for r in rows]
            scores, kept = _score_and_decide(gate, emb, conf, mt, slugs)
            if not args.dry_run:
                await conn.executemany(UPDATE_SQL, [
                    (r["signal_id"], r["topic_id"], float(sc), bool(k), args.gate_id)
                    for r, sc, k in zip(rows, scores, kept)
                ])
            for slug, k in zip(slugs, kept):
                agg = per_topic.setdefault(slug, [0, 0])
                agg[0] += int(k); agg[1] += 1
            total += len(rows)
            print(f"  scored {total} (+{len(rows)}, kept {sum(kept)})", file=sys.stderr)
            if args.rescore or len(rows) < args.batch:
                if args.rescore:
                    break
    finally:
        await conn.close()
    out = {"scored": total, "gate_id": args.gate_id, "dry_run": args.dry_run}
    if args.dry_run:
        out["per_topic_keep"] = {
            s: {"kept": k, "n": n, "keep_pct": round(100.0 * k / n, 1)}
            for s, (k, n) in sorted(per_topic.items(), key=lambda x: -x[1][1])
        }
    print(json.dumps(out, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="Score atlas assignments with the scope gate.")
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--gate-id", default="atlas-scope-gate-v1-e5base")
    ap.add_argument("--window-hours", type=int, default=0, help="0 = all joinable; else recent window.")
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--rescore", action="store_true", help="Re-score even rows that already have a score.")
    ap.add_argument("--dry-run", action="store_true", help="Score + report per-topic keep, but write nothing.")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
