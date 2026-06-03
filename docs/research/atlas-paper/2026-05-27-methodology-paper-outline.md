# Paper 1 — Evidence-role topic classification + distillation methodology

Date: 2026-05-27
Status: canon (active; RQ1 measured at scale on 2026-06-02, manuscript not yet closed)
Series framing: this is **Paper 1 of the Atlas methodology series**.
See `docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`
for the full series index (Papers 1-8 covering ingestion, source
quality, NLP, sentiment, topic classification, heat, threads,
temporal model, visualization, and open-set topic discovery).
Current result skeleton:
`docs/research/atlas-paper/2026-06-03-paper-1-result-skeleton.md`.
Supersedes for outline purposes: `2026-05-25-atlas-narrative-intelligence-state-of-art-and-validation-plan.md` (which remains the source for state-of-the-art and research questions)

## 1. Decision: paper type and scope within the series

The Atlas system covers a dozen methodological decision classes
(see the master plan). A single mega-paper would be 50+ pages and
hard to peer review. The series approach lets each paper target a
specific decision class and a specific venue.

**Paper 1 scope (this document):** the topic-classification layer of
Atlas. This includes the evidence-role schema, the audit and
benchmark workflow, baseline comparisons against LLM zero-shot /
few-shot, statistical scoring, and the LLM-distillation loop that
feeds insights back into the rule-based classifier. Other
decision classes (source quality, sentiment fusion, atlas heat,
thread aggregation, temporal model, visualization, open-set
discovery) are deferred to Papers 2-8 of the series.

Three possible paper types were considered for Paper 1:

| Type | Contribution claim | Heavy validation requirement |
|---|---|---|
| Engineering / systems | Atlas as a productive narrative-intelligence platform | Latency, throughput, maintainability, real users |
| Methodology / NLP | Evidence-role labeling for narrative classification | Baselines, inter-annotator agreement, ablations |
| Product / HCI | Narrative threads as the user-facing unit of analysis | User studies, qualitative coding, task completion |

**Choice: methodology / NLP**, because it is closest to the work already in
the repository (`topic_quality_audit.py`, `topic_benchmark_harness.py`,
`benchmark_bootstrap.py`, `llm_baseline_classifier.py`, the Phase 1 review
workflow). The product and engineering papers correspond to later
papers in the series (Papers 4, 6, 7).

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

2026-06-02 update: RQ1 now has a scale result. On a 660-row usable
3-vendor consensus-gold benchmark, Atlas v2 scored `41.6%` precision,
LLM zero-shot scored `78.6%`, and LLM few-shot scored `81.1%`. The main
failure modes were semantic (`off_topic` and `scope_mismatch`), while
classic substring noise was only `0.6%` of incorrect rows. Paper 1 should
therefore frame Atlas's next model step as a measured correction path:
scope gate, evidence-role student, topic remediation, and dynamic topic
self-curation.

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
| Reviewed batches | 2 (N=64 total, N=61 labeled) | Keep as diagnostic human-reviewed evidence |
| 3-vendor consensus gold | ✓ N=660 usable / 31 ties | Use as Paper 1 headline RQ1 evidence |
| Per-topic Wilson CI | ✓ via `benchmark_bootstrap.py` | None |
| Stratified bootstrap overall CI | ✓ | None |
| LLM zero-shot baseline | ✓ 78.6% on N=660 | Keep table/figure current |
| LLM few-shot baseline | ✓ 81.1% on N=660 | Keep table/figure current |
| Multi-annotator agreement | ✓ Fleiss kappa 0.625 | Continue daily calibration monitor |
| Scope gate improvement | ✓ 41%→70% precision at 37% coverage | Add as Paper 1 improvement result |
| Evidence-role student | ✓ primary_evidence precision 78.2% | Add as measured M2, not final promotion |
| Dynamic topics self-curation | ✓ local canonical cutover implemented | Treat as M4 future/product bridge |
| Cohen's κ vs. human reviewer | partial earlier comparison | Revisit only if needed for limitations |
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

## 10. Relationship to the rest of the series

Paper 1 establishes the schema (`atlas-topic-benchmark-v2`) and the
statistical evaluation conventions used across the series:

- Wilson interval per topic, stratified bootstrap overall (see
  `benchmark_bootstrap.py`).
- Cohen's kappa with bootstrap CI for inter-annotator agreement
  (see `kappa_calculator.py`).
- LLM-as-classifier baseline and LLM-as-annotator gold expansion
  (see `llm_baseline_classifier.py`, `llm_annotator.py`).
- Reasoning-mining distillation (see `llm_reasoning_mine.py`).

Subsequent papers reuse these tools and extend the schema where
needed (for example, the thread-level paper will add per-thread
fields for the seven analyst questions, and the sentiment paper
will add per-headline sentiment labels). The decision to ship
Paper 1 first is documented in the master plan: every later paper
benefits from having the topic-classification layer validated.
