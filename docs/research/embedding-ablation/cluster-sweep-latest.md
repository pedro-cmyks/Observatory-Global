# Clustering-recall sweep (spec §4B.4)

Sample 1074 deduped rows · gaza probe 455 · title-only embedding.
Goal: lower `gaza_noise` (diverse coverage shattered to noise) without over-fragmenting.

Production baseline today: `mcs=5 ms=3 leaf`.

| sel | mcs | ms | clusters | global_noise | gaza_recall | gaza_noise | gaza_purity | modal_size |
|---|---|---|---|---|---|---|---|---|
| eom | 8 | 1 | 4 | 0.091 | 0.967 | 0.031 | 0.491 | 896 |
| eom | 5 | 2 | 5 | 0.14 | 0.934 | 0.066 | 0.501 | 849 |
| eom | 8 | 2 | 3 | 0.128 | 0.934 | 0.066 | 0.501 | 849 |
| eom | 5 | 3 | 4 | 0.187 | 0.91 | 0.09 | 0.51 | 811 |
| eom | 8 | 3 | 2 | 0.169 | 0.91 | 0.09 | 0.51 | 811 |
| eom | 3 | 1 | 88 | 0.504 | 0.046 | 0.442 | 0.724 | 29 |
| eom | 4 | 1 | 52 | 0.553 | 0.053 | 0.466 | 1.0 | 24 |
| leaf | 3 | 1 | 96 | 0.565 | 0.029 | 0.497 | 1.0 | 13 |
| eom | 5 | 1 | 35 | 0.601 | 0.053 | 0.501 | 1.0 | 24 |
| leaf | 5 | 1 | 36 | 0.608 | 0.053 | 0.516 | 1.0 | 24 |
| leaf | 4 | 1 | 57 | 0.615 | 0.053 | 0.53 | 1.0 | 24 |
| leaf | 8 | 1 | 19 | 0.672 | 0.053 | 0.541 | 1.0 | 24 |
| eom | 3 | 2 | 53 | 0.636 | 0.044 | 0.571 | 0.714 | 28 |
| eom | 4 | 2 | 34 | 0.664 | 0.046 | 0.593 | 1.0 | 21 |
| leaf | 8 | 2 | 17 | 0.704 | 0.046 | 0.609 | 1.0 | 21 |
| leaf | 5 | 2 | 28 | 0.684 | 0.046 | 0.611 | 1.0 | 21 |
| leaf | 3 | 2 | 60 | 0.693 | 0.031 | 0.613 | 1.0 | 14 |
| leaf | 4 | 2 | 38 | 0.696 | 0.046 | 0.655 | 1.0 | 21 |
| eom | 3 | 3 | 32 | 0.714 | 0.044 | 0.659 | 1.0 | 20 |
| eom | 4 | 3 | 29 | 0.723 | 0.044 | 0.659 | 1.0 | 20 |
| leaf | 5 | 3 | 25 | 0.737 | 0.044 | 0.662 | 1.0 | 20 |
| leaf | 8 | 3 | 16 | 0.75 | 0.044 | 0.686 | 1.0 | 20 |
| leaf | 3 | 3 | 34 | 0.735 | 0.044 | 0.699 | 1.0 | 20 |
| leaf | 4 | 3 | 31 | 0.743 | 0.044 | 0.699 | 1.0 | 20 |

## Read
- Top rows = lowest Gaza-noise configs. If one materially beats the baseline `mcs=5 ms=3 leaf` WITHOUT global_noise/cluster-count exploding into junk, that param set feeds the snapshot + persisted clustering crons (#229 lever 1/2).
- If nothing beats baseline meaningfully, the recall ceiling is intrinsic to headline-only short text → escalate to scoped REGIONAL passes (#229 lever 2) or the article-body lever (§4C).