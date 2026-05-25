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
  "schema_version": "atlas-topic-benchmark-v2",
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
  "gold_scope": null,
  "gold_evidence_role": null,
  "gold_parent_thread": null,
  "gold_child_thread": null,
  "gold_supported_questions": [],
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

Optional semantic/evidence fields:

| Field | Meaning |
|---|---|
| `gold_scope` | What the row really represents: domain, parent thread, child thread, entity thread, evidence, context, or noise. |
| `gold_evidence_role` | How the row supports analysis: primary event, follow-up, background, reaction, analysis, public attention, source amplification, or not evidence. |
| `gold_parent_thread` | Analyst-readable parent thread candidate when the row is broader than the assigned topic. |
| `gold_child_thread` | Analyst-readable child thread candidate when the row is specific enough to form a subthread. |
| `gold_supported_questions` | Which Atlas questions the row can support. |

Allowed `gold_scope` values:

| Value | Meaning |
|---|---|
| `domain` | Broad measurement domain, useful as an internal anchor but not a visible thread by itself. |
| `parent_thread` | Broad living thread that may contain more specific child threads. |
| `child_thread` | Specific current storyline with evidence and movement. |
| `entity_thread` | Entity-centered participation lens. |
| `geo_context` | Geography context, not direct thread evidence. |
| `source_context` | Source/provenance context, not direct thread evidence. |
| `evidence` | Direct evidence for the assigned thread. |
| `context_signal` | Relevant background but not primary evidence. |
| `noise` | Not useful for Atlas thread modeling. |

Allowed `gold_evidence_role` values:

| Value | Meaning |
|---|---|
| `primary_event` | Directly describes the event or change driving the thread. |
| `followup` | Follow-up coverage on an already established thread. |
| `background` | Historical or contextual support. |
| `reaction` | Official, public, market, or institutional response. |
| `analysis` | Analytical interpretation rather than primary reporting. |
| `public_attention` | Search, wiki, social, or attention signal. |
| `source_amplification` | Evidence of spread/syndication/source behavior. |
| `not_evidence` | Should not support the thread. |

Allowed `gold_supported_questions` values:

| Value | Atlas question |
|---|---|
| `why_moving` | Why is this moving now? |
| `what_changed` | What changed in the last 10h? |
| `where_concentrated` | Where is it concentrated? |
| `subthreads_forming` | Which subthreads are forming? |
| `sources_driving` | Which sources are driving it? |
| `evidence_support` | What evidence supports it? |
| `related_thread` | What related thread does it connect to? |

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
- error-type distribution;
- semantic-scope distribution;
- evidence-role distribution;
- supported-question distribution;
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

1. Relabel or supplement the 103-row priority sample with semantic scope,
   evidence role, parent/child candidates, and supported Atlas questions.
2. Score it with the harness.
3. If any promoted topic fails the 85% floor, keep it behind review/thin ranking
   and fix taxonomy/terms first.
4. Use the scope/role/question distributions to generate a read-only Narrative
   Thread Graph report.
5. Only after this loop is reliable should Path B train a multilingual encoder.
