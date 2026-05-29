# Phase B at scale: the learned scope gate clears 90% precision

Date: 2026-05-28
Status: Phase A complete (5k 3-vendor consensus), Phase B scope-gate
re-run at scale. This is the decisive result for the v3 architecture bet.

## What changed since the 207-row probe

The cheap-first probe (207 binary rows, 7-LLM consensus over a 256-signal
sample) showed a learned gate *could* beat Atlas confidence, but was
lexical-only and too small-N to be conclusive. We then executed Phase A:

- Stratified sample scaled to **5,557 assignments** (30 topics x 4
  confidence buckets) pulled from the live Supabase `signal_topic_assignments`
  (`theme-hint-lex-v2`, 72h window of the 15,692 available).
- Annotated by a **3-vendor panel**: claude-sonnet-4-6 (Anthropic) +
  gpt-4.1 (OpenAI) + deepseek-chat (DeepSeek), independent training
  lineages. Resume-safe; one power outage mid-run recovered cleanly.
- 3-vendor consensus built keyed by **(signal_id, topic_slug)** — the
  assignment, not the signal (290 signals carry 2 topics).

Consensus corpus: **5,507 assignments**, 73% unanimous (4,035 / 3-of-3),
1,188 at 2-of-3, 284 three-way splits (no majority). Binary `is_evidence`
target = consensus correct (1) vs incorrect (0), ambiguous dropped:
**4,911 rows (1,850 evidence / 3,061 not)**. Base-rate precision = current
Atlas precision on this decided subset = **37.67%**.

## Result

Same numpy logistic gate, pooled stratified 5-fold OOF, metrics
self-tested vs sklearn. Positive class = evidence (gate keeps).

| feature set | ROC-AUC (CI95) | PR-AUC (CI95) | keep@0.90 recall | keep@0.85 recall |
|---|---|---|---|---|
| atlas_conf | 0.748 [0.735, 0.761] | 0.597 [0.572, 0.621] | 1.8% | 2.0% |
| charngram | 0.898 [0.889, 0.906] | 0.857 [0.843, 0.871] | 51.1% | 61.4% |
| **charngram+conf** | **0.926 [0.919, 0.933]** | **0.888 [0.874, 0.902]** | **64.0%** | **75.1%** |

### vs the 207-row probe

| metric (charngram+conf) | 207 rows | 4,911 rows |
|---|---|---|
| ROC-AUC | 0.818 | **0.926** |
| keep@0.90 recall | 16.1% | **64.0%** |
| keep@0.85 recall | 28.0% | **75.1%** |
| AUC CI width | 0.12 | **0.014** |

## Reading

1. **The 90% target is cleared.** Applied as a gate over Atlas
   assignments, the learned model keeps a subset that is **90% precise and
   covers 64% of all true-evidence assignments** (75% coverage at 85%
   precision). Gated Atlas precision = 90% at 64% evidence-recall. This is
   the project's precision-first goal, achieved — with CIs tight enough
   (AUC [0.919, 0.933]) to trust.

2. **This is a lower bound.** The features are pure lexical char n-grams +
   Atlas's own confidence — no semantic embeddings yet. The roadmap's
   actual bet (a semantic encoder that reads scope) should push higher.
   That the *cheapest* possible learned gate already clears 90%@64% is the
   strong version of the architecture argument.

3. **Atlas confidence remains useless as a scope gate** (keep@0.90 = 1.8%),
   now confirmed at N=4,911 with tight CIs — the production pipeline has no
   intrinsic scope signal. The lift comes entirely from learning over the
   headline+topic text.

4. **Data volume was the binding constraint, not the method.** The same
   model went from AUC 0.818 / keep@90 16% (N=207) to AUC 0.926 / keep@90
   64% (N=4,911). The roadmap's instinct to scale labels was correct.

## What this settles for the v3 plan

- Phase A (scope-typed multi-vendor consensus at scale) and Phase B
  (learned gate that approximates the LLM panel) are validated. A learned
  scope gate is the right architecture to move Atlas from ~38-51% to 90%+
  precision.
- The remaining roadmap work is now engineering, not feasibility:
  1. Add the semantic-embedding feature arm (multilingual encoder) and
     measure the lift over char n-grams — expected to raise coverage at
     90% precision above 64%.
  2. Wire the gate as a confidence/abstention layer over `theme-hint-lex-v2`
     (Phase C): keep high-precision assignments, abstain on the rest,
     report coverage alongside precision.
  3. Promote behind the existing gate criteria (consensus precision >= 90%,
     CI lower bound clearing 85% — already met on this benchmark).

## Cost / provenance

3-vendor annotation of ~5.5k rows: **~$27** Phase A (vendor-billed:
cumulative across all Atlas LLM work is Anthropic $23.09 + OpenAI $9.11 +
DeepSeek $0.25 = **$32.45**, of which ~$5.48 was the prior methodology
study). Well under the $45-90 authorized envelope. Sonnet ~3x slower per
call than gpt-4.1/deepseek (latency, not rate-limit). Full ledger:
`docs/research/atlas-paper/2026-05-28-atlas-llm-spend-ledger.md`. Parser hardened mid-run:
invalid `scope`/`evidence_role` now coerce to None instead of discarding
the whole annotation (gpt-4.1 was field-swapping `insufficient_context` /
`context_signal`).

## Semantic arm (2026-05-29) — the lift the roadmap predicted

Added a hosted multilingual encoder (OpenAI `text-embedding-3-small`,
1536-dim) over the same "headline | topic_label" string, on the same 4,911
binary rows. Hosted API sidesteps the local torch/transformers iCloud
stall; cost <$0.01.

| feature set | ROC-AUC (CI95) | keep@0.90 recall | keep@0.85 recall |
|---|---|---|---|
| charngram+conf (lexical) | 0.926 | 64.0% | 75.1% |
| openai_emb | 0.949 [0.942, 0.955] | 79.9% | 87.3% |
| **openai_emb+conf** | **0.956 [0.951, 0.962]** | **84.3%** | **89.3%** |
| openai_emb+charngram+conf | 0.946 [0.939, 0.951] | 71.1% | 82.0% |

Reading:
1. **Semantic features deliver the predicted lift.** keep@0.90 recall goes
   from 64.0% (lexical) to **84.3%** (emb+conf). The gate now keeps a
   90%-precise slice covering **84% of all true evidence** — only 16%
   abstained. At 85% precision it covers 89%. This is production-grade
   precision-first behaviour.
2. **char n-grams become redundant once you have embeddings.** Adding the
   16k-dim sparse char-ngram features to the 1536-dim dense embedding
   *hurts* (keep@0.90 71.1% vs 84.3% for emb+conf) — the sparse features
   dilute the dense signal at the high-precision tail. The winning,
   simplest gate is **embedding + Atlas confidence**.
3. Best gate report: `reports/phase-b/2026-05-29-scope-gate-probe-5k-semantic.json`.

Production recommendation: the v3 scope gate is `openai_emb + atlas_conf`
logistic, thresholded for 90% keep-precision (~84% coverage). Per-topic
threshold calibration (Phase C) can trade coverage per topic. Embedding
cost at inference is ~$0.00002/signal (or swap to a local multilingual
sentence encoder once the env is off iCloud).

## Local encoder ($0/signal) — production efficiency (2026-05-29)

OpenAI embeddings cost ~$0.00002/signal forever + an external dependency.
The production goal is $0 marginal cost (the gate is meant to REPLACE
per-signal LLM cost, not reintroduce it). So we tested local multilingual
encoders (hosted in the Fly nlp_worker, which already runs torch) on the
same 4,911 rows.

| encoder | dim | keep@0.90 recall | $/signal | +Fly RAM |
|---|---|---|---|---|
| OpenAI text-embedding-3-small | 1536 | **84.3%** | ~$0.00002 | none (+API dep) |
| **multilingual-e5-base (local)** | 768 | **74.9%** | **$0** | ~280MB |
| multilingual-e5-large (local) | 1024 | 69.7% | $0 | ~560MB |

- **e5-large is worse than e5-base** here: at N=4,911 the 1024-dim model
  overfits the high-precision tail. Bigger is not better at this data size.
- **e5-base is the local winner**: 74.9% coverage at 90% precision, $0
  marginal, smallest RAM footprint. ~9pp less coverage than OpenAI.
- Decision: ship the **e5-base gate** as the production encoder
  (`models/2026-05-29-scope-gate-v1-e5base.json`, OOF AUC 0.940, embedding
  model `intfloat/multilingual-e5-base`). Per-topic calibration: 22
  calibrated, 3 abstain, 5 fallback (vs OpenAI 25/0/5). The OpenAI gate
  (`scope-gate-v1.json`, 84.3%) stays as the higher-coverage option if the
  ~$1/mo + dependency is ever acceptable; swapping is a seconds-long
  retrain.

Cost context: Fly is ~$14/mo, 73% of which is the worker's "Additional
RAM" (4GB). e5-base (+280MB) likely fits the existing 4GB → ~$0 marginal;
if it needs a bump it is small. Reusing the worker's already-loaded XLM-R
(mean-pool) would be $0-RAM but is a weaker sentence encoder — e5-base is
the better quality/cost point.

Infra note: local ML dev was blocked by iCloud evicting the venv's torch/
transformers (Desktop is iCloud-synced, disk ~88% full — `brctl` lost the
race, dataless count rose under download). Fixed permanently with an
off-iCloud venv at `/Users/pedro/AtlasLocalWorker/mlvenv` (torch 2.12 +
transformers 5.9, MPS). Embedding caches are gitignored (regenerable).

## Artifacts

- Sample: `docs/research/topic-quality/benchmark-samples/2026-05-28-atlas-v2-stratified-5k.jsonl` (5,557)
- Annotations: `labels/llm-annotator/2026-05-28-{sonnet46,gpt41,deepseekchat}-stratified-5k.annotations.jsonl`
- Consensus: `labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl` (+ summary)
- Probe report: `reports/phase-b/2026-05-28-scope-gate-probe-5k.json`
- Tools: `build_consensus_corpus.py` (now keyed by (signal_id, topic_slug)),
  `phase_b_scope_gate_probe.py`, `llm_annotator.py` (lenient scope/role parse)
