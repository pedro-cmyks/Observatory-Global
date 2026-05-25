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
4. Future adjudicated labels:
   `docs/research/atlas-paper/phase-1-validation/labels/gold/`
5. Score reports:
   `docs/research/atlas-paper/phase-1-validation/reports/`
6. Progress snapshots:
   `docs/research/atlas-paper/phase-1-validation/progress*.json`

## Current Artifacts

- Label guide:
  `docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md`
- Raw sample manifest:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.md`
- Raw batches: 8 files, 32 rows each, 256 total rows.
- Assistant pilot labels: batch 01 only, 32 rows.
- Assistant pilot score:
  `docs/research/atlas-paper/phase-1-validation/reports/assistant-pilot-batch-01-score.json`

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

## Next Work

1. Review assistant-pilot batch 01.
2. Decide whether to treat it as `reviewed` after human edits.
3. Continue labeling batches 02-08.
4. Merge reviewed/gold labels.
5. Score the full sample.
6. Use the score to define the first read-only Narrative Thread Graph report.
