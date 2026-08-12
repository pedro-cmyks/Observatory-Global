# M0 — measurement for P3 (Brief = diario de la cobertura)

**Task**: T3.0 of `docs/superpowers/plans/2026-08-12-puerta-y-carpetas.md`.
**Status**: MEASURED. Read-only. Nothing pre-registered here — the three bars
below are **proposals**; they freeze when the P3 build starts (T3.1/T3.2).
**Date**: 2026-08-12. **Machine**: M1, all queries `taskpolicy -b`, bounded.
**Data**: `atlas_daily_editions` (25 sealed editions, 2026-07-12 → 2026-08-11),
`topic_members` ⋈ `signals_v2` (24h raw membership), `topic_movement`
(movement-kalman-v1), prod `/api/v2/briefing?hours=24` snapshot
(generated 2026-08-12).
**Companion data**: `2026-08-12-m0-measurement.json` (every number below).

## The three proposals

| | bar | measured support | confidence |
|---|---|---|---|
| **(a) veto jalapeño** | largest **Jaccard@0.5 headline family ≥ 0.70** of raw 24h membership, min n=8 → may never lead | 950-topic histogram; fires on 8 (0.84%); **100% hand-checked precision**; witness at 0.846 in an **empty bin** (nothing between 0.667 and 0.846) | **high** |
| **(b) el vacío** | **multiplier ≥ 3.0** AND **self-voice ≤ 0.20** AND volume ≥ 20 AND `known_origin_n ≥ 50` | anomaly side 6/7 days = 86%; witness TL **11.2x / 0.00 self-voice**, #1 by 5x; joint rate **bounded, not measured** | **low** — re-derive from logged candidates |
| **(c) lo que sube** | **surprise ≥ 2.5 AND velocity > 0 AND volume ≥ 20**, top 2–3 | `topic_movement` fresh **18/18 days**; ≥2 items on **15/15 days** (median 10); ~p99 selectivity; excludes the witness | **high** |

Each bar is refuted by, and survives, its own witness: (a) fires on the jalapeño,
(b) fires on East Timor, (c) *excludes* the jalapeño.

---

## 0 · The finding that reorders the build

The plan assumes the veto lands in `select_daily_edition` / the seal step.
**Measured: the seal already handles the witness, and the visible Brief does
not read the seal.**

- On the 2026-08-11 sealed edition the jalapeño story (`dynamic-topic-11877`,
  "Taylor Farms Jalapeño Recall") scored **0.705 — rank 26 of 964 by score,
  status `downranked`, pareto_front 1** — outside the 12 selected, so the Pareto
  selection kept it out of the lead (lead was "Iran Strait of Hormuz", 0.924).
  Its low `global_breadth` (0.267), `language_breadth` (1) and `velocity`
  (0.044) sank it by construction. (Note: `selection.ledger` is **not** stored in
  score order — verified — so ledger position 88 is not a rank; rank 26 is the
  score-derived one.)
- **All 25 sealed editions carry `status='degraded'`.** Per the degraded-seal
  path the Brief serves LIVE threads, so the front page is ranked by
  `thread_ranking.rank_threads` over the briefing `top_threads`, not by the
  Pareto selection.
- Live `top_threads[0]` at measurement time **is** the witness:
  `dynamic-topic-11877` "Jalapeño Salmonella Outbreak", 67 signals, 24 served
  receipts.

**Consequence for T3.1**: a veto applied only to `select_daily_edition` would
not have touched its own witness. It must land on the live lead path
(`rank_threads` / `lib/leadConfidence.selectLiveLead`) as well — or the seal
must stop being degraded. Both, ideally.

---

## (a) VETO JALAPEÑO — the syndicated-family bar

### a.1 Which syndication signal, and why

Asked to choose between `thread_ranking._norm_headline` and
`corroboration.cluster_syndicated`. **Measured both. Neither works as-is; the
Jaccard clusterer works at τ=0.5 once the denominator is fixed.**

**`_norm_headline` exact-key is refuted for this job.** The witness's wire
family is stamped with an **en-dash** masthead suffix:

```
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – The Fort Morgan Times
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – The Morning Call
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – Hazleton Standard Speaker
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – The Press Democrat
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – Sun Sentinel
'Guac signal' sparked Chipotle's frantic bid to recall jalapeños – Orlando Sentinel
```

`_norm_headline` strips only the **pipe**-delimited masthead stamp (the 2026-07-18
AU Community Media signature), so each of these folds to a *different* key.
Witness scores **0.077** on raw membership (0.042 on served receipts) — near the
population floor. Across the 950-topic universe its p99 is only 0.375: exact-key
matching under-detects wire families systematically.

**`cluster_syndicated` (Jaccard over token sets) is the right shape but carries a
Latin-only tokenizer.** `corroboration._tokens` is `[a-zà-ÿ0-9]{3,}` — the exact
defect class `_norm_headline` fixed on 2026-07-30. Cyrillic/CJK/Greek/Devanagari
headlines reduce to their **digits**, so three Russian/Ukrainian topics clustered
on the bare token `"2026"` and produced fabricated syndication families:

| topic | label | jac@0.5 | what the "family" actually was |
|---|---|---|---|
| dt-2746 | Moscow 24 Expert Tips Roundup | 0.552 | password advice + a flood + a cruise ad + a holidays list |
| dt-450 | Ukraine 2026 Education and Housing Costs | 0.533 | budget + visa + smartwatches + FX rates |
| dt-6184 | Central Bank Forecasts | 0.529 | budget + two IEA oil stories + an ambulance procurement |

All three land in **[0.50, 0.56)** — below the bar proposed here, so they do not
contaminate it. They *would* contaminate a bar at 0.50.

> **Build requirement (blocking for T3.1)**: fix the tokenizer before freezing
> the bar — fold like `_fold_headline` (NFKD + `[\W_]+`, script-safe) and treat a
> token set with no letters as *unclusterable* (never matches), mirroring
> `_degenerate_key`. Otherwise the veto misfires on non-Latin coverage, which is
> precisely the coverage the Brief exists to surface.

**Second build requirement**: the greedy clusterer is **order-sensitive**. The
same 26 witness members returned in two different row orders scored `top_jac0.6`
= 0.538 and 0.731. τ=0.5 was stable across both (0.846 twice), but T3.1 must sort
deterministically before clustering.

### a.2 Which denominator — NOT the sealed receipts

**The package receipts cannot measure syndication: they are de-duplicated by
construction.** Every sealed lead carries ~6 receipts, one per outlet, and the
serving path applies `DISTINCT ON (LOWER(headline))`. The measurement saturates
at the floor:

| edition | lead | n | top-family share | distinct outlets |
|---|---|---|---|---|
| 2026-08-11 | Iran Strait of Hormuz | 6 | 0.167 (1/6) | 6 |
| 2026-08-10 | Typhoon Dolphin Emergency Response | 4 | 0.250 (1/4) | 4 |
| 2026-08-09 | Spain Italy Border Checks | 6 | 0.167 (1/6) | 5 |
| 2026-08-08 | Defense Agreement Clarifications | 6 | 0.167 (1/6) | 5 |
| 2026-08-07 | Russian Executions of POWs | 6 | 0.167 (1/6) | 6 |
| … 16 more … | | | **0.167 in 18 of 21** | |
| 2026-07-12 | Russian Attacks on Zaporizhzhia | 1 | 1.000 (1/1) | 1 |

n=21 editions with a lead: min 0.167 · p25 0.167 · **median 0.167** · p75 0.167 ·
max 1.000 (the max is the n=1 degenerate case). The distribution is a constant.

Edition-coverage caveats: 4 of 25 editions produced **no lead receipts at all**
(2026-07-21/28/29/30) and are excluded; a further 4 (2026-07-12/13/22/23) carry
no `package.article.story_id` and their lead was resolved via the graph's first
node (graph node order == `selection.selected_ids` order, verified on 2026-08-11).

**The honest denominator is raw 24h membership** (`topic_members` role='evidence',
not quarantined, joined to `signals_v2`) — the story's actual coverage, before
serving de-duplicates it.

### a.3 The histogram

Universe: **950 dynamic topics** with ≥8 raw members in the last 24h
(32,860 member rows). Metric: largest Jaccard@0.5 family ÷ n.

```
[0.0,0.1)   489  ############################################################
[0.1,0.2)   286  ###################################
[0.2,0.3)   110  #############
[0.3,0.4)    33  ####
[0.4,0.5)    10  #
[0.5,0.6)    11  #
[0.6,0.7)     3  
[0.7,0.8)     0            <-- empty bin
[0.8,0.9)     2  
[0.9,1.0]     6  
```

min 0.004 · p50 **0.091** · p75 0.145 · p90 0.250 · p95 0.333 · p99 0.645 · max 1.000

| bar | topics ≥ bar | % of universe |
|---|---|---|
| 0.40 | 32 | 3.4% |
| 0.50 | 22 | 2.3% |
| 0.60 | 11 | 1.2% |
| **0.70** | **8** | **0.84%** |
| 0.80 | 8 | 0.84% |

### a.4 Hand-check of the tail (the FP audit)

All 32 topics ≥0.40 were hand-classified from their largest family's actual
member headlines + outlets (full dump in the JSON).

**True amplification** (a veto *should* fire):

| topic | jac@0.5 | family | mechanism |
|---|---|---|---|
| dt-3895 | 1.000 | 9/9 | tribunnews.com regional-budget template, one outlet × N municipalities |
| dt-12302 | 1.000 | 10/10 | nrhz.de single-outlet self-listing |
| dt-12309 | 1.000 | 8/8 | se933.com radio-station listing junk |
| dt-8607 | 0.923 | 12/13 | AU Community Media "Phuket Elephant Sanctuary" × 12 mastheads |
| dt-1706 | 0.909 | 20/22 | sponichi.co.jp single-outlet celebrity feed |
| dt-7962 | 0.900 | 9/10 | sponichi.co.jp same |
| dt-10814 | 0.865 | 32/37 | AU Community Media "Brodaty dementia" × 32 mastheads |
| **dt-11877** | **0.846** | **22/26** | **the witness — one wire piece × 22 US mastheads** |

**False positives that a bar must clear** — real multi-source stories whose
independent outlets word the same facts alike (or run the same agency wire):

| topic | jac@0.5 | why it must not be vetoed |
|---|---|---|
| dt-4585 | 0.667 | Urban One radio network — same text, but a real arrest story |
| dt-11210 | 0.625 | dpa "BSW für AfD-Einbindung nach Landtagswahl" — real German politics |
| dt-9316 | 0.583 | Assad sentenced to death in absentia — 7 independent outlets, 4 continents |
| dt-8591 | 0.538 | "Colombia quake death toll tops 250" — AP on a real disaster |
| dt-1787 | 0.529 | "Weiter Hoffnung auf Überlebende in Kolumbien" — dpa, real disaster |
| dt-9064 | 0.444 | North Korea ballistic missile launch — 4 Spanish outlets |
| dt-1619 | 0.419 | North Korea missile — 13 members across **4 languages** |

Precision by bar (hand-checked):

| bar | vetoed | true amplification | precision |
|---|---|---|---|
| 0.50 | 22 | ~16 | ~73% |
| 0.60 | 11 | 10 | ~91% |
| **0.70** | **8** | **8** | **100%** |
| 0.80 | 8 | 8 | 100% |

### a.5 → PROPOSED BAR

> **X = 0.70**, on the **largest Jaccard@0.5 headline family** over **raw 24h
> membership**, with a **minimum of n ≥ 8** members. A story at or above X may
> never take the lead slot (it stays in the list — damp/veto-the-slot, never a
> silent drop).

Why 0.70:

- **The witness clears it with margin**: 0.846 vs 0.70 = +0.146 (vs +0.046 at 0.80).
- **It sits inside an empty bin.** No topic in the entire 950-universe scores
  between 0.667 and 0.846 — the bar falls in natural separation, not through a
  cluster.
- **100% hand-checked precision.** All 8 vetoed topics are template spam,
  single-outlet feeds, or one wire piece across mastheads.
- **The nearest real story is far below**: Assad 0.583, Colombia quake 0.538,
  NK missile 0.419 — all safe by ≥0.117.
- **It fires rarely**: 0.84% of the universe, ~8 topics/day — a lead-slot veto
  should be a rare, legible event.
- The three tokenizer artifacts (§a.1) all sit ≤0.552, so the bar survives even
  if the tokenizer fix slips.

**Minimum-n guard is load-bearing**: without it, a 1-member topic scores 1.000
(observed: "Syria Russia Bases Deal", n=1). n≥8 is the floor used to build this
histogram; the sealed ledger's existing `evidence_floor` is the natural home.

### a.6 → FROZEN FIXTURE (G-JALAPEÑO)

```
thread_id            dynamic-topic-11877
label                Jalapeño Salmonella Outbreak
                     (sealed 2026-08-11 ledger label: "Taylor Farms Jalapeño Recall")
observed             2026-08-12, live /api/v2/briefing?hours=24 top_threads[0]
served signal_count  67
raw 24h members      26
largest family       22 of 26  = 0.8462   (Jaccard 0.5)
                     14 of 26  = 0.5385   (Jaccard 0.6, order-sensitive: 0.731 in a second run)
                      4 of 26  = 0.1538   (Jaccard 0.7)
reprint mass @0.5    0.9231
top _norm_headline   0.0769   <-- exact-key signal FAILS to see it
distinct outlets     26 of 26  (outlet_diversity 1.00)
distinct owner grps  26        <-- source_tiers.ownership_group is BLIND here
country_breadth      2      language_breadth 1
served headline_diversity  1.000   <-- the existing damp gives it FULL marks
sealed 2026-08-11    score 0.705, rank 26/964 by score, downranked, pareto_front 1
family text          "'Guac signal' sparked Chipotle's frantic bid to recall
                      jalapeños – <masthead>"
```

**Negative fixture** (a real multi-source story that must still be able to lead):
`dynamic-topic-1619` "North Korea Missile Launch" — n=31, largest family 13
(0.419), 4 languages, outlet_diversity 0.94.

### a.7 Why the existing damp did not stop it — the mechanism

`rank_threads` (v2) already multiplies the volume term by
`headline_diversity(t)`. On the witness it returns **1.000 — the maximum, no
damp at all** (confirmed in the served payload: `quality.headline_diversity: 1.0`).
Two independent reasons:

1. It reads **`evidence_samples`**, which the serving path has already
   de-duplicated to one row per distinct headline/outlet — so
   `outlet_ratio = 24/24 = 1.0` and `headline_ratio = 24/24 = 1.0`.
2. Even on raw membership its `_norm_headline` exact-key would score
   0.077 reprint concentration, because of the en-dash suffix (§a.1).

So the veto is not a new idea bolted onto a working damp — **it is the repair of
a damp that is currently blind**. T3.1 should treat `headline_diversity` itself
as in-scope: fix its denominator (raw membership) and its matcher (Jaccard@0.5,
script-safe), and the veto becomes a threshold on a signal that finally means
something.

---

## (b) EL VACÍO — the attention/self-voice divergence bar

### b.1 What is measurable, and what is not

**The anomaly side has 8 days of history (7 usable). The self-voice side has
none.** Two independent causes, both verified:

1. `signals_v2` hot retention is ~7 days (`min(created_at) = 2026-08-05`), and
   `country_hourly_v2` is a matview over it (same span). `country_daily_v2` is
   **empty**.
2. The archive lane that *would* carry it does not compute it:
   `historical_process_partition.py` sets
   `bucket["local_voice_ratio"] = None` **unconditionally**, so
   `historical_topic_country_daily.local_voice_ratio` — which runs back to
   2020-09-15 — is NULL for every row.

So the ~14-day retrospective the plan asks for is **not reconstructible today**.
What is measured instead: the **anomaly side over 8 days (7 with a full
baseline)**, the **voice side for the current 24 h window**, and the **witness**.

> **Build requirement for T3.2**: log the day's EL VACÍO candidate (country,
> multiplier, self-voice, receipt ids) into the sealed package. Two weeks of that
> makes the joint rate verifiable — and it is the only way it ever will be, short
> of teaching the archive lane to compute `local_voice_ratio`.

### b.2 The witness — confirmed

```
country              TL (Timor-Leste / East Timor)
day                  2026-08-12
daily volume         28          baseline (leave-one-out mean, 6 days)  2.5
multiplier           11.2x       <-- reported witness: "12x"
local_voice_ratio    0.0000      <-- reported witness: "100% foreign"
atlas_heat           0.5426
rank today           #1 anomaly of all countries with n>=20
```

The second-place anomaly today is `BW` at 2.19x — the witness leads the field by
**5x**. Today's full top-10 (n≥20):

| cc | multiplier | n | baseline | local_voice_ratio |
|---|---|---|---|---|
| **TL** | **11.20** | 28 | 2.5 | **0.000** |
| BW | 2.19 | 21 | 9.57 | 0.5 † |
| ZW | 2.03 | 105 | 51.71 | 0.038 |
| BB | 1.56 | 27 | 17.29 | 0.5 † |
| MN | 1.52 | 65 | 42.71 | 0.5 † |
| KP | 1.51 | 122 | 80.57 | 0.000 |
| FJ | 1.51 | 94 | 62.14 | 0.358 |
| MO | 1.47 | 22 | 15.00 | 0.5 † |
| UG | 1.44 | 112 | 77.57 | 0.5 † |
| KG | 1.30 | 255 | 196.00 | 0.935 |

† **`0.5` is a SENTINEL, not a measurement.** `country_heat_v2` (migration 017)
computes `CASE WHEN known_origin_n >= 50 THEN local_voice_ratio_raw ELSE 0.5 END`
— so 0.5 means *too few origin-attributable signals to judge*. Five of today's
top ten carry it.

> **Build requirement for T3.2**: treat `local_voice_ratio = 0.5` (or
> `known_origin_n < 50`) as **unknown**, never as "half local". A bar written as
> `lvr <= V` happens to exclude the sentinel and is therefore fail-safe by
> accident — but the section must not *report* a sentinel country as measured
> silence. This is the same honesty rule that killed silent-risk on 2026-07-22:
> press silence must be measured, not assumed from absence.

### b.3 The anomaly side, per day

Countries clearing each multiplier bar (daily volume ≥ 20, baseline = leave-one-out
mean of the other retained days — the shape the production detector uses over the
same matview):

| day | countries scored | ≥2x | ≥3x | ≥4x | ≥5x | ≥8x |
|---|---|---|---|---|---|---|
| 2026-08-05 † | 195 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-06 | 195 | 10 | 1 | 0 | 0 | 0 |
| 2026-08-07 | 195 | 8 | 2 | 1 | 0 | 0 |
| 2026-08-08 | 195 | 2 | 0 | 0 | 0 | 0 |
| 2026-08-09 | 195 | 5 | 1 | 0 | 0 | 0 |
| 2026-08-10 | 195 | 20 | 4 | 2 | 1 | 1 |
| 2026-08-11 | 195 | 10 | 2 | 1 | 1 | 0 |
| 2026-08-12 | 195 | 3 | 1 | 1 | 1 | 1 |

† 2026-08-05 is the first retained day; its baseline is truncated, so it is
excluded from the rates below.

**Days with ≥1 anomaly (of 7 full days):**

| bar | days | rate |
|---|---|---|
| ≥2x | 7/7 | 100% |
| **≥3x** | **6/7** | **86%** |
| ≥4x | 4/7 | 57% |
| ≥5x | 3/7 | 43% |

### b.4 → PROPOSED BAR

> **multiplier ≥ 3.0** (daily volume vs the country's trailing daily baseline)
> **AND self_voice_ratio ≤ 0.20** **AND daily volume ≥ 20** **AND the voice is
> attributable** (`known_origin_n ≥ 50`; the `0.5` sentinel is *unknown*, never a
> candidate). Rank candidates by multiplier, take the top one. **Honest-empty
> when nothing clears** — "hoy no hay vacío que supere la barra" is the state.

Why:

- **The anomaly side alone gives 86% of days (6/7).** The self-voice condition
  can only subtract, so the joint rate is bounded above by 86% — and today's
  cross-section shows the voice condition removing about half the field (5 of the
  top 10 are sentinel/unknown, 2 are genuinely local). That places the joint
  squarely in the **50–80% target band**, though it is *bounded*, not measured
  (§b.1).
- **≥4x would already be too tight**: 57% of days on the anomaly side *before*
  the voice condition, so the joint would fall below the band.
- **≥2x is too loose**: 20 countries on 2026-08-10 is a list, not a finding, and
  a 2x wobble on a small country is inside normal variance.
- **The witness clears by a wide margin**: 11.2x vs 3.0 — and it is the day's #1
  anomaly by 5x, so "the best divergence candidate of the day" and "the witness"
  are the same row.
- `volume ≥ 20` keeps a 3-signal country from posting a 10x on noise;
  `known_origin_n ≥ 50` is the matview's own confidence floor, reused rather than
  reinvented.

**This bar is the least-supported of the three.** The joint rate is inferred, not
measured. It should be re-derived from two weeks of logged candidates (§b.1)
before it is treated as settled — the anomaly side and the witness are solid, the
joint frequency is not.

---

## (c) LO QUE SUBE — the meaningful-acceleration bar

### c.1 Freshness — verified, no gaps

`topic_movement` (`movement-kalman-v1`) is written **every day, 2–3 runs/day,
for 18 consecutive days** (2026-07-26 → 2026-08-12, the full retained span).
No missing day, no stale run.

| day | rows | topics | of which ACTIVE | runs | last run (UTC) |
|---|---|---|---|---|---|
| 2026-08-12 | 10,965 | 5,620 | 2,527 | 2 | 10:54 |
| 2026-08-11 | 11,509 | 5,772 | 2,509 | 2 | 12:02 |
| 2026-08-10 | 11,272 | 5,651 | 2,482 | 2 | 11:24 |
| 2026-08-09 | 16,633 | 5,713 | 2,522 | 3 | 23:02 |
| 2026-08-08 | 10,852 | 5,481 | 2,360 | 2 | 23:02 |
| … 13 more days, all present … | | | | | |
| 2026-07-26 | 5,239 | 5,239 | 1,159 | 1 | 23:02 |

The serving population (`dynamic_topics.state='active'` carrying a movement row)
grew 1,159 → 2,527 over the window. **LO QUE SUBE has a live daily substrate.**

### c.2 Which Kalman field

Pooled over the latest run per day per active topic (15 days, ~33k topic-days):

| field | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| `velocity` | −0.002 | 0.043 | 0.214 | 0.346 | 0.617 | 1.841 |
| `surprise` | 0.721 | 1.091 | 1.480 | 1.754 | 2.457 | 6.005 |

**`velocity` alone cannot carry the bar.** Its whole distribution is compressed
below 1.0 (p99 = 0.617); a bar at v≥1.0 yields **0–7 topics/day (median 2)** and
returns *zero* on 6 of 15 days. This is consistent with the 2026-07-04 backtest
finding that velocity mean-reverts and does not lead volume.

**`surprise` is the well-behaved field** — smooth, wide, and a bar at 2.5 sits
at roughly its p99, i.e. the top ~1% of active topics.

`trend='surging'` is far too loose to be a bar on its own: 55–156 topics/day
(median 106).

### c.3 Candidate bars, per day (15 days, ACTIVE topics, latest run per day)

| rule | min/day | median | max | days with ≥2 items | days with ≥3 |
|---|---|---|---|---|---|
| `s≥2.5` | 6 | 17 | 45 | 15/15 | 15/15 |
| `s≥3.0` | 1 | 6 | 24 | 14/15 | 14/15 |
| **`s≥2.5 & v>0`** | **2** | **10** | **37** | **15/15** | 14/15 |
| `s≥2.0 & v>0` | 17 | 28 | 81 | 15/15 | 15/15 |
| `s≥2.5 & v>0 & vol≥20` | 2 | 10 | 37 | 15/15 | 14/15 |
| `trend='surging'` | 55 | 106 | 156 | 15/15 | 15/15 |

### c.4 → PROPOSED BAR

> **`surprise ≥ 2.5` AND `velocity > 0` AND `volume ≥ 20`**, over active topics,
> reading the latest `topic_movement` run of the edition day. Take the top 2–3 by
> surprise. Honest-empty if nothing clears.

Why:

- **The section is always servable**: 15/15 days yield ≥2 items (median 10, min 2).
  The section asks for "2-3 items"; the bar never comes up short.
- **`v>0` is semantically load-bearing**: LO QUE SUBE means *rising*. `s≥2.5`
  alone admits high-surprise topics that are *cooling* — a surprise spike on a
  collapsing story is not "lo que sube".
- **It is genuinely selective**: ~p99 of the surprise distribution, ~0.4% of
  active topics, vs 4% for `trend='surging'`.
- **It excludes the jalapeño.** Measured today the witness carries
  `surprise = 2.2995`, `velocity = 0.396`, `trend = 'surging'`, `volume = 86` —
  it clears `s≥2.0 & v>0` and `trend='surging'` but **fails `s≥2.5`**. A
  service/wire recall story should not be the day's rising news either, so the
  bar that keeps it out of the LEAD should keep it out of LO QUE SUBE. This is a
  second, independent reason to pick 2.5 over 2.0.
- **`volume ≥ 20` is free insurance**: it changed no daily count in the measured
  window (identical to the rule without it), so it costs nothing and guards the
  freak-swing-on-a-tiny-base class that `_MOVEMENT_VOL_FLOOR` already guards in
  `rank_threads`.

**Residual**: 2026-08-12 is a partial day (last run 10:54 UTC) and produced the
minimum, 2 items. The bar should be re-checked once against a full day before
freezing; if a 3-item floor is required rather than 2, `s≥2.0 & v>0 & vol≥20`
(min 17/day) is the fallback — at the cost of admitting the jalapeño class.

---

## Reproduce

All scripts are read-only. Run from the repo root with
`/Users/pedro/AtlasLocalWorker/.env` sourced and `backend/.venv/bin/python`,
under `taskpolicy -b`.

- (a) universe histogram — `topic_members` ⋈ `signals_v2`, 24h, ≥8 members;
  largest Jaccard@0.5 family ÷ n.
- (a) sealed leads — `atlas_daily_editions`: lead = `package.article.story_id`,
  matched to `graph.nodes[].label` → `node_id`, receipts filtered on that
  `node_id`.
- (b) — anomaly from `country_hourly_v2` (cheap); self-voice from
  `country_heat_v2.local_voice_ratio`. **Wide `signals_v2` aggregates are not
  viable on this pooler under nightly load** — a 9-day `GROUP BY day, country`
  and its day-chunked variants all exceeded 240 s; parameterised `created_at`
  bounds additionally forced a generic plan. Use the matviews.
- (c) — `topic_movement`, latest run per topic per day, joined to
  `dynamic_topics` on `('dynamic-topic-' || id::text) = topic_id`
  (`topic_id` is **text**, not the bigint `dynamic_topics.id`).

## Residuals and honest limits

1. **The syndication histogram is a single 24-hour snapshot** (2026-08-12).
   Raw membership is not retained per past edition, so a 30-edition histogram of
   *lead* syndication is not reconstructible — the sealed receipts that do
   survive are pre-deduplicated (§a.2). The bar is therefore set on a
   950-topic cross-section plus one hand-checked tail, not on 30 days of leads.
   Re-running the histogram on a second day before freezing X is cheap and
   advisable.
2. **`corroboration._tokens` is Latin-only** and must be fixed before the bar is
   frozen (§a.1). The three measured artifacts sit below the proposed X, so the
   proposal survives the defect — but the *build* must not ship on top of it.
3. **The greedy clusterer is order-sensitive** (§a.1); T3.1 must sort before
   clustering or the veto is non-deterministic.
4. **All 25 sealed editions are `degraded`.** Every "sealed lead" number here
   describes an artifact the front page is not currently reading. This is itself
   a finding (§0) and G-SELLO should probably include "the seal reaches `ready`".
5. `source_tiers.ownership_group` does not know US newspaper groups (Tribune
   Publishing / MediaNews Group), so ownership-collapse is **not** a usable
   syndication signal for the witness: 22 reprints read as 22 independent
   voices. Headline-family is the signal that works.
6. **(b) is the weak one.** Its joint rate is inferred from the anomaly side
   (86%) times an unmeasured voice-side attrition. The two structural blockers
   (7-day hot retention, and the archive lane hard-coding `local_voice_ratio =
   None`) mean no amount of querying fixes this retrospectively — only forward
   logging does. Treat X_vacío as provisional until two weeks of candidates exist.
7. **`local_voice_ratio = 0.5` is a sentinel** (`known_origin_n < 50`), not a
   measurement — 5 of today's top-10 anomalies carry it. Any consumer of that
   column that reads 0.5 as "half local" is wrong.

## Suggested amendments to the plan (T3.1/T3.2)

1. **T3.1 must cover the live lead path**, not only `select_daily_edition` (§0).
2. **T3.1 should repair `headline_diversity` rather than add a parallel veto**
   (§a.7) — same signal, fixed denominator and matcher, with X as its threshold.
3. **Two tokenizer/determinism fixes are blocking** for (a): script-safe folding
   with a degenerate-token guard, and a deterministic sort before clustering (§a.1).
4. **T3.2 must log the EL VACÍO candidate into the sealed package** so its bar can
   ever be validated (§b.1).
5. **G-SELLO should include "the seal reaches `ready`"** — 25 of 25 editions are
   `degraded`, which is why the seal's own correct selection never reaches a reader.

---

## ADDENDUM (T3.1, 2026-08-12) — the repaired signal, and why 25/25 seal `degraded`

Appended by T3.1 after the (i) `headline_diversity` and (ii) `corroboration`
repairs. Read-only for §D; §A–C record the re-measurement that froze X.

### A · The histogram, re-measured on the repaired signal

Same universe (950 dynamic topics, ≥8 raw 24h members), same metric (largest
Jaccard@0.5 family ÷ n), now with the script-safe tokenizer, the
deterministic content-ordered best-fit clusterer, and the dash-repaired
`_norm_headline`. Fresh 24h window (~5 h after M0).

```
bin          REPAIRED    M0
[0.0,0.1)       492     489
[0.1,0.2)       300     286
[0.2,0.3)       105     110
[0.3,0.4)        29      33
[0.4,0.5)         9      10
[0.5,0.6)         5      11     <-- the fabricated families are gone
[0.6,0.7)         4       3
[0.7,0.8)         0       0     <-- STILL EMPTY
[0.8,0.9)         2       2
[0.9,1.0]         4       6
```

min 0.004 · p50 **0.091** · p75 0.143 · p90 0.222 · p95 0.300 · p99 0.600 · max 1.000
(M0: p90 0.250 · p95 0.333 · p99 0.645 — the tail thinned, the body did not move.)

| bar | repaired | % | M0 |
|---|---|---|---|
| 0.40 | 24 | 2.53% | 32 |
| 0.50 | 15 | 1.58% | 22 |
| 0.60 | 10 | 1.05% | 11 |
| **0.70** | **6** | **0.63%** | 8 |
| 0.80 | 6 | 0.63% | 8 |

**X = 0.70 FROZEN**, on the largest Jaccard@0.5 family over raw 24h
membership, with a minimum **family** size of 8 (the parent task's stricter
form of M0's n≥8; on this universe both guards select the same 6 topics).

The bar still falls inside natural separation: nothing scores between **0.667**
(dt-4585, Urban One radio network — a real arrest story) and **0.846** (the
witness). All 6 topics at or above the bar are amplification, hand-checked:

| topic | share | family | mechanism |
|---|---|---|---|
| dt-12302 | 1.000 | 10/10 | nrhz.de single-outlet self-listing |
| dt-12309 | 1.000 | 8/8 | se933.com radio-station listing junk |
| dt-3895 | 1.000 | 9/9 | tribunnews.com regional-budget template |
| dt-8607 | 0.923 | 12/13 | AU Community Media wire × 12 mastheads |
| dt-10814 | 0.865 | 32/37 | AU Community Media wire × 32 mastheads |
| **dt-11877** | **0.846** | **22/26** | **the witness** |

### B · What the repairs changed, measured

- **The three Cyrillic artifacts collapsed**: dt-2746 0.552 → **0.035**,
  dt-450 0.533 → **0.067**, dt-6184 0.529 → **0.118**. The fabricated
  "families" built on the bare token `"2026"` no longer exist.
- **Two of M0's eight vetoed topics were artifacts of the same defect**:
  dt-1706 0.909 → **0.045** and dt-7962 0.900 → **0.100**, both
  `sponichi.co.jp` Japanese single-outlet feeds, same member count. M0's
  *label* was right (a single-outlet feed IS amplification) but the evidence
  was a digit artifact. After the repair the headline-family signal honestly
  reports that it cannot see that class — **single-outlet non-Latin feeds need
  an OUTLET-concentration signal, which this one is not.**
- **The exact-key matcher now sees the witness as well as the clusterer does**:
  `top_normkey` 0.077 → **0.846**, identical to `top_jac0.5`. The dash strip
  alone recovers the whole wire family. Template families (dt-12302 0.100,
  dt-3895 0.111) still need Jaccard, so both repairs are load-bearing.
- **The negative fixture moved further to safety**: dt-1619 (NK missile,
  4 languages) 0.419 → **0.161**.
- **Live**: the witness's served `headline_diversity` went **1.000 → 0.917**.

### C · Where the veto had to land, and what it costs

The raw-membership join is not reachable on the request path — measured on
prod under nightly load: **72 s cold / 5.7 s warm for 41 topics**, against a
15 s serving budget. But the veto only decides slot 1, so only the threads
that could take it are queried: a LATERAL over the **top 4** costs **2.0 s
cold / 0.1 s warm** (26–107 rows). Everything below the lead is judged by the
served receipts alone, expanded by `syndication_count`.

Honest residual: for dynamic topics `topic_members` is itself a projected
sample (~24–26 rows per topic in this window), not full membership — so the
share is measured over the ETL's sample, not the whole story. The witness's
amplification is visible in that sample (22 of 26) and was hand-checked, but a
story whose reprints fall outside the sample would be invisible to the veto.

### D · Why all 25 sealed editions carry `status='degraded'` — the standing condition

**Named: `_edition_status` demands UNANIMOUS per-story-node attribution, and
only about half of story nodes ever have it.**

`build_daily_publication._edition_status` returns `ready` only when all five
readiness dimensions are `ready`. Two of them are computed as an *all-nodes*
conjunction (`investigation_graph.py:672-702`):

- `who` is `ready` only when **every** story node carries a verified subject or
  verified subject country (`story_nodes_with_actor == len(story_nodes)`);
- `where` is `ready` only when **every** story node carries verified subject
  geography.

Measured over the 25 sealed editions (read-only, from the stored artifacts,
using the production helpers):

| | count |
|---|---|
| editions failing on readiness | **24 of 25** |
| …with `who:actor_attribution_incomplete_for_story_nodes` + `where:subject_geography_incomplete_for_story_nodes` | 19 |
| …structurally empty (0 story nodes → who/what/when/where/how all missing) | 4 (2026-07-21/28/29/30) |
| editions failing the completion arm (`receipt_fetch_error` or `cursor_exhausted=false`) | **0 of 25** |
| editions exceeding the 6 h `data_lag_hours` bar | 6 of 25 |

Per-node coverage across the 21 non-empty editions — **252 story nodes**
(12 per edition, every edition):

- **130 carry an actor (51.6%)**
- **118 carry verified subject geography (46.8%)**
- exactly **1 edition of 21** reached unanimity on actor, and **1** on geography

**The decisive row: 2026-07-13 is the one edition in 25 that reached all five
dimensions `ready` (12/12 actors, 12/12 geography). It still sealed
`degraded`, because its `data_lag_hours` was 8.455 > 6.** So on the
only night the readiness conjunction was satisfiable, the freshness arm failed
it. No edition has ever cleared both.

The arithmetic is the finding: an all-or-nothing conjunction over 12 nodes
turns ~50% per-node attribution into a ~0% edition pass rate
(0.5¹² ≈ 0.02%). The two dimensions that fail are exactly the two standing
enrichment gaps — verified subjects come from NER (`nlp_persons`, the #184
throughput backlog) and verified subject countries from subject geography
(#238). The seal is not lying: `who`/`where` are `partial`, not `missing`, and
the union of names is served. It simply can never say `ready`.

**Not fixed here** (it is a policy decision, not a one-liner): whether a
`partial` on `who`/`where` should degrade a whole edition, or whether the bar
should be a *fraction* of story nodes (e.g. ≥⅔ attributed) with the shortfall
named in the payload. Both readiness computation and `_edition_status` would
have to move together, and G-SELLO would need to state which of the two it is
asserting. Filed as the named condition behind M0 §0 and residual 4: **the
seal's correct Pareto selection never reaches a reader because the edition can
never leave `degraded`.**
