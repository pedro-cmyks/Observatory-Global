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

## Canonical benchmark regime (PR3.1)

**Reconciliation (2026-07-01, R3 §8.1 / staleness ledger PR3-01, PR3-07).** Four
Atlas precision numbers and two LLM baselines accumulated across "active" docs
under different sample sizes, annotator panels, and gold sets. Read straight, they
look like the same metric disagreeing with itself; they are not. This section
declares the ONE canonical regime for Paper 1's headline and demotes the rest to
labeled variants so no reader — and no downstream doc (e.g. R3.2's "successor to
41.6%") — has to guess which number is the claim.

### The canonical regime

Paper 1's **headline precision comparison is the 3-vendor consensus benchmark
(batch-03, N=660 usable)**:

| Model | Precision | Wilson interval | Gold set |
|---|---:|---|---|
| **Atlas v2** | **41.6%** | [37.8, 45.5] | 3-vendor consensus (batch-03) |
| **LLM zero-shot** | **78.6%** | [75.3, 81.7] | 3-vendor consensus (batch-03) |
| LLM few-shot | 81.1% | [77.7, 84.0] | 3-vendor consensus (batch-03) |

This regime is canonical because it is the largest sample (N=660 usable / 691
drawn), uses an independent 3-annotator panel (deepseek-chat, gpt-4.1,
claude-sonnet-4-6) with majority-vote consensus gold and a reported Fleiss
κ=0.625, and — decisively — **scores Atlas and the LLM baseline on the SAME gold
set**, so the ~37pp gap is a real head-to-head, not an artifact of two different
answer keys. Primary artifact:
`docs/research/atlas-paper/phase-1-validation/reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.md`.

### The other Atlas numbers (labeled variants, NOT competing headlines)

Each is a valid measurement of a *different* quantity; footnoted here, never
presented as the headline:

- **59.02% (N=61 reviewed, CI [46.50, 70.46]).** Human-reviewed gold, batches
  01+02 combined (`2026-05-27-session-summary.md` L176). Smaller N, single primary
  reviewer, and it *failed* the precision gate — Paper 1 keeps it as **diagnostic
  human-reviewed evidence**, not the scale result. Higher than 41.6% mainly
  because N is small and the reviewed sample is not the batch-03 stratification.
- **50.79% (N=189, CI [43.72, 57.83], 30 topics).** Atlas v2 full-taxonomy
  precision under a **balanced 6-model** LLM consensus (`2026-05-28-precision-to-90-roadmap.md`
  L9). Differs from 41.6% by a *different annotator panel* (6 balanced models vs
  3-vendor) and a *different balanced sample* (N=189). This is the roadmap's
  starting point for the "51% → 90%" plan; it is the same phenomenon as 41.6%
  measured on a different panel, NOT a contradiction.
- **Scope-gate / learned-gate precision (a coverage trade, not a full-taxonomy
  number).** The M1 scope gate lifts precision to **70.3% at 37.3% coverage** on
  scored rows (§R3 below); the later Path-B learned scope gate reached the higher
  **~90%-band precision at reduced coverage** (`2026-05-29`, precision-to-90 Phase
  B). These are **precision-at-coverage points on the gate curve**, achieved by
  *abstaining* on low-confidence rows — they answer "how high can precision go if
  we trade recall?", a different question from the full-taxonomy headline (which
  assigns everything). They belong in the **R3 improvement-levers** table, never in
  the headline row.

### The LLM baseline split (78.6% vs 95.08%) — resolved

Two LLM zero-shot numbers exist and they are **not comparable, because they are
scored on different gold sets** — which is precisely the label-drift confound this
paper warns of (see §"LLM-judge cross-check", and Limitations):

- **78.6%** = LLM zero-shot vs the **N=660 3-vendor consensus** gold (the canonical
  regime above).
- **95.08%** (Wilson CI [86.51, 98.31]) = Sonnet-4.6 zero-shot vs the **N=61
  human-reviewed** gold (`2026-05-28-precision-to-90-roadmap.md` L44).

The gap is not a modeling result; it is the **answer key changing**. Against a
smaller human-reviewed key an LLM looks near-ceiling (95%); against the larger,
independent 3-vendor consensus key the same class of model sits at ~79%. The
canonical, apples-to-apples number Paper 1 reports is **78.6% (N=660)**; the 95.08%
is cited only as the *existence proof that ≥90% is reachable in principle by a
semantic reader* (its role in the precision-to-90 roadmap), explicitly flagged as a
different, smaller gold set. This is itself a Paper-1 finding: **LLM-judge/baseline
precision must be read against a fixed, declared gold set** — the production-label
judge (and any mismatched-gold comparison) is confounded by label drift.

## Benchmark universe re-scope (PR3.2): crisis-anchor precision + open-set coverage

**Re-scope (2026-07-01, R3 spec §3.1/§8, staleness ledger PR3-02).** The canonical
regime above measures a universe the engine has since superseded: **30 fixed
`atlas_topics` × 4 stratification buckets** — a FIXED-taxonomy category layer in
which every signal must land in one of 30 crisis topics. R3.1 made the taxonomy
**ANCHORED-EMERGENT**: the crisis-32 (#204 candidate-v2) are **seed anchors + an
editorial lens, not the typing target**; emergent super-clusters extend the set;
`category` is OPEN for every story; `crisis_relevant` is a flag/filter (mig 061),
never suppression. R3.2 collapses `atlas_topics` from a served population to an
attribute. Served population (R3.7): **348 active stories, typed 348/348 = 182
crisis-anchored + 166 non-crisis** (DeepSeek-primary typer; cosine seed-prototype
matching measured spurious). One fixed-taxonomy precision number cannot evaluate
this engine — the benchmark is now **two parts**.

### Part A — crisis-anchor precision (the fixed-taxonomy half, the successor to 41.6%)

Precision of crisis-class assignment on the **crisis-only held-out split** of the
ensemble gold. Current measurement (ledger PR3-10):

| quantity | value | artifact |
|---|---|---|
| crisis-anchor precision, hinted | 53.8% (170/316) | `docs/research/embedding-ablation/2026-07-01-crisis-only-precision-and-kappa.md` |
| crisis-anchor precision, blind (unanchored) | 48.2% | `docs/research/embedding-ablation/2026-07-01-anchoring-control.json` |
| **de-biased current band** | **48–54% (48% floor)** | hint measured ~5.6pp optimistic → anchoring control is MANDATORY in this regime |
| gold reliability | Fleiss κ 0.734 binary / 0.623 4-cat | `docs/research/embedding-ablation/2026-07-01-gold-kappa.json` |
| CI machinery (proven on the canonical N660) | baseline 40.9% [37.2, 44.7] · ablated 48.3% [43.8, 52.7] · Δ +7.4pp [5.2, 9.6] | `docs/research/embedding-ablation/2026-07-01-ablation-cis.json` |
| target | 90% verified-evidence | unreached |

Regime rules for Part A: crisis-only denominator; Wilson + bootstrap CIs on every
reported point; blind-vs-hinted anchoring control on any LLM-in-loop scoring; gold
= the ensemble-κ base. External reference (PR3-09,
`docs/research/embedding-ablation/2026-07-01-external-baseline.md`): HDBSCAN-global
cliffs at every `min_cluster_size`; flat KMeans/Agglo reach in-sample coherence
parity but carry no identity/lifecycle — Atlas's edge is scoping + lifecycle, which
Part A does not measure and Part B partly does.

### Part B — open-set evaluation for the emergent extensions (delegated to Paper 8)

The 166 non-crisis stories (→ 15 emergent super-categories @0.95 complete-linkage +
open domains) are NOT scored on fixed-taxonomy precision — that metric is undefined
for an open, growing set. They are evaluated on Paper 8's metrics: **COVERAGE**
(share of corpus explained), **COHERENCE** (member↔centroid), and **DYNAMISM**
(category births/deaths; R3.7 retirement/resurrection). Paper 1 cross-references
these (`docs/research/atlas-paper/2026-06-30-paper-8-result-skeleton.md` + the
master-plan P8 section) and does not duplicate them.

### The bridge: 41.6% → 48–54% is NOT the same measurement

The number moved partly because the QUESTION changed, and the paper must say how:

- **Old universe:** "of everything assigned into the 30 fixed crisis topics, how
  much is correct?" With no reject class, ~49% of usable assignments were
  out-of-scope force-fits scoring 27.1% — they pin the headline at 41.6% and
  charge non-crisis content to the crisis classifier.
- **New universe:** "of stories genuinely in a crisis anchor's scope, how well are
  they classed?" The OUT_OF_SCOPE reject class (#204 candidate-v2) excludes
  force-fits from the crisis denominator.

So 41.6% → 48–54% is part **denominator hygiene** (force-fits the old universe
wrongly charged to the classifier) and part **real engine change** (reject class +
typing). Any "improved by X pp" claim must declare which universe it is measured
in; cross-universe deltas are not improvement claims.

### Open gaps (honest)

- **Temporal hold-out: DATA-LIMITED.** Batch-03 gold carries no timestamps and the
  underlying signals were purged; requires a fresh labeled window (ledger PR3-10).
- **`role_noise_rate` calibration:** open (ledger PR3-10, the remaining item).
- **The 90% north-star:** unreached in either universe; 48–54% is the honest
  current position of the crisis-anchor classifier.

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

Open baselines — RESOLVED 2026-07-01 (see the PR3 experiment results section below):

- lex-only / theme-only → DONE: `gdelt_hint_ablation.py` (PR3-05) — theme-hint-dependent
  assignments are 20.2% correct ≪ 40.9% baseline (net noise); lexicon-standalone lifts to 48.3%.
- BERTopic / open clustering → DONE: `external_baseline_comparison.py` (PR3-09) — HDBSCAN-global
  (BERTopic core) cliffs at every mcs (0/8 top-overlap justification for scoped design); flat
  KMeans/Agglo reach in-sample coherence parity but no identity/lifecycle.
- temporal holdout → DATA-LIMITED: batch-03 gold has no timestamp + signals purged (needs a fresh
  labeled window).

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

## PR3 experiment results (2026-07-01) — the reproducibility + rigor gates, RUN

The four experiments P1 required (the ledger's PR3-05/09/10) are now built + measured. All
offline, repeatable, artifacts under `docs/research/embedding-ablation/`.

**Statistical rigor (PR3-10 CIs, bootstrap 5000 + Wilson, batch-03 N660):**

| quantity | point | 95% CI |
|---|---:|---|
| baseline precision (theme-hints on) | 40.9% | [37.2, 44.7] |
| ablated (lexicon-standalone) | 48.3% | [43.8, 52.7] |
| Δ ablated − baseline | +7.4pp | [5.2, 9.6] (excludes 0 = significant) |
| theme-hint-dependent precision | 20.2% | [14.9, 26.8] (non-overlap w/ baseline) |

**Theme-hint ablation (PR3-05):** theme-hint-dependent assignments (lex_count=0) are 20.2% correct
— HALF the baseline; the theme-only path is a NET NOISE source (the KILL-class idiom hypothesis,
measured). Semantic recovers 86–100% of the small true-loss at a moderate threshold (cliff in the
[0.73,0.80] e5 band). Verdict: theme-hints removable. `2026-07-01-gdelt-hint-ablation.md`.

**Crisis-only precision — the successor to 41.6% (PR3-10):** the taxonomy was 100%-crisis; ~49%
of usable assignments are non-crisis force-fits at 27.1% precision (they pin the headline number,
not the crisis classifier). Restricted to genuine crisis: **48% (unanchored) – 54% (hinted)** —
the anchoring control shows the category hint was ~5.6pp optimistic; 48% is the conservative floor,
still ≫ 40.9%. `2026-07-01-crisis-only-precision-and-kappa.md`.

**Gold reliability (PR3-10 κ):** Fleiss binary 0.734 / 4-cat 0.623 = substantial — the 41.6% rests
on a reliable gold, not annotator noise. `2026-07-01-gold-kappa.json`.

**External baseline (PR3-09):** on the same e5 corpus, HDBSCAN-global (BERTopic's core) cliffs at
every `min_cluster_size` (mega-blob 43.6% @mcs10 / collapse @mcs25 / 0 topics @mcs75) — 0/8 top
overlap with Atlas's scoped topics = the measured justification for scoping. Flat KMeans/Agglo reach
in-sample coherence parity (0.88 vs 0.849) but provide no identity/lifecycle/noise-rejection.
Honest framing: Atlas's edge is scoping + lifecycle, NOT raw one-shot coherence.
`2026-07-01-external-baseline.md`.

**Two levers compound:** theme-hint removal (+7.4pp, significant) and the crisis reject class
(+7–13pp) attack DIFFERENT noise; a v2 engine applying both clears well above the 41.6% headline.

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

**Reject GATE ≠ category TYPING (PR3-04, R3 §2/§3.1 / staleness ledger).** Two
things share the "v2" name and must not be read as one: (1) the LIVE production
thing is `apply_v2_reject.py` (`gate_model='v2-gate-e5-lr-1'`) — a **binary
keep/reject demoter** within the existing lexical assignments (it demotes force-fit
evidence, reversibly), NOT a category classifier; (2) **category typing** — assign
each story its crisis class or an emergent/open category — was genuinely UNBUILT at
the time of the κ benchmark and is a *new* operation on the e5 substrate (shipped
2026-07-01 as R3.1's `compute_category_typing.py`, DeepSeek-primary). So "candidate-v2
NOT wired" and "v2 reject gate LIVE" are both true and not a contradiction: the reject
gate was live, category typing was not. The κ=0.739 above validates the candidate-v2
LABEL SPACE (reliability of the annotation), which is the precondition for typing, not
the typing precision itself. The **crisis-only in-category precision** — the actual
"successor to 41.6%" — is measured on a crisis-only held-out κ split with Wilson/
bootstrap CIs and an anchoring control; that split **landed 2026-07-01** (ledger
PR3-10): **48–54% de-biased** (53.8% hinted / 48.2% blind, anchoring hint ~5.6pp
optimistic) — see §"Benchmark universe re-scope (PR3.2)" for the full regime. The
headline of §"Canonical benchmark regime" (41.6% / 78.6%, N=660) remains Paper 1's
stated result for the OLD universe; the two are bridged, not interchangeable.

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
