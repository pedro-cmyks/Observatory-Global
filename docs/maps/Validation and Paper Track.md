# Validation and Paper Track MOC

This map tracks the research/validation work behind Atlas precision, scope
gating, annotator agreement, and the future paper series.

## Start here

- [[2026-05-27-atlas-papers-master-plan]] — eight-paper series outline.
- [[2026-05-27-methodology-paper-outline]] — Paper 1 outline.
- [[2026-05-28-precision-to-90-roadmap]] — path from static-topic precision to
  90-95%.
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — teacher-student
  design for classifying evidence roles inside narrative clusters.
- [[2026-06-01-narrative-cluster-evidence-roles]] — implementation plan for
  teacher packets, consensus labels, student reporting, and coverage metrics.
- [[2026-05-25-atlas-v2-labeling-guide]] — semantic/evidence-role label guide.
- Evidence-role teacher/student reports:
  `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`.

## Validation findings

- Rule editing helped but hit a ceiling; remaining failures are mainly semantic
  scope mismatches.
- Multi-vendor consensus is the defensible benchmark path; single-annotator
  precision claims are not reliable enough.
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

## Reports and artifacts

- `docs/research/atlas-paper/phase-1-validation/reports/`
- `docs/research/atlas-paper/phase-1-validation/reports/agreement/`
- `docs/research/atlas-paper/phase-1-validation/reports/phase-b/`
- `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`
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
