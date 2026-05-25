# Atlas V2 Labeling Guide

Date: 2026-05-25  
Status: active guide for Phase 1 validation  
Related: #203, #204, #207  
Schema: `atlas-topic-benchmark-v2`  

## Purpose

This guide defines how to label Atlas benchmark rows so the model can be
validated as a narrative intelligence system rather than a flat topic
classifier.

The goal is not to make every row fit the assigned topic. The goal is to
identify what the row actually is:

- direct evidence;
- broader parent thread;
- specific child thread;
- entity participation;
- geography/source context;
- background context;
- or noise.

This guide supports the research plan in
`docs/research/atlas-paper/2026-05-25-atlas-narrative-intelligence-state-of-art-and-validation-plan.md`.

## Labeling Unit

Each JSONL row is one candidate assignment:

```json
{
  "signal_id": 4439755,
  "assigned_topic_slug": "armed-conflict-escalation",
  "assigned_topic_label": "Armed conflict escalation",
  "headline": "Missile strikes pound Kyiv after Russia vows retaliation",
  "source_name": "example.org",
  "source_family": "api",
  "source_lang": "en",
  "country_code": "UA",
  "confidence": 0.9,
  "sample_bucket": "lex_high_conf",
  "evidence": {
    "lex_count": 2,
    "matched_terms": ["missile strike", "missile strikes"]
  }
}
```

Label the assignment using only the fields present in the row. If the headline
is too thin, use `gold_decision = "unclear"` and explain why in `notes`.

## Required Label Fields

### `gold_decision`

| Value | Use when |
|---|---|
| `correct` | The row is valid for the assigned Atlas anchor or thread level. |
| `incorrect` | The row should not support the assigned anchor/thread. |
| `unclear` | The available row is too thin to label confidently. |

Decision rule:

- Use `correct` when the row can support the assigned topic as direct evidence,
  a valid child thread, or a valid parent-thread signal.
- Use `incorrect` when the row is noise, wrong scope, wrong primary context, or
  belongs elsewhere.
- Use `unclear` sparingly. It is excluded from precision denominators and
  should not become a hiding place for difficult labels.

### `gold_scope`

| Value | Definition | Example cue |
|---|---|---|
| `domain` | Broad internal measurement area, not a visible thread by itself. | "health", "security", "labor" without current event. |
| `parent_thread` | Broad living narrative that can contain child threads. | "Panama Canal shipping pressure" without a specific incident. |
| `child_thread` | Specific current storyline with evidence and movement. | "coal mine explosion in Shanxi". |
| `entity_thread` | Entity-centered participation lens. | "Donald Trump in election legitimacy dispute". |
| `geo_context` | Geography context, not direct thread evidence. | country mention without event relevance. |
| `source_context` | Source/provenance context, not direct thread evidence. | source repeats a wire story or syndication signal. |
| `evidence` | Direct evidence for the assigned thread. | incident, policy, strike, outbreak, protest, disaster. |
| `context_signal` | Related background, not primary evidence. | explainer, historical summary, broad analysis. |
| `noise` | Not useful for Atlas thread modeling. | sports, entertainment, substring artifact. |

Preferred rule:

- If a row describes a specific event or update, prefer `child_thread` or
  `evidence`.
- If a row names a broad concept without a specific disruption/crisis/event,
  prefer `parent_thread` or `context_signal`.
- If a row is only connected by a coincidental term, use `noise`.

### `gold_evidence_role`

| Value | Definition |
|---|---|
| `primary_event` | Directly reports the event/change driving the thread. |
| `followup` | Later update on an established event/thread. |
| `background` | Historical/contextual material. |
| `reaction` | Official, public, institutional, market, or civil response. |
| `analysis` | Analytical interpretation, forecast, or opinion. |
| `public_attention` | Search, wiki, social, or attention signal. |
| `source_amplification` | Evidence of spread, syndication, or source behavior. |
| `not_evidence` | Should not support the thread. |

Decision rule:

- `gold_scope` says what the row is in the Atlas model.
- `gold_evidence_role` says how the row supports analysis.
- A row can be `parent_thread` scope and `background` role.
- A row can be `child_thread` scope and `primary_event` role.
- A row labeled `noise` should usually use `not_evidence`.

### `gold_supported_questions`

Use zero or more values.

| Value | Question supported |
|---|---|
| `why_moving` | Why is this moving now? |
| `what_changed` | What changed in the last 10h? |
| `where_concentrated` | Where is it concentrated? |
| `subthreads_forming` | Which subthreads are forming? |
| `sources_driving` | Which sources are driving it? |
| `evidence_support` | What evidence supports it? |
| `related_thread` | What related thread does it connect to? |

Decision rule:

- Do not mark a question unless the row actually helps answer it.
- Most single headlines should support only one to three questions.
- A direct incident headline often supports `where_concentrated` and
  `evidence_support`.
- A follow-up or timeline headline may support `what_changed`.
- A broad parent/entity row may support `related_thread`.
- Source behavior rows may support `sources_driving`.

## Optional Fields

### `gold_topic_slug`

Use when there is a better existing Atlas topic.

- If the assignment is correct, use the assigned slug or leave null.
- If another Atlas topic is clearly better, put that slug.
- If the row is outside current Atlas taxonomy, leave null and explain in
  `notes`.

### `gold_parent_thread`

Use a short natural-language parent candidate:

- `mining-resource-safety`;
- `transport-corridor-pressure`;
- `election-legitimacy`;
- `cross-border-displacement`;
- `labor-and-cost-of-living-pressure`.

This does not need to match an existing slug. It is evidence for future thread
graph design.

### `gold_child_thread`

Use when the row is specific enough to form or support a child storyline:

- `shanxi-coal-mine-explosion`;
- `panama-canal-drought-shipping-delays`;
- `ebola-border-preparedness`;
- `kyiv-missile-strikes`;
- `fuel-price-protest-in-nepal`.

### `gold_error_type`

Use only when `gold_decision` is `incorrect` or `unclear`.

| Value | Use when |
|---|---|
| `substring_noise` | String match artifact. |
| `scope_mismatch` | Correct broad area, wrong assigned level. |
| `parent_thread_candidate` | Broad concept is useful, but not direct evidence. |
| `primary_context_mismatch` | Assigned term is background, not the main story. |
| `insufficient_context` | Headline/source too thin. |
| `off_topic` | Truly unrelated. |

## Canonical Examples

### Correct Child Evidence

Headline:

> Coal mine explosion in Shanxi leaves workers trapped

Labels:

```json
{
  "gold_decision": "correct",
  "gold_scope": "child_thread",
  "gold_evidence_role": "primary_event",
  "gold_parent_thread": "mining-resource-safety",
  "gold_child_thread": "shanxi-coal-mine-explosion",
  "gold_supported_questions": ["where_concentrated", "evidence_support"]
}
```

Why: specific event, clear geography, direct evidence.

### Broad Parent, Not Direct Disruption

Headline:

> Panama Canal authority announces annual infrastructure forum

Labels:

```json
{
  "gold_decision": "incorrect",
  "gold_error_type": "parent_thread_candidate",
  "gold_scope": "parent_thread",
  "gold_evidence_role": "background",
  "gold_parent_thread": "panama-canal-shipping-pressure",
  "gold_child_thread": null,
  "gold_supported_questions": ["related_thread"]
}
```

Why: Panama Canal may be a valid parent/entity thread, but this row is not
evidence of transport disruption.

### Primary Context Mismatch

Headline:

> Mayor discusses housing in speech after corruption indictment

Labels:

```json
{
  "gold_decision": "incorrect",
  "gold_error_type": "primary_context_mismatch",
  "gold_scope": "context_signal",
  "gold_evidence_role": "background",
  "gold_supported_questions": []
}
```

Why: housing appears, but the primary story is corruption/legal process.

### Source Amplification

Headline:

> Reuters: fuel protest story republished by regional outlets

Labels:

```json
{
  "gold_decision": "correct",
  "gold_scope": "source_context",
  "gold_evidence_role": "source_amplification",
  "gold_parent_thread": "fuel-price-unrest",
  "gold_supported_questions": ["sources_driving"]
}
```

Why: not primary event evidence, but useful for source dynamics.

### Unclear

Headline:

> Officials respond as tensions rise

Labels:

```json
{
  "gold_decision": "unclear",
  "gold_error_type": "insufficient_context",
  "gold_scope": null,
  "gold_evidence_role": null,
  "gold_supported_questions": [],
  "notes": "No actor, place, event, or issue is visible in the row."
}
```

Why: too little information to label responsibly.

## Sample Buckets

The benchmark sample currently uses four assignment buckets:

| Bucket | Meaning |
|---|---|
| `lex_high_conf` | Lexicon-supported assignment with confidence >= 0.75. |
| `lex_low_conf` | Lexicon-supported assignment with confidence < 0.75. |
| `theme_high_conf` | Theme-only assignment with confidence >= 0.75. |
| `theme_low_conf` | Theme-only assignment with confidence < 0.75. |

Interpretation:

- `lex_high_conf` should be the cleanest bucket.
- `theme_low_conf` should reveal theme leakage and weak assignment logic.
- `lex_low_conf` often reveals broad terms that need scope separation.
- `theme_high_conf` tests whether GDELT theme hints can ever be trusted without
  direct lexical support.

## Label Quality Rules

1. Prefer explicit evidence over inferred meaning.
2. Do not mark `correct` just because the assigned topic is nearby.
3. Do not mark `incorrect` just because the row is broad; broad rows may be
   parent/entity/context signals.
4. Use `notes` for uncertainty and for potential new parent/child threads.
5. Keep labels stable across languages. If the row is non-English and the
   meaning is clear, label the meaning, not the language.
6. Do not optimize for Atlas looking good. The labels exist to find where the
   model fails.

## Reviewer Workflow

1. Read the assigned topic label and headline.
2. Decide whether the row supports the assigned topic/thread.
3. Assign `gold_decision`.
4. Assign `gold_scope`.
5. Assign `gold_evidence_role`.
6. Fill parent/child candidates if useful.
7. Mark supported Atlas questions.
8. Add `gold_error_type` if incorrect or unclear.
9. Add a short `notes` value when the decision would not be obvious to a second
   reviewer.

## Immediate Use

Use this guide for the next stratified sample:

```bash
backend/.venv/bin/python backend/scripts/topic_benchmark_harness.py sample \
  --hours 24 \
  --per-bucket 4 \
  --output docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl
```

Expected maximum size with 30 active topics and four buckets is 480 rows. Actual
size may be lower if some topics have no rows in a bucket.
