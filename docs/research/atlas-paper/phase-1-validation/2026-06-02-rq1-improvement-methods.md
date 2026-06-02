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

**Measured result — student v1 (2026-06-02).** Trained the local
multinomial-logistic student on the 603-row evidence-role consensus gold
(`train_evidence_role_student.py`; e5-base headline embedding + headline↔cluster_label
cosine; honest stratified 5-fold CV;
`reports/evidence-role/2026-06-02-student-v1-eval.json`,
model `models/2026-06-02-evidence-role-student-v1.json`):

| role | precision | recall | support |
|---|---:|---:|---:|
| primary_evidence | **78.2%** | 77.4% | 288 |
| noise | 69.8% | **71.4%** | 227 |
| reaction | 65.5% | 82.6% | 23 |
| context | 36.5% | 35.2% | 54 |
| analysis | 60.0% | 27.3% | 11 |

Accuracy 70.6%, macro-F1 0.59. No LLM at inference. Cluster tiering over the 29
gold clusters: 27 verified / 1 candidate / 1 context_rich.

Read: a headline-only local student already separates primary_evidence
(78% precision) and noise (71% recall) — a strong v1 floor against the LLM-teacher
gold. `context`/`analysis` are weak (small support, semantically fuzzy, confused
with noise/primary). Per-signal primary precision (78%) is below the 90% verified
target, but the `verified` tier requires ≥2 high-score (≥0.85) primaries per
cluster, a stricter cluster-level bar. Path to 90%: richer features (cluster
centroid, gate_score, source/country — deferred to v2), role_score-threshold
calibration, and more gold (toward 1,000–1,500 via the 4x/day cron).

**Student v2 — DB-enriched features (2026-06-02, honest near-null result).**
Added the design's cluster + provenance features (cosine to cluster
label/description/**centroid_vec**, cohesion, log n_signals, country_match,
source_family one-hot, is_english; `train_evidence_role_student_v2.py`,
`reports/evidence-role/2026-06-02-student-v2-eval.json`, 29 clusters joined, 782
features). Result vs v1: primary_evidence precision **78.2% (flat)**, noise recall
71.4%→72.7%, accuracy 70.6%→71.3%, macro-F1 0.590→0.572. The rich features barely
move the needle. **Why:** the centroid is the mean of the *same* cluster the
signal belongs to, so noise members also score high cosine-to-centroid — it is a
weak discriminator for in-cluster noise. **Conclusion:** the lever to 90% is not
per-row feature engineering; it is (a) more gold (toward 1,000–1,500) and (b)
cleaner clusters / a better candidate generator (M4), which also removes the
in-cluster noise that caps primary precision at ~78%.

**Status.** Student v1 + v2 done. The model is also the coverage engine (see M4).

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

**Measured result (2026-06-02, `topic_remediation_report.py`;
`reports/llm-baseline/2026-06-02-rq1-topic-remediation.json`).**

*Match source* — the off_topic tail comes from GDELT theme hints, confirmed:

| match source | n | precision |
|---|---:|---:|
| lex+theme | 173 | 51.5% |
| lex_only | 314 | 46.5% |
| **theme_only** (lex_count=0, theme_hits>0) | 173 | **20.2%** |

theme_only (pure GDELT-theme-hint, no lexicon term) is ~2.5× more likely to be
wrong. **M3a:** dropping theme_only matches lifts precision **40.9% → 48.3%** at
74% coverage — a mechanical fix, no model. The learned gate (M1) already does a
softer version of this; making it an explicit candidate-generation rule is cheap
insurance.

*Worst topics (n≥8)* — **M3b** targets:

| topic | n | precision |
|---|---:|---:|
| mining-royalty-risk | 23 | 0% |
| fuel-subsidy-unrest | 36 | 2.8% |
| humanitarian-access-conflict | 22 | 4.5% |
| student-youth-protest | 12 | 8.3% |
| election-legitimacy-dispute | 35 | 8.6% |
| currency-debt-stress | 27 | 11.1% |

These contribute almost only false positives; retire or near-fully gate them
until their lexicons are rebuilt. **Expected lift:** removing/gating the worst
~6 topics raises the macro average materially.

**Self-healing note.** The durable fix for both M3a and M3b is to stop relying on
hand-maintained GDELT-theme-hint lexicons at all: the Phase 6 `dynamic_topics` +
emergent self-curation path lets topics be created, scored, and retired
automatically from embedding clusters, so the low-precision theme-hint tail is
removed at the source rather than patched per-topic.

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

## 4.1 M1↔M2 bridge — are the gate's residual errors recoverable? (measured)

The two levers are complementary, not redundant: the **gate handles relevance**
(abstains off_topic) and the **student handles granularity** (grades the rest).
To test that the gate's *residual* errors are recoverable rather than garbage,
score the batch-03 gold with both and cross-tab against the annotator error type
(`bridge_gate_student_scope.py`; `reports/llm-baseline/2026-06-02-gate-student-bridge.json`):

| population | n | student non-noise rate |
|---|---:|---:|
| **gate-kept AND consensus-incorrect** | 73 | **90.4%** |
| incorrect, error = scope_mismatch | 135 | **90.4%** |
| incorrect, error = off_topic | 145 | 71.0% |

**Reading.** Of the errors the gate keeps, 90% are typed by the student as
non-noise (60/73 primary_evidence, plus context/analysis) — they are real
evidence at the wrong granularity, recoverable as graded `candidate`/`context_rich`
tiers rather than counted as precision misses. scope_mismatch rows confirm this at
90% non-noise. **Honest limitation:** off_topic rows are still 71% non-noise — the
headline-only student v1 over-assigns primary_evidence and does not suppress
off_topic well on its own. That is exactly why off_topic is the *gate's* job (it
abstains most of them before the student sees them) and why student v2 needs the
cluster-membership features (centroid cosine, gate_score) to sharpen noise
suppression. The combined pipeline — gate for relevance, student for role — is
what closes the gap to the LLM upper bound.

## 5. Status and next experiment

**M1 done and quantified** (§3, +29 points). The paper now has its first
measured improvement result: the learned scope gate raises single-layer
precision from 41% to 70% at 37% coverage.

**M2 v1 done** (§3): local student, primary_evidence precision 78%, noise recall
71%, no LLM at inference. **Next for M2:** (a) run the student over the RQ1
batch-03 `scope_mismatch` rows the gate keeps and show they get non-noise roles
(i.e. they are real evidence at the wrong granularity, recoverable as graded
context rather than precision misses); (b) v2 features (centroid, gate_score,
source, country) + role-score calibration to push primary precision toward 90%;
(c) grow the gold toward 1,000–1,500. Then M3 (retire/gate the 0%-precision
topics) for the macro-average lift.
