# Whitening cluster sweep — crossing the recall/purity cliff

Sample 3393 deduped rows · Gaza probe 512 · title-only embedding · window 168h.

Cliff test: does a space's BEST config hit high recall AND high purity together (F1) — the pair the 2026-06-29 raw-e5 sweep could not?

## Best joint config per embedding space

| space | sel | mcs | ms | recall | purity | R/P F1 | noise | clusters | modal |
|---|---|---|---|---|---|---|---|---|---|
| e5_raw | eom | 8 | 3 | 0.756 | 0.146 | 0.245 | 0.216 | 2 | 2646 |
| e5_whiten_k1 | eom | 5 | 1 | 0.109 | 1.0 | 0.197 | 0.589 | 119 | 56 |
| e5_whiten_k2 | eom | 5 | 1 | 0.055 | 1.0 | 0.104 | 0.576 | 124 | 28 |
| e5_whiten_k3 | eom | 8 | 1 | 0.223 | 1.0 | 0.365 | 0.644 | 60 | 114 |

## Global frontier (top 12 by joint score)

| space | sel | mcs | ms | recall | purity | R/P F1 | joint | noise |
|---|---|---|---|---|---|---|---|---|
| e5_raw | eom | 8 | 3 | 0.756 | 0.146 | 0.245 | 0.192 | 0.216 |
| e5_whiten_k3 | eom | 8 | 1 | 0.223 | 1.0 | 0.365 | 0.13 | 0.644 |
| e5_whiten_k3 | eom | 4 | 3 | 0.207 | 1.0 | 0.343 | 0.094 | 0.726 |
| e5_whiten_k3 | eom | 5 | 3 | 0.207 | 1.0 | 0.343 | 0.088 | 0.743 |
| e5_whiten_k1 | eom | 5 | 1 | 0.109 | 1.0 | 0.197 | 0.081 | 0.589 |
| e5_whiten_k3 | eom | 8 | 3 | 0.207 | 1.0 | 0.343 | 0.079 | 0.769 |
| e5_whiten_k1 | eom | 8 | 1 | 0.109 | 1.0 | 0.197 | 0.074 | 0.623 |
| e5_whiten_k1 | eom | 4 | 3 | 0.107 | 1.0 | 0.193 | 0.054 | 0.721 |
| e5_whiten_k1 | eom | 5 | 3 | 0.107 | 1.0 | 0.193 | 0.053 | 0.725 |
| e5_whiten_k1 | eom | 8 | 3 | 0.107 | 1.0 | 0.193 | 0.048 | 0.752 |
| e5_whiten_k2 | eom | 5 | 1 | 0.055 | 1.0 | 0.104 | 0.044 | 0.576 |
| e5_raw | eom | 8 | 1 | 0.068 | 1.0 | 0.127 | 0.041 | 0.678 |

## Read
- If a whitened space's best `R/P F1` materially beats `e5_raw`'s best (raw is expected ~0 — high recall XOR high purity, never both), whitening CROSSES the cliff → wire it into the snapshot clustering behind `--whiten-k` (reversible).
- Compare `e5_whiten_k1` vs `openai_raw` vs `openai_whiten_k*`: whitening is free (no API), OpenAI costs tokens. If whitened-e5 matches OpenAI, whitening is the cheaper cliff-crosser.
- Watch `global_noise` on the winning config: a low-noise, high-F1 config is the real win (fewer near-duplicate topics at the source, less constellation-assembly downstream).