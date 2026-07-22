# Task 0 — placebo of the DOMAIN-LEVEL divergence metric

**Date:** 2026-07-22 · read-only, prod · **Verdict: metric does not survive. Close the spec.**

## Why this test

The measurement synthesis placebo'd the **per-keyword** `coverage_count` and showed
it is a lexical-match rate. The attention–coverage divergence design does not use
that field for its metric: its coverage side is Atlas's own classification of
press volume (`signal_topic_assignments` × `atlas_topics.parent_domain`). So the
domain-level metric needed its own control, pre-registered in the plan as Task 0
with the kill threshold written **before** the run:

> ρ high (≳0.7) → domain divergence is the same with fake coverage as with real
> coverage. **The metric is dead. Close the spec, do not fix it.**

## Design

Three arms, identical attention side (7,211 trend pairs / 5,693 distinct keywords,
last 24h, typed with whitened multilingual-e5 into the 32 seed domains):

| arm | coverage side |
|---|---|
| **A · REAL** | press classified in the last 48h (1,099 country×domain rows) |
| **B · PLACEBO** | press classified 5–7 days ago — *before these keywords trended* (1,077 rows) |
| **C · NULL** | arm A with country labels shuffled; 200 draws, to give the floor a distribution |

Comparison space: 960 `(country, domain)` pairs over **96 countries and 10 domains**.

## Results

| quantity | ρ |
|---|---|
| coverage_real vs coverage_placebo | **+0.600** |
| **divergence_real vs divergence_placebo** | **+0.714** (re-run: +0.710) |
| divergence_real vs divergence_NULL (200 shuffles) | mean **+0.497**, sd 0.023, p95 +0.533, max +0.559 |
| divergence_real vs attention_share alone | **+0.548** |

Top-3 under-the-radar domains per country, real vs placebo: **mean overlap
2.27 / 3** across 96 countries; the set is **identical in 36 / 96** countries.

## Reading

**The pre-registered criterion fires.** ρ(real, placebo) = 0.714 ≥ 0.7. Divergence
computed from week-old coverage reproduces divergence computed from current
coverage. Two of every three surfaced domains per country are the same whether the
coverage half is real or a week stale.

**The residual is real but small.** The placebo sits 9.4 sd above the shuffled-country
null (0.710 vs 0.497 ± 0.023), so the metric is not *pure* noise — it does carry
some time-specific coverage information, and the top-3 does change in 60 of 96
countries. Reported so it is not averaged away. It does not rescue the metric: the
comparison that matters for a product is real-vs-stale, and that is 0.71.

**Divergence is mostly the attention side.** ρ(divergence, attention_share) = +0.548,
about the same as the null floor. The coverage half is close to a constant offset —
consistent with ρ(coverage_real, coverage_placebo) = +0.600, i.e. domain proportions
of press volume are substantially stationary week to week.

**The independent, non-threshold kill: resolution.** Only **10 domains** are
populated. A country-scoped "what is under-covered" reading with ten buckets cannot
do the journalistic job — at that grain the answer is always some permutation of
conflict / governance / climate. The obvious fix is to compute at `slug` (56
categories) instead, but the design rejected that on measured grounds: the specific
category assignment is unreliable (`snelheidscontrole` → gang-control,
`uppehållstillstånd` → fuel-subsidy) while the domain is stable. **The granularity
that makes the metric honest is the granularity that makes it uninformative.** That
is a design dead-end independent of the placebo, and it is the cleaner reason to stop.

## What survives

- The **GDELT encoder defect** — root-caused to `ingest_v2.py:427`, in flight in a
  separate session. ~47% of GDELT rows were embedded, NER'd and dedup'd from
  mojibake. This is the session's real finding and it is unrelated to the metric.
- **`_INFO_DESERT_FLOOR` deletion** — measured inverted, fires on 0 of 99 trends
  countries.
- **Cross-lingual typing of public attention** — whitened e5 places a local-language
  query into Atlas's taxonomy with no per-language lexicon (margin spread
  0.122 → 0.308). This works and is reusable; it just has nothing sound to feed
  in this design.
- The negative results on wiki, forums, ensemble and voice-mix, which close four
  directions.

## Reproduce

`scratchpad/task0_domain_placebo.py` (three arms) and `scratchpad/null_dist.py`
(200-shuffle null). Both read-only; typing cached in `task0_typed_cache.json`.
