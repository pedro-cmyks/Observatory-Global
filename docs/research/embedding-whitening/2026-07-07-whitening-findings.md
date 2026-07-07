# Whitening the e5 clustering substrate — measured across 3 samples

**Date:** 2026-07-07 · **Harness:** `backend/scripts/cluster_whiten_sweep.py`
(reuses `emergent_poc` pull/clean/cluster + `embedding_input_ablation` Gaza
probe) · **Compute:** M1 mlvenv, read-only, sampled · **Runs:** 3 independent
168h samples (~3.3k deduped rows / 390–512-row Gaza probe each), taken ~40 min apart.

## Question

The 2026-06-29 sweep found NO HDBSCAN config over raw e5 gives both high recall
and high purity: `leaf` shatters (high purity, ~70% noise); `eom`/big mcs
mega-blobs (high recall, low purity — the #224 black hole). The 2026-07-06/07
signal-separation harness (`measure_signal_separation.py`) diagnosed the cause:
raw e5 cosine is scale-**compressed** (same/diff-story medians ~0.916/0.788, both
pegged high) so HDBSCAN density can't separate structure — even though the
signal-pair AUC is already ~0.985. All-but-top(k=1) whitening (subtract the batch
mean, project out the top-1 PC, re-normalize) de-compresses it 4.4× at the
signal-pair level. **Does that translate to a config that clusters BOTH with high
recall AND high purity — the pair raw e5 could not?**

## Answer: NO dramatic cliff-crossing, but whitening STABILIZES clustering

The signal-pair separation is real and reproducible. It does **not** translate
into a reliable dramatic recall+purity jump at the cluster level. What it does,
reproducibly, is make density clustering **more stable** — purity-preserving and
blob-resistant, with a modest recall lift.

### Why the first read was wrong (measure-twice caught it)

Run A (one sample) showed `e5_whiten_k1 eom mcs=8 ms=1` at **recall 0.477 /
purity 0.96** vs raw's 0.09 — a 3.9× F1 jump that looked like a clean crossing.
It did **not reproduce**. The same config across three samples:

| config: `eom mcs=8 ms=1` | run A | run B | run C |
|---|---|---|---|
| **e5_raw** recall / purity | 0.09 / 0.878 | 0.067 / 1.0 | 0.068 / 1.0 |
| **e5_whiten_k1** recall / purity | **0.477** / 0.96 | 0.062 / 1.0 | 0.109 / 1.0 |
| noise: raw → whiten_k1 | 0.68 → 0.556 | 0.681 → 0.602 | 0.678 → 0.623 |

Whitened recall {0.477, 0.062, 0.109} is **high-variance** — 0.477 was the high
tail of a knife-edge distribution, not a stable operating point. Reading a single
sample as a cliff-crossing was the error; the third sample settled it.

### What reproduces across all three samples

1. **Whitening resists the mega-blob failure mode.** Raw e5 (and OpenAI) fall
   into the #224 black hole at the merge-prone corner — `e5_raw eom mcs=8 ms=3`
   gave **recall 0.756 / purity 0.146** (2 clusters, one swallowing everything)
   in run C, and `openai_raw eom mcs=8 ms=3` gave **0.995 / 0.132** (modal
   cluster 2938 of ~3276 rows). At that **same config on the same sample**,
   whitened-e5 (k=1) held **purity 1.0** (run C: raw 0.146 vs whiten_k1 1.0) —
   and it **never dropped below ~0.93 purity** in any config or run. The
   de-compressed geometry doesn't collapse into one giant cluster.
2. **Whitening lowers HDBSCAN noise ~6–12pp at held purity** (matched config,
   all 3 runs: raw ~0.68 → whitened ~0.55–0.62). More diverse coverage is pulled
   out of noise into pure clusters — without a blob.
3. **Recall is never worse, sometimes better** (whitened ≥ raw in all 3 runs at
   `eom mcs=8 ms=1`), but the size of the gain is unstable.
4. **k=1 only.** k=2/k=3 revert to raw-like recall AND can *hurt* purity
   (run B: `e5_whiten_k2 eom mcs=4` fell to **purity 0.45**). Projecting out the
   2nd/3rd PC removes real topical signal — k=1 is the sole useful setting,
   matching the signal-separation harness.

### Metric caveat

The Gaza probe treats "Gaza" as ONE story, but ~400 Gaza rows over 168h span many
distinct sub-stories (ceasefire / airstrikes / hostages / aid / ICC…). A *low*
single-cluster recall can therefore be *correct* fragmentation. That is exactly
why recall alone is unreliable here and why **purity + blob-resistance + noise**
(which reproduce) carry the conclusion, not the recall headline (which doesn't).
Cohesion is also not comparable raw-vs-whitened — whitening removes the shared
high-cosine component, so absolute within-cluster cosine is lower by construction.

## OpenAI comparison (same sample, run B)

Best joint config per space (preserved as `whiten-sweep-with-openai.json`, run B;
`whiten-sweep-latest.json` is the most recent e5-only run):

| space | sel | mcs | ms | recall | purity | noise | modal | note |
|---|---|---|---|---|---|---|---|---|
| e5_raw | eom | 8 | 1 | 0.067 | 1.0 | 0.681 | 26 | shatters |
| e5_whiten_k1 | eom | 8 | 1 | 0.062 | 1.0 | 0.602 | 27 | lower noise |
| openai_raw | eom | 8 | 3 | 0.995 | 0.132 | 0.094 | 2938 | **mega-blob** |
| openai_whiten_k1 | eom | 4 | 1 | 0.069 | 1.0 | 0.476 | 27 | no crossing |

OpenAI's larger native separation does **not** hand it a clean high-recall+high-
purity config either: its best-joint config is the mega-blob (0.995/0.132), and
whitening OpenAI doesn't cross the cliff (recall ~0.07). Whitening's benefit is
**e5-specific** — OpenAI isn't scale-compressed, so there's no shared direction to
project out. Net: paying OpenAI tokens buys no clustering win over free
whitened-e5 here, and OpenAI carries the same eom-blob risk.

## Production implication + what shipped

`snapshot_emergent_topics.py` clusters with **`leaf`, mcs=20, ms=10** today.
Whitening's reproducible value (blob-resistance + ~10pp less noise at held purity)
is **modest, not a headline win**, and appears with `eom`, not the current `leaf`.
So it is worth having as a reversible, measurable lever — **not** a default flip,
and to be validated by a full production A/B (`engine_ab_report.py`) before any
adoption, on the real params and multiple subjects.

Shipped (reversible, default-off):

- `emergent_poc.py`: `fit_whiten_all_but_top` / `apply_whiten_all_but_top` /
  `whiten_all_but_top` (batch-fit mean + top-k PC, project out, L2-renormalize).
  `_cluster` gained `ATLAS_HDBSCAN_JOBS` (cap core-dist parallelism; default -1 =
  unchanged) so mindful M1 sweeps don't spike system load.
- `snapshot_emergent_topics.py`: `--whiten-k` (env `ATLAS_CLUSTER_WHITEN_K`,
  **default 0 = OFF**). Whitening applies to the HDBSCAN **input only** — persisted
  `centroid_vec`, `_kept_centroid`, `_row_raw_sample`, and the gate all keep the
  RAW e5 vectors, so serving / dossier neighbors / gate scoring are unchanged.
  It changes only *which* signals land in a cluster.

**Bottom line:** the compressed-scale diagnosis holds and whitening is the right
mechanism against it, but the operational payoff is "clustering stability"
(purity-preserving, blob-resistant, lower noise), not the recall/purity cliff
being decisively crossed. Don't over-sell it. Next lever for coverage recall stays
scoped regional passes (#229 lever 2).

## Reproduce

```
set -a; source ~/AtlasLocalWorker/.env; set +a
ATLAS_HDBSCAN_JOBS=3 ~/AtlasLocalWorker/mlvenv/bin/python \
  -m backend.scripts.cluster_whiten_sweep --hours 168 --max-n 3000 [--openai]
# artifact: docs/research/embedding-whitening/whiten-sweep-latest.{json,md}
# NOTE: run it 2-3× — the eom-corner recall is knife-edge; a single sample misleads.
```
