# Scoped clustering recall probe — US (#229 lever 2, R0)

15000 embedded signals (last 168h). **Global baseline: 388 in a topic = 2.59%.** Goal: a scoped pass lifts recall WITHOUT a blob (largest cluster > 40% = #224 black-hole, not a win).

| sel | mcs | ms | clusters | scoped_recall% | noise% | largest | median | blob |
|---|---|---|---|---|---|---|---|---|
| leaf | 5 | 2 | 530 | 38.11 | 61.89 | 86 | 8 |  |
| eom | 8 | 3 | 271 | 33.59 | 66.41 | 206 | 12 |  |
| leaf | 8 | 3 | 280 | 32.05 | 67.95 | 177 | 12 |  |
| leaf | 12 | 3 | 158 | 28.45 | 71.55 | 177 | 19 |  |
| eom | 15 | 5 | 115 | 26.97 | 73.03 | 189 | 28 |  |

## Read
- Global baseline for US is 2.59%. If a non-blob config here beats it MATERIALLY, scoped regional passes are the recall lever — wire the per-country loop (engine spec R1) on the M1 off-peak.
- If the best non-blob config is also ~1% (no lift), scoping does not help for this country → the ceiling is intrinsic (escalate to article bodies / language-scoped passes).