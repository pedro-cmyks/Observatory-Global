# Scoped clustering recall probe — CN (#229 lever 2, R0)

6000 embedded signals (last 168h). **Global baseline: 146 in a topic = 2.43%.** Goal: a scoped pass lifts recall WITHOUT a blob (largest cluster > 40% = #224 black-hole, not a win).

| sel | mcs | ms | clusters | scoped_recall% | noise% | largest | median | blob |
|---|---|---|---|---|---|---|---|---|
| leaf | 5 | 2 | 213 | 32.92 | 67.08 | 43 | 7 |  |
| eom | 8 | 3 | 88 | 29.42 | 70.58 | 170 | 15 |  |
| leaf | 12 | 3 | 56 | 26.68 | 73.32 | 170 | 19 |  |
| leaf | 8 | 3 | 93 | 26.25 | 73.75 | 96 | 14 |  |
| eom | 15 | 5 | 37 | 22.03 | 77.97 | 152 | 29 |  |

## Read
- Global baseline for CN is 2.43%. If a non-blob config here beats it MATERIALLY, scoped regional passes are the recall lever — wire the per-country loop (engine spec R1) on the M1 off-peak.
- If the best non-blob config is also ~1% (no lift), scoping does not help for this country → the ceiling is intrinsic (escalate to article bodies / language-scoped passes).