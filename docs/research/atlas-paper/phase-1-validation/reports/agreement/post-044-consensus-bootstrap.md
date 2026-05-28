# Atlas v2 post-044 vs LLM consensus (N=212, 3-model majority)

Schema: `atlas-bootstrap-ci-v1`
Resamples: 10000 · Confidence: 95% · Seed: 20260527

## Overall

| Metric | Value |
|---|---:|
| Labeled | 212 |
| Correct | 90 |
| Incorrect | 122 |
| Unclear (excluded) | 0 |
| Precision | 42.45% |
| Wilson 95% CI | [35.99%, 49.18%] |
| Bootstrap 95% CI (stratified) | [37.26%, 48.11%] |
| Gate minimum | 85% |
| Gate target | 90% |
| Gate result | `fail` |

## Per-topic precision (Wilson 95% CI)

| Topic | n | correct | incorrect | unclear | precision | CI low | CI high | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `election-legitimacy-dispute` | 14 | 1 | 13 | 0 | 7.14% | 1.27% | 31.47% | `fail` |
| `corruption-investigation` | 12 | 8 | 4 | 0 | 66.67% | 39.06% | 86.19% | `fail` |
| `currency-debt-stress` | 11 | 4 | 7 | 0 | 36.36% | 15.17% | 64.62% | `fail` |
| `oil-gas-supply-risk` | 11 | 6 | 5 | 0 | 54.55% | 28.01% | 78.73% | `fail` |
| `agriculture-crop-risk` | 9 | 3 | 6 | 0 | 33.33% | 12.06% | 64.58% | `fail` |
| `disease-outbreak` | 9 | 7 | 2 | 0 | 77.78% | 45.26% | 93.68% | `fail` |
| `flood-landslide-disaster` | 9 | 6 | 3 | 0 | 66.67% | 35.42% | 87.94% | `fail` |
| `fuel-subsidy-unrest` | 9 | 0 | 9 | 0 | 0.00% | 0.00% | 29.92% | `fail` |
| `gang-control-urban-security` | 9 | 2 | 7 | 0 | 22.22% | 6.32% | 54.74% | `fail` |
| `housing-cost-pressure` | 9 | 6 | 3 | 0 | 66.67% | 35.42% | 87.94% | `fail` |
| `mining-royalty-risk` | 9 | 0 | 9 | 0 | 0.00% | 0.00% | 29.92% | `fail` |
| `armed-conflict-escalation` | 8 | 4 | 4 | 0 | 50.00% | 21.52% | 78.48% | `fail` |
| `constitutional-institutional-crisis` | 8 | 6 | 2 | 0 | 75.00% | 40.93% | 92.85% | `fail` |
| `cyberattack-infrastructure` | 8 | 6 | 2 | 0 | 75.00% | 40.93% | 92.85% | `fail` |
| `heat-health-risk` | 8 | 2 | 6 | 0 | 25.00% | 7.15% | 59.07% | `fail` |
| `sanctions-diplomatic-pressure` | 8 | 0 | 8 | 0 | 0.00% | 0.00% | 32.44% | `fail` |
| `gender-violence-rights` | 7 | 7 | 0 | 0 | 100.00% | 64.57% | 100.00% | `pass_target` |
| `humanitarian-access-conflict` | 7 | 0 | 7 | 0 | 0.00% | 0.00% | 35.43% | `fail` |
| `migration-border-pressure` | 7 | 5 | 2 | 0 | 71.43% | 35.89% | 91.78% | `fail` |
| `energy-grid-instability` | 6 | 3 | 3 | 0 | 50.00% | 18.76% | 81.24% | `fail` |
| `food-price-stress` | 6 | 4 | 2 | 0 | 66.67% | 30.00% | 90.32% | `fail` |
| `labor-strike-disruption` | 5 | 3 | 2 | 0 | 60.00% | 23.07% | 88.24% | `fail` |
| `disinformation-influence-operation` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `trade-export-restriction` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `transport-corridor-disruption` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `water-stress-drought` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `student-youth-protest` | 3 | 1 | 2 | 0 | 33.33% | 6.15% | 79.23% | `fail` |
| `forced-displacement` | 2 | 1 | 1 | 0 | 50.00% | 9.45% | 90.55% | `fail` |
| `press-freedom-crackdown` | 1 | 1 | 0 | 0 | 100.00% | 20.65% | 100.00% | `pass_target` |
| `telecom-internet-shutdown` | 1 | 0 | 1 | 0 | 0.00% | 0.00% | 79.35% | `fail` |

## Interpretation notes

- Wilson intervals are exact for binomial proportions and behave well when `n` is small or `p` is near 0/1.
- The overall bootstrap CI uses stratified resampling: each topic stratum is resampled with replacement to its original size, then precision is recomputed on the pooled set. This preserves the topic mix and avoids degenerate CIs when one stratum is small.
- Topics with `n = 1` produce wide Wilson intervals by design. Treat them as anecdotal until additional labels arrive.
- A `pass_minimum` row clears the 85% floor but not the 90% target; treat as developing.

## Forest plot

![Forest plot](post-044-consensus-forest.svg)
