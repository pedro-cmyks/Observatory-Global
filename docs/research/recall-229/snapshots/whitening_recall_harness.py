#!/usr/bin/env python3
"""#229 whitening recall harness — OFFLINE, READ-ONLY (writes nothing to
dynamic_topics/emergent_clusters; SELECT-only against signal_embeddings/signals_v2).

Replicates the PRODUCTION clustering path (run_scoped_snapshot.py: per-country
HDBSCAN leaf, mcs=5/ms=2, precision gate, min_kept=8) over a bounded persisted
sample, and A/Bs:

  CONTROL   raw e5 fed to HDBSCAN (current production)
  WHITENED  all-but-top(k=1) whitening of the HDBSCAN input, fit PER-COUNTRY
            batch (exactly how --whiten-k would wire into run_scoped_snapshot;
            gate + centroids stay RAW e5, mirroring snapshot_emergent_topics.py)

x min_cluster_size in {5 (current), 4 (-25%), 3 (-50%)}  (ms=2 held).

Metrics per (space, mcs), aggregated across countries:
  raw clusters, gated clusters at kept>=8 (prod), kept>=12 (promotion
  volume_min proxy), kept>=3, kept-size p50/p90/max, mean cohesion of
  gated>=8, weighted noise fraction, total kept signals.

Plus a 10-cluster DeepSeek same-story spot judge (temp 0) on control-vs-
whitened at the production mcs.

Run (repo root on sys.path; mlvenv):
  ATLAS_HDBSCAN_JOBS=2 taskpolicy -b mlvenv/bin/python whitening_recall_harness.py
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time

import asyncpg
import httpx
import numpy as np

REPO = "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal"
sys.path.insert(0, REPO)

from backend.scripts.emergent_poc import (  # noqa: E402
    _apply_gate, _clean_and_dedupe, _cluster, _cluster_stats, _load_gate,
    whiten_all_but_top, DEEPSEEK_URL, DEEPSEEK_MODEL,
)
from pathlib import Path  # noqa: E402

GATE = Path(REPO) / ("docs/research/atlas-paper/phase-1-validation/models/"
                     "2026-05-30-emergent-precision-gate-v1.json")

HOURS = 168
MIN_EMBEDDED = 100        # production --min-embedded
PER_COUNTRY_CAP = 3000    # bound the sample
TOTAL_CAP = 30000         # ~30k bound so one run stays cheap
MAX_COUNTRIES = 60
MS = 2                    # production
MCS_SWEEP = [5, 4, 3]     # current, -25%, -50%
MIN_KEPT_PROD = 8         # production min_kept
SEED = 229

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


def _pct(a, q):
    return float(np.percentile(a, q)) if len(a) else 0.0


async def main() -> None:
    t0 = time.time()
    db = os.environ["DATABASE_URL"]
    gate = _load_gate(GATE)
    conn = await asyncpg.connect(db)
    await conn.execute("SET statement_timeout = '300s'")
    await conn.execute("SET default_transaction_read_only = on")

    ccs_rows = await conn.fetch(_COUNTRIES, HOURS, MIN_EMBEDDED)
    print(f"eligible countries: {len(ccs_rows)}", file=sys.stderr, flush=True)

    # Accumulate a bounded per-country sample.
    corpora: list[tuple[str, list[dict], np.ndarray]] = []
    total = 0
    for r in ccs_rows[:MAX_COUNTRIES]:
        if total >= TOTAL_CAP:
            break
        cc = r["country_code"]
        recs = await conn.fetch(_FETCH, cc, HOURS, PER_COUNTRY_CAP)
        if len(recs) < MCS_SWEEP[-1] * 2:
            continue
        emb_by_id = {int(x["id"]): _parse_vec(x["emb"]) for x in recs}
        rows = _clean_and_dedupe(
            [{k: x[k] for k in ("id", "headline", "country_code",
                                "source_name", "timestamp")} for x in recs])
        if len(rows) < 10:
            continue
        embs = np.array([emb_by_id[int(x["id"])] for x in rows], dtype=np.float32)
        corpora.append((cc, rows, embs))
        total += len(rows)
        print(f"  pulled {cc}: {len(rows)} (total {total})", file=sys.stderr, flush=True)
    await conn.close()
    print(f"sample: {len(corpora)} countries, {total} deduped rows "
          f"({time.time()-t0:.0f}s)", file=sys.stderr, flush=True)

    # Sweep. Per config: aggregate across countries.
    results: dict[tuple[str, int], dict] = {}
    judge_pool: dict[tuple[str, int], list[dict]] = {}
    for space in ("control", "whitened"):
        for mcs in MCS_SWEEP:
            key = (space, mcs)
            agg = dict(raw_clusters=0, ge3=0, ge8=0, ge12=0, kept_signals=0,
                       kept_sizes=[], cohesions=[], noise_num=0, noise_den=0)
            pool: list[dict] = []
            for cc, rows, embs in corpora:
                if len(rows) < mcs * 2:
                    continue
                cin = embs if space == "control" else whiten_all_but_top(embs, 1)
                labels = _cluster(cin, mcs, MS, "leaf")
                agg["noise_num"] += int((labels == -1).sum())
                agg["noise_den"] += len(labels)
                stats = _cluster_stats(labels, embs, rows, top_k=8)  # RAW embs
                agg["raw_clusters"] += len(stats)
                if not stats:
                    continue
                gated3 = _apply_gate(stats, embs, gate, 3, top_k=8)  # RAW embs
                for c in gated3:
                    ks = c["kept_size"]
                    agg["ge3"] += 1
                    if ks >= MIN_KEPT_PROD:
                        agg["ge8"] += 1
                        agg["kept_sizes"].append(ks)
                        agg["cohesions"].append(c["cohesion"])
                        agg["kept_signals"] += ks
                        pool.append({
                            "cc": cc, "kept": ks, "cohesion": c["cohesion"],
                            "ids": {int(rows[i]["id"])
                                    for i in c["top_signal_idxs"]},
                            "headlines": [rows[i]["headline"]
                                          for i in c["top_signal_idxs"]],
                        })
                    if ks >= 12:
                        agg["ge12"] += 1
            ks = np.array(agg["kept_sizes"]) if agg["kept_sizes"] else np.array([])
            results[key] = dict(
                space=space, mcs=mcs,
                raw_clusters=agg["raw_clusters"],
                gated_ge3=agg["ge3"], gated_ge8=agg["ge8"], gated_ge12=agg["ge12"],
                kept_signals=agg["kept_signals"],
                size_p50=round(_pct(ks, 50), 1), size_p90=round(_pct(ks, 90), 1),
                size_max=int(ks.max()) if len(ks) else 0,
                mean_cohesion=round(float(np.mean(agg["cohesions"])), 4)
                if agg["cohesions"] else None,
                noise_frac=round(agg["noise_num"] / max(agg["noise_den"], 1), 3),
            )
            judge_pool[key] = pool
            print(f"  [{space} mcs={mcs}] raw={agg['raw_clusters']} ge8={agg['ge8']} "
                  f"ge12={agg['ge12']} noise={results[key]['noise_frac']}",
                  file=sys.stderr, flush=True)

    # DeepSeek spot judge: 10 clusters from the BEST non-control variant
    # (max gated>=8, tiebreak cohesion), preferring clusters NEW vs the
    # control@production-mcs baseline (top-8 signal-id overlap < 0.5).
    variant_keys = [k for k in results if k != ("control", MCS_SWEEP[0])]
    best_key = max(variant_keys, key=lambda k: (
        results[k]["gated_ge8"], results[k]["mean_cohesion"] or 0.0))
    ctrl_sets: dict[str, list[set]] = {}
    for p in judge_pool.get(("control", MCS_SWEEP[0]), []):
        ctrl_sets.setdefault(p["cc"], []).append(p["ids"])

    def _is_new(p) -> bool:
        for s in ctrl_sets.get(p["cc"], []):
            if len(p["ids"] & s) / max(min(len(p["ids"]), len(s)), 1) >= 0.5:
                return False
        return True

    judge = {"best_variant": f"{best_key[0]} mcs={best_key[1]}", "clusters": []}
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if ds_key:
        rng = random.Random(SEED)
        pool = judge_pool.get(best_key, [])
        new_pool = [p for p in pool if _is_new(p)]
        old_pool = [p for p in pool if not _is_new(p)]
        rng.shuffle(new_pool)
        rng.shuffle(old_pool)
        picks = (new_pool + old_pool)[:10]
        prompt = ("These news headlines were grouped as ONE story cluster:\n\n{h}\n\n"
                  "Judge coherence. Return JSON only:\n"
                  '{{"same_story": true|false, "coherent_fraction": 0.0-1.0, '
                  '"note": "<10 words"}}')
        async with httpx.AsyncClient(timeout=60) as client:
            for p in picks:
                body = {"model": DEEPSEEK_MODEL, "temperature": 0,
                        "messages": [{"role": "user", "content": prompt.format(
                            h="\n".join(f"- {h}" for h in p["headlines"]))}]}
                try:
                    resp = await client.post(
                        DEEPSEEK_URL, json=body,
                        headers={"Authorization": f"Bearer {ds_key}"})
                    txt = resp.json()["choices"][0]["message"]["content"]
                    txt = txt.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    v = json.loads(txt)
                except Exception as ex:  # judge is best-effort
                    v = {"same_story": None, "coherent_fraction": None,
                         "note": f"judge-error {type(ex).__name__}"}
                judge["clusters"].append({
                    "cc": p["cc"], "kept": p["kept"],
                    "cohesion": round(p["cohesion"], 3),
                    "new_vs_control": _is_new(p),
                    "sample_headlines": p["headlines"][:3], **v})
                print(f"  judge {p['cc']} new={_is_new(p)}: {v}",
                      file=sys.stderr, flush=True)

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window_hours": HOURS, "countries": len(corpora), "rows": total,
        "config": {"ms": MS, "selection": "leaf", "min_kept_prod": MIN_KEPT_PROD,
                   "gate": str(GATE.name), "whiten": "all-but-top k=1, per-country fit",
                   "gate_space": "raw e5 (whitening only feeds HDBSCAN)"},
        "sweep": [results[(s, m)] for s in ("control", "whitened") for m in MCS_SWEEP],
        "judge": judge,
        "elapsed_s": round(time.time() - t0, 1),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
