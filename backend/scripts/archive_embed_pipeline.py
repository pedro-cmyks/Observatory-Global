#!/usr/bin/env python
"""Archive embedding pipeline — process ALL historical data, once, durably.

Pedro 2026-07-05: the category robot (and everything after it) must work
over the FULL history, not the hot window. The archive holds the raw
headlines (May-19+, ~772 gzip partitions) but no vectors. This pipeline
streams every partition, globally dedupes headlines, filters junk, embeds
with text-embedding-3-small (the engine's semantic space) and writes
durable shards to the external volume:

  /Volumes/Ext/Atlas/Embeddings/openai-3-small/
      shard-NNNN.npz      float16 (N,1536), L2-normalized
      shard-NNNN.meta.jsonl   one row per vector: sha1, headline, first
                              seen (year,month,day), country, lang
      manifest.json       partitions done, shards written, counts — the
                          pipeline is RESUMABLE (re-run continues)

Cost: ~38 tok/headline -> ~$0.02/M tok -> low single-digit dollars for the
full archive. Network-bound, safe next to the M1 crons.

Usage:
  python backend/scripts/archive_embed_pipeline.py \
      [--archive-root /Volumes/Ext/Atlas/Archive] \
      [--out-root /Volumes/Ext/Atlas/Embeddings/openai-3-small] \
      [--shard-size 50000] [--max-partitions 0]
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

OPENAI_MODEL = "text-embedding-3-small"

_JUNK = re.compile(
    r"^(digit:|in words:|story\d|doc \S+\.shtml)|^\W*$", re.I)


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(h).strip().lower())


def _is_junk(h: str) -> bool:
    if len(h) < 20 or len(h) > 500:
        return True
    if _JUNK.search(h):
        return True
    alpha = sum(1 for w in h.split() if sum(c.isalpha() for c in w) >= 3)
    return alpha < 3


def openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        chunk = [t[:2000] for t in texts[i : i + 512]]
        for attempt in range(1, 7):
            try:
                resp = client.embeddings.create(model=OPENAI_MODEL, input=chunk)
                break
            except Exception:  # noqa: BLE001
                if attempt == 6:
                    raise
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
    a = np.asarray(vecs, dtype=np.float32)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    return a.astype(np.float16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root", default="/Volumes/Ext/Atlas/Archive")
    ap.add_argument("--out-root",
                    default="/Volumes/Ext/Atlas/Embeddings/openai-3-small")
    ap.add_argument("--shard-size", type=int, default=50_000)
    ap.add_argument("--max-partitions", type=int, default=0,
                    help="0 = all; N = stop after N new partitions (smoke)")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    root = Path(args.archive_root)
    if not root.exists():
        print(f"archive root missing: {root}", file=sys.stderr)
        return 2
    out = Path(args.out_root)
    out.mkdir(parents=True, exist_ok=True)

    mpath = out / "manifest.json"
    manifest = (json.loads(mpath.read_text())
                if mpath.exists() else
                {"done_partitions": [], "shards": [], "n_vectors": 0,
                 "n_rows_seen": 0, "n_junk": 0, "n_dup": 0,
                 "model": OPENAI_MODEL})
    done = set(manifest["done_partitions"])

    # global dedupe index: sha1 of every embedded headline (rebuilt from
    # meta shards on resume — the manifest alone is not the truth)
    seen: set[str] = set()
    for meta in sorted(out.glob("shard-*.meta.jsonl")):
        with open(meta) as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["sha1"])
                except Exception:  # noqa: BLE001
                    continue
    print(f"resume: {len(done)} partitions done, {len(seen)} vectors on disk",
          file=sys.stderr)

    parts = sorted(glob.glob(str(root / "**/*.jsonl.gz"), recursive=True))
    todo = [p for p in parts if p not in done]
    if args.max_partitions:
        todo = todo[: args.max_partitions]
    print(f"{len(parts)} partitions total, {len(todo)} to process",
          file=sys.stderr)

    shard_idx = len(manifest["shards"])
    buf_texts: list[str] = []
    buf_meta: list[dict] = []

    def flush() -> None:
        nonlocal shard_idx, buf_texts, buf_meta
        if not buf_texts:
            return
        vecs = openai_embed(buf_texts)
        name = f"shard-{shard_idx:04d}"
        np.savez_compressed(out / f"{name}.npz", vecs=vecs)
        with open(out / f"{name}.meta.jsonl", "w") as f:
            for m in buf_meta:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        manifest["shards"].append(name)
        manifest["n_vectors"] += len(buf_texts)
        shard_idx += 1
        print(f"  wrote {name}: {len(buf_texts)} vectors "
              f"(total {manifest['n_vectors']})", file=sys.stderr)
        buf_texts, buf_meta = [], []

    t0 = time.time()
    for pi, p in enumerate(todo):
        m = re.search(r"year=(\d+)/month=(\d+)/day=(\d+)", p)
        ymd = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        try:
            with gzip.open(p, "rt", errors="replace") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except Exception:  # noqa: BLE001
                        continue
                    manifest["n_rows_seen"] += 1
                    h = d.get("headline") or ""
                    hn = _norm(h)
                    if _is_junk(hn):
                        manifest["n_junk"] += 1
                        continue
                    sha = hashlib.sha1(hn.encode()).hexdigest()
                    if sha in seen:
                        manifest["n_dup"] += 1
                        continue
                    seen.add(sha)
                    buf_texts.append(hn)
                    buf_meta.append({
                        "sha1": sha, "headline": h[:300], "date": ymd,
                        "cc": d.get("country_code") or d.get("country"),
                        "lang": d.get("source_lang"),
                    })
                    if len(buf_texts) >= args.shard_size:
                        flush()
        except Exception as exc:  # noqa: BLE001 — one bad partition never kills the run
            print(f"  partition failed (skipped, NOT marked done): {p}: {exc}",
                  file=sys.stderr)
            continue
        manifest["done_partitions"].append(p)
        if (pi + 1) % 20 == 0:
            mpath.write_text(json.dumps(manifest))
            rate = (pi + 1) / max(time.time() - t0, 1)
            print(f"[{pi+1}/{len(todo)}] rows={manifest['n_rows_seen']} "
                  f"uniq={len(seen)} junk={manifest['n_junk']} "
                  f"dup={manifest['n_dup']} ({rate:.1f} part/s)",
                  file=sys.stderr)

    flush()
    mpath.write_text(json.dumps(manifest))
    print(json.dumps({k: manifest[k] for k in
                      ("n_rows_seen", "n_vectors", "n_junk", "n_dup")},
                     indent=1))
    print(f"done: {len(manifest['done_partitions'])}/{len(parts)} partitions, "
          f"{manifest['n_vectors']} vectors in {len(manifest['shards'])} shards",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
