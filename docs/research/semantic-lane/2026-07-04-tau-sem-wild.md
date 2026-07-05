# tau_sem wild-calibrated (argmax, OpenAI space)

Rule: wild clearance <= 1/2000 per topic; lane ON iff gold recall at tau >= 0.1 and >=10 positives. **24/30 lanes on.**

| topic | tau | pos | recall@tau | goldP@tau | wild routed | wild clear | lane |
|---|---|---|---|---|---|---|---|
| agriculture-crop-risk | 0.316 | 286 | 0.57 | 0.83 | 36 | 1 | ON |
| armed-conflict-escalation | 0.258 | 172 | 0.08 | 0.33 | 46 | 1 | off |
| constitutional-institutional-crisis | 0.294 | 28 | 0.46 | 0.67 | 58 | 1 | ON |
| corruption-investigation | 0.338 | 114 | 0.82 | 0.71 | 177 | 0 | ON |
| currency-debt-stress | 0.348 | 299 | 0.16 | 0.51 | 85 | 1 | ON |
| cyberattack-infrastructure | 0.313 | 30 | 0.80 | 0.35 | 28 | 1 | ON |
| disease-outbreak | 0.341 | 275 | 0.36 | 0.88 | 48 | 1 | ON |
| disinformation-influence-operation | 0.243 | 34 | 0.56 | 0.46 | 38 | 1 | ON |
| election-legitimacy-dispute | 0.279 | 203 | 0.57 | 0.47 | 54 | 1 | ON |
| energy-grid-instability | 0.238 | 33 | 0.85 | 0.07 | 11 | 1 | ON |
| flood-landslide-disaster | 0.344 | 106 | 0.34 | 0.90 | 69 | 1 | ON |
| food-price-stress | 0.331 | 45 | 0.82 | 0.39 | 59 | 1 | ON |
| forced-displacement | 0.163 | 60 | 0.13 | 0.48 | 17 | 1 | ON |
| fuel-subsidy-unrest | 0.337 | 41 | 0.95 | 0.07 | 137 | 1 | ON |
| gang-control-urban-security | 0.256 | 205 | 0.52 | 0.83 | 35 | 1 | ON |
| gender-violence-rights | 0.318 | 109 | 0.03 | 0.60 | 56 | 1 | off |
| heat-health-risk | 0.503 | 116 | 0.11 | 0.93 | 122 | 1 | ON |
| housing-cost-pressure | 0.339 | 131 | 0.82 | 0.79 | 111 | 1 | ON |
| humanitarian-access-conflict | 0.345 | 12 | 0.42 | 0.91 | 81 | 1 | ON |
| labor-strike-disruption | 0.296 | 96 | 0.27 | 0.61 | 22 | 1 | ON |
| migration-border-pressure | 0.343 | 100 | 0.75 | 0.57 | 101 | 1 | ON |
| mining-royalty-risk | 0.269 | 0 | 0.00 | 0.04 | 80 | 1 | off |
| oil-gas-supply-risk | 0.323 | 190 | 0.66 | 0.43 | 35 | 1 | ON |
| press-freedom-crackdown | 0.354 | 1 | 1.00 | 0.06 | 90 | 1 | off |
| sanctions-diplomatic-pressure | 0.336 | 276 | 0.59 | 0.81 | 83 | 1 | ON |
| student-youth-protest | 0.342 | 3 | 0.33 | 0.20 | 86 | 1 | off |
| telecom-internet-shutdown | 0.274 | 148 | 0.89 | 0.37 | 49 | 1 | ON |
| trade-export-restriction | 0.273 | 33 | 0.85 | 0.43 | 53 | 1 | ON |
| transport-corridor-disruption | 0.307 | 5 | 0.20 | 0.08 | 100 | 1 | off |
| water-stress-drought | 0.334 | 35 | 0.63 | 0.78 | 33 | 1 | ON |
