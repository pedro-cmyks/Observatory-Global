#!/usr/bin/env python3
"""Persistent emergent topic snapshot writer (Phase 2).

Same pipeline as `emergent_poc.py` (pull → clean → embed → HDBSCAN → gate
→ DeepSeek label) but writes survivors to the `emergent_clusters` table
and computes velocity vs the prior snapshot via centroid cosine match.

Designed to run from the off-iCloud mlvenv at the 6-hour snapshot
cadence (00 / 06 / 12 / 18 UTC) per the spec; launchd plist will be wired
in Phase 3.

Idempotent within a single run: writes one snapshot keyed by the
script's start time. Re-running creates a new snapshot row set with a
later timestamp; nothing is overwritten.

CLI:
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m backend.scripts.snapshot_emergent_topics \
      --window-hours 24 --max-signals 20000 \
      --min-cluster-size 20 --min-samples 10 \
      --gate docs/research/atlas-paper/phase-1-validation/models/2026-05-30-emergent-precision-gate-v1.json \
      --top-clusters 30 [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np

# Reuse the POC's pure helpers — they are stable and identical math.
from backend.scripts.emergent_poc import (
    _apply_gate,
    _build_embedder,
    _clean_and_dedupe,
    _cluster,
    _cluster_stats,
    _label_all,
    _load_gate,
    whiten_all_but_top,
)


CENTROID_MATCH_THRESHOLD = 0.85
# Cluster preview size persisted per snapshot. POC default is 8 (stdout
# friendly); the production snapshot persists more headlines so the thread
# focus panel + cluster-N theme detail can render richer evidence without
# re-running clustering.
SAMPLE_TOP_K = 24
DEFAULT_GATE = Path(
    "docs/research/atlas-paper/phase-1-validation/models/2026-05-30-emergent-precision-gate-v1.json"
)


# Unified Engine F2 (spec 2026-06-29-atlas-unified-engine §8): social signals
# ATTACH to topics as discussion members (assign_discussion_topics, kNN over the
# embeddings) but must NEVER SEED clusters — only press/institutional signals
# anchor the topic spine. Social is still embedded and still attaches; it is just
# kept OUT of the HDBSCAN seeding corpus so daily-life forum chatter cannot form
# or pollute clusters as F1 forum volume scales. A measured exception for
# high-signal forum events can flip this via the env knob.
_ALLOW_SOCIAL_SEED = os.getenv("ATLAS_CLUSTER_ALLOW_SOCIAL_SEED", "").strip().lower() in {
    "1", "true", "on", "yes",
}


def _social_seed_pred(alias: str = "") -> str:
    """SQL predicate that excludes source_family='social' from the seeding pull
    (empty when the measured-exception knob allows social to seed). `alias` is the
    table alias prefix ('s.' for the joined query, '' for the bare table)."""
    if _ALLOW_SOCIAL_SEED:
        return ""
    p = f"{alias}." if alias else ""
    return f" AND ({p}source_family IS NULL OR {p}source_family <> 'social')"


async def _pull_signals(conn: asyncpg.Connection, hours: int, max_n: int):
    return await conn.fetch(f"""
        SELECT id, headline, country_code, source_name, timestamp
        FROM signals_v2
        WHERE timestamp > NOW() - INTERVAL '{int(hours)} hours'
          AND headline IS NOT NULL
          AND length(headline) >= 20
          {_social_seed_pred()}
        ORDER BY timestamp DESC
        LIMIT $1
    """, max_n)


_PERSISTED_SELECT = """
    SELECT s.id, s.headline, s.country_code, s.source_name, s.timestamp,
           se.vec::text AS emb
    FROM signal_embeddings se
    JOIN signals_v2 s ON s.id = se.signal_id
    WHERE s.timestamp > NOW() - INTERVAL '{hours} hours'
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
      AND s.source_lang {lang_pred}
      {social_pred}
    ORDER BY s.timestamp DESC
    LIMIT $1
"""


async def _pull_embedded_stratified(
    conn: asyncpg.Connection, hours: int, max_n: int, nonenglish_cap: int,
):
    """#229 lever 1: cluster over the PERSISTED signal_embeddings corpus (no
    re-embed), stratified so the world's non-English voice is guaranteed a seat
    at the table instead of being crowded out by GDELT's English firehose in a
    latest-N-by-timestamp draw.

    Returns rows (id/headline/country_code/source_name/timestamp) and a parallel
    {id: vector} map. Takes ALL recent non-English embedded signals (up to
    nonenglish_cap), then fills the remainder with English/untagged.
    """
    h = int(hours)
    social_pred = _social_seed_pred("s")
    ne = await conn.fetch(
        _PERSISTED_SELECT.format(
            hours=h, social_pred=social_pred,
            lang_pred="IS NOT NULL AND s.source_lang NOT IN ('en','xx','un','und')"),
        nonenglish_cap)
    fill = max(max_n - len(ne), 0)
    en = await conn.fetch(
        _PERSISTED_SELECT.format(
            hours=h, social_pred=social_pred,
            lang_pred="IS NULL OR s.source_lang IN ('en','xx','un','und')"),
        fill) if fill else []
    return list(ne) + list(en)


async def _prior_snapshot_clusters(conn: asyncpg.Connection, before: datetime):
    """Fetch the clusters of the most recent prior snapshot for velocity.

    Returns list of dicts with n_signals + centroid_vec. Empty list when
    there is no prior snapshot (first run).
    """
    snap = await conn.fetchrow(
        """
        SELECT snapshot_at FROM emergent_clusters
        WHERE snapshot_at < $1
        ORDER BY snapshot_at DESC LIMIT 1
        """,
        before,
    )
    if not snap:
        return []
    rows = await conn.fetch(
        """
        SELECT n_signals, centroid_vec
        FROM emergent_clusters
        WHERE snapshot_at = $1 AND centroid_vec IS NOT NULL
        """,
        snap["snapshot_at"],
    )
    return [
        {
            "n_signals": int(r["n_signals"]),
            "centroid": np.asarray(r["centroid_vec"], dtype=np.float32),
        }
        for r in rows
    ]


def _compute_velocity(cluster: dict, kept_centroid: np.ndarray, prior: list) -> int | None:
    """Velocity = (current kept_size) - (matched prior n_signals).

    Match = most-similar prior centroid by cosine, threshold ≥ 0.85.
    Returns None if there is no prior snapshot at all (first run).
    Returns the full kept_size if no prior centroid matches (new cluster).
    """
    if not prior:
        return None
    pri_mat = np.vstack([p["centroid"] for p in prior])
    sims = pri_mat @ kept_centroid
    best = int(np.argmax(sims))
    if float(sims[best]) >= CENTROID_MATCH_THRESHOLD:
        return int(cluster["kept_size"] - prior[best]["n_signals"])
    return int(cluster["kept_size"])


def _row_top_countries(rows: list[dict], all_idxs: list[int]) -> list[str]:
    counts: Counter = Counter()
    for j in all_idxs:
        cc = rows[int(j)]["country_code"]
        if cc:
            counts[cc] += 1
    return [c for c, _ in counts.most_common(5)]


def _row_raw_sample(embs: np.ndarray, all_idxs: list[int], k: int = 8) -> list[int]:
    """Top-K from the full raw HDBSCAN cluster, by cosine to raw centroid."""
    idxs = np.asarray(all_idxs)
    members_emb = embs[idxs]
    centroid = members_emb.mean(axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-9)
    cos = members_emb @ centroid
    order = np.argsort(-cos)
    return [int(idxs[j]) for j in order[:k]]


def _kept_centroid(cluster: dict, embs: np.ndarray) -> np.ndarray:
    """Centroid of the kept_set members (post-gate)."""
    kept_ids = np.asarray(cluster["top_signal_idxs"])  # top-K of kept (refreshed by _apply_gate)
    # Use ALL kept indices, not just the top-K. Recover them by re-running
    # the gate decision is overkill; the kept set centroid produced by
    # _apply_gate was already used to rank. We reconstruct it cleanly from
    # the kept members the gate decided on.
    # _apply_gate stored only top_signal_idxs; that's the visible sample. For
    # the persisted centroid we use the same kept_size derived members,
    # which requires re-scoring. To avoid a second gate pass, we accept the
    # top_signal_idxs (kept_size>=10 by construction; top-K covers the
    # dense core). Persisted centroid is a representative summary, not a
    # statistically exact mean — good enough for cross-snapshot matching.
    members_emb = embs[kept_ids]
    centroid = members_emb.mean(axis=0)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-9)
    return centroid


_INSERT_SNAPSHOT_SQL = """
    INSERT INTO emergent_clusters (
        snapshot_at, snapshot_window_h, cluster_id, label, description,
        raw_signal_count, n_signals, gate_threshold, velocity, cohesion,
        top_country_codes, sample_signal_ids, raw_sample_ids,
        centroid_vec, vendor_agreement, vendor_labels
    ) VALUES (
        $1, $2, $3, $4, $5,
        $6, $7, $8, $9, $10,
        $11, $12, $13,
        $14, $15, $16::jsonb
    )
"""


def _prepare_snapshot_rows(
    *,
    snapshot_at: datetime,
    window_hours: int,
    clusters: list[dict],
    ds_labels: list[dict],
    embs: np.ndarray,
    rows: list[dict],
    prior: list,
    gate_threshold: float,
) -> list[tuple[Any, ...]]:
    """Materialize compact insert rows without mutating the database.

    Scoped snapshots can run for hours. Preparing each country's compact rows
    lets that runner retain only a few megabytes and commit the whole snapshot
    once every country has completed, instead of exposing partial snapshots.
    """
    rows_to_insert = []
    for c, dl in zip(clusters, ds_labels):
        kept_cen = _kept_centroid(c, embs)
        velocity = _compute_velocity(c, kept_cen, prior)
        raw_sample_local = _row_raw_sample(embs, c["all_idxs"], k=SAMPLE_TOP_K)
        # _cluster_stats / _apply_gate emit LOCAL row indices, not signal ids.
        # Translate to signals_v2.id before persisting so downstream readers
        # (e.g. /api/v2/theme/cluster-N) can JOIN signals_v2 by id directly.
        sample_signal_ids = [int(rows[i]["id"]) for i in c["top_signal_idxs"]]
        raw_sample_ids = [int(rows[i]["id"]) for i in raw_sample_local]
        rows_to_insert.append((
            snapshot_at,
            int(window_hours),
            int(c["cluster_id"]),
            dl.get("label") or "(no label)",
            dl.get("description"),
            int(c["raw_size"]),
            int(c["kept_size"]),
            float(gate_threshold),
            velocity,
            float(c["cohesion"]),
            _row_top_countries(rows, c["all_idxs"]),
            sample_signal_ids,
            raw_sample_ids,
            [float(x) for x in kept_cen.tolist()],
            "deepseek",
            json.dumps({"deepseek": dl}, ensure_ascii=False),
        ))
    return rows_to_insert


async def _insert_prepared_snapshot(
    conn: asyncpg.Connection,
    rows_to_insert: list[tuple[Any, ...]],
) -> int:
    if rows_to_insert:
        await conn.executemany(_INSERT_SNAPSHOT_SQL, rows_to_insert)
    return len(rows_to_insert)


async def _write_snapshot(
    conn: asyncpg.Connection,
    *,
    snapshot_at: datetime,
    window_hours: int,
    clusters: list[dict],
    ds_labels: list[dict],
    embs: np.ndarray,
    rows: list[dict],
    prior: list,
    gate_threshold: float,
):
    prepared = _prepare_snapshot_rows(
        snapshot_at=snapshot_at,
        window_hours=window_hours,
        clusters=clusters,
        ds_labels=ds_labels,
        embs=embs,
        rows=rows,
        prior=prior,
        gate_threshold=gate_threshold,
    )
    return await _insert_prepared_snapshot(conn, prepared)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Persistent emergent topic snapshot writer.")
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument("--max-signals", type=int, default=20000)
    ap.add_argument("--from-persisted", action="store_true",
                    help="#229: cluster over the persisted signal_embeddings corpus "
                         "(no re-embed), stratified to guarantee non-English voice.")
    ap.add_argument("--nonenglish-cap", type=int, default=8000,
                    help="With --from-persisted: max non-English embedded signals to "
                         "include before filling with English/untagged.")
    ap.add_argument("--min-cluster-size", type=int, default=20)
    ap.add_argument("--min-samples", type=int, default=10)
    ap.add_argument("--selection", choices=["leaf", "eom"], default="leaf")
    ap.add_argument("--whiten-k", type=int, default=int(os.getenv("ATLAS_CLUSTER_WHITEN_K", "0")),
                    help="All-but-top(k) whitening of the embeddings used for HDBSCAN "
                         "labeling ONLY (de-compresses e5's scale-pegged cosine; see "
                         "docs/research/embedding-whitening/2026-07-07-whitening-findings.md). "
                         "0 = OFF (default, current behavior). Reversible. Persisted "
                         "centroids + sample selection stay in RAW e5 space regardless — "
                         "serving/dossier/gate vectors are unchanged. NOTE (measured over 3 "
                         "samples): whitening does NOT reliably cross the recall/purity cliff "
                         "(that was a one-sample artifact); its reproducible effect is "
                         "clustering STABILITY — with selection=eom it resists the mega-blob "
                         "failure mode (holds purity ~1.0 where raw collapses to ~0.15) and "
                         "lowers noise ~10pp. Only k=1 helps (k>=2 hurts purity). Modest, not "
                         "a headline win. Do NOT default-on without a production A/B.")
    ap.add_argument("--top-clusters", type=int, default=30)
    ap.add_argument("--top-k-headlines", type=int, default=8)
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--min-kept", type=int, default=10)
    ap.add_argument("--skip-label", action="store_true",
                    help="HDBSCAN-only output; useful when iterating cluster params.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run the full pipeline but do not INSERT to emergent_clusters.")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    ds_key = os.environ.get("DEEPSEEK_API_KEY")
    if not ds_key and not args.skip_label:
        print("DEEPSEEK_API_KEY not set (or use --skip-label)", file=sys.stderr)
        sys.exit(2)
    if not args.gate.is_file():
        print(f"gate artifact not found: {args.gate}", file=sys.stderr)
        sys.exit(2)

    snapshot_at = datetime.now(timezone.utc)
    t0 = time.time()
    print(f"snapshot_at = {snapshot_at.isoformat()}  window={args.window_hours}h", file=sys.stderr)

    conn = await asyncpg.connect(db)
    emb_by_id: dict[int, list] | None = None
    try:
        if args.from_persisted:
            raw = await _pull_embedded_stratified(
                conn, args.window_hours, args.max_signals, args.nonenglish_cap)
            emb_by_id = {int(r["id"]): json.loads(r["emb"]) for r in raw}
        else:
            raw = await _pull_signals(conn, args.window_hours, args.max_signals)
    except Exception:
        await conn.close()
        raise
    rows = [dict(r) for r in raw]
    if emb_by_id is not None:
        for r in rows:
            r.pop("emb", None)
    print(f"  pulled {len(rows)}", file=sys.stderr)
    rows = _clean_and_dedupe(rows)
    print(f"  clean + dedupe: {len(rows)}", file=sys.stderr)

    if len(rows) < args.min_cluster_size * 2:
        print(f"too few rows ({len(rows)}) for clustering", file=sys.stderr)
        await conn.close()
        return

    if emb_by_id is not None:
        # #229: use the PERSISTED vectors (no re-embed). Rebuild the matrix in the
        # cleaned/deduped row order so embeddings stay aligned with rows.
        embs = np.array([emb_by_id[int(r["id"])] for r in rows], dtype=np.float32)
        print(f"  persisted embeddings {embs.shape} (no re-embed)", file=sys.stderr)
    else:
        print("embedding e5-base...", file=sys.stderr)
        embed, device = _build_embedder()
        texts = [f"passage: {r['headline']}" for r in rows]
        embs = embed(texts).astype(np.float32)
        print(f"  embeddings {embs.shape} on {device}", file=sys.stderr)

    # Whitening (if enabled) applies ONLY to the vectors HDBSCAN sees. Everything
    # downstream — _cluster_stats centroids, the precision gate, _kept_centroid,
    # _row_raw_sample — keeps using the RAW `embs`, so the persisted centroid_vec,
    # dossier neighbors, and gate scoring stay in the original e5 space. Whitening
    # changes only WHICH signals land in a cluster, never the vectors we store.
    cluster_input = embs
    if args.whiten_k > 0:
        cluster_input = whiten_all_but_top(embs, args.whiten_k)
        print(f"  whitened HDBSCAN input: all-but-top(k={args.whiten_k}) "
              f"(centroids/serving stay raw e5)", file=sys.stderr)
    print(
        f"clustering HDBSCAN ({args.min_cluster_size}/{args.min_samples}/{args.selection})...",
        file=sys.stderr,
    )
    labels = _cluster(cluster_input, args.min_cluster_size, args.min_samples, args.selection)
    n_noise = int((labels == -1).sum())
    raw_count = int(((labels != -1).any()) and (int(labels.max()) + 1))
    print(f"  {raw_count} raw clusters | {n_noise} noise ({100*n_noise/len(labels):.1f}%)", file=sys.stderr)

    all_clusters = _cluster_stats(labels, embs, rows, top_k=SAMPLE_TOP_K)
    if not all_clusters:
        print("no clusters", file=sys.stderr)
        await conn.close()
        return

    gate = _load_gate(args.gate)
    print(
        f"gate threshold={gate['_threshold']:.3f}  min_kept={args.min_kept}",
        file=sys.stderr,
    )
    gated = _apply_gate(all_clusters, embs, gate, args.min_kept, top_k=SAMPLE_TOP_K)
    print(f"  {len(gated)} survive after precision filter", file=sys.stderr)
    clusters = gated[: args.top_clusters]

    if args.skip_label:
        ds_labels = [{"label": "(no label)", "description": "", "confidence": 0.0} for _ in clusters]
    else:
        print("labeling via DeepSeek...", file=sys.stderr)
        ds_labels = await _label_all(clusters, rows, ds_key or "")

    if args.dry_run:
        print("--dry-run set; skipping INSERT.", file=sys.stderr)
        n_written = 0
    else:
        prior = await _prior_snapshot_clusters(conn, snapshot_at)
        async with conn.transaction():
            n_written = await _write_snapshot(
                conn,
                snapshot_at=snapshot_at,
                window_hours=args.window_hours,
                clusters=clusters,
                ds_labels=ds_labels,
                embs=embs,
                rows=rows,
                prior=prior,
                gate_threshold=float(gate["_threshold"]),
            )
        print(
            f"  wrote {n_written} clusters | prior snapshot had {len(prior)} clusters "
            f"for velocity matching",
            file=sys.stderr,
        )

    await conn.close()
    elapsed = time.time() - t0
    summary = {
        "snapshot_at": snapshot_at.isoformat(),
        "window_hours": args.window_hours,
        "rows_after_dedupe": len(rows),
        "raw_clusters": int(raw_count),
        "gated_clusters": int(len(gated)),
        "written": int(n_written),
        "elapsed_seconds": round(elapsed, 1),
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
