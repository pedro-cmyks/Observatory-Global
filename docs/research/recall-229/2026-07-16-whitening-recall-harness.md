# #229 Whitening recall harness — per-country all-but-top(k=1), control vs whitened

**Date:** 2026-07-16 · **Status:** MEASURED, read-only — NO production wiring
**Inputs (versioned):** `snapshots/harness-out.json`, `snapshots/whitening_recall_harness.py`
**Question:** does whitening the HDBSCAN input (gate untouched, raw e5) lift the
gated-cluster yield toward the ≥80 active-topic substrate target without blob or
purity collapse?

## Method (honest description, from the script)

Offline, SELECT-only harness (`SET default_transaction_read_only = on`) that
replicates the R1 production clustering path (`run_scoped_snapshot.py`):
per-country pull over persisted `signal_embeddings ⋈ signals_v2` (168h window,
headline ≥20 chars), `_clean_and_dedupe`, HDBSCAN **leaf** selection with
`min_samples=2`, then the `2026-05-30-emergent-precision-gate-v1` gate.

- **Control** = raw L2-normalized e5 fed to HDBSCAN (current production).
- **Whitened** = `whiten_all_but_top(embs, k=1)` — all-but-top(k=1) whitening
  **fit per-country batch** (mean-center, remove the top principal component,
  re-normalize) — applied ONLY to the vectors HDBSCAN sees.
- **Everything downstream stays raw e5**: `_cluster_stats` (centroids,
  cohesion) and `_apply_gate` (precision gate scoring, per-signal keep) both
  receive the RAW embeddings. This mirrors exactly how `--whiten-k` is already
  plumbed in `snapshot_emergent_topics.py` (whitening is a clustering-geometry
  lever, never a scoring/identity space).
- Sweep: `min_cluster_size ∈ {5 (prod), 4, 3}` × {control, whitened}.

**Sample bounds (matter for reading absolutes):** per-country cap 3,000 rows,
total cap ~30k → the run covered the **top-11 countries by volume of 151
eligible** (US, IN, GB, RU, IR, IT, DE, ES, UA, TR, FR), 31,473 deduped rows.
Absolute cluster counts are NOT the production substrate count; the
**relative control→whitened deltas** are the finding. Runtime 2,423s on the M1
(`ATLAS_HDBSCAN_JOBS=2`, `taskpolicy -b`).

**Threshold mapping (stated honestly):**
- `gated_ge8` = clusters keeping ≥8 gate-kept signals — this is production
  `min_kept=8` in `run_scoped_snapshot.py`, i.e. the clusters that would be
  *written* to `emergent_clusters`.
- `gated_ge12` = kept ≥12 — a **proxy** for the promotion gate's
  `volume_min=12` (LifecycleConfig, recalibrated 2026-07-01). It is only a
  proxy: real promotion also requires `persist_min≥2` (persistence across
  snapshots), so `ge12` bounds what a single snapshot can feed toward the
  active pool, not what promotes that day.
- `gated_ge3` = a loose recall indicator below the write floor.

## Results — control vs whitened across the sweep

| space | mcs | raw clusters | gated ≥3 | gated ≥8 (write floor) | gated ≥12 (promo proxy) | kept signals | size p50 | p90 | max | mean cohesion (≥8) | noise frac |
|---|---|---|---|---|---|---|---|---|---|---|---|
| control | 5 | 713 | 510 | 159 | 58 | 2,033 | 10.0 | 20.2 | **137** | 0.9647 | 0.793 |
| control | 4 | 1,046 | 700 | 133 | 43 | 1,527 | 10.0 | 15.8 | 36 | 0.9663 | 0.773 |
| control | 3 | 1,617 | 967 | 95 | 27 | 1,058 | 9.0 | 14.0 | 36 | 0.9680 | 0.743 |
| **whitened** | **5** | **937** | **653** | **174** | **70** | **2,191** | 11.0 | 19.7 | **44** | 0.9613 | 0.719 |
| whitened | 4 | 1,304 | 837 | 142 | 52 | 1,683 | 10.0 | 17.0 | 38 | 0.9635 | 0.702 |
| whitened | 3 | 1,976 | 1,095 | 108 | 34 | 1,206 | 10.0 | 15.0 | 38 | 0.9655 | 0.674 |

**Deltas at the production config (mcs=5, ms=2, leaf):**

| metric | control | whitened | Δ |
|---|---|---|---|
| gated ≥8 (written clusters) | 159 | 174 | **+15 (+9.4%)** |
| gated ≥12 (volume_min proxy) | 58 | 70 | **+12 (+20.7%)** |
| kept signal mass | 2,033 | 2,191 | +158 (+7.8%) |
| max kept size (blob check) | 137 | 44 | **−93 (splits the one large cluster)** |
| mean cohesion of gated ≥8 (raw space) | 0.9647 | 0.9613 | −0.0034 |
| HDBSCAN noise fraction | 0.793 | 0.719 | −7.4 pp |

Two structural observations beyond the headline deltas:

1. **Lowering mcs is NOT the lever — whitening is.** In the control, dropping
   mcs 5→4→3 *shatters*: gated ≥8 falls 159→133→95 and ≥12 falls 58→43→27
   (more raw fragments, fewer survive the gate at size). Whitened mcs=5 beats
   every control config on both promotion-relevant counts.
2. **No blob risk — the opposite.** The only large cluster in the whole sweep
   is the control's 137-member cluster; whitening breaks it to max 44 while
   p50/p90 stay flat. Size distribution shifts are benign (p50 10→11).

## Coherence spot-judge (DeepSeek temp 0, 10 marginal clusters)

The judge ran **inside the harness** (script §"spot judge", seed 229): it
sampled 10 clusters from the best variant (**whitened mcs=5**), *preferring
clusters NEW vs control@mcs=5* (top-8 signal-id overlap < 0.5 against every
control cluster in the same country). **All 10 picks were new-vs-control** —
i.e. this is exactly the marginal recall whitening would add. Headlines judged
are the gate-kept top-8 samples per cluster (member ids retained in-harness;
the persisted JSON carries 3 sample headlines each). Cost < $0.01. No re-run
was needed; results below are verbatim from `snapshots/harness-out.json`.

| cc | kept | cohesion (raw) | same story | coherent frac | judge note |
|---|---|---|---|---|---|
| FR | 13 | 0.955 | ✅ | 1.0 | "All headlines report Musk endorsing Le Pen." — *"Elon Musk: Marine Le Pen es 'la última esperanza de Francia'"* |
| IT | 8 | 0.961 | ✅ | 0.9 | Ranucci attack wiretaps — *"Ranucci, le intercettazioni dell'arrestato: 'Male che vada mi faccio 30 anni'"* |
| IT | 9 | 0.961 | ✅ | 0.9 | Palazzo Chigi cuisine-masters award — *"Chicco Cerea premiato a Palazzo Chigi"* |
| RU | 8 | 0.964 | ❌ | **0.0** | "Unrelated topics: finance, crime, politics, auto sales, music." (Russian-language grab-bag) |
| TR | 8 | 0.967 | ✅ | 1.0 | 15 Temmuz commemoration events across cities |
| DE | 19 | 0.922 | ❌ | 0.6 | Merz-warns-US core + "Two headlines about defense and FIFA are unrelated." |
| FR | 12 | 0.962 | ✅ | 0.95 | Fontainebleau forest fire — *"Forêt de Fontainebleau : les pompiers cherchent à contenir les reprises de feu"* |
| TR | 10 | 0.977 | ✅ | 1.0 | Erdoğan anti-FETÖ statements |
| IR | 8 | 0.978 | ✅ | 0.9 | US strikes on Iranian targets in Hormuz (syndicated Spanish regionals) |
| GB | 10 | 0.952 | ✅ | 1.0 | Ann Widdecombe "targeted attack" — judge: *"All headlines report the same false event."* Coherent cluster of a possibly-false story; clustering ≠ veracity. |

**Marginal purity: 8/10 same-story, mean coherent_fraction 0.825.** The
marginal clusters are largely REAL stories production currently misses —
including non-English regional stories squarely in the wedge (Ranucci, 15
Temmuz, Fontainebleau, Hormuz-in-Spanish). Two failure cases:

- **RU grab-bag (coherent 0.0 at raw cohesion 0.964)** — the important
  negative. In a language-monoculture batch, removing the top PC can strip the
  shared-language/style direction that raw cosine leans on, and the leftover
  residue clusters spuriously — while raw-space cohesion AND the raw-space
  gate still read it as tight. Raw cohesion is an unreliable purity signal for
  whitened-formed clusters in monoculture batches. This is the class a gold
  gate must count.
- **DE 0.6** — a real core with 2 stragglers; garden-variety attach noise, the
  gate class we already live with.

n=10 is a directional spot-judge, not a calibration; it bounds marginal purity
at roughly 80% same-story (mean member coherence ~0.83), below the pristine
core (raw cohesion ~0.96 suggests near-1.0 for control-shared clusters) but
far above junk.

## Honest read

**Yes — within this sample, whitening lifts gated-cluster yield toward the ≥80
target without blob or purity collapse, at a measurable marginal-purity cost
that needs a gold gate before cutover.**

- The promotion-relevant count (≥12 proxy) rises **+20.7%** and the written
  count (≥8) **+9.4%** at the exact production config — and this is on the
  top-11 highest-volume countries only, where control is strongest; the full
  production pass runs ~150 countries where thin-country recall may benefit
  more (unmeasured — do not assume, measure in the dry-run).
- Cohesion cost is nominal in raw space (−0.0034) and the max-size check goes
  the *right* way (137→44). Noise fraction drops 7.4 pp — whitening genuinely
  de-compresses density structure for HDBSCAN, consistent with the 2026-07-06
  separation measurements (centroid gap 0.04→0.31, AUC 0.80→0.87).
- BUT the spot-judge shows raw-space cohesion overestimates coherence for
  whitened-formed clusters (RU: judged 0.0 at cohesion 0.964). ~10-20% of the
  marginal clusters may be incoherent. Since the marginal clusters are +15 of
  174 written, the system-level purity dilution is small (~1-2% of written
  clusters), but the promotion pipeline would carry some of them upward.
- Context: the 2026-07-07 whitening findings
  (`docs/research/embedding-whitening/2026-07-07-whitening-findings.md`,
  referenced in the `--whiten-k` help text) concluded whitening "does NOT
  reliably cross the recall/purity cliff" — that was measured on **global**
  samples. This harness is the **per-country scoped** regime (R1), where the
  per-batch fit is better conditioned; the two results are about different
  regimes, not a contradiction. Both stand.

## Risks

1. **Per-country fit stability / drift.** The transform is re-fit per batch
   per run: the top PC direction depends on that window's corpus, so cluster
   *boundaries* vary more run-to-run than raw. Identity continuity is safe by
   construction — centroids, gate, and resurrection matching all stay in raw
   e5 — but topic churn (dissolve/re-form at the margins) may rise. Watch
   lifecycle metrics on any trial.
2. **Small-batch fit.** Countries near `--min-embedded 100` give a noisy top-PC
   estimate; one syndicated mega-story can BE the top PC and get its
   within-story variance amplified. k=1 is conservative, but the harness only
   sampled ≥2,700-row countries — thin-country behavior is unmeasured.
3. **Gate-space mismatch (the RU class).** The precision gate scores in raw
   e5; whitened-formed groupings can pass it while being incoherent
   (monoculture batches especially). The gate was trained on raw-space cluster
   formation; its calibration does not automatically transfer.
4. **Non-Latin monoculture batches** are the concrete failure slice (RU here).
   The gold gate below must stratify on them.
5. **Judged-coherent ≠ true** (GB Widdecombe cluster: same-story of a false
   event). Not a whitening problem — but marginal recall adds stories, and
   more stories means more of everything, including fabrications. Downstream
   honesty labels carry this, as today.

## Wiring recommendation (NO production change yet)

**Where the transform lives:**

- **`backend/scripts/run_scoped_snapshot.py`** (the R1 production path, the
  one that matters for #229): inside `_country_clusters` (currently ~line
  76-96), between the per-country `embs` assembly and the clustering call at
  line 88 —

  ```python
  cluster_input = whiten_all_but_top(embs, whiten_k) if whiten_k > 0 else embs
  labels = _cluster(cluster_input, mcs, ms, "leaf")
  # _cluster_stats(labels, embs, ...) and _apply_gate(..., embs, ...) stay on RAW embs
  ```

  Plumb a `--whiten-k` arg (default `int(os.getenv("ATLAS_CLUSTER_WHITEN_K",
  "0"))`) from `main` into `_country_clusters`, importing
  `whiten_all_but_top` from `emergent_poc`. This is byte-for-byte what the
  harness measured (per-country fit falls out for free — the batch IS the
  country).

- **`backend/scripts/snapshot_emergent_topics.py`** (global fallback path):
  **already wired** — `--whiten-k` / `ATLAS_CLUSTER_WHITEN_K` exists (lines
  ~340-343, applied at ~416-430, gate/centroids raw). No code change; do NOT
  flip it based on this harness — the global regime is the one the 2026-07-07
  findings cautioned on.

- Rollback is trivial by design: whitening only affects how NEW snapshots form
  clusters; no schema, no stored-vector, no identity-space change. Revert =
  unset `ATLAS_CLUSTER_WHITEN_K` (next snapshot re-forms raw).

**Gold gate REQUIRED before cutover (per project discipline — same class as
PB-3/PB-5, F4 gold-gating):**

1. **Marginal-purity gold pass:** run `run_scoped_snapshot --dry-run` with
   whiten-k=1 over ALL eligible countries (off-peak, M1 mlvenv); collect every
   marginal cluster (new-vs-control by the harness's id-overlap<0.5 rule);
   2-vendor label (DeepSeek + GPT-4o, temp 0) ≥50 of them, **stratified to
   over-sample non-Latin monoculture batches (RU/IR/UA/TR class)**.
   **Acceptance: marginal same-story rate ≥ the control baseline measured the
   same way** (judge ~50 control clusters in the same pass; the n=10 spot
   judge's 80% is directional, underpowered — do not cut over on it).
2. **Thin-country check:** include countries near `min_embedded=100` in the
   dry-run and eyeball their marginal clusters — the harness never measured
   them (risk 2).
3. **Substrate + churn watch:** after any trial flip, verify the promotion
   funnel (gated≥12 per snapshot, actives trending toward ≥80) AND lifecycle
   churn (dissolve/re-form rate vs the raw baseline) for ≥3 snapshots before
   calling it held. The ≥80-active-centroid precondition discipline (PB-5)
   applies to any downstream A/B run on top of this.
4. Pedro's explicit go on the env flip — one variable, reversible, but it
   changes what the whole product serves.

**Bottom line:** whitened HDBSCAN input at the unchanged production config is
the first #229 recall lever measured to raise promotion-relevant cluster yield
(+20.7% at the volume_min proxy) while *shrinking* the largest cluster and
holding cohesion — at the cost of a real, bounded, gold-gateable marginal-purity
question concentrated in language-monoculture batches.
