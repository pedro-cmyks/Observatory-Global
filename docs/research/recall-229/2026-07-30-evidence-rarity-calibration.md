# M3 — evidence rarity calibration (2026-07-28)

**Script:** `backend/scripts/calibrate_evidence_rarity.py` · read-only (`default_transaction_read_only`) · **writes no prod table**
**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` §3.1/§3.4/§10 · **Plan:** T-A2 (M3)
**Primary snapshot:** `2026-07-28` (2032 clusters, sample-ref resolvability **97.5%**) · **days profiled:** 8

> **Read this first.** df is measured per SNAPSHOT with the CLUSTER as the document. Older snapshots are measured through a decaying window — `sample_signal_ids` resolvability falls from ~97.5% to ~16% over 7 days (spec §2.4) — so their df is biased LOW and they are used here only as a **volatility check**. Every proposal is anchored on the primary snapshot, which is the resolvability the Stage-1 writer will actually see (it builds fingerprints immediately after the snapshot write).

## 0. What this measured, in one screen

| question (spec) | answer |
|---|---|
| `df_max` per lane | entity **600**, domain **200**, headline **50**, url **n/a (degenerate — treat as binary)**. Use FIXED constants, not the observed max: the observed max swings up to 4.2× night to night while `norm_rarity(df=2)` moves by <0.03 across every candidate — the denominator is volatile and the answer is insensitive, so pin it. |
| §10 Q2 — `nlp_persons` noise floor | **53.0% garbage** at df=1 (n=200, model-labeled). Well over the 30% line → **df=1 is not admissible as sole evidence**. The spec blamed `nlp_persons` (§2.5); the measurement says the worst array is **GDELT `organizations[]` at 81%**, vs `nlp_persons` 43% and GDELT `persons[]` 24%. |
| §10 Q1 — does lane U's domain half discriminate? | **Not at DP-1** (6.0% true vs 3.2% false, lift 1.8730). **Yes at DP-2** (cross-day 61.5% vs 1.2%). The question has two answers and the spec asks it once. |
| lane U's exact-URL half | **structurally silent at DP-1** — clusters partition the snapshot and `source_url` is unique, so two same-night clusters cannot share a URL. Not a threshold problem. |
| `w_E / w_U / w_H` | seeds **0.92 / 0.652 / 1.0** — but see §5: lane E fires on 46% of true pairs and every other lane under 6%, so at DP-1 `strength` is lane E and the other weights decide almost nothing. |

**Two findings the spec did not anticipate, both actionable before Stage 1:**

1. **Lane H manufactures false evidence on non-Latin headlines** (§4d). `_norm_headline` deletes non-Latin characters, so a Cyrillic or Arabic headline reduces to its DIGITS — `'Атака РФ по АТБ у Чернігові 26 липня'` → `'26'`. A rare digit-residue key scores `norm_rarity ≈ 1.0`, the maximum. T-B2 must filter these before writing fingerprints; a frozen fingerprint cannot be cleaned later.
2. **Stage 2 has no script-blind lane.** Lane U is silent at DP-1 (§4c) and lane H is unusable for ru/uk/ar/fa (§4d), so a Cyrillic-only fragment pair is judged by lane E alone — whose ru coverage is 10.0% (spec §2.2). The spec's §3.4 argument that U and H cover the entity lane's holes **does not hold at the decision point Stage 2 builds first.**

## 1. df distributions per lane (primary snapshot)

| lane | distinct items | df_max | df p50 | p90 | p95 | p99 | share df=1 | items/cluster (mean) | cluster coverage |
|---|---|---|---|---|---|---|---|---|---|
| **entity** | 30,957 | 383 | 1.0 | 2.0 | 3.0 | 9.0 | 83.8% | 23.328 | 99.1% |
| **domain** | 3,338 | 168 | 2.0 | 11.0 | 20.0 | 49.63 | 39.1% | 8.455 | 100.0% |
| **url** | 23,582 | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 100.0% | 11.608 | 100.0% |
| **headline** | 16,235 | 23 | 1.0 | 1.0 | 1.0 | 2.0 | 98.7% | 8.34 | 91.7% |
| **headline_clean** | 15,601 | 15 | 1.0 | 1.0 | 1.0 | 1.0 | 99.6% | 7.731 | 78.3% |

df histogram (primary snapshot, item counts):

| lane | 1 | 2 | 3 | 4-5 | 6-10 | 11-20 | 21-50 | 51-100 | 101+ |
|---|---|---|---|---|---|---|---|---|---|
| entity | 25,938 | 2,729 | 899 | 672 | 456 | 162 | 77 | 17 | 7 |
| domain | 1,306 | 586 | 356 | 388 | 347 | 206 | 119 | 27 | 3 |
| url | 23,577 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| headline | 16,020 | 118 | 35 | 18 | 24 | 18 | 2 | 0 | 0 |
| headline_clean | 15,545 | 44 | 6 | 1 | 3 | 2 | 0 | 0 | 0 |

Most frequent items per lane (the ubiquity that rarity weighting has to defuse):

- **entity** — `united states` (383), `reuters` (225), `donald trump` (192), `white house` (109), `trump` (103), `young` (101), `european union` (101), `x2013` (100)
- **domain** — `inewsgr.com` (168), `rt.com` (163), `indiatimes.com` (158), `thehindu.com` (97), `zazoom.it` (97), `aol.co.uk` (88), `tribunnews.com` (86), `hindustantimes.com` (84)
- **url** — `spiegel.de/politik/ukrainekrieg-eu-verhaengt` (2), `russian.rt.com/ussr/news/1661416-ugolovnoe-d` (2), `russian.rt.com/ussr/news/1660403-vs-rossiya-` (2), `russian.rt.com/ussr/article/1661814-vs-rossi` (2), `punchng.com/londons-gatwick-airport-suffers-` (2), `elevenwarriors.com/the-big-ten/2026/07/16311` (1), `thegamenashville.com/2026/07/27/manuel-gets-` (1), `wxyz.com/news/michigan-set-to-pay-warde-manu` (1)
- **headline** — `2026` (23), `23` (21), `5` (20), `100` (20), `27` (19), `22` (19), `24` (19), `21` (18)
- **headline_clean** — `blackseanews` (15), `patrisnews` (15), `wildberries` (9), `dsnews ua` (9), `the press project` (6), `bloomberg` (4), `politico` (3), `caucasian knot` (3)

## 2. `df_max` per lane — proposal, volatility and sensitivity

`norm_rarity(df, df_max) = (1/df − 1/df_max)/(1 − 1/df_max)`. `df_max` is the denominator that is **frozen into every fingerprint** (spec §3.2), so the question is not only 'what is the max tonight' but 'does the max hold still'.

### 2a. Observed `df_max` per night (the volatility check)

| lane | 2026-07-28 | 2026-07-27 | 2026-07-26 | 2026-07-25 | 2026-07-24 | 2026-07-23 | 2026-07-22 | 2026-07-21 | min | max | ratio max/min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **entity** | 383 | 600 | 561 | 571 | 362 | 171 | 186 | — | 171 | 600 | 3.51× |
| **domain** | 168 | 191 | 170 | 168 | 107 | 71 | 45 | — | 45 | 191 | 4.24× |
| **url** | 2 | 2 | 2 | 2 | 2 | 1 | 1 | — | 1 | 2 | 2.00× |
| **headline** | 23 | 34 | 31 | 32 | 16 | 11 | 14 | — | 11 | 34 | 3.09× |
| **headline_clean** | 15 | 16 | 16 | 15 | 12 | 10 | 4 | — | 4 | 16 | 4.00× |

Per-day context for every table in this document (both are confounds, and both are inherited by M1/M2):

| day | clusters | sample refs | **resolvability** | **NULL-label share** |
|---|---|---|---|---|
| `2026-07-28` | 2,032 | 24,192 | 97.5% | 0.0% |
| `2026-07-27` | 3,475 | 42,159 | 82.5% | 100.0% ⚠ label-VOID |
| `2026-07-26` | 3,593 | 43,704 | 69.8% | 100.0% ⚠ label-VOID |
| `2026-07-25` | 3,854 | 46,765 | 58.0% | 100.0% ⚠ label-VOID |
| `2026-07-24` | 2,395 | 29,086 | 46.6% | 100.0% ⚠ label-VOID |
| `2026-07-23` | 2,190 | 26,455 | 31.0% | 100.0% ⚠ label-VOID |
| `2026-07-22` | 2,517 | 30,124 | 16.4% | 0.0% |
| `2026-07-21` | 2,369 | 28,520 | 0.0% | 0.0% |

### 2b. Sensitivity — how far `norm_rarity` actually moves

**entity** (observed df_max 383):

| df | df_max=50 | df_max=100 | df_max=200 | df_max=383 | df_max=500 | df_max=1000 | df_max=2000 | spread |
|---|---|---|---|---|---|---|---|---|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 0.4898 | 0.4949 | 0.4975 | 0.4987 | 0.4990 | 0.4995 | 0.4997 | 0.0099 |
| 3 | 0.3197 | 0.3266 | 0.3300 | 0.3316 | 0.3320 | 0.3327 | 0.3330 | 0.0133 |
| 5 | 0.1837 | 0.1919 | 0.1960 | 0.1979 | 0.1984 | 0.1992 | 0.1996 | 0.0159 |
| 10 | 0.0816 | 0.0909 | 0.0955 | 0.0976 | 0.0982 | 0.0991 | 0.0995 | 0.0179 |
| 25 | 0.0204 | 0.0303 | 0.0352 | 0.0375 | 0.0381 | 0.0390 | 0.0395 | 0.0191 |
| 100 | -0.0102 | 0.0000 | 0.0050 | 0.0074 | 0.0080 | 0.0090 | 0.0095 | 0.0197 |

**domain** (observed df_max 168):

| df | df_max=50 | df_max=100 | df_max=168 | df_max=200 | df_max=383 | df_max=500 | df_max=1000 | df_max=2000 | spread |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 0.4898 | 0.4949 | 0.4970 | 0.4975 | 0.4987 | 0.4990 | 0.4995 | 0.4997 | 0.0099 |
| 3 | 0.3197 | 0.3266 | 0.3293 | 0.3300 | 0.3316 | 0.3320 | 0.3327 | 0.3330 | 0.0133 |
| 5 | 0.1837 | 0.1919 | 0.1952 | 0.1960 | 0.1979 | 0.1984 | 0.1992 | 0.1996 | 0.0159 |
| 10 | 0.0816 | 0.0909 | 0.0946 | 0.0955 | 0.0976 | 0.0982 | 0.0991 | 0.0995 | 0.0179 |
| 25 | 0.0204 | 0.0303 | 0.0343 | 0.0352 | 0.0375 | 0.0381 | 0.0390 | 0.0395 | 0.0191 |
| 100 | -0.0102 | 0.0000 | 0.0041 | 0.0050 | 0.0074 | 0.0080 | 0.0090 | 0.0095 | 0.0197 |

**url** (observed df_max 2):

| df | df_max=2 | df_max=50 | df_max=100 | df_max=200 | df_max=383 | df_max=500 | df_max=1000 | df_max=2000 | spread |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 0.0000 | 0.4898 | 0.4949 | 0.4975 | 0.4987 | 0.4990 | 0.4995 | 0.4997 | 0.4997 |
| 3 | -0.3333 | 0.3197 | 0.3266 | 0.3300 | 0.3316 | 0.3320 | 0.3327 | 0.3330 | 0.6663 |
| 5 | -0.6000 | 0.1837 | 0.1919 | 0.1960 | 0.1979 | 0.1984 | 0.1992 | 0.1996 | 0.7996 |
| 10 | -0.8000 | 0.0816 | 0.0909 | 0.0955 | 0.0976 | 0.0982 | 0.0991 | 0.0995 | 0.8995 |
| 25 | -0.9200 | 0.0204 | 0.0303 | 0.0352 | 0.0375 | 0.0381 | 0.0390 | 0.0395 | 0.9595 |
| 100 | -0.9800 | -0.0102 | 0.0000 | 0.0050 | 0.0074 | 0.0080 | 0.0090 | 0.0095 | 0.9895 |

**headline** (observed df_max 23):

| df | df_max=23 | df_max=50 | df_max=100 | df_max=200 | df_max=383 | df_max=500 | df_max=1000 | df_max=2000 | spread |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 0.4773 | 0.4898 | 0.4949 | 0.4975 | 0.4987 | 0.4990 | 0.4995 | 0.4997 | 0.0224 |
| 3 | 0.3030 | 0.3197 | 0.3266 | 0.3300 | 0.3316 | 0.3320 | 0.3327 | 0.3330 | 0.0300 |
| 5 | 0.1636 | 0.1837 | 0.1919 | 0.1960 | 0.1979 | 0.1984 | 0.1992 | 0.1996 | 0.0360 |
| 10 | 0.0591 | 0.0816 | 0.0909 | 0.0955 | 0.0976 | 0.0982 | 0.0991 | 0.0995 | 0.0404 |
| 25 | -0.0036 | 0.0204 | 0.0303 | 0.0352 | 0.0375 | 0.0381 | 0.0390 | 0.0395 | 0.0431 |
| 100 | -0.0350 | -0.0102 | 0.0000 | 0.0050 | 0.0074 | 0.0080 | 0.0090 | 0.0095 | 0.0445 |

**headline_clean** (observed df_max 15):

| df | df_max=15 | df_max=50 | df_max=100 | df_max=200 | df_max=383 | df_max=500 | df_max=1000 | df_max=2000 | spread |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| 2 | 0.4643 | 0.4898 | 0.4949 | 0.4975 | 0.4987 | 0.4990 | 0.4995 | 0.4997 | 0.0354 |
| 3 | 0.2857 | 0.3197 | 0.3266 | 0.3300 | 0.3316 | 0.3320 | 0.3327 | 0.3330 | 0.0473 |
| 5 | 0.1429 | 0.1837 | 0.1919 | 0.1960 | 0.1979 | 0.1984 | 0.1992 | 0.1996 | 0.0567 |
| 10 | 0.0357 | 0.0816 | 0.0909 | 0.0955 | 0.0976 | 0.0982 | 0.0991 | 0.0995 | 0.0638 |
| 25 | -0.0286 | 0.0204 | 0.0303 | 0.0352 | 0.0375 | 0.0381 | 0.0390 | 0.0395 | 0.0681 |
| 100 | -0.0607 | -0.0102 | 0.0000 | 0.0050 | 0.0074 | 0.0080 | 0.0090 | 0.0095 | 0.0702 |

### 2c. Proposals

| lane | proposed `df_max` | basis | norm_rarity(df=2) at the proposal | worst-case move vs the observed max |
|---|---|---|---|---|
| **entity** | **600** | fixed constant ≥ observed max, rounded to 50 — stability of a frozen denominator over nightly exactness | 0.4992 | +0.0005 |
| **domain** | **200** | fixed constant ≥ observed max, rounded to 50 — stability of a frozen denominator over nightly exactness | 0.4975 | +0.0005 |
| **url** | **n/a — degenerate** | DEGENERATE — observed df_max ≤ 2, there is no rarity gradient to normalise; treat a shared item in this lane as BINARY evidence (weight 1.0) and do not store a df_max for it | — | — |
| **headline** | **50** | fixed constant ≥ observed max, rounded to 50 — stability of a frozen denominator over nightly exactness | 0.4898 | +0.0125 |
| **headline_clean** | **50** | fixed constant ≥ observed max, rounded to 50 — stability of a frozen denominator over nightly exactness | 0.4898 | +0.0255 |

- **entity** — observed max swings 171–600 across the profiled nights (3.51×) while p99 tonight is only 9.0 — the max is set by a handful of ubiquitous items and is exactly the kind of quantity that must not drift under a FROZEN fingerprint. Fixing it costs |Δ|=0.0005 on a df=2 item, i.e. nothing.
- **domain** — observed max swings 45–191 across the profiled nights (4.24×) while p99 tonight is only 49.63 — the max is set by a handful of ubiquitous items and is exactly the kind of quantity that must not drift under a FROZEN fingerprint. Fixing it costs |Δ|=0.0005 on a df=2 item, i.e. nothing.
- **url** — observed max is 2 across every profiled night: essentially every item in this lane is unique, so rarity weighting adds nothing. Any df_max would be arbitrary — the sensitivity table's 0.4898 'move' on df=2 is an artifact of that arbitrariness, not a calibration.
- **headline** — observed max swings 11–34 across the profiled nights (3.09×) while p99 tonight is only 2.0 — the max is set by a handful of ubiquitous items and is exactly the kind of quantity that must not drift under a FROZEN fingerprint. Fixing it costs |Δ|=0.0125 on a df=2 item, i.e. nothing.
- **headline_clean** — observed max swings 4–16 across the profiled nights (4.00×) while p99 tonight is only 1.0 — the max is set by a handful of ubiquitous items and is exactly the kind of quantity that must not drift under a FROZEN fingerprint. Fixing it costs |Δ|=0.0255 on a df=2 item, i.e. nothing.

## 3. The `nlp_persons` noise floor (df=1 stratum)

**Labeling provenance: model-labeled, single rater (see artifact header).** Every one of the 200 sampled items ships in the companion `.json` with its verdict, its raw spellings, its provenance counts and an example headline, so a human can re-check the call. The sample is deterministic (seed 42) and keyed BY NAME, so a re-label stays valid.

Labeling rule (full statement + the borderline policy live in `2026-07-30-df1-entity-labels.json`): the question is **is this string a STABLE IDENTIFIER** — one an independent report of the same story would plausibly also produce — because that, not grammatical entity-hood, is what makes a df=1 item usable at norm_rarity 1.0. **REAL** = a canonical-ish name (NER mistyping does not disqualify it — overlap matches the STRING, not the type). **REAL_WEAK** = a real, stable entity that is nonetheless poor same-story evidence: photo credits, reporter bylines, the covering outlet's own name. **GARBAGE** = sentence fragments, GDELT machine-translation word-salad, generic common nouns, bare ambiguous tokens, truncations, and two entities glued into one key.

| stratum | n labeled | garbage | real | real-but-weak | **garbage rate** | unusable rate (garbage + weak) |
|---|---|---|---|---|---|---|
| **all df=1 entities** | 200 | 106 | 88 | 6 | **53.0%** | 56.0% |
| exclusive: gdelt_any | 146 | 82 | 61 | 3 | 56.2% | 58.2% |
| exclusive: nlp_only | 54 | 24 | 27 | 3 | 44.4% | 50.0% |
| source array: `gdelt_organizations` | 83 | 67 | 16 | 0 | 80.7% | 80.7% |
| source array: `gdelt_persons` | 63 | 15 | 45 | 3 | 23.8% | 28.6% |
| source array: `nlp_persons` | 56 | 24 | 29 | 3 | 42.9% | 48.2% |

*(Source-array rows are memberships, not a partition — an entity present in two arrays counts in both.)*

**Recommendation:** garbage rate **53.0% > 30%** → **df=1 entities must NOT be admissible as the sole evidence for a merge.** By source array: `gdelt_organizations` 81% (n=83); `nlp_persons` 43% (n=56); `gdelt_persons` 24% (n=63). The noise is NOT uniform — `gdelt_organizations` is the worst array and `gdelt_persons` the cleanest — so the cheapest honest cut is per-array admissibility at df=1, with the excluded count published (`entities_excluded_noise_floor`) rather than silently dropped. Note this INVERTS the spec's §2.5 assumption if the worst array is a GDELT one.

## 4. Does the DOMAIN half of lane U discriminate? (spec §10 Q1)

TRUE = every within-family cluster pair of the witness families (**caspian** 9 clusters / 36 pairs, **berlin-pride** 22 clusters / 231 pairs). FALSE = 500 mechanical pairs: disjoint non-empty country sets AND `different_story` labels — the SAME construction as the whitened-taus harness (imported, not re-derived).

### 4a. Every lane, true vs false (no df gate)

| lane | TRUE share w/ ≥1 shared item | FALSE share | lift | TRUE score p50 | FALSE score p95 | AUC |
|---|---|---|---|---|---|---|
| **entity** | 45.7% | 4.0% | 11.4230 | 0.0000 | 0.0000 | 0.7147 |
| **domain** | 6.0% | 3.2% | 1.8730 | 0.0000 | 0.0000 | 0.5141 |
| **url** | 0.0% | 0.0% | — | 0.0000 | 0.0000 | 0.5000 |
| **headline** | 3.8% | 0.4% | 9.3630 | 0.0000 | 0.0000 | 0.5168 |
| **headline_clean** | 1.9% | 0.0% | — | 0.0000 | 0.0000 | 0.5094 |

### 4b. Domain half under a df ceiling ("only low-df domains count")

| max df of a shared domain | TRUE fire | FALSE fire | lift |
|---|---|---|---|
| 1 | 0.0% (0) | 0.0% (0) | — |
| 2 | 0.0% (0) | 0.2% (1) | 0.0000 |
| 3 | 0.0% (0) | 0.2% (1) | 0.0000 |
| 5 | 0.0% (0) | 0.2% (1) | 0.0000 |
| 10 | 0.4% (1) | 0.2% (1) | 1.8730 |
| 20 | 1.1% (3) | 1.0% (5) | 1.1240 |
| 50 | 4.9% (13) | 1.6% (8) | 3.0430 |
| any | 6.0% (16) | 3.2% (16) | 1.8730 |

**Domain verdict:** **at DP-1 the domain half is nearly worthless and dangerous ungated.** It fires on only 6.0% of true pairs against 3.2% of false — a lift of 1.873, i.e. syndication infrastructure. A df≤50 ceiling improves the lift to 3.043 but on 13 true pairs out of 267, which is too few to calibrate on and buys ~5% recall. **Recommendation: drop the domain half from the DP-1 gate**; if it is kept at all, it is kept ONLY with the df≤50 ceiling and only as a borderline-band corroborator, never as a merge trigger. **The answer flips by decision point.** The same domain lane measured across the day boundary reads 61.5% true / 1.2% false (AUC 0.8020) — strong, for the §4c reason (a 168-hour clustering window means cross-day same-story pairs largely re-use the same articles, hence the same domains). So 'does the domain half discriminate' has no single answer: **NO at DP-1, YES at DP-2.** The spec asks the question once; it needs asking twice.

### 4c. The exact-URL half — a STRUCTURAL result

| check | value |
|---|---|
| `sample_signal_ids` on the primary snapshot | 24,192 refs, 24,192 distinct |
| → do clusters PARTITION the corpus? | **yes — no signal is in two clusters** |
| duplicate `source_url` values in `signals_v2` | **0** of 1,001,964 rows |
| normalized url keys at df=2 within the snapshot | 5 of 23,582 |
| `snapshot_window_h` | **[168]** |
| signals sampled on BOTH `2026-07-28` and `2026-07-27` | 15,159 (62.7% of the primary's refs) |

**URL verdict:** **the exact-URL half is structurally silent on same-snapshot pairs — this is a consequence of the schema, not a low rate that better thresholds could lift.** `sample_signal_ids` PARTITION the snapshot (24,192 refs, 24,192 distinct → no signal is in two clusters), and `signals_v2` holds 0 duplicate `source_url` values across 1,001,964 rows. Two clusters of one snapshot can therefore only share a URL when the normalizer collapses two distinct rows — measured at **5 keys out of 23,582**. Fire rates: 0.0% true / 0.0% false. **Consequence for the build order: lane U contributes NOTHING to Stage 2 (DP-1, same-snapshot merge) — the first thing being built.** Cross-day is a different object entirely, and the reason is `snapshot_window_h = [168]`: each snapshot re-clusters a SEVEN-DAY window, so 15,159 signals (62.7% of tonight's refs) are also in last night's, and the cross-day probe reads 51.2% true / 0.0% false. **Read that number with its mechanism**: a cross-day same-story pair is largely the same ARTICLES re-clustered, so lane U is measuring membership continuity, not a translation-surviving same-story signal. That is still exactly what DP-2 needs — but it is not evidence for the spec's §3.4 claim that lane U rescues cross-script matching. **Keep lane U, scope it to DP-2, and do not let its Stage-2 zero be read as 'lane U fails'.**

Cross-day probe (`2026-07-28` × `2026-07-22`, a **6-day gap**, 166 true / 500 false pairs; old side at 16.4% resolvability, so these are FLOORS):

> ⚠ The nearest prior nights were **skipped as label-VOID**: `2026-07-27`, `2026-07-26`, `2026-07-25`, `2026-07-24`, `2026-07-23` carry 100% NULL `emergent_clusters.label` (the 2026-07-23→07-27 DeepSeek-402 blackout). Both constructions here are label-based, so those nights cannot be used — spec §5.1's confounder rule. The probe therefore reaches back 6 days, where only 16.4% of sample refs still resolve. **Treat this table as an existence proof, not a rate.**

| lane | TRUE fire | FALSE fire | lift | AUC |
|---|---|---|---|---|
| **entity** | 77.1% | 2.4% | 32.1290 | 0.8808 |
| **domain** | 61.5% | 1.2% | 51.2050 | 0.8020 |
| **url** | 51.2% | 0.0% | — | 0.7560 |
| **headline** | 44.6% | 0.0% | — | 0.7229 |
| **headline_clean** | 40.4% | 0.0% | — | 0.7018 |

### 4d. 🔴 Lane H manufactures date-residue keys on non-Latin headlines

`_norm_headline` folds through `normalize_search_text`, whose `[^a-z0-9]` class deletes every non-Latin character. A non-Latin headline therefore does **not** reduce to the empty string — it reduces to whatever DIGITS it contained. Measured live:

```
'27 липня 2026 року — яке сьогодні свято'  ->  '27 2026'
'Атака РФ по АТБ у Чернігові 26 липня'     ->  '26'
'انفجار في كييف 2026'                        ->  '2026'
```

On the primary snapshot **10.6%** of resolved signals (2,497 of 23,599) produce such a key, and 17.2% produce an empty one. The top lane-H keys by df are pure residue — `2026` (23), `23` (21), `5` (20), `100` (20), `27` (19), `22` (19).

**Why this is not cosmetic.** A residue key like `26` can be RARE in a given night, and the rarity weighting would then hand it `norm_rarity ≈ 1.0` — the MAXIMUM evidence score — for two headlines that merely mention the same number. That is a false-merge generator aimed precisely at the ru/uk/ar/CJK corpus the spec is trying to protect (§2.2, §3.4).

**Hygiene rule measured here** (`headline_key_usable`: a key must contain ≥1 alphabetic character and be ≥8 chars). Its cost and benefit, as the `headline_clean` lane:

| lane | distinct keys | TRUE fire | FALSE fire | lift |
|---|---|---|---|---|
| `headline` | 16,235 | 3.8% | 0.4% | 9.3630 |
| `headline_clean` | 15,601 | 1.9% | 0.0% | — |

**Verdict:** **the hygiene rule is mandatory, and it is cheap.** Dropping alpha-free / short keys removes 10.6% of resolved signals from lane H and costs 1.9pp of the true fire rate (3.8% → 1.9%) while removing 0.4pp of the false fire rate (0.4% → 0.0%). `build_evidence_fingerprints.py` (T-B2) must apply `headline_key_usable` BEFORE writing `headline_keys`, and publish the dropped count — a residue key is not a headline, and a frozen fingerprint cannot be cleaned later. Note this is a defect in lane H's INPUT, not in `_norm_headline`, which is correct for its own job (syndication detection over an English-dominant front page); the design's mistake is reusing it unfiltered as an identity signal over a 31-language corpus.

**And the rule is necessary but not sufficient.** After hygiene, the most frequent surviving keys are OUTLET NAMES — `blackseanews` (15), `patrisnews` (15), `wildberries` (9), `dsnews ua` (9), `the press project` (6) — the same defect wearing a different hat: when the masthead stamp is not the last `|` segment, the Latin outlet name is the only text that survives deletion of a non-Latin headline. **0.4%** of resolved signals (97) produce such a key. That makes any two stories from one outlet look like one story — the DOMAIN lane in lane H's clothes, and without the domain lane's df ceiling. T-B2 should reject keys that reduce to the signal's own `source_name`/domain (`headline_key_is_outlet_residue` here) as well as alpha-free ones.

Per-language residue on the primary snapshot (top by signal count):

| lang | signals | empty key | digit-residue key | unusable share |
|---|---|---|---|---|
| `xx` | 14,620 | 3,595 | 2,314 | 40.4% |
| `en` | 7,488 | 27 | 32 | 0.8% |
| `ru` | 319 | 224 | 67 | 91.2% |
| `pt` | 253 | 0 | 0 | 0.0% |
| `ar` | 191 | 152 | 39 | 100.0% |
| `es` | 142 | 0 | 0 | 0.0% |
| `tr` | 136 | 0 | 0 | 0.0% |
| `id` | 118 | 0 | 0 | 0.0% |
| `de` | 83 | 0 | 0 | 0.0% |
| `uk` | 81 | 40 | 37 | 95.1% |
| `fr` | 64 | 0 | 0 | 0.0% |
| `it` | 52 | 0 | 0 | 0.0% |
| `fa` | 18 | 18 | 0 | 100.0% |
| `ro` | 17 | 0 | 0 | 0.0% |

## 5. Seed weights `w_E / w_U / w_H`

Rule: `w_lane = precision(true_fire, false_fire), normalised to max=1.0`.

| spec weight | measured lane | precision | **seed value** |
|---|---|---|---|
| `w_E` | entity | 0.9195 | **0.92** |
| `w_U` | max(url, domain) — the locator lane | 0.6518 | **0.652** |
| `w_H` | headline_clean (post-§4d hygiene) | 1.0000 | **1.0** |

Underlying per-lane precisions: `entity` 0.9195 · `domain` 0.6518 · `url` 0.0000 · `headline` 0.9036 · `headline_clean` 1.0000

- ⚠ `url` fires on only 0.0% of TRUE pairs — whatever its precision, it contributes almost no recall, so its weight decides very little.
- ⚠ `headline` fires on only 3.8% of TRUE pairs — whatever its precision, it contributes almost no recall, so its weight decides very little.
- ⚠ `headline_clean` fired on 0 of 500 false pairs, so its precision of 1.0000 is an UPPER BOUND, not a measurement — the rule of three puts the true false-rate anywhere below 0.60%. Its weight is the least trustworthy number in this table.
- ⚠ `headline_clean` fires on only 1.9% of TRUE pairs — whatever its precision, it contributes almost no recall, so its weight decides very little.

> **SEED — the M1/M2 grid sets the operating point; these feed it.** `strength` is a MAX over lanes, so these only decide tie-breaks and where the borderline band lands. They are an INPUT to the M1/M2 grid, never a contradiction of it — if the sweep lands elsewhere, the sweep wins.

**The practical reading is blunter than the table.** Lane E fires on 46% of true pairs; every other lane fires on under 6%. At DP-1, **lane E is not the primary lane — it is effectively the only lane**, and `strength` reduces to `w_E · max_norm_rarity(shared entities)`. The other two weights are contingency for a corpus mix this snapshot does not contain.

## 6. Residuals and honest limits

- **Cross-day df is measured through a decaying window.** Resolvability by day: `2026-07-28` 97.5% · `2026-07-27` 82.5% · `2026-07-26` 69.8% · `2026-07-25` 58.0% · `2026-07-24` 46.6% · `2026-07-23` 31.0% · `2026-07-22` 16.4% · `2026-07-21` 0.0%. df on the low-resolvability days is biased LOW; only the primary day's numbers are proposal-grade.
- **Lane H is Latin-only by construction, and fails UNSAFELY rather than emptily** (§4d). Languages whose headline keys are >80% unusable on the primary snapshot: `ru` (91% of 319), `ar` (100% of 191), `uk` (95% of 81), `fa` (100% of 18). Lane H therefore **cannot** cover the ru/uk entity hole — and spec §3.4 reads as though it might. With lane U also silent at DP-1 (§4c), **Stage 2 has no script-blind lane at all**: for a Cyrillic-only fragment pair, the evidence gate reduces to lane E, whose ru coverage is 10.0% (§2.2). That combination should be stated in the plan before go/no-go 0, not discovered at go/no-go 2.
- **The noise-floor labels are model-produced and single-rater.** They are a first pass, published item-by-item in the `.json` precisely so the number can be contested rather than inherited.
- **df's document unit is the cluster, and clusters are sampled.** `sample_signal_ids` is capped at 24 (spec §2.5: 4.1% of clusters truncated), so every df here is a df over a near-complete, not complete, membership view.
- **The FALSE construction is mechanical, not adjudicated.** It is imported verbatim from the whitened-taus harness so M1/M2/M3 share one definition; it inherits that harness's known bias (cross-script pairs are refused, so the false set skews same-script).
- **The witness families are single-country** (Berlin Pride all DE, Caspian 8/9 IR) — a true set that is easy for every lane on geography. The cross-country/cross-script reconvergence case is NOT represented here and is M1's job to supply.
- **The cross-day probe's TRUE set is label-defined** (SequenceMatcher ≥ 0.80 + shared country across the day boundary) and its old side is measured at 16.4% resolvability, so its absolute rates are a floor, not an estimate. It is here to establish that the DP-2 geometry EXISTS, not to set DP-2's threshold — that is M5, and M5 is gated on ≥14 nights of fingerprints.
- **`w_E/w_U/w_H` are seeds, not an operating point.** They are fitted on one night and two single-country families. The M1/M2 grid is the authority; if it lands elsewhere, it is right and this table is the prior it moved.
- **`snapshot_window_h = [168]` makes the cross-day lanes partly tautological.** Each snapshot re-clusters a seven-day window, so 62.7% of tonight's sampled signals were also sampled last night. A cross-day 'same story' pair therefore shares ARTICLES, not just a story — which is what DP-2 wants, but it means the cross-day URL/domain numbers must never be quoted as evidence that locators survive translation.
- **The 07-23→07-27 label blackout removed five of the eight profiled nights from every label-based construction** (100% NULL `emergent_clusters.label`). It does not affect the df distributions (those need no labels), but it is why the cross-day probe reaches back 6 days. M1/M2 inherit this: their witness families and FALSE sets can only be built on labelled nights, and there are currently three in the window.

---

_Generated 2026-07-28T14:59:02+00:00 · seed 42 · `--days 8` · companion data `2026-07-30-evidence-rarity-calibration.json`._
