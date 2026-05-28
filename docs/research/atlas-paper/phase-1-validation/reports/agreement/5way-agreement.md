# Multi-annotator agreement

Schema: `atlas-multi-annotator-v1`
Categories: ['correct', 'incorrect', 'partial']
Annotators: pedro, sonnet46, opus47, haiku45, gpt41

## Strictness profile (decision distribution)

| Annotator | total | correct | incorrect | partial |
|---|---:|---:|---:|---:|
| pedro | 61 | 36 | 25 | 0 |
| sonnet46 | 243 | 84 | 105 | 54 |
| opus47 | 244 | 86 | 120 | 38 |
| haiku45 | 225 | 95 | 85 | 45 |
| gpt41 | 244 | 122 | 98 | 24 |

## Pairwise Cohen's kappa

| Pair | overlap | kappa | observed agreement | band |
|---|---:|---:|---:|---|
| pedro vs sonnet46 | 61 | 0.5488 | 0.7377 | `moderate` |
| pedro vs opus47 | 61 | 0.5736 | 0.7541 | `moderate` |
| pedro vs haiku45 | 54 | 0.5439 | 0.7222 | `moderate` |
| pedro vs gpt41 | 59 | 0.6377 | 0.7966 | `substantial` |
| sonnet46 vs opus47 | 240 | 0.6243 | 0.7625 | `substantial` |
| sonnet46 vs haiku45 | 221 | 0.6933 | 0.8009 | `substantial` |
| sonnet46 vs gpt41 | 240 | 0.5319 | 0.7042 | `moderate` |
| opus47 vs haiku45 | 223 | 0.7043 | 0.8117 | `substantial` |
| opus47 vs gpt41 | 242 | 0.6138 | 0.7645 | `substantial` |
| haiku45 vs gpt41 | 224 | 0.6457 | 0.7812 | `substantial` |

## Fleiss' kappa

- All annotators: kappa = 0.6229 over 53 items x 5 annotators (`substantial`)
- LLM-only annotators: kappa = 0.6295 over 218 items x 4 annotators (`substantial`)

## Consensus

- All-annotator overlap subset: 53 items
- Unanimous: 32 (60.4%)

## Interpretation

- Landis & Koch: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect.
- High LLM-only Fleiss kappa means the LLM annotators agree with each other and can serve as a consensus reference without circular dependence on any single model.
- A large strictness gap between annotators (very different correct/incorrect splits) explains precision-estimate divergence even when kappa is moderate.
