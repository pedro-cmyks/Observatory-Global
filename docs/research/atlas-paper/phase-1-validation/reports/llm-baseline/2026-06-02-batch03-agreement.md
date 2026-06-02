# Multi-annotator agreement

Schema: `atlas-multi-annotator-v1`
Categories: ['correct', 'incorrect', 'partial']
Annotators: deepseek, openai, anthropic

## Strictness profile (decision distribution)

| Annotator | total | correct | incorrect | partial |
|---|---:|---:|---:|---:|
| deepseek | 666 | 270 | 396 | 0 |
| openai | 666 | 303 | 289 | 74 |
| anthropic | 657 | 230 | 312 | 115 |

## Pairwise Cohen's kappa

| Pair | overlap | kappa | observed agreement | band |
|---|---:|---:|---:|---|
| deepseek vs openai | 666 | 0.6230 | 0.7898 | `substantial` |
| deepseek vs anthropic | 657 | 0.6224 | 0.7823 | `substantial` |
| openai vs anthropic | 657 | 0.6393 | 0.7778 | `substantial` |

## Fleiss' kappa

- All annotators: kappa = 0.6251 over 657 items x 3 annotators (`substantial`)
- LLM-only annotators: kappa = 0.6251 over 657 items x 3 annotators (`substantial`)

## Consensus

- All-annotator overlap subset: 657 items
- Unanimous: 458 (69.7%)

## Interpretation

- Landis & Koch: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect.
- High LLM-only Fleiss kappa means the LLM annotators agree with each other and can serve as a consensus reference without circular dependence on any single model.
- A large strictness gap between annotators (very different correct/incorrect splits) explains precision-estimate divergence even when kappa is moderate.
