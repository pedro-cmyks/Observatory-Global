# Atlas methodology paper — outline and validation map

Date: 2026-05-27
Status: canon (active)
Supersedes for outline purposes: `2026-05-25-atlas-narrative-intelligence-state-of-art-and-validation-plan.md` (which remains the source for state-of-the-art and research questions)

## 1. Decision: paper type

Three possible paper types were considered:

| Type | Contribution claim | Heavy validation requirement |
|---|---|---|
| Engineering / systems | Atlas as a productive narrative-intelligence platform | Latency, throughput, maintainability, real users |
| Methodology / NLP | Evidence-role labeling for narrative classification | Baselines, inter-annotator agreement, ablations |
| Product / HCI | Narrative threads as the user-facing unit of analysis | User studies, qualitative coding, task completion |

**Choice: methodology / NLP**, because it is closest to the work already in
the repository (`topic_quality_audit.py`, `topic_benchmark_harness.py`,
`benchmark_bootstrap.py`, `llm_baseline_classifier.py`, the Phase 1 review
workflow). The product and engineering papers can be derivative work later.

## 2. Working title

> **Evidence-Role Labeling for Narrative Classification: A Reproducible
> Benchmark and Audit of GDELT-Based Topic Assignment**

## 3. Thesis

A single-layer topic classifier collapses semantic roles in news signals
(parent thread, child thread, evidence, context signal, noise) into one
bucket, which inflates assignment volume while degrading precision. We
propose an evidence-role schema (`atlas-topic-benchmark-v2`), a
reproducible audit and benchmark workflow, and a stratified labeled
sample that allows direct comparison of GDELT-based classifiers and
LLM zero-shot / few-shot baselines.

## 4. Research questions

1. How does a hand-crafted GDELT-based classifier (Atlas v2) compare to
   an LLM zero-shot / few-shot baseline on a stratified labeled sample?
2. How much of the apparent volume in such classifiers is attributable
   to scope mismatch (parent thread, child thread, context signal,
   noise) rather than substring noise?
3. Does an evidence-role labeling schema improve the diagnostic value
   of benchmark results compared to a single correctness flag?
4. What is the anchoring effect of assistant-pilot hints on reviewer
   decisions, and how does it bound the LLM-as-second-annotator
   strategy for scaling labels?

## 5. Contributions

- **C1.** Evidence-role schema `atlas-topic-benchmark-v2` with semantic
  scope, evidence role, error type, and supported research question
  fields.
- **C2.** Reproducible read-only topic audit (`topic_quality_audit.py`)
  with quality-score direction and migration history.
- **C3.** Stratified benchmark harness and label workflow
  (`topic_benchmark_harness.py`, `atlas_label_workflow.py`, local
  adjudication server) supporting batch labeling at scale.
- **C4.** Statistical scoring with Wilson intervals and stratified
  bootstrap CIs (`benchmark_bootstrap.py`).
- **C5.** LLM zero-shot and few-shot baselines under the same
  benchmark (`llm_baseline_classifier.py`).
- **C6.** Anchoring-effect measurement: blind vs. assistant-hinted
  reviewer agreement on a held-out subset.
- **C7.** Error taxonomy: substring noise, scope mismatch, parent
  candidate, primary context mismatch, insufficient context, off-topic.

## 6. Outline

### 6.1 Introduction
- Motivation: narrative intelligence platforms inflate volume by
  collapsing semantic roles.
- Concrete failure cases from the Atlas audit (gender-violence-rights,
  disease-outbreak before mig 040/041).
- Contribution statement.

### 6.2 Related work
- GDELT GKG and global event taxonomies.
- Topic modeling (LDA, BERTopic, top2vec, dynamic topic modeling).
- Narrative maps and event-centric narrative graphs.
- Media framing, attention platforms, StoryAtlas-style visualizations.
- Crowdsourced labeling and LLM-as-judge / LLM-as-annotator literature.

### 6.3 Schema and method
- `atlas-topic-benchmark-v2` fields with definitions.
- Stratified sampling design (lex_high_conf, lex_low_conf,
  theme_high_conf, theme_low_conf buckets).
- Labeling guide and adjudication workflow.
- Anchoring-effect measurement design.

### 6.4 The Atlas v2 classifier
- Lex + theme hint architecture.
- Audit and precision-first migrations (040, 041) with before/after.
- Operational constraints (multilingual ingest, hot/cold storage).

### 6.5 Experiments
- E1. Reviewed precision (combined N=61 today; target N≥250 for paper).
- E2. Bootstrap CIs per topic and overall.
- E3. LLM zero-shot baseline (Sonnet 4.6).
- E4. LLM few-shot baseline (5 hand-curated examples).
- E5. LLM-as-second-annotator on uncovered topics; report Cohen's κ
  vs. human reviewer on a sub-sample.
- E6. Anchoring effect: 30 blind rows vs. assistant-hinted rows.

### 6.6 Results
- Tables: precision + Wilson CI per topic, overall bootstrap CI.
- Forest plot of per-topic precision.
- Error taxonomy distribution.
- Inter-annotator agreement.
- Comparison table: Atlas v2 vs. LLM zero-shot vs. LLM few-shot.

### 6.7 Discussion
- Why scope_mismatch dominates and how a multi-layer assignment fixes it
  (parent / child / evidence / context).
- Trade-off: lex-first precision vs. multilingual recall.
- Implications for narrative-intelligence platforms beyond Atlas.

### 6.8 Limitations
- Single primary reviewer; LLM second annotator partially mitigates.
- Anchor effect from assistant-pilot suggestions.
- Stratified sample window is one week; temporal generalization
  not yet established.

### 6.9 Future work
- Multi-layer classifier with explicit scope head.
- Active learning loop driven by ensemble disagreement.
- Public crowdsourced labeling via an Atlas Review-style interface.

## 7. Validation map (what we already have vs. what is missing)

| Item | State | Next action |
|---|---|---|
| Stratified sample (256 rows, 30 topics) | ✓ | Use as draw pool |
| Reviewed batches | 2 (N=64 total, N=61 labeled) | Continue to N≥250 |
| Per-topic Wilson CI | ✓ via `benchmark_bootstrap.py` | None |
| Stratified bootstrap overall CI | ✓ | None |
| LLM zero-shot baseline | scaffolded today | Live run pending |
| LLM few-shot baseline | scaffolded today | Live run pending |
| Cohen's κ vs. LLM annotator | not started | Design subset of 50 rows; blind reviewer + LLM |
| Anchoring effect | not started | 30 blind rows in next batch |
| Temporal generalization | not started | Hold-out week, re-score |
| Error taxonomy | ✓ from existing scores | None |
| Baseline classifiers (lex-only, theme-only, BERTopic) | not started | Add scripts after LLM baseline lands |

## 8. Target venues (to be revisited closer to submission)

- **EMNLP** (industry track or main).
- **NAACL** (main or Findings).
- **ICWSM** for the narrative-intelligence framing.
- **ACL Findings**.
- Workshop: **NLP4PI** (NLP for Positive Impact), **NLPerspectives** for
  the anchoring-effect angle.

## 9. Reproducibility statement

- All labels, sample manifests, audit reports, classifier outputs,
  scores, and forest plots live under
  `docs/research/atlas-paper/phase-1-validation/` and
  `docs/research/topic-quality/`.
- All scripts are stdlib-only or use pinned dependencies in
  `backend/.venv`.
- Atlas topic snapshot is committed
  (`backend/data/atlas_topics_snapshot_2026-05-25.json`); regenerate
  when the production taxonomy changes.
