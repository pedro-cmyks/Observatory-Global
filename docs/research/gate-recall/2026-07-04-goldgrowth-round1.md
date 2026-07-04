# Gold-growth round 1: labels landed, thresholds too unstable to deploy (2026-07-04)

**Goal.** Lift hard-topic gate recall by growing gold positives (election-legit
had 38). Pipeline built + run: 226 decision-band candidates (6 hard topics,
stratified over gate_score 0.15–0.999) → 2-vendor labeling (DeepSeek +
gpt-4o-mini via `llm_annotator.py`) → unanimity consensus
(`build_goldgrowth_corpus.py`) → OpenAI embeds (`embed_goldgrowth.py`) →
retrain (`train_scope_gate.py`) → OOF compare + live dry-run.

**Labels:** 181/226 unanimous (80% inter-vendor agreement; 29 splits, 16
partial/unclear). +70 positives: election-legit 38→51, sanctions +20, oil-gas
+17, agriculture +16(+6 r2), currency +3, telecom +1 (its pool is simply tiny).

**Result — NOT deployed. The honest finding is instability, not improvement:**

| topic (recall@90% OOF) | v1 (5k) | v2 (+181) | v2b (+201) |
|---|---|---|---|
| election-legitimacy | 0.395 | **0.549** | **0.235** |
| sanctions | 0.278 | 0.393 | 0.268 |
| currency-debt | 0.263 | 0.366 | 0.220 |
| telecom | 0.864 | 0.289 | 0.311 |
| agriculture | 0.758 | 0.577 | 0.714 |
| GLOBAL | 0.843 | 0.811 | 0.819 |

Adding 20 unrelated agriculture rows (v2→v2b) swung election-legit by −31pp.
**Per-topic threshold calibration at n≈300/40-60 positives is high-variance:
fold reshuffles + a handful of boundary rows move the operating point more than
any real signal.** The v2 "wins" are within this noise band. Deploying on them
would be statistical self-deception. Also: the new rows are decision-band by
construction (harder), so cross-benchmark comparisons v1-vs-v2 are not
apples-to-apples; and 80% vendor agreement means label noise compounds it.

**What holds:** v1-OpenAI gate + two-tier serving stay in prod (both measured
wins). The labeling→consensus→embed→retrain pipeline is now BUILT and
repeatable at pennies per hundred rows.

**What it takes to do this right (next pass):**
1. **Volume**: several hundred positives per hard topic (5–10× this round) —
   run the annotator pipeline over 7–30d windows on a schedule until n_pos
   per topic ≥ 200; only then are per-topic thresholds stable.
2. **Variance-aware calibration**: bootstrap the OOF threshold per topic and
   deploy the CI-lower-bound operating point (or hierarchical shrinkage toward
   the global threshold for thin topics) — makes small-n topics conservative
   instead of erratic.
3. Add a 3rd vendor (or human tiebreak) on splits to cut label noise.

Artifacts: /tmp/goldgrowth/* (votes, corpora, gates v2/v2b + calibrations);
scripts committed: `build_goldgrowth_corpus.py`, `embed_goldgrowth.py`.
