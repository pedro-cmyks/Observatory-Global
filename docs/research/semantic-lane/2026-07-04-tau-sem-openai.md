# tau_sem calibration v1 — engine openai (text-embedding-3-small)

Corpus: `/tmp/goldgrowth/mega2-corpus.jsonl` (13663 rows, 3186 pos, 30 topics). Caveat: lexicon-biased sample; precision = upper bound.

Global: assigned-pair AUC 0.790, pos p50 0.327 vs neg p50 0.206; top-1 hits assigned topic on 55.0% of rows (83.0% of positives).

Cross-fire (absolute rule): 3185/3186 positives fire a foreign anchor. Argmax rule: 0 by construction.

## rule = absolute

| topic | elig | pos | AUC | tau@0.6 | P | R(elig) | R(all) | kept |
|---|---|---|---|---|---|---|---|---|
| agriculture-crop-risk | 630 | 286 | 0.868 | 0.2260 | 0.60 | 0.94 | 0.94 | 450 |
| armed-conflict-escalation | 338 | 172 | 0.776 | 0.0658 | 0.60 | 0.99 | 0.99 | 285 |
| constitutional-institutional-crisis | 187 | 28 | 0.949 | 0.2566 | 0.61 | 0.89 | 0.89 | 41 |
| corruption-investigation | 163 | 114 | 0.834 | 0.0117 | 0.70 | 1.00 | 1.00 | 163 |
| currency-debt-stress | 1708 | 299 | 0.883 | 0.3923 | 0.61 | 0.08 | 0.08 | 38 |
| cyberattack-infrastructure | 195 | 30 | 0.908 | 0.3461 | 0.61 | 0.77 | 0.77 | 38 |
| disease-outbreak | 305 | 275 | 0.764 | 0.0807 | 0.90 | 1.00 | 1.00 | 305 |
| disinformation-influence-operation | 70 | 34 | 0.787 | 0.1912 | 0.61 | 0.91 | 0.91 | 51 |
| election-legitimacy-dispute | 1874 | 203 | 0.888 | 0.3056 | 0.60 | 0.40 | 0.40 | 135 |
| energy-grid-instability | 99 | 33 | 0.853 | 0.2771 | 0.60 | 0.91 | 0.91 | 50 |
| flood-landslide-disaster | 317 | 106 | 0.900 | 0.1750 | 0.60 | 1.00 | 1.00 | 176 |
| food-price-stress | 61 | 45 | 0.531 | 0.2285 | 0.74 | 1.00 | 1.00 | 61 |
| forced-displacement | 140 | 60 | 0.802 | 0.1739 | 0.60 | 0.98 | 0.98 | 98 |
| fuel-subsidy-unrest | 2031 | 41 | 0.964 | 0.4654 | 0.60 | 0.73 | 0.73 | 50 |
| gang-control-urban-security | 813 | 205 | 0.968 | 0.1381 | 0.60 | 0.99 | 0.99 | 338 |
| gender-violence-rights | 164 | 109 | 0.625 | -0.0315 | 0.66 | 1.00 | 1.00 | 164 |
| heat-health-risk | 167 | 116 | 0.841 | 0.1487 | 0.69 | 1.00 | 1.00 | 167 |
| housing-cost-pressure | 303 | 131 | 0.971 | 0.1321 | 0.60 | 1.00 | 1.00 | 218 |
| humanitarian-access-conflict | 154 | 12 | 0.815 | 0.2891 | 0.64 | 0.58 | 0.58 | 11 |
| labor-strike-disruption | 154 | 96 | 0.839 | 0.0297 | 0.62 | 1.00 | 1.00 | 154 |
| migration-border-pressure | 157 | 100 | 0.778 | 0.0624 | 0.64 | 1.00 | 1.00 | 157 |
| mining-royalty-risk | 165 | 0 | — | — | — | — | — | — |
| oil-gas-supply-risk | 715 | 190 | 0.905 | 0.2978 | 0.60 | 0.89 | 0.89 | 281 |
| press-freedom-crackdown | 2 | 1 | 1.000 | — | — | — | — | — |
| sanctions-diplomatic-pressure | 718 | 276 | 0.915 | 0.2436 | 0.60 | 0.96 | 0.96 | 441 |
| student-youth-protest | 11 | 3 | 0.917 | 0.2905 | 0.60 | 1.00 | 1.00 | 5 |
| telecom-internet-shutdown | 1774 | 148 | 0.940 | 0.3457 | 0.60 | 0.76 | 0.76 | 186 |
| trade-export-restriction | 149 | 33 | 0.753 | — | — | — | — | — |
| transport-corridor-disruption | 21 | 5 | 0.637 | — | — | — | — | — |
| water-stress-drought | 78 | 35 | 0.906 | 0.1847 | 0.60 | 1.00 | 1.00 | 58 |

## rule = argmax

| topic | elig | pos | AUC | tau@0.6 | P | R(elig) | R(all) | kept |
|---|---|---|---|---|---|---|---|---|
| agriculture-crop-risk | 464 | 242 | 0.859 | 0.2140 | 0.60 | 0.98 | 0.83 | 395 |
| armed-conflict-escalation | 80 | 63 | 0.714 | 0.1056 | 0.79 | 1.00 | 0.37 | 80 |
| constitutional-institutional-crisis | 58 | 18 | 0.890 | 0.2811 | 0.60 | 0.83 | 0.54 | 25 |
| corruption-investigation | 147 | 114 | 0.760 | 0.2017 | 0.78 | 1.00 | 1.00 | 147 |
| currency-debt-stress | 629 | 250 | 0.679 | 0.3923 | 0.61 | 0.09 | 0.08 | 38 |
| cyberattack-infrastructure | 99 | 29 | 0.848 | 0.3461 | 0.61 | 0.79 | 0.77 | 38 |
| disease-outbreak | 271 | 247 | 0.759 | 0.1864 | 0.91 | 1.00 | 0.90 | 271 |
| disinformation-influence-operation | 40 | 28 | 0.673 | 0.1354 | 0.70 | 1.00 | 0.82 | 40 |
| election-legitimacy-dispute | 1273 | 190 | 0.862 | 0.3052 | 0.60 | 0.42 | 0.39 | 133 |
| energy-grid-instability | 42 | 28 | 0.714 | 0.1870 | 0.67 | 1.00 | 0.85 | 42 |
| flood-landslide-disaster | 133 | 101 | 0.648 | 0.1334 | 0.76 | 1.00 | 0.95 | 133 |
| food-price-stress | 58 | 43 | 0.524 | 0.2285 | 0.74 | 1.00 | 0.96 | 58 |
| forced-displacement | 12 | 8 | 0.781 | 0.2056 | 0.67 | 1.00 | 0.13 | 12 |
| fuel-subsidy-unrest | 1531 | 40 | 0.966 | 0.4654 | 0.60 | 0.75 | 0.73 | 50 |
| gang-control-urban-security | 217 | 161 | 0.857 | 0.0631 | 0.74 | 1.00 | 0.79 | 217 |
| gender-violence-rights | 50 | 43 | 0.492 | 0.1024 | 0.86 | 1.00 | 0.39 | 50 |
| heat-health-risk | 165 | 116 | 0.835 | 0.2319 | 0.70 | 1.00 | 1.00 | 165 |
| housing-cost-pressure | 164 | 131 | 0.869 | 0.1321 | 0.80 | 1.00 | 1.00 | 164 |
| humanitarian-access-conflict | 23 | 7 | 0.991 | 0.2490 | 0.64 | 1.00 | 0.58 | 11 |
| labor-strike-disruption | 88 | 70 | 0.656 | 0.1504 | 0.80 | 1.00 | 0.73 | 88 |
| migration-border-pressure | 147 | 98 | 0.770 | 0.1614 | 0.67 | 1.00 | 0.98 | 147 |
| mining-royalty-risk | 104 | 0 | — | — | — | — | — | — |
| oil-gas-supply-risk | 444 | 175 | 0.838 | 0.2979 | 0.60 | 0.90 | 0.83 | 261 |
| press-freedom-crackdown | 1 | 1 | — | — | — | — | — | — |
| sanctions-diplomatic-pressure | 462 | 237 | 0.880 | 0.2255 | 0.60 | 0.99 | 0.85 | 391 |
| student-youth-protest | 7 | 3 | 0.833 | 0.2905 | 0.60 | 1.00 | 1.00 | 5 |
| telecom-internet-shutdown | 669 | 142 | 0.923 | 0.3185 | 0.60 | 0.84 | 0.80 | 198 |
| trade-export-restriction | 81 | 30 | 0.553 | — | — | — | — | — |
| transport-corridor-disruption | 6 | 2 | 0.625 | — | — | — | — | — |
| water-stress-drought | 47 | 27 | 0.854 | 0.1822 | 0.60 | 1.00 | 0.77 | 45 |
