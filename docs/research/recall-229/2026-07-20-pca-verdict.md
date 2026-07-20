# #229 PCA-128 gold gate — same-as_of dry-run pair, judged. Verdict: WIRE

**Date:** 2026-07-20 · **Status:** MEASURED + WIRED — verdict against the same
pre-registered bars as the whitening gate
(`2026-07-18-whitening-gold-gate.md`).
**Inputs:** two full `run_scoped_snapshot --dry-run` passes at the production
config (168h, mcs=5, ms=2, min_kept=8), both pinned to the **same** `as_of`
(2026-07-19T23:30:46Z, `same_as_of: true`) — the 27h window confound of the
whitening pair is eliminated by construction (every marginal has
`old_member_frac = 1.0`; window-new marginals = 0). Control `pca_dim=0`
(168 countries, 5.9h) vs treatment `pca_dim=128` (169 countries, 59min).
Dumps live in the session scratchpad (not committed); judge script + judged
sample are versioned in `snapshots-gold-gate/` (`pca_gold_judge_run.py`,
`pca-gold-judgments.json`).

Dump pins (sha256):

| file | sha256 |
|---|---|
| `pca-control.json` | `62b6aab23f97dda06318e51dd1321ff1a3b8ca7f833e0188ea8c03ec4eef4bff` |
| `pca-128.json` | `356e2bdf978669f61658801f64f00f6cd1f837268273d92a843f16fc086c5b44` |
| `pca-harness-summary.json` | `d72f034bfee4f596685cd3552b4b402b4295560962a5ce39d17ed37764c05167` |
| `pca-gold-judgments.json` | `862a11aee4537c0547976b80a7b5490949764552dc998bab34dae2872f09d0f3` |

## 1. Structural comparison (harness summary — all bars PASS)

| metric | control (dim=768) | PCA-128 | Δ / bar |
|---|---|---|---|
| kept clusters (≥8) | 3,582 | 3,708 | **+3.5%** (bar: drop ≤10%) PASS |
| ≥12 promotable | 1,447 | 1,499 | **+3.6%** (bar: drop ≤10%) PASS |
| kept signal mass | 46,138 | 47,434 | +2.8% |
| kept size p50 | 10 | 10 | flat |
| max kept cluster | **276** (ES World-Cup syndication) | **92** (RU Arabic-content bin) | −67% (bar ≤1.5×) PASS — **PCA shrinks the largest** |
| mean cohesion (raw space) | 0.9703 | 0.9685 | −0.0018 |
| p10 cohesion | 0.9537 | 0.9504 | −0.0033 |
| clustering time (168 countries timed both) | 19,362 s | 2,247 s | **8.62× speedup** (bar ≥4×) PASS; median per-country 8.81×; US alone 8,777→1,074 s |

The one structural flag: **marginal fraction 33.6%** (1,247 of 3,708 PCA-kept
clusters have <50% member overlap with every control cluster in their
country; 348 of them ≥12) > the 15% cap ⇒ `JUDGE_REQUIRED`. Reverse churn:
1,131 control clusters have no ≥50% match in PCA — re-partitioning is
substantial in both directions, same class as the whitening churn but now
with zero window artifact. Marginal country mix is volume-shaped: US 122,
RU 86, UA 68, IN 64, IR 62, ES 55, GB/GR 51…

## 2. Gold judge (the wire decision)

`snapshots-gold-gate/pca_gold_judge_run.py` (adapted from the whitening
judge, same seed/method): 40 marginal PCA clusters (non-Latin monoculture
stratum RU/UA/CN/IR/GR oversampled to 50%) + 40 control clusters matched to
the same country mix. DeepSeek (deepseek-chat, temp 0) judged all 80 — "do
these ≤12 headlines cover the same real-world story?" — with a GPT-4o
agreement spot-check on a random 20 (100 LLM calls, ~$0.03). Vendor
agreement **19/20 (95%)** — judge stable, same as the whitening run. Zero
judge errors. Full per-cluster verdicts:
`snapshots-gold-gate/pca-gold-judgments.json`.

| arm | n | same-story | precision (95% Wilson CI) |
|---|---|---|---|
| **marginal (PCA-new)** | 40 | 23 | **57.5%** (42–71%) |
| — non-Latin stratum | 20 | 13 | **65.0%** (43–82%) |
| — other | 20 | 10 | 50.0% |
| **control (matched mix)** | 40 | 25 | **62.5%** (47–76%) |
| — non-Latin stratum | 20 | 14 | 70.0% |
| — other | 20 | 11 | 55.0% |

### Against the pre-registered bars

1. **Marginal precision within 10pp of control: PASS.** 57.5% vs 62.5% =
   **−5.0pp** (whitening failed this at −20.0pp).
2. **Non-Latin stratum ≥60%: PASS** (65.0%).
3. Structural bars (yield, blob, speed): all PASS (§1).

**All bars pass ⇒ WIRE.**

### Reading the numbers honestly

- The marginal point estimate (57.5%) is *identical* to the whitening run's —
  what changed the verdict is the **control arm**: matched to this marginal
  country mix (heavy US/RU/UA local-news volume), production raw-space
  clustering itself only scores 62.5% under this strict judge. PCA's
  re-partitioning is **quality-neutral at the margin** — it re-cuts the same
  substrate into different boundaries of the same same-story rate, unlike
  whitening, which *created* a new 40%-junk class. (The whitening control,
  drawn from a different country mix, scored 77.5% — the two controls are
  not comparable to each other.)
- Failure classes among the 17/40 marginal fails are the *pre-existing*
  classes, not a PCA artifact: topical/template bins (NYT puzzles, exam
  results, ETF filings), local-news roundups (UA oblast mixes, RO road
  accidents), and monoculture residue (the new max cluster itself — RU 92,
  Arabic-language RT-style content mixing World Cup with drones — judged
  false; its control-arm sibling class exists too, e.g. ES 276 World-Cup
  syndication). These are #224-roundup / junk-gate territory in both arms.
- Cohesion deltas are noise-level (−0.002 mean); identity, gate thresholds,
  centroids, and cohesion are all still computed in raw e5 space — PCA only
  changes the HDBSCAN input, so there is no identity-space migration risk.

## 3. Verdict: WIRE

`ATLAS_CLUSTER_PCA_DIM=128` is exported in the nightly runner
(`scripts/run-scoped-snapshot.sh`, right after the weekend-mode block; ALW
copy synced byte-identical, `bash -n` clean on both). The runner logs
`pca_dim=…` unconditionally each fire as the per-night receipt.

**Rollback (one line):** set `ATLAS_CLUSTER_PCA_DIM=0` (i.e. unset the
128 default in `scripts/run-scoped-snapshot.sh` + the ALW copy, or export
`ATLAS_CLUSTER_PCA_DIM=0` in the environment — the runner honors an existing
value). Next snapshot clusters raw, byte-identical to the pre-wire path; no
schema/identity change to revert.

**⚠ First wired nightly (2026-07-20 02:30 fire) must be checked in the
morning:** grep `scoped-snapshot.err.log` for `pca_dim=128`, confirm the
country pass completed inside budget, and eyeball `/threads` — expected
shape ≈ the dry run (kept ≈3.7k pre-lifecycle, max cluster well under 276,
clustering step ~1h not ~6h). If the night looks wrong, apply the rollback
line above.

**What the speedup buys next:** the 8.6× frees ~4–5h of nightly mutex time —
headroom for the deferred-country rotation to reach zero and for the embed
window to grow, which was the point of the cost lever (#229).
