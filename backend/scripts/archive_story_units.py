#!/usr/bin/env python
"""Stage B — archive embeddings -> story units for the category robot.

Spec: docs/specs/2026-07-05-category-robot.md §4.2. The robot eats STORY
units, not raw signals; this turns the 6.9M archive vectors into per-day
story clusters, mirroring the live engine's snapshot methodology (daily
granularity; multi-day canonical events are re-grouped by the ROBOT's
event output — that is its job, not Stage B's).

Two subcommands (run in order):

  repartition   stream the 166 fp16 shards once, split vectors+meta by DAY
                into /Volumes/Ext/Atlas/Embeddings/by-day/ (raw fp16 .bin
                appended + .meta.jsonl). IO-bound, ~minutes.

  cluster       per day: sample cap (default 25k, same order of magnitude
                as the live snapshot pulls), HDBSCAN leaf (mcs 8), emit one
                unit per cluster: {label: medoid headline, samples,
                centroid fp32, n, first_seen=last_seen=day, top_cc}.
                Appends to units jsonl. Resumable (skips days already in
                the output). Run nice'd — daytime discipline.

Unit labels are the MEDOID headline ($0): the robot groups by centroid
structure; DeepSeek naming happens once per robot GROUP, not per unit.

Usage:
  python backend/scripts/archive_story_units.py repartition
  nice -n 15 python backend/scripts/archive_story_units.py cluster \
      [--cap 25000] [--mcs 8] [--out /Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

EMB_ROOT = Path("/Volumes/Ext/Atlas/Embeddings/openai-3-small")
DAY_ROOT = Path("/Volumes/Ext/Atlas/Embeddings/by-day")
DIM = 1536


def repartition() -> int:
    """INCREMENTAL desde 2026-08-25 (R1 del plan archivo-al-frente): el
    todo-o-nada con marcador congeló Stage-B en jul-03 — con el marcador
    presente los shards NUEVOS jamás se particionaban, y sin él se
    re-streameaba todo DUPLICANDO días. Ahora un manifest por-shard
    (.repartition-shards.json) procesa solo shards no vistos; el marcador
    viejo se honra una vez sembrando el manifest con los shards existentes
    a esa fecha (ya particionados)."""
    DAY_ROOT.mkdir(parents=True, exist_ok=True)
    done_marker = DAY_ROOT / ".repartition-done"
    manifest_path = DAY_ROOT / ".repartition-shards.json"
    all_shards = sorted(EMB_ROOT.glob("shard-*.npz"))
    if manifest_path.exists():
        done = set(json.loads(manifest_path.read_text()))
    elif done_marker.exists():
        done = {p.name for p in all_shards}
        manifest_path.write_text(json.dumps(sorted(done)))
        print(f"repartition: marcador legacy → manifest sembrado con "
              f"{len(done)} shards existentes", file=sys.stderr)
    else:
        done = set()
    shards = [p for p in all_shards if p.name not in done]
    if not shards:
        print("repartition: no new shards", file=sys.stderr)
        return 0
    handles: dict[str, tuple] = {}

    def get(day: str):
        if day not in handles:
            handles[day] = (open(DAY_ROOT / f"{day}.bin", "ab"),
                            open(DAY_ROOT / f"{day}.meta.jsonl", "a"))
        return handles[day]

    n = 0
    for si, sp in enumerate(shards):
        vecs = np.load(sp)["vecs"]  # (N,1536) fp16
        metas = [json.loads(l) for l in open(sp.parent / f"{sp.stem}.meta.jsonl")]
        assert len(metas) == len(vecs), f"meta/vec mismatch in {sp.name}"
        for v, m in zip(vecs, metas):
            day = m.get("date") or "unknown"
            fb, fm = get(day)
            fb.write(v.tobytes())
            fm.write(json.dumps(m, ensure_ascii=False) + "\n")
            n += 1
        if (si + 1) % 20 == 0:
            print(f"  {si+1}/{len(shards)} shards → {n} rows, "
                  f"{len(handles)} days", file=sys.stderr)
    for fb, fm in handles.values():
        fb.close(); fm.close()
    done |= {p.name for p in shards}
    manifest_path.write_text(json.dumps(sorted(done)))
    print(f"repartitioned {n} vectors into {len(handles)} day files "
          f"({len(shards)} new shards; manifest {len(done)} total)")
    return 0


def cluster(cap: int, mcs: int, out: Path, slice_spec: str | None,
            jobs: int) -> int:
    import hdbscan

    done_days = set()
    if out.exists():
        for line in open(out):
            try:
                done_days.add(json.loads(line)["day"])
            except Exception:  # noqa: BLE001
                continue
    days = sorted(p.stem for p in DAY_ROOT.glob("*.bin")
                  if p.stem != "unknown")
    if slice_spec:
        i, k = (int(x) for x in slice_spec.split("/"))
        days = [d for j, d in enumerate(days) if j % k == i]
    todo = [d for d in days if d not in done_days]
    print(f"{len(days)} days, {len(todo)} to cluster "
          f"(resume skips {len(done_days)})", file=sys.stderr)

    rng = np.random.default_rng(11)
    total_units = 0
    for day in todo:
        raw = np.fromfile(DAY_ROOT / f"{day}.bin", dtype=np.float16)
        V = raw.reshape(-1, DIM).astype(np.float32)
        metas = [json.loads(l) for l in open(DAY_ROOT / f"{day}.meta.jsonl")]
        if len(V) != len(metas):
            print(f"  {day}: vec/meta mismatch ({len(V)}/{len(metas)}), "
                  "skipped", file=sys.stderr)
            continue
        if len(V) > cap:
            idx = rng.choice(len(V), cap, replace=False)
            V, metas = V[idx], [metas[i] for i in idx]
        if len(V) < mcs * 3:
            with open(out, "a") as f:
                f.write(json.dumps({"day": day, "n_signals": len(V),
                                    "units": 0, "note": "too few rows"}) + "\n")
            continue
        labels = hdbscan.HDBSCAN(
            min_cluster_size=mcs, min_samples=4,
            cluster_selection_method="leaf", core_dist_n_jobs=jobs,
        ).fit_predict(V)
        units = 0
        with open(out, "a") as f:
            for lab in sorted(set(int(x) for x in labels) - {-1}):
                ii = np.where(labels == lab)[0]
                c = V[ii].mean(axis=0)
                c /= np.linalg.norm(c)
                sims = V[ii] @ c
                order = ii[np.argsort(-sims)]
                medoid = metas[int(order[0])]
                ccs = Counter(m.get("cc") for m in (metas[int(i)] for i in ii)
                              if m.get("cc"))
                f.write(json.dumps({
                    "day": day,
                    "label": medoid["headline"][:160],
                    "samples": [metas[int(i)]["headline"][:120]
                                for i in order[:3]],
                    "centroid": [round(float(x), 5) for x in c],
                    "n": int(len(ii)),
                    "cohesion": round(float(sims.mean()), 4),
                    "first_seen": day, "last_seen": day,
                    "top_cc": [c0 for c0, _ in ccs.most_common(3)],
                }, ensure_ascii=False) + "\n")
                units += 1
        total_units += units
        print(f"  {day}: {len(V)} rows → {units} units "
              f"(noise {(labels == -1).mean():.0%})", file=sys.stderr)
    print(f"done: +{total_units} units → {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("repartition")
    pc = sub.add_parser("cluster")
    pc.add_argument("--cap", type=int, default=15_000,
                    help="per-day sample cap (15k = the live snapshot pull size)")
    pc.add_argument("--mcs", type=int, default=8)
    pc.add_argument("--slice", default=None, metavar="I/K",
                    help="process only days where index %% K == I (parallel workers, "
                         "give each its own --out and merge after)")
    pc.add_argument("--jobs", type=int, default=4)
    pc.add_argument("--out", type=Path,
                    default=Path("/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl"))
    args = ap.parse_args()
    if args.cmd == "repartition":
        return repartition()
    return cluster(args.cap, args.mcs, args.out, args.slice, args.jobs)


if __name__ == "__main__":
    raise SystemExit(main())
