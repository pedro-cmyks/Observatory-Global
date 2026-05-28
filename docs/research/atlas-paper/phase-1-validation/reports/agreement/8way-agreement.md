# Multi-annotator agreement

Schema: `atlas-multi-annotator-v1`
Categories: ['correct', 'incorrect', 'partial']
Annotators: pedro, sonnet46, opus47, haiku45, gpt41, gpt4o, gpt4omini, deepseekchat

## Strictness profile (decision distribution)

| Annotator | total | correct | incorrect | partial |
|---|---:|---:|---:|---:|
| pedro | 61 | 36 | 25 | 0 |
| sonnet46 | 243 | 84 | 105 | 54 |
| opus47 | 244 | 86 | 120 | 38 |
| haiku45 | 225 | 95 | 85 | 45 |
| gpt41 | 244 | 122 | 98 | 24 |
| gpt4o | 239 | 108 | 118 | 13 |
| gpt4omini | 204 | 89 | 115 | 0 |
| deepseekchat | 247 | 86 | 161 | 0 |

## Pairwise Cohen's kappa

| Pair | overlap | kappa | observed agreement | band |
|---|---:|---:|---:|---|
| pedro vs sonnet46 | 61 | 0.5488 | 0.7377 | `moderate` |
| pedro vs opus47 | 61 | 0.5736 | 0.7541 | `moderate` |
| pedro vs haiku45 | 54 | 0.5439 | 0.7222 | `moderate` |
| pedro vs gpt41 | 59 | 0.6377 | 0.7966 | `substantial` |
| pedro vs gpt4o | 60 | 0.7686 | 0.8833 | `substantial` |
| pedro vs gpt4omini | 52 | 0.7355 | 0.8654 | `substantial` |
| pedro vs deepseekchat | 61 | 0.6211 | 0.8033 | `substantial` |
| sonnet46 vs opus47 | 240 | 0.6243 | 0.7625 | `substantial` |
| sonnet46 vs haiku45 | 221 | 0.6933 | 0.8009 | `substantial` |
| sonnet46 vs gpt41 | 240 | 0.5319 | 0.7042 | `moderate` |
| sonnet46 vs gpt4o | 235 | 0.5861 | 0.7447 | `moderate` |
| sonnet46 vs gpt4omini | 200 | 0.4946 | 0.6850 | `moderate` |
| sonnet46 vs deepseekchat | 243 | 0.5115 | 0.7078 | `moderate` |
| opus47 vs haiku45 | 223 | 0.7043 | 0.8117 | `substantial` |
| opus47 vs gpt41 | 242 | 0.6138 | 0.7645 | `substantial` |
| opus47 vs gpt4o | 238 | 0.6449 | 0.7899 | `substantial` |
| opus47 vs gpt4omini | 201 | 0.5955 | 0.7662 | `moderate` |
| opus47 vs deepseekchat | 244 | 0.5955 | 0.7746 | `moderate` |
| haiku45 vs gpt41 | 224 | 0.6457 | 0.7812 | `substantial` |
| haiku45 vs gpt4o | 223 | 0.6343 | 0.7758 | `substantial` |
| haiku45 vs gpt4omini | 190 | 0.5333 | 0.7158 | `moderate` |
| haiku45 vs deepseekchat | 225 | 0.5015 | 0.6978 | `moderate` |
| gpt41 vs gpt4o | 238 | 0.7270 | 0.8445 | `substantial` |
| gpt41 vs gpt4omini | 202 | 0.5741 | 0.7624 | `moderate` |
| gpt41 vs deepseekchat | 244 | 0.5201 | 0.7295 | `moderate` |
| gpt4o vs gpt4omini | 197 | 0.7051 | 0.8426 | `substantial` |
| gpt4o vs deepseekchat | 239 | 0.7111 | 0.8494 | `substantial` |
| gpt4omini vs deepseekchat | 204 | 0.8085 | 0.9069 | `substantial` |

## Fleiss' kappa

- All annotators: kappa = 0.6142 over 45 items x 8 annotators (`substantial`)
- LLM-only annotators: kappa = 0.6255 over 183 items x 7 annotators (`substantial`)

## Consensus

- All-annotator overlap subset: 45 items
- Unanimous: 24 (53.3%)

## Interpretation

- Landis & Koch: <0.21 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, >0.80 almost perfect.
- High LLM-only Fleiss kappa means the LLM annotators agree with each other and can serve as a consensus reference without circular dependence on any single model.
- A large strictness gap between annotators (very different correct/incorrect splits) explains precision-estimate divergence even when kappa is moderate.
