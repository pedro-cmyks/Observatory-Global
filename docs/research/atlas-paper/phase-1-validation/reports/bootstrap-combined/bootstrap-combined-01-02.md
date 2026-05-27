# Atlas v2 — combined batches 01 + 02 (bootstrap CI)

Schema: `atlas-bootstrap-ci-v1`
Resamples: 10000 · Confidence: 95% · Seed: 20260527

## Overall

| Metric | Value |
|---|---:|
| Labeled | 61 |
| Correct | 36 |
| Incorrect | 25 |
| Unclear (excluded) | 3 |
| Precision | 59.02% |
| Wilson 95% CI | [46.50%, 70.46%] |
| Bootstrap 95% CI (stratified) | [47.54%, 70.49%] |
| Gate minimum | 85% |
| Gate target | 90% |
| Gate result | `fail` |

## Per-topic precision (Wilson 95% CI)

| Topic | n | correct | incorrect | unclear | precision | CI low | CI high | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `armed-conflict-escalation` | 15 | 10 | 5 | 1 | 66.67% | 41.71% | 84.82% | `fail` |
| `corruption-investigation` | 12 | 10 | 2 | 0 | 83.33% | 55.20% | 95.30% | `fail` |
| `currency-debt-stress` | 11 | 7 | 4 | 1 | 63.64% | 35.38% | 84.83% | `fail` |
| `agriculture-crop-risk` | 8 | 2 | 6 | 1 | 25.00% | 7.15% | 59.07% | `fail` |
| `constitutional-institutional-crisis` | 8 | 5 | 3 | 0 | 62.50% | 30.57% | 86.32% | `fail` |
| `cyberattack-infrastructure` | 7 | 2 | 5 | 0 | 28.57% | 8.22% | 64.11% | `fail` |

## Interpretation notes

- Wilson intervals are exact for binomial proportions and behave well when `n` is small or `p` is near 0/1.
- The overall bootstrap CI uses stratified resampling: each topic stratum is resampled with replacement to its original size, then precision is recomputed on the pooled set. This preserves the topic mix and avoids degenerate CIs when one stratum is small.
- Topics with `n = 1` produce wide Wilson intervals by design. Treat them as anecdotal until additional labels arrive.
- A `pass_minimum` row clears the 85% floor but not the 90% target; treat as developing.

## Forest plot

![Forest plot](bootstrap-combined-01-02-forest.svg)
