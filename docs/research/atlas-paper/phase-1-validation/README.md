# Atlas Paper Phase 1 Validation

Date: 2026-05-25  
Status: active validation workspace  

## Purpose

This folder keeps Phase 1 of the Atlas Narrative Intelligence paper track in one
place. Phase 1 asks whether the `atlas-topic-benchmark-v2` label schema is
usable and whether it reveals meaningful semantic/evidence failures.

This is a validation workspace, not a final paper folder.

## Route

1. Source sample:
   `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl`
2. Raw labeling batches:
   `docs/research/atlas-paper/phase-1-validation/batches/`
3. Pilot labels:
   `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/`
4. Human review/adjudication packets:
   `docs/research/atlas-paper/phase-1-validation/review-packets/`
5. Machine-editable review templates:
   `docs/research/atlas-paper/phase-1-validation/review-templates/`
6. Future adjudicated labels:
   `docs/research/atlas-paper/phase-1-validation/labels/gold/`
7. Score reports:
   `docs/research/atlas-paper/phase-1-validation/reports/`
8. Visual validation reports:
   `docs/research/atlas-paper/phase-1-validation/reports/<run-name>/`
9. Progress snapshots:
   `docs/research/atlas-paper/phase-1-validation/progress*.json`

## Current Artifacts

- Label guide:
  `docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md`
- Raw sample manifest:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.md`
- Raw batches: 8 files, 32 rows each, 256 total rows.
- Assistant pilot labels: batch 01 only, 32 rows.
- Assistant pilot labels: batch 01 and batch 02, 32 rows each.
- Assistant pilot score:
  `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01-score.json`
- Assistant pilot visual report:
  `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01/assistant-pilot-batch-01.md`
- Human review packet:
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md`
- Machine-editable review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl`
- Review progress snapshot:
  `docs/research/atlas-paper/phase-1-validation/progress-review-batch-01.json`
- Reviewed labels:
  `docs/research/atlas-paper/phase-1-validation/labels/reviewed/2026-05-25-atlas-v2-stratified-batch-01.reviewed.jsonl`
- Reviewed score:
  `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01-score.json`
- Reviewed visual report:
  `docs/research/atlas-paper/phase-1-validation/reports/reviewed-batch-01/reviewed-batch-01.md`
- Markdown normalization report:
  `docs/research/atlas-paper/phase-1-validation/reports/batch-01-md-review-normalization.json`
- Batch 02 assistant-pilot labels:
  `docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-02.assistant-pilot.jsonl`
- Batch 02 review packet:
  `docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-02.review.md`
- Batch 02 review template:
  `docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl`
- Batch 02 review progress:
  `docs/research/atlas-paper/phase-1-validation/progress-review-batch-02.json`

## Label Quality Levels

| Level | Meaning | Paper usage |
|---|---|---|
| `raw` | Unlabeled sample/batch. | Input only. |
| `assistant-pilot` | Labels proposed by an AI assistant for workflow testing. | Not gold; use for process debugging only. |
| `reviewed` | Human reviewed but not adjudicated. | Useful for internal decisions. |
| `gold` | Human/adjudicated labels. | Eligible for paper metrics. |

Do not cite assistant-pilot labels as final evidence in a paper. They are useful
for testing the schema and workflow.

## Commands

Split the sample into batches:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py split \
  --input docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl \
  --output-dir docs/research/atlas-paper/phase-1-validation/batches \
  --batch-size 32 \
  --prefix 2026-05-25-atlas-v2-stratified
```

Check progress:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py progress \
  docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/*.jsonl
```

Generate a human review packet from raw rows plus assistant-pilot labels:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py review-packet \
  --raw docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl \
  --labels docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md \
  --title "Atlas V2 Batch 01 Human Review Packet"
```

Generate a machine-editable review template:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py review-template \
  --raw docs/research/atlas-paper/phase-1-validation/batches/2026-05-25-atlas-v2-stratified-batch-01.jsonl \
  --labels docs/research/atlas-paper/phase-1-validation/labels/assistant-pilot/2026-05-25-atlas-v2-stratified-batch-01.assistant-pilot.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl
```

Check review/adjudication progress:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py review-progress \
  docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl \
  > docs/research/atlas-paper/phase-1-validation/progress-review-batch-01.json
```

Apply reviewer answers from a Markdown review packet into the JSONL template:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py apply-review-packet \
  --packet docs/research/atlas-paper/phase-1-validation/review-packets/2026-05-25-atlas-v2-stratified-batch-01.review.md \
  --template docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl \
  --report docs/research/atlas-paper/phase-1-validation/reports/batch-01-md-review-normalization.json
```

Finalize a completed review template into scoreable labels:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py finalize-review \
  --input docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-01.review-template.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/labels/reviewed/2026-05-25-atlas-v2-stratified-batch-01.reviewed.jsonl \
  --label-quality reviewed \
  --require-complete
```

Merge future gold batches:

```bash
backend/.venv/bin/python backend/scripts/atlas_label_workflow.py merge \
  --input-dir docs/research/atlas-paper/phase-1-validation/labels/gold \
  --output docs/research/atlas-paper/phase-1-validation/labels/atlas-v2-stratified.gold.jsonl
```

Score labels:

```bash
backend/.venv/bin/python backend/scripts/topic_benchmark_harness.py score \
  --input docs/research/atlas-paper/phase-1-validation/labels/atlas-v2-stratified.gold.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/reports/atlas-v2-stratified.gold-score.json
```

Render a visual report from a score:

```bash
backend/.venv/bin/python backend/scripts/atlas_validation_report.py \
  --score docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01-score.json \
  --output-dir docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01 \
  --title "Atlas V2 Assistant Pilot Batch 01 Validation Report" \
  --label-quality assistant-pilot \
  --report-name assistant-pilot-batch-01
```

Open the local adjudication UI for batch 02:

```bash
backend/.venv/bin/python backend/scripts/atlas_review_server.py \
  --template docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl \
  --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

The local UI writes directly to the review template. It shows one row at a time,
keeps assistant hints as `assistant_*`, and writes reviewer choices to
`reviewer_*`.

Deprecated local Ollama comparison, kept only for reproducibility:

```bash
backend/.venv/bin/python backend/scripts/atlas_ollama_pilot.py \
  --input docs/research/atlas-paper/phase-1-validation/review-templates/2026-05-25-atlas-v2-stratified-batch-02.review-template.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/reports/ollama-local/2026-06-02-batch-02-llama32-1b.jsonl \
  --report docs/research/atlas-paper/phase-1-validation/reports/ollama-local/2026-06-02-batch-02-llama32-1b-report.json \
  --limit 20 \
  --model llama3.2:1b
```

This writes separate `ollama_*` fields and resolved `gold_*` comparison fields.
It does not modify review templates.

Decision: do not use local Ollama models on Pedro's M1 as Atlas judges, label
teachers, or reviewer substitutes. The 2026-06-02 `llama3.2:1b` pilot reached
only 25% decision accuracy on 20 reviewed batch 02 rows. Keep the script and
artifacts as historical evidence; restart this route only with a materially new
model/hardware hypothesis and a fresh benchmark.

## Next Work

1. Keep batch 01 and batch 02 as reviewed diagnostic evidence, not paper-grade
   proof; both remain below the 85% minimum precision gate.
2. Use the reviewed batch 02 labels for assistant-vs-reviewer and local-model
   comparison, but do not treat local Ollama output as gold or hints.
3. Continue the paper track with larger consensus-gold batches and the measured
   improvement levers: scope gate, evidence-role student, dynamic topic
   self-curation, and per-topic remediation.
4. Merge reviewed/gold labels only after the current batch's normalization
   report and score have been inspected.
5. Score the full sample.
6. Render visual validation reports for reviewed/gold scores.
7. Use the score and visual report to define the first read-only Narrative
   Thread Graph report.
