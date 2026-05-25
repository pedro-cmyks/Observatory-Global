# Path B Benchmark Harness

Date: 2026-05-25  
Issue: https://github.com/pedro-cmyks/Observatory-Global/issues/203  
Status: first read-only harness implemented

## Purpose

Atlas needs a quality indicator that is defensible. That means precision must be
measured from labeled examples, not inferred only from `lex_pct`, confidence, or
visual review.

This first Path B increment does **not** train or promote an encoder. It creates
the benchmark harness needed before any model promotion.

## Tool

```text
backend/scripts/topic_benchmark_harness.py
```

Modes:

```bash
# Generate label-ready JSONL from production assignments.
python backend/scripts/topic_benchmark_harness.py sample \
  --hours 24 \
  --per-bucket 12 \
  --topic armed-conflict-escalation \
  --output docs/research/topic-quality/benchmark-samples/sample.jsonl

# Score a labeled JSONL file.
python backend/scripts/topic_benchmark_harness.py score \
  --input docs/research/topic-quality/benchmark-samples/sample-labeled.jsonl \
  --output docs/research/topic-quality/benchmark-scores/sample-score.json
```

The script is read-only against the database. It does not write benchmark labels
into `topic_learning_examples` yet.

## Label Schema

Each JSONL row is one candidate assignment:

```json
{
  "schema_version": "atlas-topic-benchmark-v1",
  "signal_id": 4439755,
  "assigned_topic_slug": "armed-conflict-escalation",
  "assigned_topic_label": "Armed conflict escalation",
  "headline": "Missile strikes pound Kyiv after Russia vows retaliation",
  "source_name": "thefrontierpost.com",
  "country_code": "UA",
  "confidence": 0.9,
  "sample_bucket": "lex_supported",
  "evidence": {
    "lex_count": 2,
    "matched_terms": ["missile strike", "missile strikes"]
  },
  "gold_decision": null,
  "gold_topic_slug": null,
  "gold_error_type": null,
  "notes": null
}
```

Allowed `gold_decision` values:

| Value | Meaning |
|---|---|
| `correct` | Headline fits the assigned topic label. |
| `incorrect` | Headline does not fit the assigned topic label. |
| `unclear` | Not enough context from headline/source to judge. Excluded from denominator. |

Optional `gold_topic_slug`:

- same as `assigned_topic_slug` for confirmed rows;
- another topic slug if the assignment is wrong but a better Atlas topic exists;
- `null` if it is noise or outside current taxonomy.

Optional `gold_error_type`:

| Value | Meaning |
|---|---|
| `substring_noise` | The match is an artifact of substring matching, such as `rape` inside `parapente`. |
| `scope_mismatch` | The signal belongs to a broader/neighboring concept but not the assigned specific thread. |
| `parent_thread_candidate` | The term may deserve a parent/entity thread, but not this specific assignment. |
| `primary_context_mismatch` | The matched topic appears as background, while another topic is primary. |
| `insufficient_context` | The headline alone is too thin to label confidently. |
| `off_topic` | The row is unrelated to the assigned topic and not useful as a parent candidate. |

## First Benchmark Sample

Generated artifact:

```text
docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl
```

Rows: 103

| Topic | Rows | Buckets |
|---|---:|---|
| `armed-conflict-escalation` | 24 | 12 lex-supported, 12 theme-only |
| `disease-outbreak` | 24 | 12 lex-supported, 12 theme-only |
| `food-price-stress` | 10 | 10 lex-supported |
| `forced-displacement` | 12 | 12 lex-supported |
| `gender-violence-rights` | 12 | 12 lex-supported |
| `labor-strike-disruption` | 12 | 12 lex-supported |
| `transport-corridor-disruption` | 9 | 9 lex-supported |

This set intentionally emphasizes topics that recently changed or remain risky
after migrations 040-041.

## Precision Gate

The scoring function reports:

- overall precision;
- per-topic precision;
- `unclear` counts outside the precision denominator;
- gate classification.

Gate:

| Precision | Gate |
|---:|---|
| `< 85%` | `fail` |
| `85%` to `< 90%` | `pass_minimum` |
| `>= 90%` | `pass_target` |

No encoder score or ranking change should ship below `pass_minimum`; production
default behavior should target `pass_target`.

## Next Step

1. Label the 103-row priority sample.
2. Score it with the harness.
3. If any promoted topic fails the 85% floor, keep it behind review/thin ranking
   and fix taxonomy/terms first.
4. Only after this loop is reliable should Path B train a multilingual encoder.
