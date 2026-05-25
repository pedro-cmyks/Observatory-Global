# Atlas V2 Assistant Pilot Batch 01 Validation Report

Label quality: `assistant-pilot`
Schema: `atlas-topic-benchmark-v2`

## Summary

| Metric | Value |
|---|---:|
| Labeled denominator | 31 |
| Correct | 19 |
| Incorrect | 12 |
| Unclear | 1 |
| Precision | 61.29% |
| Gate | `fail` |
| Minimum gate | 85.00% |
| Target gate | 90.00% |

## Visuals

### Semantic Scope

![Semantic Scope](assistant-pilot-batch-01-scope.svg)

### Evidence Role

![Evidence Role](assistant-pilot-batch-01-evidence-role.svg)

### Supported Questions

![Supported Questions](assistant-pilot-batch-01-supported-questions.svg)

### Per-Topic Precision

![Per-Topic Precision](assistant-pilot-batch-01-topic-precision.svg)

## Per-Topic Precision

| Topic | Labeled | Correct | Incorrect | Unclear | Precision | Gate |
|---|---:|---:|---:|---:|---:|---|
| agriculture-crop-risk | 9 | 5 | 4 | 0 | 55.56% | `fail` |
| armed-conflict-escalation | 15 | 10 | 5 | 1 | 66.67% | `fail` |
| constitutional-institutional-crisis | 7 | 4 | 3 | 0 | 57.14% | `fail` |

## Interpretation Guardrail

This report may be useful for workflow debugging and internal model design. Do not treat non-gold labels as paper-grade evidence. Assistant-pilot labels require human review or adjudication before they can support final claims.
