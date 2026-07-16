#!/usr/bin/env python3
"""Emergent topic discovery POC.

Pulls last N hours of signals_v2 headlines, embeds with the local
multilingual-e5-base encoder (MPS), clusters with HDBSCAN, labels the
top clusters via DeepSeek chat, prints to stdout. No DB writes, no API
wiring — this is a research script to size the clustering quality
before any persistence.

Run from the off-iCloud mlvenv (asyncpg + torch + transformers +
hdbscan + sklearn + scipy):
  DATABASE_URL=... DEEPSEEK_API_KEY=... \\
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python -m scripts.emergent_poc \\
      --hours 24 --min-cluster-size 20

Skip labeling to iterate cluster params cheaply: ``--skip-label``.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import asyncpg
import httpx
import numpy as np
import hdbscan

# Headlines whose normalized form looks like a URL/CMS slug (e.g.
# "Doc Inhzsssh7003772.Shtml") leak into signals_v2 from a few RSS
# feeds. They cluster together and dominate noise. Drop them at intake.
URL_SLUG_RE = re.compile(r"\.(s?html?|php|aspx?)\b", re.IGNORECASE)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
EMBED_MODEL = "intfloat/multilingual-e5-base"
LABEL_PROMPT = """You are labeling a cluster of news headlines for a narrative intelligence brief.

Given these representative headlines:

{headlines}

Return JSON only, no other text:
{{
  "label": "3-5 word topic name in title case",
  "description": "one-line description of what this cluster is about",
  "confidence": 0.0-1.0
}}"""


def _build_embedder():
    """multilingual-e5-base on MPS, mean-pool + L2 normalize."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    model = AutoModel.from_pretrained(EMBED_MODEL)
    model.eval()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    @torch.no_grad()
    def embed(texts: list[str]) -> np.ndarray:
        outs: list[np.ndarray] = []
        for i in range(0, len(texts), 64):
            batch = texts[i : i + 64]
            enc = tok(batch, padding=True, truncation=True, max_length=96,
                      return_tensors="pt").to(device)
            hs = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            outs.append(pooled.cpu().numpy())
        return np.vstack(outs)

    return embed, device


async def _pull_signals(conn: asyncpg.Connection, hours: int, max_n: int):
    return await conn.fetch(f"""
        SELECT id, headline, country_code, source_name, timestamp
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND headline IS NOT NULL
          AND length(headline) >= 20
        ORDER BY timestamp DESC
        LIMIT $1
    """, max_n)


def _clean_headline(raw: str | None) -> str | None:
    """Decode HTML entities, drop URL-slug/junk headlines, return cleaned text.

    Many ingest paths leave headlines HTML-entity-encoded (`&#x041D;...`).
    Without decoding, e5 sees raw entity sequences instead of words, and
    clusters degrade. Also reject URL-style slugs (.shtml, .php) and rows
    with fewer than 3 whitespace tokens.
    """
    if not raw:
        return None
    h = html.unescape(raw).strip()
    if len(h) < 25:
        return None
    if URL_SLUG_RE.search(h):
        return None
    if len(h.split()) < 3:
        return None
    return h


def _clean_and_dedupe(rows: list[dict]) -> list[dict]:
    """Drop URL-slug junk + dedupe normalized cleaned headlines."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        cleaned = _clean_headline(r["headline"])
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        r["headline"] = cleaned
        out.append(r)
    return out


def fit_whiten_all_but_top(embs: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Fit the "all-but-top" whitening transform over a batch.

    Returns (mean, top) where `mean` is the batch centroid and `top` is the
    (k, dim) matrix of the top-k principal directions of the centered batch.
    Apply with `apply_whiten_all_but_top`.

    Rationale (2026-07-06/07 signal-separation harness): raw e5 cosine is
    scale-COMPRESSED — same-story vs diff-story medians sit at ~0.92/0.79, both
    pegged high, so HDBSCAN density can't separate structure even though the
    signal-pair AUC is already ~0.985. Subtracting the mean and projecting out
    the top-1 principal direction (the shared "news" component) de-compresses
    the geometry (same ~0.56 / diff ~0.00), which is exactly the within-vs-
    between contrast density clustering needs. See measure_signal_separation.py.
    """
    x = embs - embs.mean(axis=0, keepdims=True)
    mean = embs.mean(axis=0)
    if k <= 0:
        return mean, np.zeros((0, embs.shape[1]), dtype=embs.dtype)
    _, _, Vt = np.linalg.svd(x, full_matrices=False)
    return mean, Vt[:k]


def apply_whiten_all_but_top(embs: np.ndarray, mean: np.ndarray, top: np.ndarray) -> np.ndarray:
    """Center by `mean`, project out the `top` directions, L2-renormalize.

    Re-normalization matters: HDBSCAN uses euclidean distance, and the pipeline
    relies on euclidean-on-unit-sphere being monotone in cosine (_cluster's
    contract). After projecting out a direction the residual is no longer unit
    norm, so we renormalize to keep that equivalence."""
    x = embs - mean
    if top.shape[0] > 0:
        x = x - (x @ top.T) @ top
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (x / n).astype(np.float32)


def whiten_all_but_top(embs: np.ndarray, k: int) -> np.ndarray:
    """Convenience: fit + apply the all-but-top(k) whitening over one batch."""
    mean, top = fit_whiten_all_but_top(embs, k)
    return apply_whiten_all_but_top(embs, mean, top)


def _cluster(embs: np.ndarray, min_cluster_size: int, min_samples: int,
             selection_method: str = "leaf"):
    """HDBSCAN on L2-normalized e5 vectors.

    Note: e5 outputs are L2-normalized, so euclidean distance on them is
    a monotone function of cosine distance — HDBSCAN's default euclidean
    metric is fine and avoids the slower precomputed cosine path.

    selection_method:
      - 'leaf' (default): keeps fine sub-clusters, prevents a mega-blob
        from absorbing distinct sub-narratives. Best for news where many
        small coherent stories share generic "news" vibes in embedding
        space.
      - 'eom': excess-of-mass, returns the most stable clusters; can
        merge sub-narratives into one big stable parent.
    """
    # core-dist parallelism defaults to all cores (-1, unchanged for prod). Set
    # ATLAS_HDBSCAN_JOBS to cap it — used by the mindful research sweeps so a
    # 48-config grid on the M1 doesn't stack all-core HDBSCAN on top of Chrome/
    # iCloud/NLP and spike the load into the WindowServer-watchdog zone.
    try:
        _jobs = int(os.getenv("ATLAS_HDBSCAN_JOBS", "-1"))
    except ValueError:
        _jobs = -1
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method=selection_method,
        core_dist_n_jobs=_jobs,
    )
    labels = clusterer.fit_predict(embs)
    return labels


def _cluster_stats(labels: np.ndarray, embs: np.ndarray, rows: list[dict],
                   top_k: int = 8):
    by: dict[int, list[int]] = {}
    for i, lab in enumerate(labels):
        if lab == -1:
            continue
        by.setdefault(int(lab), []).append(i)
    clusters = []
    for cid, idxs_list in by.items():
        idxs = np.asarray(idxs_list)
        members_emb = embs[idxs]
        centroid = members_emb.mean(axis=0)
        centroid /= max(float(np.linalg.norm(centroid)), 1e-9)
        cos = members_emb @ centroid
        order = np.argsort(-cos)
        top_idxs = [int(idxs[j]) for j in order[:top_k]]
        countries: Counter = Counter()
        for j in idxs:
            cc = rows[int(j)]["country_code"]
            if cc:
                countries[cc] += 1
        clusters.append({
            "cluster_id": cid,
            "all_idxs": idxs.tolist(),
            "size": int(len(idxs)),
            "cohesion": float(cos.mean()),
            "top_signal_idxs": top_idxs,
            "top_countries": [c for c, _ in countries.most_common(5)],
        })
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters


def _load_gate(path: Path) -> dict:
    """Load emergent-precision-gate-v1 artifact + materialize numpy arrays."""
    g = json.loads(path.read_text(encoding="utf-8"))
    g["_mean"] = np.asarray(g["scaler_mean"], dtype=np.float64)
    g["_std"] = np.asarray(g["scaler_std"], dtype=np.float64)
    g["_coef"] = np.asarray(g["lr_coef"], dtype=np.float64)
    g["_intercept"] = float(g["lr_intercept"])
    g["_threshold"] = float(g["global_threshold"])
    return g


def _gate_scores(gate: dict, signal_embs: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    """Score each member against the cluster centroid via the persisted gate.

    Feature shape MUST match training:
      [signal_emb (768) || centroid_emb (768) || cos(signal, centroid) (1)]
    """
    c = centroid / max(float(np.linalg.norm(centroid)), 1e-9)
    centroid_mat = np.broadcast_to(c, signal_embs.shape).astype(np.float64)
    emb64 = signal_embs.astype(np.float64)
    cos_vec = np.sum(emb64 * centroid_mat, axis=1, keepdims=True)
    X = np.hstack([emb64, centroid_mat, cos_vec])
    Xs = (X - gate["_mean"]) / gate["_std"]
    z = Xs @ gate["_coef"] + gate["_intercept"]
    return 1.0 / (1.0 + np.exp(-z))


def _apply_gate(clusters: list[dict], embs: np.ndarray, gate: dict, min_kept: int,
                top_k: int = 8) -> list[dict]:
    """Score every cluster member, keep score >= threshold.

    Mutates each cluster dict in place: adds raw_size, kept_size,
    kept_ratio, gate_threshold; refreshes centroid/cohesion/top_signal_idxs
    from the kept_set when non-empty. Returns clusters with kept_size >=
    min_kept (drop the rest: too thin to honestly claim ≥90% precision).
    """
    thr = gate["_threshold"]
    survivors: list[dict] = []
    for c in clusters:
        idxs = np.asarray(c["all_idxs"])
        members_emb = embs[idxs]
        raw_centroid = members_emb.mean(axis=0)
        scores = _gate_scores(gate, members_emb, raw_centroid)
        keep_mask = scores >= thr
        kept_idxs = idxs[keep_mask]
        kept_embs = members_emb[keep_mask]

        c["raw_size"] = int(len(idxs))
        c["kept_size"] = int(keep_mask.sum())
        c["kept_ratio"] = round(c["kept_size"] / max(c["raw_size"], 1), 3)
        c["gate_threshold"] = thr
        # Full kept-member local indices (additive; consumers read explicit
        # keys). Needed by dry-run diagnostics that compare kept membership
        # across configurations — top_signal_idxs alone caps at top_k.
        c["kept_idxs"] = [int(i) for i in kept_idxs.tolist()]

        if c["kept_size"] < min_kept:
            continue  # drop — cannot honestly claim 90% precision on a thin keep

        # refresh centroid + ranking from kept_set
        new_c = kept_embs.mean(axis=0)
        new_c /= max(float(np.linalg.norm(new_c)), 1e-9)
        cos = kept_embs @ new_c
        order = np.argsort(-cos)
        c["cohesion"] = float(cos.mean())
        c["top_signal_idxs"] = [int(kept_idxs[j]) for j in order[:top_k]]
        survivors.append(c)
    survivors.sort(key=lambda c: c["kept_size"], reverse=True)
    return survivors


async def _label_one(client: httpx.AsyncClient, headlines: list[str], api_key: str) -> dict:
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": LABEL_PROMPT.format(
                    headlines="\n".join(f"- {h}" for h in headlines)
                ),
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 200,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = await client.post(DEEPSEEK_URL, json=body, headers=headers, timeout=30.0)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:  # pragma: no cover — POC tolerance
        return {"label": "(label failed)", "description": str(e)[:120], "confidence": 0.0}


async def _label_all(clusters: list[dict], rows: list[dict], api_key: str,
                      max_concurrency: int = 5) -> list[dict]:
    sem = asyncio.Semaphore(max_concurrency)
    async with httpx.AsyncClient() as client:
        async def task(c: dict) -> dict:
            async with sem:
                hls = [rows[i]["headline"] for i in c["top_signal_idxs"]]
                return await _label_one(client, hls, api_key)
        return await asyncio.gather(*(task(c) for c in clusters))


async def main() -> None:
    ap = argparse.ArgumentParser(description="Emergent topic discovery POC.")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--max-signals", type=int, default=20000,
                    help="Cap on signals pulled (HDBSCAN scales poorly above ~50k).")
    ap.add_argument("--min-cluster-size", type=int, default=20)
    ap.add_argument("--min-samples", type=int, default=5)
    ap.add_argument("--selection", choices=["leaf", "eom"], default="leaf",
                    help="HDBSCAN cluster_selection_method. 'leaf' keeps fine "
                         "sub-clusters; 'eom' merges into stable parents.")
    ap.add_argument(
        "--gate",
        type=Path,
        default=Path("docs/research/atlas-paper/phase-1-validation/models/2026-05-30-emergent-precision-gate-v1.json"),
        help="Path to the emergent precision-gate artifact (or empty string to skip).",
    )
    ap.add_argument("--no-gate", action="store_true",
                    help="Skip the precision gate (raw HDBSCAN clusters only).")
    ap.add_argument("--min-kept", type=int, default=10,
                    help="Drop clusters whose kept_set after the gate is < this.")
    ap.add_argument("--top-clusters", type=int, default=20)
    ap.add_argument("--top-k-headlines", type=int, default=8,
                    help="Top headlines per cluster fed to DeepSeek labeler.")
    ap.add_argument("--skip-label", action="store_true",
                    help="HDBSCAN-only output; useful while iterating cluster params.")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    ds_key = os.environ.get("DEEPSEEK_API_KEY")
    if not ds_key and not args.skip_label:
        print("DEEPSEEK_API_KEY not set (or use --skip-label)", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    print(f"pulling signals (last {args.hours}h, max {args.max_signals})...", file=sys.stderr)
    conn = await asyncpg.connect(db)
    try:
        raw = await _pull_signals(conn, args.hours, args.max_signals)
    finally:
        await conn.close()
    rows = [dict(r) for r in raw]
    print(f"  pulled {len(rows)}", file=sys.stderr)

    rows = _clean_and_dedupe(rows)
    print(f"  clean + dedupe: {len(rows)}", file=sys.stderr)
    if len(rows) < args.min_cluster_size * 2:
        print(f"too few rows ({len(rows)}) for clustering", file=sys.stderr)
        return

    print("embedding e5-base...", file=sys.stderr)
    embed, device = _build_embedder()
    texts = [f"passage: {r['headline']}" for r in rows]
    embs = embed(texts).astype(np.float32)
    print(f"  embeddings {embs.shape} on {device}", file=sys.stderr)

    print(
        f"clustering HDBSCAN (min_cluster_size={args.min_cluster_size}, "
        f"min_samples={args.min_samples}, selection={args.selection})...",
        file=sys.stderr,
    )
    labels = _cluster(embs, args.min_cluster_size, args.min_samples, args.selection)
    n_noise = int((labels == -1).sum())
    distinct = sorted(set(int(x) for x in labels if x != -1))
    n_clusters = len(distinct)
    print(
        f"  {n_clusters} clusters, {n_noise} noise "
        f"({100 * n_noise / len(labels):.1f}%)",
        file=sys.stderr,
    )
    if n_clusters == 0:
        print("no clusters — try lowering --min-cluster-size", file=sys.stderr)
        return

    all_clusters = _cluster_stats(labels, embs, rows)
    print(f"  {len(all_clusters)} raw clusters by size", file=sys.stderr)

    if args.no_gate or not args.gate or not Path(args.gate).is_file():
        if not args.no_gate and args.gate:
            print(f"  gate {args.gate} not found — skipping precision filter", file=sys.stderr)
        clusters = all_clusters[: args.top_clusters]
    else:
        gate = _load_gate(Path(args.gate))
        print(
            f"applying emergent precision gate (threshold={gate['_threshold']:.3f}, "
            f"min_kept={args.min_kept})...",
            file=sys.stderr,
        )
        gated = _apply_gate(all_clusters, embs, gate, args.min_kept)
        print(
            f"  {len(gated)} clusters survive (dropped {len(all_clusters) - len(gated)} "
            f"as kept_size < {args.min_kept})",
            file=sys.stderr,
        )
        clusters = gated[: args.top_clusters]
    print(f"  top {len(clusters)} for labeling", file=sys.stderr)

    if args.skip_label:
        ds_labels = [{"label": "(no label)", "description": "", "confidence": 0.0} for _ in clusters]
    else:
        print("labeling via DeepSeek (concurrency 5)...", file=sys.stderr)
        ds_labels = await _label_all(clusters, rows, ds_key or "")

    elapsed = time.time() - t0
    print(
        f"\n=== EMERGENT TOPICS POC "
        f"(last {args.hours}h, {len(rows)} signals, {elapsed:.1f}s) ===\n"
    )
    for c, dl in zip(clusters, ds_labels):
        label = dl.get("label", "(no label)")
        countries = ",".join(c["top_countries"]) or "n/a"
        if "kept_size" in c:
            size_str = f"kept={c['kept_size']}/{c['raw_size']} ({int(100*c['kept_ratio'])}%)"
        else:
            size_str = f"size={c['size']}"
        print(
            f"[#{c['cluster_id']:>3}] {label}  {size_str}  "
            f"cohesion={c['cohesion']:.3f}  countries={countries}"
        )
        desc = dl.get("description", "")
        if desc:
            print(f"      {desc}")
        for idx in c["top_signal_idxs"][:5]:
            r = rows[idx]
            print(
                f"      • [{(r.get('country_code') or '??'):>2}] "
                f"{(r['headline'] or '')[:110]}"
            )
        print()


if __name__ == "__main__":
    asyncio.run(main())
