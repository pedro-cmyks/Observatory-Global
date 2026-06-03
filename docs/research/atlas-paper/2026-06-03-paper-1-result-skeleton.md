# Paper 1 Result Skeleton

**Date:** 2026-06-03  
**Status:** draft skeleton; RQ1 measured, manuscript not final  
**Parent outline:** `docs/research/atlas-paper/2026-05-27-methodology-paper-outline.md`

## Working Title

Evidence-Role Labeling for Narrative Classification: A Reproducible Benchmark
and Audit of GDELT-Based Topic Assignment

## Current Claim

Single-layer topic assignment is not sufficient for narrative intelligence
because it collapses evidence, context, parent threads, child threads, entity
mentions, and noise into one label. On a 3-vendor consensus benchmark, Atlas v2's
static single-layer classifier scores far below LLM semantic baselines. The
measured path forward is not more keyword editing alone; it is a layered model:
scope gate, evidence-role student, topic remediation, and dynamic topic
self-curation.

## Research Questions

| RQ | Status | Evidence |
|---|---|---|
| RQ1: Atlas v2 vs LLM zero/few-shot | Measured at scale | 660 usable consensus rows; Atlas `41.6%`, LLM zero-shot `78.6%`, LLM few-shot `81.1%`. |
| RQ2: Failure anatomy | Measured | Incorrect rows are dominated by `off_topic` and `scope_mismatch`; substring noise is `0.6%`. |
| RQ3: Evidence-role schema value | Partially measured | Evidence-role consensus + student show semantic errors that binary correctness hides. |
| RQ4: Assistant/LLM annotation strategy | Partially measured | Multi-vendor consensus works; local Ollama failed; anchoring effect still open. |

## Methods Section Skeleton

### System Under Test

Atlas v2 assigns topics using multilingual lexicon terms plus curated GDELT theme
hints. It writes `signal_topic_assignments` and uses confidence/gate metadata to
separate high-confidence assignments from low-quality candidates.

### Benchmark

The current headline benchmark is batch-03:

- 691 stratified rows drawn from a 7-day window.
- Three independent LLM annotators: deepseek-chat, gpt-4.1, claude-sonnet-4-6.
- Majority-vote consensus gold.
- 660 usable rows, 31 ties.
- Fleiss kappa `0.625`.

### Label Schema

The schema distinguishes:

- decision: correct / partial / incorrect / unclear;
- semantic scope: domain, parent_thread, child_thread, entity_thread, evidence,
  context_signal, noise;
- evidence role: primary_evidence, context, reaction, analysis,
  entity_reference, noise;
- error type;
- supported Atlas questions.

### Baselines

Current baselines:

- Atlas v2 static single-layer classifier.
- LLM zero-shot classifier.
- LLM few-shot classifier.

Open baselines:

- lex-only;
- theme-only;
- BERTopic/open clustering;
- temporal holdout.

## Results Section Skeleton

### R1 — Classifier Precision

| Model | Precision | Interval |
|---|---:|---|
| Atlas v2 | 41.6% | [37.8, 45.5] |
| LLM zero-shot | 78.6% | [75.3, 81.7] |
| LLM few-shot | 81.1% | [77.7, 84.0] |

Interpretation:

The single-layer classifier roughly halves achievable precision on the current
benchmark. LLM baselines are meaningfully better but still below the Atlas 90%
verified-evidence target.

Primary artifact:
`docs/research/atlas-paper/phase-1-validation/reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.md`

### R2 — Error Composition

Current finding:

- `off_topic`: largest failure bucket;
- `scope_mismatch`: second major bucket;
- substring noise: `0.6%` of incorrect rows.

Interpretation:

Most errors are semantic. Further topic-specific regex edits will have limited
impact unless the model separates candidate generation, scope, evidence role,
and thread identity.

Artifact:
`docs/research/atlas-paper/phase-1-validation/reports/llm-baseline/2026-06-02-rq1-error-composition.json`

### R3 — Improvement Levers

| Lever | Result | Interpretation |
|---|---|---|
| M1 scope gate | `41%` -> `70.3%` precision at `37.3%` coverage | Dominant precision lever. |
| M2 evidence-role student v1 | `78.2%` primary_evidence precision, `71.4%` noise recall | Useful local semantic layer; not yet final. |
| M3 topic remediation | Drop theme-only raises `40.9%` -> `48.3%` at 74% coverage | Confirms theme-hint tail is noisy. |
| M4 dynamic topics | Active topics gated by noise/roundup lifecycle | Product bridge away from brittle static topics. |

Artifact:
`docs/research/atlas-paper/phase-1-validation/2026-06-02-rq1-improvement-methods.md`

## Discussion Skeleton

### Why This Matters For Atlas

Atlas's product purpose is information-disorder sensemaking. The model must not
promote raw volume as truth. A thread should become visible because it has
coherent movement, source context, and supporting evidence, not because a broad
topic label captured many weak matches.

### Why The Paper Improves The Model

The paper is not separate from product work. It creates the evidence loop:

1. measure a model decision;
2. identify failure mode;
3. build the smallest justified correction;
4. re-score;
5. promote only if precision, coverage, or answerability improves.

### Expected Model Direction

Paper 1 justifies:

- keeping the scope gate rather than lowering thresholds for coverage;
- using evidence-role labels to separate verified evidence from context/noise;
- suppressing noisy dynamic topics via local student noise rates;
- treating `dynamic_topics` as the product-facing narrative identity layer once
  deployed and browser-smoked.

## Limitations To Write

- Consensus gold is LLM-generated, not a large human adjudicated gold set.
- Human-reviewed batch 01/02 results are diagnostic and below the precision gate.
- LLM baselines do not reach the 90% verified-evidence product target.
- Local Ollama on Pedro's current M1 is not a valid judge or teacher.
- Temporal generalization still needs a holdout week.
- Ablations beyond LLM baselines remain open.

## Figure/Table Checklist

| Asset | Status | Path |
|---|---|---|
| Atlas vs LLM comparison Markdown | Ready | `reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.md` |
| Atlas vs LLM comparison JSON | Ready | `reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.json` |
| Forest plot | Ready | `reports/llm-baseline/2026-06-02-comparison-forest-n660.svg` |
| Error composition | Ready | `reports/llm-baseline/2026-06-02-rq1-error-composition.json` |
| Gate precision/coverage | Ready | `reports/llm-baseline/2026-06-02-rq1-gate-precision-coverage.json` |
| Evidence-role student v1 | Ready | `reports/evidence-role/2026-06-02-student-v1-eval.json` |
| Dynamic topic result | Ready | `docs/research/topic-quality/2026-06-02-dynamic-topics-shadow-result.md` |

Paths under `reports/` are relative to
`docs/research/atlas-paper/phase-1-validation/`.

## Close Criteria For Paper 1 Draft

Paper 1 can move from skeleton to draft when:

1. the result tables above are copied into prose;
2. the error taxonomy is explained with examples;
3. the improvement levers are described as model decisions, not final claims;
4. limitations are written honestly;
5. open ablations are listed as future work unless completed before submission.

This is enough to continue the engineering sequence: deploy `dynamic_topics`,
run browser smoke, and use the paper evidence as the model justification.
