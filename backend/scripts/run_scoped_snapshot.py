"""R1 — scoped per-country emergent snapshot writer (#229).

R0 proved (read-only) that clustering WITHIN each country lifts recall ~5.4×
system-wide (~54× more narratives) vs a single global HDBSCAN pass. This is the
PRODUCTION version: it actually FORMS the scoped topics and writes them.

Reuses the proven snapshot pipeline verbatim (clean/dedupe → HDBSCAN → precision
gate → DeepSeek label → _write_snapshot) — the ONLY change vs
snapshot_emergent_topics.py is the pull is scoped per-country and every country's
clusters land under ONE shared snapshot_at with globally-unique cluster_ids, so
the existing project_dynamic_topics folds them into dynamic_topics with the #224
anchor-guard as one coherent snapshot (one lifecycle tick).

Writes emergent_clusters ONLY. Run project_dynamic_topics separately afterwards
(so the write can be inspected before it reaches serving). Reversible: it is a new
snapshot_at; reverting = re-project the prior snapshot.

Run (repo root, M1 ML env, off-peak — heavy + DeepSeek labeling):
  # test first:
  python -m backend.scripts.run_scoped_snapshot --countries US,CN --dry-run
  python -m backend.scripts.run_scoped_snapshot --countries US,CN         # writes 2
  # then all:
  python -m backend.scripts.run_scoped_snapshot --min-embedded 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

import asyncpg
import numpy as np

from backend.scripts.emergent_poc import (
    _apply_gate, _clean_and_dedupe, _cluster, _cluster_stats, _label_all, _load_gate,
)
from backend.scripts.snapshot_emergent_topics import (
    SAMPLE_TOP_K, DEFAULT_GATE, _prior_snapshot_clusters, _write_snapshot,
)

_ID_OFFSET = 100000  # per-country cluster_id block (>> max clusters/country)

_COUNTRIES = """
    SELECT s.country_code, COUNT(*) AS n
    FROM signal_embeddings e JOIN signals_v2 s ON s.id = e.signal_id
    WHERE s.country_code IS NOT NULL AND s.country_code <> 'XX'
      AND s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    GROUP BY s.country_code HAVING COUNT(*) >= $2
    ORDER BY n DESC
"""
_FETCH = """
    SELECT s.id, s.headline, s.country_code, s.source_name, s.timestamp,
           se.vec::text AS emb
    FROM signal_embeddings se JOIN signals_v2 s ON s.id = se.signal_id
    WHERE s.country_code = $1
      AND s.timestamp > NOW() - ($2::int * INTERVAL '1 hour')
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    ORDER BY s.timestamp DESC
    LIMIT $3
"""


def _parse_vec(t: str) -> list[float]:
    return [float(x) for x in t.strip().lstrip("[").rstrip("]").split(",") if x]


async def _country_clusters(conn, cc, hours, cap, mcs, ms, gate, min_kept, top_n):
    """Scoped pull → cluster → gate → top-N. Returns (clusters, embs, rows) or None."""
    recs = await conn.fetch(_FETCH, cc, hours, cap)
    if len(recs) < mcs * 2:
        return None
    emb_by_id = {int(r["id"]): _parse_vec(r["emb"]) for r in recs}
    rows = _clean_and_dedupe([{k: r[k] for k in
                               ("id", "headline", "country_code", "source_name", "timestamp")}
                              for r in recs])
    if len(rows) < mcs * 2:
        return None
    embs = np.array([emb_by_id[int(r["id"])] for r in rows], dtype=np.float32)
    labels = _cluster(embs, mcs, ms, "leaf")
    all_clusters = _cluster_stats(labels, embs, rows, top_k=SAMPLE_TOP_K)
    if not all_clusters:
        return None
    gated = _apply_gate(all_clusters, embs, gate, min_kept, top_k=SAMPLE_TOP_K)
    clusters = gated[:top_n]
    if not clusters:
        return None
    return clusters, embs, rows


async def main() -> None:
    ap = argparse.ArgumentParser(description="R1: scoped per-country snapshot writer.")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--min-embedded", type=int, default=100)
    ap.add_argument("--per-country-cap", type=int, default=6000)
    ap.add_argument("--top-per-country", type=int, default=15)
    ap.add_argument("--mcs", type=int, default=5)
    ap.add_argument("--ms", type=int, default=2)
    ap.add_argument("--min-kept", type=int, default=8)
    ap.add_argument("--gate", default=str(DEFAULT_GATE))
    ap.add_argument("--countries", default="", help="comma list to restrict (test)")
    ap.add_argument("--limit-countries", type=int, default=0, help="only first N (test)")
    ap.add_argument("--skip-label", action="store_true", help="headline fallback labels")
    ap.add_argument("--dry-run", action="store_true", help="no INSERT")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr); sys.exit(2)
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not ds_key and not args.skip_label:
        print("DEEPSEEK_API_KEY not set (or --skip-label)", file=sys.stderr); sys.exit(2)
    from pathlib import Path
    gate = _load_gate(Path(args.gate))

    snapshot_at = datetime.now(timezone.utc)
    t0 = time.time()
    conn = await asyncpg.connect(db)
    await conn.execute("SET statement_timeout = '600s'")
    try:
        if args.countries:
            ccs = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
        else:
            rows = await conn.fetch(_COUNTRIES, args.hours, args.min_embedded)
            ccs = [r["country_code"] for r in rows]
            if args.limit_countries:
                ccs = ccs[: args.limit_countries]
        prior = await _prior_snapshot_clusters(conn, snapshot_at)
        print(f"snapshot_at={snapshot_at.isoformat()} · {len(ccs)} countries · "
              f"top{args.top_per_country}/country · dry_run={args.dry_run}", file=sys.stderr)

        total_written = total_clusters = done = failed = 0
        base = 0
        for cc in ccs:
            done += 1
            try:
                res = await _country_clusters(conn, cc, args.hours, args.per_country_cap,
                                              args.mcs, args.ms, gate, args.min_kept,
                                              args.top_per_country)
            except Exception as ex:
                failed += 1
                print(f"  [{done}/{len(ccs)}] {cc}: FETCH/CLUSTER failed ({ex})",
                      file=sys.stderr, flush=True)
                continue
            if res is None:
                print(f"  [{done}/{len(ccs)}] {cc}: no gated clusters", file=sys.stderr, flush=True)
                base += _ID_OFFSET
                continue
            clusters, embs, rows = res
            for i, c in enumerate(clusters):
                c["cluster_id"] = base + i
            base += _ID_OFFSET
            if args.skip_label:
                ds_labels = [{"label": (rows[c["top_signal_idxs"][0]]["headline"] or cc)[:90],
                              "description": "", "confidence": 0.0} for c in clusters]
            else:
                ds_labels = await _label_all(clusters, rows, ds_key)
            total_clusters += len(clusters)
            if not args.dry_run:
                async with conn.transaction():
                    total_written += await _write_snapshot(
                        conn, snapshot_at=snapshot_at, window_hours=args.hours,
                        clusters=clusters, ds_labels=ds_labels, embs=embs, rows=rows,
                        prior=prior, gate_threshold=gate["_threshold"])
            lbls = ", ".join((d.get("label") or "?")[:24] for d in ds_labels[:2])
            print(f"  [{done}/{len(ccs)}] {cc}: n={len(rows)} clusters={len(clusters)} "
                  f"e.g. [{lbls}]", file=sys.stderr, flush=True)
    finally:
        await conn.close()

    print(f"\nR1 DONE: snapshot_at={snapshot_at.isoformat()} · {total_clusters} clusters "
          f"formed, {total_written} written{' (DRY)' if args.dry_run else ''} · "
          f"{failed} failed · {round(time.time()-t0)}s")
    if not args.dry_run and total_written:
        print("NEXT: run project_dynamic_topics to fold this snapshot into dynamic_topics "
              "(then it serves). Inspect emergent_clusters for this snapshot_at first.")


if __name__ == "__main__":
    asyncio.run(main())
