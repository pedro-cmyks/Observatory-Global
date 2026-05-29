#!/usr/bin/env python3
"""Embed consensus-corpus rows with a LOCAL multilingual encoder.

The production goal is $0 marginal cost per signal: the scope gate's
embedding must come from a model we host (in the Fly nlp_worker), not a
paid API. This script produces those embeddings locally with a
HuggingFace multilingual sentence encoder (default
`intfloat/multilingual-e5-base`, 768-dim) via mean pooling — the same
class of model the worker already runs (transformers/torch).

Output JSONL is keyed by (signal_id, assigned_topic_slug), matching
`embed_corpus_openai.py` so the probe / gate trainer consume it
identically. Resume-safe.

No API key, no network cost (model weights cache once in ~/.cache/huggingface).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_BATCH = 64


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _text(row: dict[str, Any]) -> str:
    h = (row.get("headline") or "").strip()
    t = (row.get("assigned_topic_label") or "").strip()
    # e5 expects an instruction prefix; "query:" works for short single texts.
    return f"query: {h} | {t}"


def _existing_keys(path: Path) -> set[tuple[int, str]]:
    if not path.exists():
        return set()
    seen: set[tuple[int, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            seen.add((int(r["signal_id"]), r.get("assigned_topic_slug")))
    return seen


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Embed consensus corpus with a local multilingual encoder.")
    ap.add_argument("--corpus", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl")
    ap.add_argument("--out", type=Path,
                    default=base / "labels/consensus/2026-05-29-3vendor-5k-e5-embeddings.jsonl")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    ap.add_argument("--binary-only", action="store_true")
    args = ap.parse_args()

    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModel.from_pretrained(args.model)
    model.eval()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)
    print(f"loaded {args.model} on {device}", file=sys.stderr)

    rows = _read_jsonl(args.corpus)
    if args.binary_only:
        rows = [r for r in rows if r.get("is_evidence") in (0, 1)]
    by_key = {(int(r["signal_id"]), r.get("assigned_topic_slug")): r for r in rows}
    skip = _existing_keys(args.out)
    pending = [(k, v) for k, v in by_key.items() if k not in skip]
    print(f"{len(by_key)} rows, {len(skip)} cached, {len(pending)} to embed", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("a", encoding="utf-8") as fh:
        for i in range(0, len(pending), args.batch):
            chunk = pending[i : i + args.batch]
            texts = [_text(v) for _, v in chunk]
            enc = tok(texts, padding=True, truncation=True, max_length=96, return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            vecs = pooled.cpu().numpy()
            for (k, _), v in zip(chunk, vecs):
                fh.write(json.dumps({
                    "signal_id": k[0],
                    "assigned_topic_slug": k[1],
                    "embedding": [round(float(x), 6) for x in v],
                }) + "\n")
                written += 1
            fh.flush()
            print(f"  embedded {written}/{len(pending)}", file=sys.stderr)

    print(json.dumps({"out": str(args.out), "embedded": written, "model": args.model, "dim": int(vecs.shape[1]) if written else None}, indent=2))


if __name__ == "__main__":
    main()
