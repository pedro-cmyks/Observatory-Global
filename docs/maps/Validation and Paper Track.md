# Validation and Paper Track MOC

This map tracks the research/validation work behind Atlas precision, scope
gating, annotator agreement, and the future paper series.

## Start here

- [[2026-05-27-atlas-papers-master-plan]] — eight-paper series outline.
- [[2026-05-27-methodology-paper-outline]] — Paper 1 outline.
- [[2026-05-28-precision-to-90-roadmap]] — path from static-topic precision to
  90-95%.
- [[2026-06-03-research-model-product-roadmap]] — current route connecting
  Paper 1, model correction, dynamic-topic product verification, and the
  anti-information-disorder product purpose.
- [[2026-06-03-paper-1-result-skeleton]] — Paper 1 draft skeleton with current
  RQ1 result, result tables, improvement levers, limitations, and figure list.
- [[2026-06-04-mvp-thread-volume-and-issue-sprint-design]] — temporary operating
  shift for MVP: paper remains active refinement, while product work prioritizes
  Narrative Thread volume and issue cleanup. GDELT can be used only as weak,
  bias-measured support, not as paper-grade truth.
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — teacher-student
  design for classifying evidence roles inside narrative clusters.
- [[2026-06-01-narrative-cluster-evidence-roles]] — implementation plan for
  teacher packets, consensus labels, student reporting, and coverage metrics.
- [[2026-06-02-rq1-improvement-methods]] — RQ1 contribution: how to raise the
  41.6% single-layer precision. Failure anatomy (off_topic 41.6%,
  scope_mismatch 28.1%, substring_noise only 0.6%) → scope gate (M1) +
  evidence-role layer (M2) + per-topic remediation (M3) as the precision levers.
  M1 measured: gate lifts precision 41%→70% (37% coverage). M2 v1 measured:
  local student (no LLM at inference) primary_evidence precision 78%, noise
  recall 71% on honest 5-fold CV.
- [[2026-05-25-atlas-v2-labeling-guide]] — semantic/evidence-role label guide.
- Evidence-role teacher/student reports:
  `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`.
- [[2026-06-02-local-ollama-deprecation]] — local Ollama route is deprecated
  for Atlas judging/teacher labels after the `llama3.2:1b` M1 pilot failed the
  validation bar.

## Validation findings

- Paper 1 is not closed as a manuscript. RQ1 is closed enough as a measured
  milestone to guide model decisions: the next step is a result-bearing draft
  skeleton, not more ad hoc topic repair.
- Rule editing helped but hit a ceiling; remaining failures are mainly semantic
  scope mismatches.
- Multi-vendor consensus is the defensible benchmark path; single-annotator
  precision claims are not reliable enough.
- **RQ1 answered at scale (2026-06-02, n~660, 3-vendor consensus gold,
  Fleiss kappa 0.625).** Atlas v2 (lex+theme) precision **41.6%**
  [37.8, 45.5]; LLM zero-shot **78.6%** [75.3, 81.7]; LLM few-shot
  **81.1%** [77.7, 84.0]. Tight Wilson/bootstrap CIs (~±4pts vs ±12 on the
  n=61 pilot). The single-layer classifier roughly halves achievable
  precision — the paper's core thesis holds with statistical force. Honest
  caveat: LLM precision fell from the n=61 pilot's 95% to ~80% on the larger,
  harder stratified sample; none pass the 90% gate, but the Atlas-vs-LLM gap
  is robust. Report: `reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.md`.
- The learned scope gate is the production precision lever; it decides
  keep/abstain on topic assignments.
- Gate quality must be read as precision plus coverage. Use
  `backend/scripts/gate_coverage_report.py` to monitor how many live
  assignments are scored, kept, abstained, or still unscored.
- Evidence-role quality should distinguish `verified`, `candidate`,
  `context_rich`, and `suppressed` tiers so Atlas can recover visible coverage
  without lowering the verified precision target.
- 2026-06-01 three-vendor evidence-role pass over 646 sampled cluster signals:
  605 consensus gold rows, 93.7% agreement, status
  `ready_for_student_training`. ~37.5% of sampled emergent-cluster signals are
  `noise` under consensus — emergent clusters carry significant off-topic
  membership, so the role layer is a precision/coverage filter, not just a
  re-label of cluster membership.
- [[2026-06-01-coverage-root-cause-lexicon-recall]] — the 17.77% gate kept rate
  is not gate over-abstention. 91% of the evidence-role gold set (and 93% of
  true primary_evidence) has no lexicon assignment at all. Coverage is a
  candidate-recall problem; the emergent-cluster + evidence-role student is the
  coverage engine. Do not lower the scope-gate threshold to chase coverage.
- Standing lexicon-recall baseline (`lexicon_recall_baseline.py`): 8.9% overall
  candidate recall, 6.6% on `primary_evidence`, and lexicon recall on `noise`
  (13.2%) is higher than on `primary_evidence` — the generator is biased toward
  off-topic candidates. This is the number the embedding cluster-membership
  generator must beat.
- Local Ollama on Pedro's current M1 is not a valid label teacher or judge:
  `llama3.2:1b` scored 25% decision accuracy on 20 reviewed batch 02 rows.
  Keep `ollama_*` outputs as reproducibility artifacts only; never merge them
  into `assistant_*`, `reviewer_*`, or `gold_*`.

## Reports and artifacts

- `docs/research/atlas-paper/phase-1-validation/reports/`
- `docs/research/atlas-paper/phase-1-validation/reports/agreement/`
- `docs/research/atlas-paper/phase-1-validation/reports/phase-b/`
- `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`
- `docs/research/atlas-paper/phase-1-validation/reports/ollama-local/`
- `docs/research/atlas-paper/phase-1-validation/models/`
- `docs/research/topic-quality/`

## Key scripts

- `backend/scripts/atlas_label_workflow.py`
- `backend/scripts/atlas_review_server.py`
- `backend/scripts/atlas_validation_report.py`
- `backend/scripts/llm_annotator.py`
- `backend/scripts/multi_annotator_agreement.py`
- `backend/scripts/kappa_calculator.py`
- `backend/scripts/benchmark_bootstrap.py`
- `backend/scripts/train_scope_gate.py`
- `backend/scripts/score_assignments_gate.py`
- `backend/scripts/gate_coverage_report.py`
- `backend/scripts/lexicon_recall_baseline.py`
- `backend/scripts/atlas_ollama_pilot.py`
