# Phase 1 Validation Experiment Log

## 2026-05-25 — Stratified V2 Sample Created

Input:

- `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl`

Summary:

- 256 rows.
- 30 active Atlas topics.
- Four buckets: `lex_high_conf`, `lex_low_conf`, `theme_high_conf`,
  `theme_low_conf`.
- Dominated by GDELT and English/`xx` language rows.

Purpose:

- Test whether `atlas-topic-benchmark-v2` can label semantic scope, evidence
  role, parent/child candidates, and supported Atlas questions.

## 2026-05-25 — Batch Split

Command:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py split \
  --input docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl \
  --output-dir docs/research/atlas-paper/phase-1-validation/batches \
  --batch-size 32 \
  --prefix 2026-05-25-atlas-v2-stratified
```

Result:

- 8 batch files.
- 32 rows per batch.
- 256 total rows.

## 2026-05-25 — Assistant Pilot Labels For Batch 01

Input:

- `docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl`

Output:

- `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl`

Important caveat:

- These are not gold labels.
- Use them to test workflow, score shape, and reviewer instructions.
- They need human review before becoming paper-grade evidence.

Score:

- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01-score.json`

Score summary:

| Metric | Value |
|---|---:|
| Rows | 32 |
| Labeled denominator | 31 |
| Correct | 19 |
| Incorrect | 12 |
| Unclear | 1 |
| Precision | 61.29% |
| Gate | fail |

Distribution summary:

| Dimension | Top values |
|---|---|
| `gold_scope` | `child_thread=16`, `context_signal=7`, `noise=4`, `parent_thread=4` |
| `gold_evidence_role` | `primary_event=10`, `background=7`, `analysis=5`, `not_evidence=4` |
| `gold_error_type` | `primary_context_mismatch=6`, `off_topic=3`, `scope_mismatch=2` |
| `gold_supported_questions` | `evidence_support=16`, `related_thread=15`, `where_concentrated=12` |

Interpretation:

- The label schema is exposing useful distinctions.
- The first pilot confirms that many failures are not simple noise. They include
  context rows, parent-thread candidates, and primary-context mismatches.
- The score should not be treated as a production-quality measurement until
  labels are reviewed.

## 2026-05-25 — Visual Validation Report For Assistant Pilot Batch 01

Input:

- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01-score.json`

Output:

- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01.md`
- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01-scope.svg`
- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01-evidence-role.svg`
- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01-supported-questions.svg`
- `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01-topic-precision.svg`

Purpose:

- Keep the research visuals outside the production UI.
- Make tables and charts reproducible from score JSON.
- Provide report-ready artifacts that can later support the paper after labels
  are reviewed/adjudicated.

Guardrail:

- These charts are based on assistant-pilot labels. They are workflow evidence,
  not paper-grade model evidence.
