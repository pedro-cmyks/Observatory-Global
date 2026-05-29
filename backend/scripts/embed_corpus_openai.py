#!/usr/bin/env python3
"""Embed consensus-corpus rows with a hosted multilingual encoder.

The Phase B scope gate's char-ngram features clear 90% precision at 64%
evidence-recall. The roadmap bet is that *semantic* embeddings (a model
that reads scope, not just character overlap) push coverage higher. This
script produces those embeddings via the OpenAI embeddings API
(`text-embedding-3-small`, multilingual) — hosted, so it sidesteps the
local torch/transformers iCloud-eviction stall entirely.

Embeds the string "headline | topic_label" per (signal_id, topic_slug)
assignment. Output is a JSONL cache keyed by (signal_id, assigned_topic_slug);
resume-safe so re-runs are free.

Required env: OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import openai
except ImportError as exc:  # pragma: no cover
    print(f"missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_BATCH = 512


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _text(row: dict[str, Any]) -> str:
    h = (row.get("headline") or "").strip()
    t = (row.get("assigned_topic_label") or "").strip()
    return f"{h} | {t}"


def _existing_keys(path: Path) -> set[tuple[int, str]]:
    if not path.exists():
        return set()
    seen: set[tuple[int, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        seen.add((int(r["signal_id"]), r.get("assigned_topic_slug")))
    return seen


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Embed consensus corpus with OpenAI embeddings.")
    ap.add_argument("--corpus", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl")
    ap.add_argument("--out", type=Path,
                    default=base / "labels/consensus/2026-05-28-3vendor-5k-openai-embeddings.jsonl")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    ap.add_argument("--binary-only", action="store_true",
                    help="Embed only rows with is_evidence in {0,1}.")
    args = ap.parse_args()

    api_key = __import__("os").environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    client = openai.OpenAI(api_key=api_key, timeout=60.0)

    rows = _read_jsonl(args.corpus)
    if args.binary_only:
        rows = [r for r in rows if r.get("is_evidence") in (0, 1)]
    # dedup by key
    by_key: dict[tuple[int, str], dict[str, Any]] = {
        (int(r["signal_id"]), r.get("assigned_topic_slug")): r for r in rows
    }
    skip = _existing_keys(args.out)
    pending = [(k, v) for k, v in by_key.items() if k not in skip]
    print(f"{len(by_key)} rows total, {len(skip)} cached, {len(pending)} to embed", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("a", encoding="utf-8") as fh:
        for i in range(0, len(pending), args.batch):
            chunk = pending[i : i + args.batch]
            texts = [_text(v) for _, v in chunk]
            for attempt in range(1, 6):
                try:
                    resp = client.embeddings.create(model=args.model, input=texts)
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt == 5:
                        print(f"batch {i} failed: {exc}", file=sys.stderr)
                        raise
                    time.sleep(2.0 * attempt)
            for (k, _), emb in zip(chunk, resp.data):
                fh.write(json.dumps({
                    "signal_id": k[0],
                    "assigned_topic_slug": k[1],
                    "embedding": emb.embedding,
                }) + "\n")
                written += 1
            fh.flush()
            print(f"  embedded {written}/{len(pending)}", file=sys.stderr)

    print(json.dumps({"out": str(args.out), "embedded": written, "model": args.model}, indent=2))


if __name__ == "__main__":
    main()
