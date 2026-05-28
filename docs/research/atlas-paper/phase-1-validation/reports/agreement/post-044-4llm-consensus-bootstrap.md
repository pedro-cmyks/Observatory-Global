# Atlas v2 post-044 vs 4-LLM consensus (N=180, 2 vendors)

Schema: `atlas-bootstrap-ci-v1`
Resamples: 10000 · Confidence: 95% · Seed: 20260527

## Overall

| Metric | Value |
|---|---:|
| Labeled | 180 |
| Correct | 87 |
| Incorrect | 93 |
| Unclear (excluded) | 0 |
| Precision | 48.33% |
| Wilson 95% CI | [41.14%, 55.59%] |
| Bootstrap 95% CI (stratified) | [42.78%, 53.89%] |
| Gate minimum | 85% |
| Gate target | 90% |
| Gate result | `fail` |

## Per-topic precision (Wilson 95% CI)

| Topic | n | correct | incorrect | unclear | precision | CI low | CI high | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `election-legitimacy-dispute` | 14 | 1 | 13 | 0 | 7.14% | 1.27% | 31.47% | `fail` |
| `oil-gas-supply-risk` | 11 | 6 | 5 | 0 | 54.55% | 28.01% | 78.73% | `fail` |
| `corruption-investigation` | 10 | 8 | 2 | 0 | 80.00% | 49.02% | 94.33% | `fail` |
| `flood-landslide-disaster` | 9 | 6 | 3 | 0 | 66.67% | 35.42% | 87.94% | `fail` |
| `housing-cost-pressure` | 9 | 6 | 3 | 0 | 66.67% | 35.42% | 87.94% | `fail` |
| `agriculture-crop-risk` | 8 | 2 | 6 | 0 | 25.00% | 7.15% | 59.07% | `fail` |
| `armed-conflict-escalation` | 8 | 4 | 4 | 0 | 50.00% | 21.52% | 78.48% | `fail` |
| `gang-control-urban-security` | 8 | 2 | 6 | 0 | 25.00% | 7.15% | 59.07% | `fail` |
| `heat-health-risk` | 8 | 2 | 6 | 0 | 25.00% | 7.15% | 59.07% | `fail` |
| `currency-debt-stress` | 7 | 3 | 4 | 0 | 42.86% | 15.82% | 74.95% | `fail` |
| `cyberattack-infrastructure` | 7 | 6 | 1 | 0 | 85.71% | 48.69% | 97.43% | `pass_minimum` |
| `disease-outbreak` | 7 | 7 | 0 | 0 | 100.00% | 64.57% | 100.00% | `pass_target` |
| `gender-violence-rights` | 7 | 7 | 0 | 0 | 100.00% | 64.57% | 100.00% | `pass_target` |
| `constitutional-institutional-crisis` | 6 | 5 | 1 | 0 | 83.33% | 43.65% | 96.99% | `fail` |
| `humanitarian-access-conflict` | 6 | 0 | 6 | 0 | 0.00% | 0.00% | 39.03% | `fail` |
| `migration-border-pressure` | 6 | 5 | 1 | 0 | 83.33% | 43.65% | 96.99% | `fail` |
| `energy-grid-instability` | 5 | 3 | 2 | 0 | 60.00% | 23.07% | 88.24% | `fail` |
| `fuel-subsidy-unrest` | 5 | 0 | 5 | 0 | 0.00% | 0.00% | 43.45% | `fail` |
| `labor-strike-disruption` | 5 | 3 | 2 | 0 | 60.00% | 23.07% | 88.24% | `fail` |
| `mining-royalty-risk` | 5 | 0 | 5 | 0 | 0.00% | 0.00% | 43.45% | `fail` |
| `food-price-stress` | 4 | 4 | 0 | 0 | 100.00% | 51.01% | 100.00% | `pass_target` |
| `sanctions-diplomatic-pressure` | 4 | 0 | 4 | 0 | 0.00% | 0.00% | 48.99% | `fail` |
| `trade-export-restriction` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `transport-corridor-disruption` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `water-stress-drought` | 4 | 1 | 3 | 0 | 25.00% | 4.56% | 69.94% | `fail` |
| `disinformation-influence-operation` | 3 | 1 | 2 | 0 | 33.33% | 6.15% | 79.23% | `fail` |
| `student-youth-protest` | 3 | 1 | 2 | 0 | 33.33% | 6.15% | 79.23% | `fail` |
| `forced-displacement` | 1 | 1 | 0 | 0 | 100.00% | 20.65% | 100.00% | `pass_target` |
| `press-freedom-crackdown` | 1 | 1 | 0 | 0 | 100.00% | 20.65% | 100.00% | `pass_target` |
| `telecom-internet-shutdown` | 1 | 0 | 1 | 0 | 0.00% | 0.00% | 79.35% | `fail` |

## Interpretation notes

- Wilson intervals are exact for binomial proportions and behave well when `n` is small or `p` is near 0/1.
- The overall bootstrap CI uses stratified resampling: each topic stratum is resampled with replacement to its original size, then precision is recomputed on the pooled set. This preserves the topic mix and avoids degenerate CIs when one stratum is small.
- Topics with `n = 1` produce wide Wilson intervals by design. Treat them as anecdotal until additional labels arrive.
- A `pass_minimum` row clears the 85% floor but not the 90% target; treat as developing.

## Forest plot

![Forest plot](post-044-4llm-consensus-forest.svg)
