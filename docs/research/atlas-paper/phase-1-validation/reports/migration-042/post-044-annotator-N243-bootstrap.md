# Atlas v2 post-044 — LLM-annotator quasi-gold N=243 (30 topics)

Schema: `atlas-bootstrap-ci-v1`
Resamples: 10000 · Confidence: 95% · Seed: 20260527

## Overall

| Metric | Value |
|---|---:|
| Labeled | 243 |
| Correct | 94 |
| Incorrect | 149 |
| Unclear (excluded) | 0 |
| Precision | 38.68% |
| Wilson 95% CI | [32.78%, 44.94%] |
| Bootstrap 95% CI (stratified) | [33.74%, 43.21%] |
| Gate minimum | 85% |
| Gate target | 90% |
| Gate result | `fail` |

## Per-topic precision (Wilson 95% CI)

| Topic | n | correct | incorrect | unclear | precision | CI low | CI high | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `armed-conflict-escalation` | 15 | 9 | 6 | 0 | 60.00% | 35.75% | 80.18% | `fail` |
| `election-legitimacy-dispute` | 15 | 1 | 14 | 0 | 6.67% | 1.19% | 29.82% | `fail` |
| `corruption-investigation` | 12 | 10 | 2 | 0 | 83.33% | 55.20% | 95.30% | `fail` |
| `disease-outbreak` | 12 | 11 | 1 | 0 | 91.67% | 64.61% | 98.51% | `pass_target` |
| `flood-landslide-disaster` | 12 | 6 | 6 | 0 | 50.00% | 25.38% | 74.62% | `fail` |
| `mining-royalty-risk` | 12 | 0 | 12 | 0 | 0.00% | 0.00% | 24.25% | `fail` |
| `oil-gas-supply-risk` | 12 | 6 | 6 | 0 | 50.00% | 25.38% | 74.62% | `fail` |
| `currency-debt-stress` | 11 | 2 | 9 | 0 | 18.18% | 5.14% | 47.70% | `fail` |
| `fuel-subsidy-unrest` | 11 | 0 | 11 | 0 | 0.00% | 0.00% | 25.88% | `fail` |
| `gang-control-urban-security` | 11 | 2 | 9 | 0 | 18.18% | 5.14% | 47.70% | `fail` |
| `housing-cost-pressure` | 11 | 5 | 6 | 0 | 45.45% | 21.27% | 71.99% | `fail` |
| `agriculture-crop-risk` | 9 | 3 | 6 | 0 | 33.33% | 12.06% | 64.58% | `fail` |
| `migration-border-pressure` | 9 | 4 | 5 | 0 | 44.44% | 18.88% | 73.34% | `fail` |
| `sanctions-diplomatic-pressure` | 9 | 0 | 9 | 0 | 0.00% | 0.00% | 29.92% | `fail` |
| `constitutional-institutional-crisis` | 8 | 6 | 2 | 0 | 75.00% | 40.93% | 92.85% | `fail` |
| `cyberattack-infrastructure` | 8 | 6 | 2 | 0 | 75.00% | 40.93% | 92.85% | `fail` |
| `gender-violence-rights` | 8 | 8 | 0 | 0 | 100.00% | 67.56% | 100.00% | `pass_target` |
| `heat-health-risk` | 8 | 2 | 6 | 0 | 25.00% | 7.15% | 59.07% | `fail` |
| `humanitarian-access-conflict` | 8 | 0 | 8 | 0 | 0.00% | 0.00% | 32.44% | `fail` |
| `food-price-stress` | 6 | 4 | 2 | 0 | 66.67% | 30.00% | 90.32% | `fail` |
| `energy-grid-instability` | 5 | 1 | 4 | 0 | 20.00% | 3.62% | 62.45% | `fail` |
| `labor-strike-disruption` | 5 | 3 | 2 | 0 | 60.00% | 23.07% | 88.24% | `fail` |
| `disinformation-influence-operation` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `telecom-internet-shutdown` | 4 | 0 | 4 | 0 | 0.00% | 0.00% | 48.99% | `fail` |
| `trade-export-restriction` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `transport-corridor-disruption` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `water-stress-drought` | 4 | 0 | 4 | 0 | 0.00% | 0.00% | 48.99% | `fail` |
| `student-youth-protest` | 3 | 1 | 2 | 0 | 33.33% | 6.15% | 79.23% | `fail` |
| `forced-displacement` | 2 | 0 | 2 | 0 | 0.00% | 0.00% | 65.76% | `fail` |
| `press-freedom-crackdown` | 1 | 1 | 0 | 0 | 100.00% | 20.65% | 100.00% | `pass_target` |

## Interpretation notes

- Wilson intervals are exact for binomial proportions and behave well when `n` is small or `p` is near 0/1.
- The overall bootstrap CI uses stratified resampling: each topic stratum is resampled with replacement to its original size, then precision is recomputed on the pooled set. This preserves the topic mix and avoids degenerate CIs when one stratum is small.
- Topics with `n = 1` produce wide Wilson intervals by design. Treat them as anecdotal until additional labels arrive.
- A `pass_minimum` row clears the 85% floor but not the 90% target; treat as developing.

## Forest plot

![Forest plot](post-044-annotator-N243-forest.svg)
