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
    whiten_all_but_top,
)
from backend.scripts.snapshot_emergent_topics import (
    SAMPLE_TOP_K,
    DEFAULT_GATE,
    _insert_prepared_snapshot,
    _prepare_snapshot_rows,
    _prior_snapshot_clusters,
)

_ID_OFFSET = 100000  # per-country cluster_id block (>> max clusters/country)

# Attempts per country before it counts as failed (transient Supabase
# connection drops on the heaviest fetches — US/EG class — killed three
# consecutive nightly passes via the all-or-nothing guard, 2026-07-13→16).
_COUNTRY_ATTEMPTS = 3

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
    LIMIT NULLIF($3, 0)
"""


def _parse_vec(t: str) -> list[float]:
    return [float(x) for x in t.strip().lstrip("[").rstrip("]").split(",") if x]


def _env_whiten_k() -> int:
    """ATLAS_CLUSTER_WHITEN_K → int; garbage/negative fall to 0 (off)."""
    try:
        k = int(os.environ.get("ATLAS_CLUSTER_WHITEN_K", "0"))
    except ValueError:
        return 0
    return k if k > 0 else 0


def _whiten_input(embs: np.ndarray, k: int) -> np.ndarray:
    """All-but-top(k) whitening for the HDBSCAN INPUT only.

    k=0 returns the SAME object (zero-cost, byte-identical default path).
    Whitening is a clustering-geometry lever (docs/research/recall-229/
    2026-07-16-whitening-recall-harness.md) — centroids, the precision gate
    and everything persisted stay in the RAW e5 space.
    """
    if k <= 0:
        return embs
    return whiten_all_but_top(embs, k)


async def _country_clusters(conn, cc, hours, cap, mcs, ms, gate, min_kept, top_n,
                            whiten_k: int = 0):
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
    labels = _cluster(_whiten_input(embs, whiten_k), mcs, ms, "leaf")
    all_clusters = _cluster_stats(labels, embs, rows, top_k=SAMPLE_TOP_K)
    if not all_clusters:
        return None
    gated = _apply_gate(all_clusters, embs, gate, min_kept, top_k=SAMPLE_TOP_K)
    clusters = gated if top_n <= 0 else gated[:top_n]
    if not clusters:
        return None
    return clusters, embs, rows


async def main() -> None:
    ap = argparse.ArgumentParser(description="R1: scoped per-country snapshot writer.")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--min-embedded", type=int, default=100)
    ap.add_argument("--per-country-cap", type=int, default=0,
                    help="operational diagnostic ceiling; 0 traverses every eligible signal")
    ap.add_argument("--top-per-country", type=int, default=0,
                    help="operational diagnostic ceiling; 0 keeps every gated cluster")
    ap.add_argument("--mcs", type=int, default=5)
    ap.add_argument("--ms", type=int, default=2)
    ap.add_argument("--min-kept", type=int, default=8)
    ap.add_argument("--gate", default=str(DEFAULT_GATE))
    ap.add_argument("--countries", default="", help="comma list to restrict (test)")
    ap.add_argument("--limit-countries", type=int, default=0, help="only first N (test)")
    ap.add_argument("--skip-label", action="store_true", help="headline fallback labels")
    ap.add_argument("--dry-run", action="store_true", help="no INSERT")
    ap.add_argument("--whiten-k", type=int, default=_env_whiten_k(),
                    help="all-but-top(k) whitening of the HDBSCAN input "
                         "(env ATLAS_CLUSTER_WHITEN_K; 0 = off, byte-identical)")
    ap.add_argument("--dump-json", default="",
                    help="write per-country cluster payloads (members, cohesion, "
                         "gate verdicts) to this path — diagnostic, works with --dry-run")
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
        scope = "all gated clusters" if args.top_per_country <= 0 else (
            f"top{args.top_per_country}/country"
        )
        corpus = "all eligible signals" if args.per_country_cap <= 0 else (
            f"latest {args.per_country_cap}/country"
        )
        print(f"snapshot_at={snapshot_at.isoformat()} · {len(ccs)} countries · "
              f"{scope} · {corpus} · dry_run={args.dry_run} · "
              f"whiten_k={args.whiten_k}", file=sys.stderr)

        total_written = total_clusters = done = failed = 0
        prepared_rows = []
        dump_countries: list[dict] = []
        base = 0
        for cc in ccs:
            done += 1
            # Resilience for the unattended ~1.5h run: a single transient
            # connection blip must not discard the whole staged snapshot (the
            # all-or-nothing guard below is for PERSISTENT failures). Each
            # country gets up to 3 attempts; every retry starts from a fresh
            # connection because "connection was closed in the middle of
            # operation" leaves the old one unusable.
            res = None
            last_ex: Exception | None = None
            for attempt in range(1, _COUNTRY_ATTEMPTS + 1):
                if conn.is_closed():
                    conn = await asyncpg.connect(db)
                    await conn.execute("SET statement_timeout = '600s'")
                try:
                    res = await _country_clusters(conn, cc, args.hours, args.per_country_cap,
                                                  args.mcs, args.ms, gate, args.min_kept,
                                                  args.top_per_country,
                                                  whiten_k=args.whiten_k)
                    last_ex = None
                    break
                except Exception as ex:
                    last_ex = ex
                    try:
                        if not conn.is_closed():
                            await conn.close()  # retry from a clean connection
                    except Exception:
                        pass
                    if attempt < _COUNTRY_ATTEMPTS:
                        print(f"  [{done}/{len(ccs)}] {cc}: attempt {attempt} failed ({ex}) "
                              f"— retrying", file=sys.stderr, flush=True)
                        await asyncio.sleep(5 * attempt)
            if last_ex is not None:
                failed += 1
                print(f"  [{done}/{len(ccs)}] {cc}: FETCH/CLUSTER failed after "
                      f"{_COUNTRY_ATTEMPTS} attempts ({last_ex})",
                      file=sys.stderr, flush=True)
                if args.dump_json:
                    dump_countries.append({"country": cc, "error": str(last_ex),
                                           "clusters": []})
                continue
            if res is None:
                print(f"  [{done}/{len(ccs)}] {cc}: no gated clusters", file=sys.stderr, flush=True)
                if args.dump_json:
                    dump_countries.append({"country": cc, "clusters": []})
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
            prepared_rows.extend(_prepare_snapshot_rows(
                snapshot_at=snapshot_at,
                window_hours=args.hours,
                clusters=clusters,
                ds_labels=ds_labels,
                embs=embs,
                rows=rows,
                prior=prior,
                gate_threshold=gate["_threshold"],
            ))
            lbls = ", ".join((d.get("label") or "?")[:24] for d in ds_labels[:2])
            print(f"  [{done}/{len(ccs)}] {cc}: n={len(rows)} clusters={len(clusters)} "
                  f"e.g. [{lbls}]", file=sys.stderr, flush=True)
            if args.dump_json:
                dump_countries.append({
                    "country": cc,
                    "n_signals": len(rows),
                    "clusters": [{
                        "cluster_id": int(c["cluster_id"]),
                        "label": (dl.get("label") or "")[:120],
                        "raw_size": c.get("raw_size"),
                        "kept_size": c.get("kept_size"),
                        "kept_ratio": c.get("kept_ratio"),
                        "gate_threshold": c.get("gate_threshold"),
                        "cohesion": c.get("cohesion"),
                        "members": [
                            {"signal_id": int(rows[i]["id"]),
                             "headline": rows[i]["headline"]}
                            for i in c.get("kept_idxs", c["all_idxs"])
                        ],
                    } for c, dl in zip(clusters, ds_labels)],
                })

        if args.dump_json:
            from pathlib import Path as _P
            payload = {
                "meta": {
                    "snapshot_at": snapshot_at.isoformat(),
                    "hours": args.hours,
                    "whiten_k": args.whiten_k,
                    "mcs": args.mcs, "ms": args.ms, "min_kept": args.min_kept,
                    "dry_run": args.dry_run,
                    "countries_attempted": len(ccs),
                    "failed": failed,
                    "elapsed_s": round(time.time() - t0),
                },
                "countries": dump_countries,
            }
            out = _P(args.dump_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"dump written: {out} ({len(dump_countries)} countries)",
                  file=sys.stderr, flush=True)

        if failed:
            raise RuntimeError(
                f"incomplete country pass: {failed}/{len(ccs)} countries failed; "
                "staged snapshot discarded before database commit"
            )
        if not args.dry_run and prepared_rows:
            if conn.is_closed():
                conn = await asyncpg.connect(db)
                await conn.execute("SET statement_timeout = '600s'")
            async with conn.transaction():
                total_written = await _insert_prepared_snapshot(conn, prepared_rows)
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
