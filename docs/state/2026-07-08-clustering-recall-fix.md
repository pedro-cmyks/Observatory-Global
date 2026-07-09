# 2026-07-08 — Clustering → thread recall fix (#229): the coverage unlock

**Goal.** Turn the recovered embedding substrate (`signal_embeddings` 231K,
+67K/24h) into actual served narrative threads. Baseline: **30 active
dynamic_topics**, story coverage **0.05%** (75 of 149,290 24h signals in an
active dynamic-topic member). Branch `v3-intel-layer`, M1 `mlvenv`, DB under
live embedder load throughout (queries kept light).

## Measure-first diagnosis (the money question, answered honestly)

Coverage = `count(distinct signal_id in active dynamic-topic members, 24h) /
count(signals, 24h)`. It is gated by **three multiplicative caps**, not one:

| Cap | Mechanism | Evidence |
|-----|-----------|----------|
| **A. Assignment window** | `build_unified_topics` pulls `LIMIT 15000` of ~149K signals/24h → ceiling ~10% *before* anything else | log `centroids=127 signals=15000 … coverage 83.2%`; the 15K newest-embedded span only ~4h |
| **B. Promotion gate** | raw-e5 student `noise_rate < 0.50` blocks real high-cohesion stories; only 30 topics reach `active` | funnel below |
| **C. Staleness / cadence** | build runs 3×/day; active-member 24h coverage decays between runs; only pass-1 hits *active* centroids | 796 dynamic-topic members in 24h total, only 75 in active topics |

### The promotion funnel (868 candidates → 0 promotable under the old gate)

```
868 candidates
→ 219 volume ≥ 30            (candidates already have volume: avg 83 signals)
→ 192 + persist ≥ 2          (avg 3 snapshots)
→ 192 + cohesion ≥ 0.50      (ALL candidates cohesion 0.9–1.0 — saturated/tight)
→ 145 + not roundup
→   0 + noise_rate < 0.50    ← THE WALL. all 145 sit at noise ≥ 0.50
```

The blocker was **not** `volume_min`/`persist_min` (the #229/#224 suspicion) —
candidate volume and persistence are healthy. The wall is the **evidence-role
student noise gate**, computed in **raw (un-whitened) e5** space where cosine is
compressed. It over-flags real narratives: Venezuela Earthquake `noise 0.72`,
Albanian Anti-Government Protests `0.80`, Hezbollah `0.82`, European Heatwave
Deaths `0.88` — all blocked; every `active` topic sits at `noise 0.0–0.3`.

### Whitening tested as a purity replacement — DISPROVED (honest negative)

The plan was to replace the flaky raw noise gate with a **whitened-cohesion**
purity gate (`app/services/whitening.py`, k=1). Measured raw vs whitened
cohesion on a real-vs-junk panel:

| topic | raw_coh | whitened_coh | verdict |
|-------|--------:|-------------:|---------|
| Cepeda/Espriella (real, active) | 0.939 | **0.531** | real but LOWEST |
| Venezuela Earthquake (real) | 0.953 | 0.700 | real |
| Albanian Protests (real) | 0.964 | 0.766 | real |
| News Headlines Cluster (junk) | 0.958 | 0.707 | junk ≈ real |
| TV Program Listings (junk) | 0.945 | 0.725 | junk ≈ real |
| Joys of Joyscrolling (junk) | 0.972 | **0.844** | junk > all real |

Whitened cohesion does **not** separate real from junk: grab-bags (TV listings,
joyscrolling) are *topically tight*, while an evolving real story drifts and
scores low. **Whitening decompresses cluster FORMATION recall — it is not a
promotion purity signal.** The real purity mechanism is the **semantic
roundup/junk-label guard**, so that is what was strengthened.

## The fix

### 1. Promotion gate recalibration (`project_dynamic_topics.py`)
- `noise_max` 0.50 → **0.85** (default; reversible via `--noise-max`). Lets real
  stories through; TV Listings (0.98) / News Headlines Cluster (0.90) /
  Joyscrolling (0.96) stay blocked.
- **Strengthened junk-label guard** (`LISTING_PATTERNS` + `ROUNDUP_PATTERNS`):
  now catches `tv program listings`, `market trends`, `economic and market`,
  `joyscrolling`, bare `news headlines`, `news and culture`, `<X> News <Month>
  <Year>` — the generic desk/section digests the noise gate was incidentally
  catching. Verified it does NOT over-catch `Crime Headlines`, `Sports News`,
  real event labels.
- **`--regrade`**: a one-time gate-recalibration pass. `next_state` only
  reconsiders topics *seen this tick*, so a gate change never reaches the
  standing candidate pool. `--regrade` re-evaluates the whole population against
  the current gate, with a **recency guard** (`since_seen < stale_k`) so it
  promotes only currently-live stories the old gate wrongly blocked — it never
  resurrects dead ones (retired stays retired; a resolved election stays
  deprecated). No `TRUNCATE`, pure state change, reversible.

Result: `--regrade` promoted **87 → 117 active** (from 30), 0 demotions, junk
held out (79 roundups, 105 high-noise stay non-active).

### 2. Assignment cap raise + chunked fetch (`build_unified_topics.py`)
- `--max-signals` default now reads env `ATLAS_UNIFIED_MAX_SIGNALS` (was hard
  15000). This is the coverage-ceiling lever: the numpy assign is O(n·centroids)
  and cheap; cost is the embedding fetch + residual HDBSCAN. Raising it assigns a
  much larger fresh slice, and with **117 active centroids** (vs 30) pass-1 lands
  far more fresh signals in *active* topics.
- **Chunked fetch** (`_load_signals`): a single fetch of ~768-dim vectors for a
  large cap exceeds the pooler statement timeout on a loaded DB (measured: 15k
  ok, 50k/60k both *cancelled*). Rewrote as two-phase keyset pagination — pull
  the id list (light), hydrate vectors in 8k id-chunks — so every statement is
  short and **any cap is safe regardless of DB load**. This is what made the 60k
  build complete under live embedder load.
- `SET statement_timeout=600s` on the build connection (belt-and-braces).

## Before / after (MEASURED)

| metric | baseline | after regrade + 15k build | after regrade + 60k build |
|--------|---------:|--------------------------:|--------------------------:|
| active dynamic_topics | 30 | 117 | 117 |
| story coverage (24h) | **0.05%** (75/149,290) | **1.81%** (2,697/148,838) | **8.71%** (12,938/148,504) |

**172× coverage jump** (0.05% → 8.71%). Three changes compound:
1. **regrade** widened the active-centroid set 30 → 117 (the pass-1 target);
2. **fresh build** re-ran pass-1 against those 117 centroids;
3. **60k cap** (via chunked fetch) let the build consider 60,000 fresh signals
   instead of 15,000 → 52,283 pass-1 assigned (88% window coverage).

The 15k step alone gave 36× (2,697); raising the cap to 60k pushed it to 8.71%,
past the "several %" target. Purity held at 60k: 117 active, cohesion 0.94–0.96,
**0 roundups, no blob**.

### Purity held (no #224 black-hole)
All 117 active topics: cohesion **0.94–0.98**, **0 roundups**. #224 blobs are
0.49-purity mega-clusters; nothing here is remotely that. Real stories dominate
the active set: Ukraine War Updates (2,625, noise 0.03), Venezuela Earthquake
Death Toll (556, 0.02), Albanian Anti-Government Protests (390), Securities Class
Action Lawsuits (374, 0.04), Marine Le Pen 2027 bid, DR Congo Ebola strike,
Pakistan cargo plane. Two borderline section-aggregates leaked (`Cronaca e
Incidenti` 0.64, `Côte d'Ivoire Public Service` 0.76) — coherent (0.95+), not
grab-bags; serving-side lifestyle/section damp handles them; extend the junk
guard if they surface. No blob.

## Colombia election (the acceptance case)

`id 52 "Cepeda Concedes to De la Espriella"` — 301 signals, 16 snapshots,
cohesion 0.96, **noise 0.19** — is a real, clean CO thread. It is
**`deprecated`**, not by the gate (its noise passed) but by **staleness**: the
election resolved (Cepeda conceded) and recent snapshots stopped re-matching it,
so it aged active→deprecated. Correct behaviour — the story is over. The recency
guard deliberately does not resurrect it.

## Recalibrated gate values (durable)

```
LifecycleConfig.noise_max = 0.85   (was 0.50)    # project_dynamic_topics.py
ATLAS_UNIFIED_MAX_SIGNALS  = 60000 (was 15000)   # build_unified_topics cap (run-embed-hot-corpus.sh)
build_unified_topics conn: SET statement_timeout=600s  (new — survives large fetch)
# unchanged: persist_min 2, cohesion_min 0.50, volume_min 30 (scoped 12), stale_k 2, retire_m 4
```

## Cron / durability
- `noise_max=0.85` is now the class default → the 02:30 emergent + 20:30 scoped
  projections promote seen stories under it automatically (self-sustaining; a
  live story re-matched each snapshot promotes on its own tick, no `--regrade`).
- `--regrade` was a **one-time** recalibration of the standing pool (30→117
  active); it is NOT in the cron (would over-promote on every tick). Re-run by
  hand only after another gate change.
- `run-embed-hot-corpus.sh` build now passes `--max-signals 60000`
  (`ATLAS_UNIFIED_MAX_SIGNALS`) so the nightly build assigns the full fresh
  slice off-peak.
- Both scripts synced to `~/AtlasLocalWorker/backend/scripts/`; runner edited in
  place (also needs repo-sync of `run-embed-hot-corpus.sh` if versioned).

## Follow-ups (mapped, not done)
- **Whitened assignment threshold** (the real recall lever): re-measure the
  `assign_threshold` (0.88 cliff) in *whitened* space so more true matches
  assign without admitting blobs — the whitening module's per-consumer
  re-measure. Formation-side, bigger task.
- Cadence: coverage decays between 3×/day builds; a more frequent light pass-1
  would hold 24h coverage higher.
```
