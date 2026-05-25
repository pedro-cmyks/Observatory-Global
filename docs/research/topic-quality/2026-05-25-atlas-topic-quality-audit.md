# Atlas Topic Quality Audit

Date: 2026-05-25  
Scope: all 30 active `atlas_topics`  
Window: last 24h production assignments  
Model version: `theme-hint-lex-v2`

## Why This Audit Exists

Atlas is starting to expose living Narrative Threads directly in the product.
That means topic-assignment errors compound: a bad topic label becomes a bad
thread, then a bad focus panel, then misleading entities/sources/sentiment.

The quality standard for this phase is therefore:

> Prefer a smaller, precise topic over a large noisy one.

This audit covered all active topics, not only a visual sample. It combines
quantitative checks with headline evidence review.

## Method

Added read-only script:

```text
backend/scripts/topic_quality_audit.py
```

The script outputs JSON artifacts with:

- assignment volume;
- `lex_pct`;
- theme-only share;
- average classifier confidence;
- source and country breadth;
- deterministic evidence samples per topic;
- top matched terms;
- preliminary risk flags.

Artifacts:

- `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.json`
- `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit-post-040.json`
- `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit-post-041.json`

## Quality Score Direction

This is the proposed product-grade indicator direction. It is not yet exposed in
the UI.

| Component | Weight | Meaning |
|---|---:|---|
| Evidence support | 35 | Share supported by explicit headline terms rather than theme hints only. |
| Sample precision | 30 | Human/LLM spot-check agreement that sampled headlines fit the label. |
| Source breadth | 15 | Multiple independent sources; not one source or aggregator. |
| Geo coherence | 10 | Countries match the thread geography and are not unresolved. |
| Movement integrity | 10 | Trend/velocity reflects real evidence movement, not cache or syndication artifacts. |

Future UI language should be simple:

- `Verified` — high evidence support and sample precision.
- `Developing` — usable but needs monitoring.
- `Thin` — real but too little evidence.
- `Review` — do not promote visually without analyst review.

## Pre-Migration Findings

Five high-risk topics were immediately visible from metrics:

| Topic | Problem |
|---|---|
| `gender-violence-rights` | 1,266 assignments, only 0.08% lex-supported; mostly generic crime/human-rights/death hints. |
| `disease-outbreak` | 2,687 assignments, 9.83% lex-supported; true Ebola/outbreak evidence mixed with broad health/medical noise. |
| `food-price-stress` | 200 assignments, 4.50% lex-supported; true food-price rows existed, but broad price/poverty hints polluted volume. |
| `labor-strike-disruption` | Good rows existed, but broad `strike`/`union` terms admitted military strikes, sports, politics, and generic union headlines. |
| `transport-corridor-disruption` | Bare `canal` matched TV channels, tourism, entertainment, and drowning stories. |

Additional sampled risks:

- `forced-displacement`: broad `displaced` / `evacuated` matched apartment
  fires, standoffs, and local hazmat events.
- `humanitarian-access-conflict`: broad `displaced` weakened the access/relief
  meaning.
- `migration-border-pressure`: broad `refugee` could match Gaza refugee-camp
  casualties instead of migration pressure.
- `disinformation-influence-operation`: `debunked` / `hoax` admitted casual
  rumor headlines, not influence operations.

## Migrations Applied

### Migration 040

`backend/migrations/040_topic_quality_precision_pass.sql`

Precision changes:

- `gender-violence-rights`: removed generic hints, expanded explicit
  gender-violence / rights vocabulary.
- `labor-strike-disruption`: removed bare `strike` and `union`, replaced with
  labor-specific phrases.
- `transport-corridor-disruption`: removed bare `canal`, replaced with
  corridor/chokepoint phrases.
- `disease-outbreak`: removed broad health/medical/safety hints, kept
  disease-specific hints and outbreak vocabulary.
- `food-price-stress`: reduced hints to `FOOD_SECURITY`.
- `forced-displacement`: removed broad `displaced` / `evacuated` terms.
- `humanitarian-access-conflict`: removed broad displacement term.
- `disinformation-influence-operation`: removed generic `debunked` / `hoax`.
- `migration-border-pressure`: removed broad `refugee`.

### Migration 041

`backend/migrations/041_topic_quality_lex_first_followup.sql`

Post-040 validation showed some topics still pulled large theme-only volumes.
These anchors now run lex-first until benchmark labels justify reintroducing
theme hints:

- `labor-strike-disruption`
- `transport-corridor-disruption`
- `forced-displacement`
- `water-stress-drought`

## Final Post-041 Snapshot

| Topic | Assignments | lex_pct | avg_conf | Sources | Countries | Tier | Flags |
|---|---:|---:|---:|---:|---:|---|---|
| `armed-conflict-escalation` | 6057 | 6.5% | 0.660 | 2369 | 142 | review | theme_heavy |
| `gang-control-urban-security` | 2057 | 10.8% | 0.652 | 1142 | 109 | monitor | - |
| `election-legitimacy-dispute` | 1581 | 27.8% | 0.667 | 930 | 100 | monitor | - |
| `flood-landslide-disaster` | 894 | 12.9% | 0.653 | 678 | 96 | monitor | - |
| `disease-outbreak` | 830 | 94.5% | 0.730 | 561 | 61 | promising | - |
| `fuel-subsidy-unrest` | 651 | 39.2% | 0.691 | 460 | 78 | promising | - |
| `housing-cost-pressure` | 281 | 19.2% | 0.657 | 225 | 50 | monitor | - |
| `gender-violence-rights` | 261 | 100.0% | 0.656 | 209 | 30 | promising | - |
| `heat-health-risk` | 245 | 100.0% | 0.659 | 132 | 15 | promising | - |
| `mining-royalty-risk` | 232 | 91.0% | 0.773 | 215 | 17 | promising | - |
| `currency-debt-stress` | 202 | 52.0% | 0.656 | 104 | 43 | promising | - |
| `constitutional-institutional-crisis` | 196 | 100.0% | 0.660 | 177 | 16 | promising | - |
| `sanctions-diplomatic-pressure` | 170 | 98.8% | 0.651 | 137 | 29 | promising | - |
| `corruption-investigation` | 128 | 94.5% | 0.752 | 125 | 18 | promising | - |
| `agriculture-crop-risk` | 102 | 85.3% | 0.672 | 85 | 26 | promising | - |
| `oil-gas-supply-risk` | 84 | 71.4% | 0.659 | 75 | 26 | promising | - |
| `water-stress-drought` | 74 | 100.0% | 0.650 | 74 | 10 | review | low_confidence |
| `energy-grid-instability` | 73 | 91.8% | 0.651 | 47 | 16 | promising | - |
| `telecom-internet-shutdown` | 69 | 100.0% | 0.651 | 44 | 20 | promising | - |
| `labor-strike-disruption` | 48 | 100.0% | 0.650 | 44 | 17 | review | low_confidence |
| `migration-border-pressure` | 40 | 97.5% | 0.674 | 38 | 14 | monitor | - |
| `disinformation-influence-operation` | 33 | 100.0% | 0.650 | 30 | 18 | review | low_confidence |
| `trade-export-restriction` | 30 | 100.0% | 0.652 | 27 | 13 | monitor | - |
| `humanitarian-access-conflict` | 25 | 32.0% | 0.656 | 22 | 14 | monitor | - |
| `cyberattack-infrastructure` | 24 | 29.2% | 0.652 | 24 | 15 | thin | thin_volume |
| `forced-displacement` | 24 | 100.0% | 0.650 | 22 | 13 | thin | thin_volume |
| `food-price-stress` | 10 | 100.0% | 0.725 | 10 | 3 | thin | thin_volume |
| `transport-corridor-disruption` | 8 | 100.0% | 0.650 | 7 | 5 | thin | thin_volume |
| `press-freedom-crackdown` | 1 | 100.0% | 0.650 | 1 | 1 | thin | thin_volume |
| `student-youth-protest` | 1 | 100.0% | 0.650 | 1 | 1 | thin | thin_volume |

## Result

The audit made the product stricter.

High-value fixes:

- `gender-violence-rights`: 1,266 mostly noisy rows -> 261 explicit,
  lex-supported rows.
- `disease-outbreak`: 2,687 mixed rows -> 830 strong outbreak rows.
- `mining-royalty-risk`: already corrected by migration 039 to
  `Mining and resource safety crisis`.

Precision-first contractions:

- `food-price-stress`: 200 -> 10. This topic is now thin but clean.
- `transport-corridor-disruption`: 211 -> 8. This should not lead UI until it
  accumulates stronger evidence.
- `forced-displacement`: 245 -> 24. This avoids treating generic apartment-fire
  displacement as forced displacement.
- `labor-strike-disruption`: 1,067 -> 48. This removes military/political/sports
  strike noise; it now needs better multilingual labor terms.

Residual high-risk topic:

- `armed-conflict-escalation` remains large and theme-heavy. The sampled
  evidence is mostly real conflict, often multilingual or non-Latin, so it
  should not be suppressed only because lex_pct is low. This belongs in Path B
  benchmark labeling or a dedicated multilingual conflict lex pass.

## Next Quality Work

1. Build `#203` benchmark harness so `sample_precision` becomes measurable, not
   just manually asserted.
2. Add per-thread quality bands to `/api/v2/threads` after the score formula is
   stable.
3. Keep `thin` topics available as evidence-backed anchors, but avoid promoting
   them as leading Narrative Threads until volume improves.
4. Run this audit daily or before every taxonomy migration.
