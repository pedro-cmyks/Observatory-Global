# Phase 1 — coverage gap as of batches 01 + 02

Date: 2026-05-27

## Topics labeled so far

| Topic | n (batch 01) | n (batch 02) | n (combined) |
|---|---:|---:|---:|
| `armed-conflict-escalation` | 16 | 0 | 16 |
| `corruption-investigation` | 0 | 12 | 12 |
| `currency-debt-stress` | 0 | 12 | 12 |
| `agriculture-crop-risk` | 9 | 0 | 9 |
| `constitutional-institutional-crisis` | 7 | 1 | 8 |
| `cyberattack-infrastructure` | 0 | 7 | 7 |
| **Total covered** | **32** | **32** | **64** (61 after unclear excluded) |

## Topics with zero labels (24 of 30)

`agriculture-crop-risk` is the only environmental-ish entry covered. The
following active topics still have no gold/reviewed rows:

- `disease-outbreak`
- `flood-landslide-disaster`
- `food-price-stress`
- `forced-displacement`
- `fuel-subsidy-unrest`
- `gang-control-urban-security`
- `gender-violence-rights`
- `heat-health-risk`
- `housing-cost-pressure`
- `humanitarian-access-conflict`
- `election-legitimacy-dispute`
- `energy-grid-instability`
- `labor-strike-disruption`
- `migration-border-pressure`
- `mining-royalty-risk`
- `oil-gas-supply-risk`
- `press-freedom-crackdown`
- `sanctions-diplomatic-pressure`
- `student-youth-protest`
- `telecom-internet-shutdown`
- `trade-export-restriction`
- `transport-corridor-disruption`
- `water-stress-drought`
- `disinformation-influence-operation`

## What this means for the paper

1. Overall precision `59.02%` and Wilson CI `[46.50%, 70.46%]` represent
   only six topics. Per-topic claims for the other 24 topics are not
   supported by the current gold set.
2. Domain breakdown is heavily skewed toward conflict, governance, and
   economic stress topics. Climate/disaster, public health, social
   unrest, and information-environment topics are barely represented.
3. Before extending labeling, the next sampling pass should prioritize
   the 24 zero-label topics, weighted by their production assignment
   volume so high-volume topics receive proportionally more rows.

## Recommended next sampling pass

- Sample 8-12 rows per uncovered topic in the next batch.
- Keep the 4-bucket stratification (high-conf accept, high-conf accept,
  lex_low_conf, mixed) to preserve comparability with batches 01 + 02.
- Combine with LLM-as-second-annotator on a wider draft sample so we do
  not depend solely on single-reviewer throughput.
