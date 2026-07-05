#!/usr/bin/env python3
"""Embed gold-growth corpus rows with OpenAI (train_scope_gate cache format).

Each output line: {"signal_id", "assigned_topic_slug", "embedding"} — the
(signal_id, slug) key G._load_embeddings expects. Text = "headline | label"
(train_scope_gate._texts, NO query prefix).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="text-embedding-3-small")
    args = ap.parse_args()

    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)

    rows = [json.loads(l) for l in args.corpus.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Archive rows occasionally carry scraped-garbage "headlines" thousands of
    # tokens long (OpenAI 400s at 8192). Real headlines fit in 500 chars; cap
    # hard — the gate never sees more than a headline's worth anyway.
    texts = [f"{(r.get('headline') or '').strip()[:500]} | {(r.get('assigned_topic_label') or '').strip()}" for r in rows]

    vecs: list[list[float]] = []
    for i in range(0, len(texts), 256):
        chunk = texts[i:i + 256]
        for attempt in range(1, 6):
            try:
                resp = client.embeddings.create(model=args.model, input=chunk)
                break
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
        print(f"embedded {len(vecs)}/{len(texts)}", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r, v in zip(rows, vecs):
            f.write(json.dumps({
                "signal_id": r["signal_id"],
                "assigned_topic_slug": r["assigned_topic_slug"],
                "embedding": v,
            }) + "\n")
    print(f"{len(vecs)} embeddings -> {args.out}")


if __name__ == "__main__":
    main()
