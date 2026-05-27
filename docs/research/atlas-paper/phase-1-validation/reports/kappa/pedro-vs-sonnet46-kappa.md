# Pedro vs Sonnet 4.6 annotator agreement (Cohen's kappa)

Schema: `atlas-kappa-v1`
Resamples: 10000 · Categories: ['correct', 'incorrect', 'partial']

## Inputs

| Item | Value |
|---|---:|
| Gold rows | 64 |
| Annotator rows | 247 |
| Overlapping signal_ids | 64 |
| Matched pairs (after filters) | 61 |
| Skipped (missing decision) | 0 |
| Skipped (unclear) | 3 |
| Skipped (other) | 0 |

## Cohen's kappa

| Metric | Value |
|---|---:|
| Cohen's kappa | 0.5488 |
| Observed agreement (Po) | 0.7377 |
| Chance agreement (Pe) | 0.4187 |
| Bootstrap 95% CI | [0.3838, 0.7095] |
| Landis & Koch band | `moderate` |

## Confusion matrix (rows = gold, cols = annotator)

| | correct | incorrect | partial |
|---|---:|---:|---:|
| **correct** | 26 | 3 | 7 |
| **incorrect** | 2 | 19 | 4 |
| **partial** | 0 | 0 | 0 |

## Interpretation notes

- Landis & Koch bands: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect.
- Bootstrap CI is computed by resampling the matched-pair list with replacement; CIs are wider when matched pair count is small.
- `unclear` decisions are excluded by default because they signal missing-decision rather than a positive labeling category. Toggle via `--include-unclear` to compare the full 4-category response space.
- A high kappa does NOT mean both annotators are correct, only that they agree. Use this together with the benchmark precision report.
