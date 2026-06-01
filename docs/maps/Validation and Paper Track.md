# Validation and Paper Track MOC

This map tracks the research/validation work behind Atlas precision, scope
gating, annotator agreement, and the future paper series.

## Start here

- [[2026-05-27-atlas-papers-master-plan]] — eight-paper series outline.
- [[2026-05-27-methodology-paper-outline]] — Paper 1 outline.
- [[2026-05-28-precision-to-90-roadmap]] — path from static-topic precision to
  90-95%.
- [[2026-05-25-atlas-v2-labeling-guide]] — semantic/evidence-role label guide.

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

## Reports and artifacts

- `docs/research/atlas-paper/phase-1-validation/reports/`
- `docs/research/atlas-paper/phase-1-validation/reports/agreement/`
- `docs/research/atlas-paper/phase-1-validation/reports/phase-b/`
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
