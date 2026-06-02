# Local Ollama Route Deprecation

Date: 2026-06-02
Status: deprecated for Atlas validation and judging

## Decision

Do not use local Ollama models on Pedro's current M1 Mac as Atlas validation
judges, label teachers, or reviewer substitutes.

The local route was explored with `llama3.2:1b` because it fits the machine's
8 GB unified-memory constraint better than larger models. The model ran, but it
did not produce useful validation quality for the `atlas-topic-benchmark-v2`
task.

## Evidence

Pilot artifact:

- `docs/research/atlas-paper/phase-1-validation/reports/ollama-local/2026-06-02-batch-02-llama32-1b-report.json`

Result summary:

| Metric | Result |
|---|---:|
| Rows | 20 |
| Decision accuracy | 25.00% |
| Scope accuracy | 25.00% |
| Evidence-role accuracy | 11.76% |
| Invalid prediction rows after tolerant parsing | 3 |

The model could usually return parseable JSON after tolerant normalization, but
it over-rejected evidence rows and confused semantic scope with evidence role.
That makes it unsafe as a source of training labels or adjudication hints for
paper-grade Atlas validation.

## Deprecated Uses

- Generating `gold_*` labels.
- Replacing Pedro's review/adjudication.
- Acting as an assistant-pilot label source for `atlas-topic-benchmark-v2`.
- Training narrower Atlas boundaries from its outputs.
- Scoring model quality or paper claims.

## Allowed Uses

Local Ollama may still be used for low-stakes utility work where mistakes do not
enter validation labels or production scoring:

- Smoke-testing prompt and JSON-output plumbing.
- Drafting throwaway summaries for manual review.
- Local demos of the runner shape.
- Reproducing the 2026-06-02 negative result.

Any output from local Ollama must stay in separate `ollama_*` fields or
scratch artifacts. It must not be merged into `assistant_*`, `reviewer_*`, or
`gold_*` fields.

## Reopen Criteria

Reopen this route only if at least one material condition changes:

- A stronger local model fits the machine without disrupting daily-driver use.
- Hardware changes enough to run a materially better model.
- The task is narrowed to a simpler binary gate with a new measured benchmark.

Reopening requires a fresh run against reviewed/gold rows and should target at
least the existing Atlas precision floor before becoming operational:

- 85% minimum precision.
- 90% product target.

Until then, Atlas should use local compute for deterministic or lightweight
processing, and reserve stronger remote models for semantically hard labeling,
review hints, and narrative-intelligence judgments.
