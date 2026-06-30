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

## Split-brain → unified: the A/B result (2026-06-29, Unified Engine F3)

The Unified Engine spec's A/B (`backend/scripts/engine_ab_report.py`, §11) IS this
paper's central experiment: does ONE engine over the universal embedding substrate
beat the split-brain (atlas-lexical ‖ dynamic-embedding ‖ discussion-attach)?

**Method.** v1-compat (the projection of today's split-brain assignments into the
typed `topic_members` table) vs unified-v2 (`build_unified_topics.py`: one numpy
assignment of every embedded signal to its nearest active `dynamic_topics`
centroid ≥0.88, role by `source_family`, + HDBSCAN-leaf new-topic formation on the
residual). Engine-agnostic metrics computed from the persisted e5 embeddings over
the same 168h window.

**Result (168h, 2026-06-29):**

| metric | v1-compat (split-brain) | unified-v2 | winner |
|---|---|---|---|
| coherence (mean member↔centroid) | 0.908 | **0.930** | v2 |
| evidence purity (≥0.85 to centroid) | 98.1% | **100.0%** | v2 |
| black-hole share (#224 mega-blob) | 19.0% | **12.1%** | v2 |
| size Gini | 0.758 | **0.693** | v2 |
| topics with ≥3 members | 66 | **103** | v2 |
| evidence members | **7874** | 6710 | v1 |

**The member-recall question, settled without human gold.** v2 assigns fewer
members — but the surplus-quality test shows v1's 2910 surplus members (in v1, not
v2) cohere **0.899** vs v1-shared **0.940**: v1's extra members are
OVER-ASSIGNMENT (the looser tail the lexical path absorbs), not signal v2 loses.
So on *effective* recall v2 does not regress; it wins every quality axis and finds
more distinct topics. **The unified engine is measurably better than the
split-brain.** The 41.6%-class absolute number gets its successor once unified-v2
is the serving engine (F4), gated on a recurring build (now live) + new-topic
labeling + a gold confirmation set.

### LLM-judge cross-check + the taxonomy-precision finding (2026-06-29)

To confirm the member-recall verdict in a modality independent of embeddings, an
LLM (`engine_recall_judge.py`, DeepSeek) judged whether sampled members are
on-topic for the label their engine assigned. The result was a **negative /
confounding** one, and it is the more important finding:

| stratum | on-topic (2 runs) |
|---|---|
| v1_only (v1's disputed surplus) | 47.5% / — |
| **shared (BOTH engines assigned)** | **40% / 52%** |
| v2_only (v2's distinctive picks) | 22.5% / — |

**`shared` is the tell.** Members BOTH engines confidently assigned are judged
on-topic only ~40–52% of the time. Inspection shows why: a legal antitrust filing
sits under "Gang control and urban security"; a satirical FEMA story under
"Constitutional crisis". The judge is measuring **label/taxonomy precision**, not
which engine assigned better — and the two engines have asymmetric labels (v1 =
broad atlas categories, v2 = specific, sometimes stale dynamic labels), so the
strata are not comparable. The test **cannot arbitrate the cutover**.

**The real result:** topical precision against the *current taxonomy* is ~40–52%
for BOTH engines. So the architecture choice (split-brain vs unified) is settled
in v2's favour on the label-independent structural metrics (coherence,
black-hole, topic granularity), but the **dominant remaining quality lever is the
taxonomy and labels (#204) + the relevance gate — not the engine**. A v2 cutover
buys cleaner, tighter, less-mega-blobbed topics; it does not by itself raise
topical precision above ~50%. That is a labeling/taxonomy result, and it
redirects the post-engine priority. (Methodological note for the paper: judge
quality must be evaluated against a fixed, precise label set, not the production
labels — the production-label judge is confounded by label drift.)

## Taxonomy revision — ensemble-κ gold benchmark (2026-06-29, #204)

The F3.2b finding (topical precision ~40–52% is taxonomy-bound, not engine-bound)
drove a taxonomy rewrite, built + evaluated by a **multi-model LLM-ensemble
annotation** method (DeepSeek + GPT-4o + GPT-5.5/Codex + Claude orchestrator).

**Result:** a 732-item gold-labeled base over the candidate-v2 label space, with
**Fleiss' κ = 0.739 (substantial)** full / **0.772 in-category** / 0.706 reject —
strong reliability across 3 independent model families on a 33-way task. The
diagnosis→fix→measure arc: force-fit measured (30–46% of gate-kept evidence is
out-of-scope) → structural fix (a rigorous OUT_OF_SCOPE reject class + per-category
excludes; categories barely move) → agreement lift (v1 76% → v2 96%) → at-scale
validation (κ 0.74). This is P1's **evaluation contribution** and the unconfounded
benchmark the production-label judge could not provide. Full method:
`docs/research/taxonomy-revision/2026-06-29-taxonomy-revision-methodology.md`;
dataset: `goldset.json`. The next P1 number is the v2-gate precision lift on a
held-out gold split.

## The split-brain is FIVE pipelines, not three (2026-06-30 extension)

The A/B above framed the split-brain as 3 construction pipelines (atlas-lexical ‖
dynamic-embedding ‖ discussion-attach) and showed unified-v2 reconciles them. An
L2-surface audit (`docs/specs/2026-06-26-l2-deep-review.md` §"unified-engine
connection") found the unification is **incomplete**: the unified engine's
substrate is "embeddable signal → nearest centroid", which covers press/forum/
event but silently EXCLUDES two more pipelines that never reconcile into a topic:

1. **Attention** — Wikipedia pageviews + Google Trends (the people-side reading/
   searching proxy) live in separate tables and are surfaced by a side service,
   never as typed topic members. The engine's #168 "attention" relationship types
   can only fire on forum data because that is the only attention it sees.
2. **Alert/volume** — the country-anomaly layer (z-scores) and the topic layer are
   different pipelines that never meet — the §3 split-brain that routes a 26×
   volume spike with no gate-passing thread into a fabricated "critical" lead (the
   Côte d'Ivoire case).

So the split-brain has **five brains; the unified engine closes three.** This is
not a contradiction of the A/B (unified-v2 IS better on the 3 it reconciles) — it
is a scope correction: the engine's claim of "any signal enters" is really "any
*embeddable* signal enters." The fix (an `attention` role + an `anomaly→movement`
topic property, both `verified=false`/honesty-preserving, A/B-gated like F3) is
specced in `docs/specs/2026-06-30-atlas-engine-attention-anomaly-roles.md`. Paper
note: report the unification as a 5-pipeline reconciliation with 3 done + 2
measured-and-specced, not an absolute — the honest scope is the contribution.
