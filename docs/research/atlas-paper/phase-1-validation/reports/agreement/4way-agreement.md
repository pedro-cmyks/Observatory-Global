# Multi-annotator agreement

Schema: `atlas-multi-annotator-v1`
Categories: ['correct', 'incorrect', 'partial']
Annotators: pedro, sonnet46, opus47, haiku45

## Strictness profile (decision distribution)

| Annotator | total | correct | incorrect | partial |
|---|---:|---:|---:|---:|
| pedro | 61 | 36 | 25 | 0 |
| sonnet46 | 243 | 84 | 105 | 54 |
| opus47 | 244 | 86 | 120 | 38 |
| haiku45 | 225 | 95 | 85 | 45 |

## Pairwise Cohen's kappa

| Pair | overlap | kappa | observed agreement | band |
|---|---:|---:|---:|---|
| pedro vs sonnet46 | 61 | 0.5488 | 0.7377 | `moderate` |
| pedro vs opus47 | 61 | 0.5736 | 0.7541 | `moderate` |
| pedro vs haiku45 | 54 | 0.5439 | 0.7222 | `moderate` |
| sonnet46 vs opus47 | 240 | 0.6243 | 0.7625 | `substantial` |
| sonnet46 vs haiku45 | 221 | 0.6933 | 0.8009 | `substantial` |
| opus47 vs haiku45 | 223 | 0.7043 | 0.8117 | `substantial` |

## Fleiss' kappa

- All annotators: kappa = 0.5919 over 54 items x 4 annotators (`moderate`)
- LLM-only annotators: kappa = 0.6701 over 219 items x 3 annotators (`substantial`)

## Consensus

- All-annotator overlap subset: 54 items
- Unanimous: 33 (61.1%)

## Interpretation

- Landis & Koch: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect.
- High LLM-only Fleiss kappa means the LLM annotators agree with each other and can serve as a consensus reference without circular dependence on any single model.
- A large strictness gap between annotators (very different correct/incorrect splits) explains precision-estimate divergence even when kappa is moderate.
