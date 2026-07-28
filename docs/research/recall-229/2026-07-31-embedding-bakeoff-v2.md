# Embedding bake-off v2 — is multilingual-e5-base the load-bearing weakness?

`embedding-bakeoff-v2` · generated 2026-07-28T19:37:11.671955+00:00 · harness `backend/scripts/measure_embedding_bakeoff.py` · READ-ONLY (no prod write, no commit)

## Verdict: **NO-GO**

Pre-registered rules, frozen before the first score ran:

- a candidate **wins an instrument** by beating **e5-base RECOMPUTED** with margin — I1 gap positive where e5's is negative · I2 top-12 rate ≥ 2× e5-base recomputed *and* ≥ 2× the nominal 11/54 · I3 a K2-safe **cos-only** operating point exists where e5-base has none;
- **GO** = one candidate wins all three · **PARTIAL** = wins I2 (the disease) but not all three · **NO-GO** = nothing beats e5 materially.

### Why the baseline is a RECOMPUTED e5-base, not the shipped numbers

`emergent_clusters.centroid_vec` is an e5 artifact; no other space can be compared to it. Every space here — e5-base included — is scored on centroids rebuilt from the SAME member headlines (3 sample signals per cluster, mean-pooled). The e5-base column is therefore the honest control, and the shipped-artifact numbers are a *different estimator* quoted only for continuity.

### What the three instruments say

1. **A better space DOES fix the pair-separation gates.** The `merge` gate is un-separable in e5-base (gap -0.0336) and separable in `bgem3` and both OpenAI spaces (best 0.1149, `oai-large`). So is the engine-independent `anchor` slice: e5-base -0.0524 → 0.2171 (`oai-large`). This half of the diagnosis is real and fixable.
2. **A better space does NOT fix argmax dispersion — the disease.** On the FROZEN metric every space lands within noise of e5-base (0.0714 → best 0.0857, `oai-large`), nowhere near the 2× bar. Fragments of one event still do not share a nearest topic.
3. **…but the target-free statistic moves more than the frozen one, and that is worth naming.** Mean argmax concentration goes 0.140 → 0.287 (`bgem3`, 2.04×), and on the declared-secondary identity-quality slice the top-12 rate goes 0.1250 → 0.7812 (`bgem3`, 6.25×). The frozen rule stands as written and is NOT met; this is reported as the honest residual, not as a pass.
4. **No space makes cos-only merging safe — but the margin is not an order of magnitude.** No candidate has a threshold that simultaneously bounds graph density, keeps the false side clean, and reconverges BOTH core witnesses, so the label conjunct stays load-bearing and merging stays blackout-exposed. Still, at its loosest K2-and-false-clean tau e5-base leaves the Caspian family in 8 components and Berlin Pride in 20, while `bgem3` leaves them in 3 and 7. See the per-family table under Instrument 3.
5. **Scaling the SAME model family buys nothing; changing the family does.** `e5large` — the direct scale-up of the shipping encoder — is within noise of `e5base` on every instrument (0/3 wins). `bgem3`, a different objective at the same size and the model that LOST the 2026-07-04 gate bake-off, is the strongest space here on the disease statistics and runs locally for free.

Text recovery: **43138/43138** sample signals (100.0%) → **24885/24885** clusters carry a recomputed centroid; 0 dropped and counted (`signals_v2` retention reaches only 2026-07-21; older headlines come from the external archive).

## Cost and wall-clock

| space | model | dim | texts/s | wall-clock | tokens | USD |
|---|---|---|---|---|---|---|
| `e5base` | intfloat/multilingual-e5-base | 768 | 15.8 | 2729.1s | — | — |
| `e5large` | intfloat/multilingual-e5-large | 1024 | 35.8 | 1204.9s | — | — |
| `bgem3` | BAAI/bge-m3 | 1024 | 45.5 | 947.2s | — | — |
| `oai-small` | text-embedding-3-small | 1536 | 287.5 | 150.0s | 1292975 | $0.0259 |
| `oai-large` | text-embedding-3-large | 3072 | 175.7 | 245.5s | 1292975 | $0.1681 |

**Projected full-production cost.** Ingest is **145,471 signals/24h** (measured on `signals_v2`), and the measured token rate here is 30.0 tokens/headline. Local encoders cost no money; their cost is M1 wall-clock, and the number that matters is the comparison to what ships today.

| space | $/day | $/month | M1 wall-clock/day | vs shipping e5-base |
|---|---|---|---|---|
| `e5base` | $0 | $0 | 2.6 h | baseline |
| `e5large` | $0 | $0 | 1.1 h | 2.3× faster |
| `bgem3` | $0 | $0 | 0.9 h | 2.9× faster |
| `oai-small` | $0.09 | $2.62 | n/a (API) | 18.2× faster |
| `oai-large` | $0.57 | $17.00 | n/a (API) | 11.1× faster |

Caveat: the local wall-clock figures are this session's, measured under heavy swap on an 8 GB M1 that is simultaneously running the Atlas cron fleet; they are a floor on speed, not a clean benchmark. The RELATIVE column is the reliable reading, and it was measured with identical batching for every local model except `e5base`, which ran before length-bucketing was added and is therefore understated.

## Instrument 1 — pair separation (raw cosine, per identity gate)

Construction: `measure_identity_whitening.build_pairs`, Rules **v1**, verbatim; member headlines re-embedded per space. `gap = p5(true) − p95(false)`; positive = the gate is separable in that space.

### `match` gate

| space | n true | n false | p5(true) | p95(false) | **gap** | AUC | verdict |
|---|---|---|---|---|---|---|---|
| `e5base` | 300 | 500 | 0.9234 | 0.8760 | **0.0474** | 0.9990 | PROCEED |
| `e5large` | 300 | 500 | 0.9185 | 0.8722 | **0.0463** | 0.9989 | PROCEED |
| `bgem3` | 300 | 500 | 0.5336 | 0.4448 | **0.0888** | 0.9915 | PROCEED |
| `oai-small` | 300 | 500 | 0.4916 | 0.2566 | **0.2350** | 0.9997 | PROCEED |
| `oai-large` | 300 | 500 | 0.5217 | 0.2415 | **0.2802** | 0.9998 | PROCEED |

### `anchor` gate

| space | n true | n false | p5(true) | p95(false) | **gap** | AUC | verdict |
|---|---|---|---|---|---|---|---|
| `e5base` | 300 | 500 | 0.8337 | 0.9645 | **-0.1309** | 0.5241 | STOP |
| `e5large` | 300 | 500 | 0.8420 | 0.9503 | **-0.1083** | 0.6233 | STOP |
| `bgem3` | 300 | 500 | 0.5244 | 0.5774 | **-0.0529** | 0.9766 | STOP |
| `oai-small` | 300 | 500 | 0.3427 | 0.5721 | **-0.2294** | 0.8943 | STOP |
| `oai-large` | 300 | 500 | 0.4173 | 0.5647 | **-0.1474** | 0.9367 | STOP |

### `merge` gate

| space | n true | n false | p5(true) | p95(false) | **gap** | AUC | verdict |
|---|---|---|---|---|---|---|---|
| `e5base` | 300 | 500 | 0.8433 | 0.8769 | **-0.0336** | 0.9432 | STOP |
| `e5large` | 300 | 500 | 0.8469 | 0.8747 | **-0.0278** | 0.9547 | STOP |
| `bgem3` | 300 | 500 | 0.5518 | 0.4882 | **0.0636** | 0.9966 | PROCEED |
| `oai-small` | 300 | 500 | 0.3489 | 0.2755 | **0.0735** | 0.9953 | PROCEED |
| `oai-large` | 300 | 500 | 0.3648 | 0.2500 | **0.1149** | 0.9981 | PROCEED |

### `anchor` gate — ENGINE-INDEPENDENT slice

Lineage TRUE pairs were *selected by* the raw e5 gates, so every space is flattered on them. This slice keeps only `fragment` TRUE (same snapshot, near-identical labels, the engine failed to unify them) against `false_cluster` FALSE (same snapshot, disjoint countries, dissimilar same-script labels). Neither owes anything to the gates.


| space | n true | n false | p5(true) | p95(false) | **gap** | AUC | verdict |
|---|---|---|---|---|---|---|---|
| `e5base` | 243 | 160 | 0.8313 | 0.8837 | **-0.0524** | 0.9122 | STOP |
| `e5large` | 243 | 160 | 0.8382 | 0.8740 | **-0.0358** | 0.9426 | STOP |
| `bgem3` | 243 | 160 | 0.5251 | 0.4268 | **0.0983** | 0.9990 | PROCEED |
| `oai-small` | 243 | 160 | 0.3354 | 0.2261 | **0.1093** | 0.9969 | PROCEED |
| `oai-large` | 243 | 160 | 0.4185 | 0.2015 | **0.2171** | 0.9981 | PROCEED |

## Instrument 2 — argmax dispersion (the disease)

Construction: `simulate_used_t_removal`'s top-12 probe. For every fragment of a witness family, is the family's own consolidation target among its 12 nearest topics? The target is **space-independent** — the topic `dynamic_topic_members` says the family concentrates onto today — so the same question is asked of every space. Nominal e5 baseline from the shipped artifact: **11/54 = 0.204** (Berlin Pride, window scope).

| space | topic pool | core top-12 hits | core rate | vs e5-base | mean argmax concentration |
|---|---|---|---|---|---|
| `e5base` | 6379 | 5/70 | 0.0714 | 1.00× | 0.1713 |
| `e5large` | 6379 | 5/70 | 0.0714 | 1.00× | 0.1713 |
| `bgem3` | 6379 | 5/70 | 0.0714 | 1.00× | 0.4051 |
| `oai-small` | 6379 | 5/70 | 0.0714 | 1.00× | 0.2026 |
| `oai-large` | 6379 | 6/70 | 0.0857 | 1.20× | 0.2430 |

**A confound this instrument carries, stated up front.** The target is prod's *plurality* holder, which for `berlin pride [window]` holds only 5 of 52 clusters and is labelled something else entirely — the black hole this programme exists to kill. A genuinely better space could rightly push that target OUT of a fragment's top-12 and score WORSE on the frozen rule. The target-free statistic in the last column — the largest share of a family's fragments agreeing on ONE nearest topic — is immune to it and answers the disease question directly.

Targets (space-independent, from `dynamic_topic_members`):

| family | clusters | prod target | holds | target label | right identity? |
|---|---|---|---|---|---|
| GQ-12 caspian | 9 | 2239 | 1 | EEUU vs Irán Escalada | no |
| berlin pride | 23 | 7358 | 1 | Berlin Pride Van Attack | yes |
| fresh:us-strikes-on-iran | 9 | 3688 | 1 | US Strikes Iran Seventh Night | no |
| fresh:paris-knife-attack | 9 | 3106 | 1 | Toronto Festival Shooting | no |
| fresh:russian-missile-strikes-on-kyiv | 9 | 3736 | 1 | Russian Missile Strikes on Ukraine | yes |
| fresh:wildfires-in-france-and-spain | 8 | 153 | 1 | Wildfires Rage in Spain and France, Over 200,000 Evacuated | no |
| GQ-12 caspian [window] | 16 | 8072 | 5 | Iran Attack on US Bases and Regional Fallout | no |
| berlin pride [window] | 54 | 811 | 5 | Bulgarian Children Die in Cyprus | no |
| fresh:us-strikes-on-iran [window] | 46 | 8072 | 11 | Iran Attack on US Bases and Regional Fallout | no |
| fresh:paris-knife-attack [window] | 11 | 863 | 1 | Anti-Corruption Campaign in Iraq | no |
| fresh:russian-missile-strikes-on-kyiv [window] | 38 | 3770 | 5 | Strikes on Logistics Centers | no |
| fresh:wildfires-in-france-and-spain [window] | 29 | 7580 | 7 | Wildfires Rage Across Spain and France, Mass Evacuations | no |

### Secondary reading — families whose target IS a compatible identity

Declared secondary; it does **not** decide the verdict. `right identity?` above is production's own `labels_compatible(target label, family modal cluster label)`, the same predicate `measure_cluster_consolidation` uses for `identity_ok`. Restricting the identical top-12 question to those families asks: *can the space put the CORRECT identity in a fragment's twelve nearest topics?*

| space | hits / scored | rate | vs e5-base |
|---|---|---|---|
| `e5base` | 4/32 | 0.1250 | 1.00× |
| `e5large` | 7/32 | 0.2188 | 1.75× |
| `bgem3` | 25/32 | 0.7812 | 6.25× |
| `oai-small` | 22/32 | 0.6875 | 5.50× |
| `oai-large` | 21/32 | 0.6562 | 5.25× |

Per-family (top-12 hits / scored · argmax modal share):

| family | `e5base` | `e5large` | `bgem3` | `oai-small` | `oai-large` |
|---|---|---|---|---|---|
| GQ-12 caspian | 2/9 · 0.22 | 1/9 · 0.22 | 2/9 · 0.67 | 1/9 · 0.33 | 1/9 · 0.44 |
| berlin pride | 3/23 · 0.04 | 6/23 · 0.04 | 22/23 · 0.30 | 21/23 · 0.17 | 20/23 · 0.13 |
| fresh:us-strikes-on-iran | 2/9 · 0.11 | 2/9 · 0.11 | 5/9 · 0.22 | 3/9 · 0.11 | 3/9 · 0.11 |
| fresh:paris-knife-attack | 0/9 · 0.11 | 0/9 · 0.11 | 4/9 · 0.33 | 1/9 · 0.11 | 6/9 · 0.11 |
| fresh:russian-missile-strikes-on-kyiv | 1/9 · 0.11 | 1/9 · 0.11 | 3/9 · 0.11 | 1/9 · 0.22 | 1/9 · 0.11 |
| fresh:wildfires-in-france-and-spain | 1/8 · 0.12 | 1/8 · 0.12 | 0/8 · 0.25 | 1/8 · 0.25 | 0/8 · 0.25 |
| GQ-12 caspian [window] | 0/16 · 0.25 | 0/16 · 0.25 | 0/16 · 0.62 | 0/16 · 0.31 | 1/16 · 0.38 |
| berlin pride [window] | 5/54 · 0.09 | 5/54 · 0.09 | 5/54 · 0.19 | 5/54 · 0.09 | 5/54 · 0.11 |
| fresh:us-strikes-on-iran [window] | 0/46 · 0.13 | 2/46 · 0.13 | 2/46 · 0.13 | 0/46 · 0.13 | 2/46 · 0.13 |
| fresh:paris-knife-attack [window] | 3/11 · 0.18 | 1/11 · 0.18 | 0/11 · 0.27 | 0/11 · 0.18 | 0/11 · 0.18 |
| fresh:russian-missile-strikes-on-kyiv [window] | 5/38 · 0.13 | 5/38 · 0.13 | 6/38 · 0.13 | 6/38 · 0.13 | 6/38 · 0.13 |
| fresh:wildfires-in-france-and-spain [window] | 14/29 · 0.17 | 14/29 · 0.17 | 15/29 · 0.21 | 24/29 · 0.17 | 27/29 · 0.17 |

## Instrument 3 — consolidation graph, cos-ONLY, tau swept

Construction: `measure_cluster_consolidation`'s rule with the **label conjunct removed** (metric 6). A K2-safe point requires, simultaneously: largest connected component ≤ 2% of the snapshot's clusters · ≥2 of the 2 core witness families at ≤ 3 components · **0** of the mechanically-constructed FALSE pairs admitted. A space where cos ALONE is safe would make merging blackout-immune.

### snapshot `2026-07-28T03:28:39` — primary

| space | clusters | K2-safe cos-only point? | best tau | largest share | core families ≤3 | false admitted |
|---|---|---|---|---|---|---|
| `e5base` | 2032 | **no** | — | — | — | — |
| `e5large` | 2032 | **no** | — | — | — | — |
| `bgem3` | 2032 | **no** | — | — | — | — |
| `oai-small` | 2032 | **no** | — | — | — | — |
| `oai-large` | 2032 | **no** | — | — | — | — |

How close each space gets: at the LOOSEST tau that already satisfies K2 (≤2%) and admits 0 false pairs, how many components do the witness families still occupy? (`≤3` would clear the bar.)

| space | loosest K2+false-clean tau | largest share | GQ-12 caspian | berlin pride | US-strikes-Iran | wildfires FR/ES |
|---|---|---|---|---|---|---|
| `e5base` | 0.965 | 0.0118 | 8 | 20 | 9 | 8 |
| `e5large` | 0.950 | 0.0128 | 6 | 21 | 8 | 8 |
| `bgem3` | 0.795 | 0.0197 | 3 | 7 | 4 | 1 |
| `oai-small` | 0.725 | 0.0192 | 3 | 11 | 5 | 3 |
| `oai-large` | 0.720 | 0.0192 | 2 | 9 | 8 | 2 |

### snapshot `2026-07-22T07:38:29` — density/false-side robustness only

| space | clusters | K2-safe cos-only point? | best tau | largest share | core families ≤3 | false admitted |
|---|---|---|---|---|---|---|
| `e5base` | 2517 | **n/a** | 0.955 | 0.0187 | 0/0 | 0 |
| `e5large` | 2517 | **n/a** | 0.950 | 0.0135 | 0/0 | 0 |
| `bgem3` | 2517 | **n/a** | 0.820 | 0.0199 | 0/0 | 0 |
| `oai-small` | 2517 | **n/a** | 0.750 | 0.0199 | 0/0 | 0 |
| `oai-large` | 2517 | **n/a** | 0.735 | 0.0123 | 0/0 | 0 |

## Named witness pairs (from the whitening artifact's own tails)

The hand-checked exhibits the whitening kill was argued on, re-scored in every space. `e5 stored` is the shipped centroid cosine; the space columns are the recomputed-centroid cosine.

| truth | pair | e5 stored raw | e5 stored whitened | `e5base` | `e5large` | `bgem3` | `oai-small` | `oai-large` |
|---|---|---|---|---|---|---|---|---|
| true | Berlin Pride Vehicle Attack ↔ Berlin Pride Attack Suspect | 0.8028 | -0.0604 | 0.7811 | 0.7868 | 0.5299 | 0.3583 | 0.3893 |
| true | Berlin Pride Vehicle Attack ↔ Berlin Pride Terror Attack | 0.8068 | -0.0174 | 0.7846 | 0.8063 | 0.5476 | 0.3791 | 0.4575 |
| true | France Spain Wildfires ↔ Wildfires in France and Spain | 0.8515 | -0.0132 | 0.8312 | 0.8519 | 0.6291 | 0.3170 | 0.5078 |
| true | Wildfires in France and Spain ↔ France Spain Wildfires | 0.8638 | -0.0111 | 0.8565 | 0.8862 | 0.6884 | 0.4107 | 0.6114 |
| true | Spain Reaches World Cup Final ↔ Spain vs Argentina World Cup Final | 0.8479 | -0.0042 | 0.8262 | 0.8758 | 0.5131 | 0.3996 | 0.4009 |
| true | Berlin Pride Vehicle Attack ↔ Berlin Pride Attack Suspect Killed | 0.8110 | -0.0020 | 0.7973 | 0.8079 | 0.5938 | 0.3773 | 0.4969 |
| true | Berlin Pride Attack ↔ Berlin Pride Attack Suspect | 0.8414 | -0.0015 | 0.8253 | 0.8325 | 0.7463 | 0.4875 | 0.6114 |
| true | Berlin Pride Attack ↔ Berlin Pride Attack | 0.8350 | 0.0095 | 0.8136 | 0.8384 | 0.7047 | 0.5165 | 0.5712 |
| true | Berlin Pride Attack Suspect ↔ Berlin Pride Attack Suspect | 0.8280 | 0.0160 | 0.8118 | 0.8219 | 0.6919 | 0.3721 | 0.5659 |
| true | Ukrainian Drone Attacks on Russia ↔ Ukrainian Drone Strikes in Russia | 0.8371 | 0.0188 | 0.8212 | 0.8464 | 0.8624 | 0.7157 | 0.6972 |

## Per-candidate verdict

| candidate | I1 win | I2 win | I3 win | instruments won |
|---|---|---|---|---|
| `e5large` | no | no | no | 0/3 |
| `bgem3` | yes | no | no | 1/3 |
| `oai-small` | yes | no | no | 1/3 |
| `oai-large` | yes | no | no | 1/3 |

## Honest limits

1. **Bounded universe.** Cluster centroids use the first 3 `sample_signal_ids`; topic centroids use anchor + 3 most-recent members, not the full running mean. Both approximations are applied IDENTICALLY to every space, so the cross-space comparison holds; the absolute numbers are not comparable to the shipped artifacts.
2. **The topic pool for I2 is capped the same way**, so `top-12` is measured against approximate topic positions. The e5-base recomputed column is the control for exactly this.
3. **fp16 on the 1024-dim local models.** Measured on this 8GB M1: fp32 gives 0.4 texts/s (swapping), fp16 gives ~60. The fp16↔fp32 cosine fidelity probe is in the JSON under `spaces.<name>.embed_meta`.
4. **No jina-embeddings-v3.** No API key exists in the environment and creating an account is out of scope; it was not measured.

