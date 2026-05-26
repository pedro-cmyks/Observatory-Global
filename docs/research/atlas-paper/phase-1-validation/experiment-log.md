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

## 2026-05-25 — Human Review Packet For Batch 01

Input:

- Raw batch:
  `docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl`
- Assistant-pilot labels:
  `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl`

Output:

- `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md`

Command:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py review-packet \
  --raw docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl \
  --labels docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md \
  --title "Atlas V2 Batch 01 Human Review Packet"
```

Purpose:

- Make the adjudication step explicit and reproducible.
- Keep raw evidence and assistant-pilot suggestions side by side.
- Give reviewers blank fields for decision, scope, evidence role,
  parent/child thread candidates, supported questions, and notes.

Next decision:

- Human review should either accept the assistant-pilot label, correct it into
  a reviewed label file, or mark the row as uncertain. Only reviewed/adjudicated
  labels can become paper-grade `gold` evidence.

## 2026-05-25 — Machine-Editable Review Template For Batch 01

Input:

- Raw batch:
  `docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl`
- Assistant-pilot labels:
  `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl`

Output:

- `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl`

Purpose:

- Provide a machine-editable companion to the Markdown review packet.
- Keep `assistant_*` suggestion fields separate from blank `reviewer_*` fields.
- Avoid converting assistant-pilot labels into reviewed/gold labels by accident.

Next decision:

- Fill reviewer fields after human adjudication. A future conversion step can
  then produce a reviewed/gold JSONL file for scoring without copying values out
  of Markdown.

## 2026-05-25 — Review Progress And Finalization Commands

Output:

- `docs/research/atlas-paper/phase-1-validation/progress-review-batch-01.json`

Current progress:

| Metric | Value |
|---|---:|
| Total rows | 32 |
| Ready rows | 0 |
| Remaining rows | 32 |
| Accepted assistant rows | 0 |
| Reviewer-corrected rows | 0 |

Interpretation:

- This is the expected state before human adjudication.
- No assistant-pilot label has been accepted as reviewed/gold evidence.
- No scoreable reviewed/gold file was generated.

New workflow commands:

- `review-progress` reports whether a review template has enough decisions to
  become scoreable.
- `finalize-review` converts completed rows into scoreable labels with
  `gold_*` fields and a `label_quality` of either `reviewed` or `gold`.
- `--require-complete` blocks accidental partial reviewed/gold outputs.

## 2026-05-26 — Batch 01 Markdown Review Applied

Inputs:

- Review packet:
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md`
- Review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl`

Outputs:

- Updated review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl`
- Normalization report:
  `docs/research/atlas-paper/phase-1-validation/reports/batch-01-md-review-normalization.json`
- Reviewed labels:
  `docs/research/atlas-paper/phase-1-validation/labels/reviewed/2026-05-25-atlas-v2-stratified-batch-01.reviewed.jsonl`
- Reviewed score:
  `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01-score.json`
- Reviewed visual report:
  `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01/reviewed-batch-01.md`

Review progress after applying Markdown answers:

| Metric | Value |
|---|---:|
| Total rows | 32 |
| Ready rows | 32 |
| Remaining rows | 0 |
| Accepted assistant rows | 23 |
| Reviewer-corrected rows | 9 |
| Normalization warnings | 7 |

Reviewed score:

| Metric | Value |
|---|---:|
| Labeled denominator | 30 |
| Correct | 16 |
| Incorrect | 14 |
| Unclear | 2 |
| Precision | 53.33% |
| Gate | fail |

Per-topic precision:

| Topic | Precision | Note |
|---|---:|---|
| `agriculture-crop-risk` | 25.00% | Severe scope/context leakage. |
| `armed-conflict-escalation` | 66.67% | Better but still below precision gate. |
| `constitutional-institutional-crisis` | 57.14% | Mixed evidence and scope failures. |

Interpretation:

- This is now `reviewed`, not `gold`.
- The batch supports the model-level diagnosis: failures are dominated by
  semantic scope and primary-context mismatch, not only substring noise.
- Do not promote model/ranking changes from this batch. Continue batches 02-08
  and review the 7 normalization warnings before declaring any paper-grade
  result.

## 2026-05-26 — Batch 02 Prepared With Local Review UI

New tool:

- `backend/scripts/atlas_review_server.py`

Purpose:

- Serve a local one-row-at-a-time adjudication UI at `localhost`.
- Show assistant-pilot labels as hints, not truth.
- Save reviewer choices directly into the JSONL review template.
- Make closed fields selectable through buttons/checkboxes and keep free text
  only for parent thread, child thread, and notes.

Batch 02 artifacts:

- Assistant-pilot labels:
  `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-02.assistant-pilot.jsonl`
- Review packet:
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-02.review.md`
- Review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl`
- Progress:
  `docs/research/atlas-paper/phase-1-validation/progress-review-batch-02.json`

Current batch 02 state:

| Metric | Value |
|---|---:|
| Total rows | 32 |
| Ready rows | 0 |
| Remaining rows | 32 |
| Assistant hints | 32 |

Why keep hints:

- They let us compare assistant interpretation against reviewer interpretation.
- They help identify whether failure is model/assistant interpretation,
  ambiguous evidence, or reviewer disagreement.
- They must stay separate from `reviewer_*` fields until explicitly accepted.
