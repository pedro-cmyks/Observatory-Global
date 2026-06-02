# RQ1 — From Measurement to Improvement: Precision Levers for the Single-Layer Classifier

**Date:** 2026-06-02
**Paper:** 1 (Evidence-Role Labeling for Narrative Classification)
**Status:** contribution draft, grounded in the n~660 benchmark.

## Purpose

Each paper in the series does two things: (1) **measure** a decision class
with a defensible benchmark, and (2) **propose and document concrete methods
to improve** the measured number, justified by the failure anatomy. This
document is the improvement half for RQ1. The measurement half lives in
`reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.md`.

## 1. The measured baseline (n~660, 3-vendor consensus gold)

| Method | n | precision | Wilson 95% CI |
|---|---:|---:|---|
| Atlas v2 (lex + theme) | 635 | **41.6%** | [37.8, 45.5] |
| LLM zero-shot | 627 | 78.6% | [75.3, 81.7] |
| LLM few-shot | 597 | 81.1% | [77.7, 84.0] |

Consensus quality: Fleiss kappa `0.625` (substantial), 660 usable / 31 ties,
70% unanimous. The single-layer lexicon classifier sits ~37 points below an
LLM upper bound. The improvement question: **which methods close that gap, and
by how much?**

## 2. Failure anatomy — *why* Atlas v2 is wrong

Majority-vote error type and scope across the 334 consensus-`incorrect` rows:

| Error type | share of incorrect |
|---|---:|
| **off_topic** (term matched, article unrelated) | **41.6%** |
| **scope_mismatch** (right domain, wrong granularity) | **28.1%** |
| no-majority on cause (annotators agree wrong, differ on why) | 27.8% |
| primary_context_mismatch | 1.5% |
| **substring_noise** (classic token false-match) | **0.6%** |
| insufficient_context | 0.3% |

| Annotator scope | share of incorrect |
|---|---:|
| domain (broadly the right area) | 54.8% |
| noise (genuinely off) | 34.1% |
| parent/entity/context thread | ~1.5% |

### Key reframing (this changes the improvement plan)

The earlier working assumption was that lexicon **substring noise** drives the
errors. At scale it does **not**: substring_noise is `0.6%`. The real failure is
**semantic**, in two distinct modes:

1. **off_topic (41.6%)** — the lexicon fires on a present term, but the story is
   not about the topic. This is a *relevance* problem, not a vocabulary problem.
2. **scope_mismatch (28.1%)** — the story is in the right domain but at the wrong
   level (it is context / a related thread / a parent topic, not the assigned
   child topic). This is a *role/granularity* problem.

Together these are ~70% of all errors and map cleanly onto two levers Atlas
already has architecture for.

## 3. Improvement methods (the contribution)

### M1 — Learned scope gate as the precision filter (targets off_topic, 41.6%)

**Mechanism.** The scope gate already exists
(`models/2026-05-29-scope-gate-v1-e5base.json`, threshold 0.878, target
precision 0.9). It scores each assignment on [embedding ‖ confidence ‖ matched
terms] and abstains low-relevance ones. off_topic items are exactly low-relevance
matches; the gate is designed to drop them.

**Expected lift.** If the gate abstains most off_topic and noise-scope rows, the
precision *of the kept set* should rise from 41.6% toward the LLM range, trading
coverage for precision. This is the single biggest lever because off_topic is the
largest error bucket.

**Measured result (2026-06-02).** Scoring the 660-row consensus gold through the
gate offline (`score_gold_gate.py`, e5-base, no DB writes;
`reports/llm-baseline/2026-06-02-rq1-gate-precision-coverage.json`):

| operating point | precision (kept) | coverage |
|---|---:|---:|
| no gate (baseline) | 40.9% | 100% |
| gate @ per-topic thresholds | **70.3%** | 37.3% |
| global threshold 0.95 | **78.3%** | 27.3% |

The gate lifts precision **+29 points (41% → 70%)** by abstaining the off_topic
and noise-scope buckets, and reaches the LLM zero-shot range (~78%) at ~27%
coverage. M1 is confirmed as the dominant precision lever. The residual gap to
the LLM upper bound is concentrated in `scope_mismatch` rows the gate keeps
(right domain, wrong granularity) — exactly M2's target.

**Important boundary.** Do NOT *lower* the gate threshold to chase coverage (see
`docs/research/topic-quality/2026-06-01-coverage-root-cause-lexicon-recall.md`).
The gate's job here is to *raise precision*; coverage is recovered by M2/M4.

### M2 — Evidence-role layer resolves scope_mismatch (targets 28.1%)

**Mechanism.** scope_mismatch errors are not "wrong" in a binary sense — they are
real evidence at the wrong granularity. The evidence-role schema
(primary_evidence / context / reaction / analysis / entity_reference / noise)
reclassifies them by *role* instead of forcing a binary correct/incorrect. A
story that is `context` for a topic stops being scored as a precision miss and
becomes correctly-typed supporting evidence.

**Expected lift.** Recovers up to ~28% of current "errors" as correctly-typed
context/related rather than wrong assignments, and lets the product surface them
in the right tier (verified vs context_rich) instead of hiding or mis-counting
them.

**Status.** Teacher-student pilot underway: 605-row evidence-role gold
(Fleiss-grade 3-vendor consensus) ready; the local e5-base + logistic student is
the production classifier. This is also the coverage engine (see M4).

### M3 — Per-topic remediation (targets the catastrophic tail)

Atlas v2 precision is not uniform. Worst topics on the n~660 sample:

| topic | Atlas v2 precision |
|---|---:|
| fuel-subsidy-unrest | 0% |
| mining-royalty-risk | 0% |
| humanitarian-access-conflict | 5% |
| election-legitimacy-dispute | 6% |
| student-youth-protest | 8% |
| currency-debt-stress | 11% |

**Mechanism.** These topics have lexicons that match common terms in unrelated
stories (high off_topic). Per-topic action: tighten or retire the lexicon,
require co-occurrence / negative terms, or raise the per-topic gate threshold.
A 0% topic should be gated near-fully until its definition is fixed.

**Expected lift.** Removing or gating the worst ~6 topics lifts the macro average
materially because they contribute mostly false positives.

### M4 — Embedding candidate generator (precision's coverage counterpart)

The lexicon recall baseline is `6.6%` on true primary_evidence
(`reports/evidence-role/2026-06-01-lexicon-recall-baseline.json`). Replacing the
lexicon candidate generator with embedding-based cluster membership (the emergent
HDBSCAN layer) feeds the gate + evidence-role student real candidates instead of
token matches. M1 raises precision *on what is scored*; M4 raises *what gets
scored at all*. Together they are the precision+coverage pair.

## 4. The paper's improvement claim

> A single-layer lexicon classifier achieves 41.6% precision because ~70% of its
> errors are semantic (off_topic + scope_mismatch), not lexical. Precision is
> recovered not by editing term lists but by (a) a learned relevance gate that
> abstains off_topic matches and (b) an evidence-role layer that re-types
> scope_mismatch as correctly-graded context. We measure each lever against the
> same 3-vendor consensus gold.

## 5. Status and next experiment

**M1 done and quantified** (§3, +29 points). The paper now has its first
measured improvement result: the learned scope gate raises single-layer
precision from 41% to 70% at 37% coverage.

**Next:** quantify M2. Score the same gold through the evidence-role student
(once trained) and show that `scope_mismatch` rows the gate keeps are recovered
as correctly-typed `context`/`reaction`/`analysis` rather than precision misses —
closing the residual gap to the LLM upper bound while restoring coverage. Then M3
(retire/gate the 0%-precision topics) for the macro-average lift.
