# Narrative Classification Root Cause Audit

Date: 2026-05-25  
Status: active diagnostic canon  
Related: #203, #204, #207  
Inputs:

- `docs/specs/2026-05-24-living-narrative-threads.md`
- `docs/research/topic-quality/2026-05-25-path-b-priority-label-results.md`
- `docs/research/topic-quality/2026-05-25-atlas-quality-models-market-and-product.md`
- `backend/app/services/thread_intelligence.py`
- `backend/scripts/backfill_lexicon_topics.py`
- `docs/specs/2026-05-23-ai-assisted-taxonomy.md`

## Executive Read

The first Path B benchmark should not be interpreted as "these specific topics
need fixes." That is too shallow.

The benchmark exposed a root problem in the model:

> Atlas is asking one internal assignment layer to represent several different
> semantic levels at once.

The current system compresses these different objects into one thing:

- broad domains, such as health, transport, labor, conflict;
- parent threads, such as Panama Canal coverage or Ebola concern;
- child threads, such as Panama Canal drought/closure or Ebola border
  preparedness;
- entities and places, such as Panama Canal, Gaza, Kyiv, DRC;
- evidence rows, such as one headline;
- contextual mentions, where a term appears but is not the main narrative.

That compression creates the "fix forever" loop: every false positive looks
like a topic-specific lexicon problem, so the system gets patched term by term.
Some patches are valid, but they do not solve the structural issue.

## What The Current System Actually Does

### Classification Layer

`backend/scripts/backfill_lexicon_topics.py` assigns `signals_v2` rows to
`atlas_topics` when either:

- a headline substring matches `atlas_topics.lexicon_terms`; or
- a GDELT theme overlaps `atlas_topics.gdelt_theme_hints`.

It writes `signal_topic_assignments` with:

- `method = lexicon`;
- `model_version = theme-hint-lex-v2`;
- a confidence formula based on lex hits and theme hits.

This layer is useful as an interpretable anchor layer. It is not yet a full
narrative model.

### Thread Layer

`backend/app/services/thread_intelligence.py` exposes `/api/v2/threads`, but
the current SQL groups by `atlas_topics.topic_slug`.

That means a visible "thread" is currently:

```text
one atlas_topic anchor + top countries + movement metadata + evidence samples
```

This was the correct first beta because it gave the UI a thread-shaped contract
without a schema migration. It is no longer enough for the product direction.

### Product Layer

The visible product wants living Narrative Threads:

- natural-language clusters;
- parent/child relationships;
- entities as lenses;
- evidence roles;
- split/merge/fade lifecycle;
- "why this is moving now."

Those are richer than the current assignment layer.

## Benchmark Finding

The first 103-row Path B labeled sample scored:

| Scope | Precision | Gate |
|---|---:|---|
| Overall | 80.85% | fail |
| Floor | 85.00% | minimum |
| Product target | 90.00% | target |

The useful result is not the per-topic score. The useful result is the error
type distribution:

| Error type | Count | Structural meaning |
|---|---:|---|
| `scope_mismatch` | 8 | The row belongs near the domain, but not the assigned child concept. |
| `insufficient_context` | 5 | The headline alone is too thin for a hard label. |
| `parent_thread_candidate` | 4 | The concept may be a valid broad/entity thread. |
| `primary_context_mismatch` | 4 | The matched term is context, not the main narrative. |
| `substring_noise` | 3 | Mechanical matching bug. |
| `off_topic` | 3 | True unrelated noise. |

Only `substring_noise` and some `off_topic` rows are straightforward pruning
problems. The rest indicate a missing semantic hierarchy.

## Root Causes

### 1. The unit of classification is too flat

The model currently asks: "Does this signal belong to this atlas topic?"

Atlas needs to ask a sequence of questions:

1. What broad domain does this signal touch?
2. Is there an active parent thread?
3. Is there a more specific child thread?
4. Is the matched concept an entity, geography, source lane, or evidence row?
5. Is the signal primary evidence or contextual evidence?
6. Is this signal strong enough to train a model label?

Without this sequence, terms like `Panama Canal`, `Ebola`, `union`, `asylum`,
or `missile attack` get treated as if they all mean the same kind of object.

### 2. `atlas_topics` is doing two jobs

`atlas_topics` is good as an internal anchor vocabulary:

- stable measurement;
- historical aggregation;
- precision gates;
- benchmark sampling;
- replayable SQL backfills.

It is not sufficient as the visible product taxonomy.

The app should not force the user to understand the internal anchor table. It
should expose threads that form from evidence. The internal anchor can remain
as one feature feeding that thread model.

### 3. GDELT themes are hints, not narrative truth

GDELT themes are useful for recall and context. They are not specific enough to
prove a living thread.

The current failure mode is not "GDELT is bad." It is:

- GDELT often gives a broad domain hint;
- the lexicon often gives a term/entity hint;
- Atlas currently lacks a layer that decides whether that hint is primary
  thread evidence, parent context, entity context, or noise.

### 4. Lexicon terms have mixed semantic roles

Some lexicon terms are event-specific:

- `missile strike`;
- `food inflation`;
- `public health emergency`.

Some are broad concepts:

- `Panama Canal`;
- `asylum seekers`;
- `union`;
- `Ebola`.

Some are unsafe substrings:

- `rape` matching `parapente`.

The current lexicon stores all of these as one array. That loses the role of
the term.

### 5. The benchmark question is underspecified

The first benchmark asked:

> Is this assignment correct?

That is necessary, but not sufficient. A better benchmark asks:

> What semantic role does this signal have relative to the assigned anchor?

The answer may be:

- correct child-thread evidence;
- correct parent-thread evidence;
- entity-thread candidate;
- context only;
- insufficient context;
- substring noise;
- off-topic.

This lets Atlas learn the model, not just trim terms.

## Correct Conceptual Model

Atlas should represent narrative information with separate levels:

| Level | Meaning | Example |
|---|---|---|
| `domain` | Broad area of the world model. | Health, conflict, labor, transport. |
| `parent_thread` | Broad living narrative cluster. | Ebola concern; Panama Canal coverage; labor unrest. |
| `child_thread` | Specific active narrative inside a parent. | Ebola border preparedness; Panama Canal drought/closure; health-worker strike. |
| `entity_thread` | Entity/place/person lens that can collect multiple child threads. | Panama Canal; WHO; Gaza; Kyiv. |
| `evidence` | Signal that directly supports a thread. | A headline about Ebola deaths rising in DRC. |
| `context_signal` | Signal that mentions the concept but is not primary evidence. | Tennis player mentions missile attack back home. |

This model matches the product direction:

```text
Thread Focus is the strong focus.
Country Focus = which threads live here.
Entity Focus = which threads this entity participates in and with what role.
Signal Focus = evidence.
Workspace = analytical route.
```

## What This Means For The UI

The UI should not expose all these internal words as user-facing jargon.

The user flow should feel natural:

1. User opens a visible Narrative Thread.
2. Atlas shows related threads inside the same cluster.
3. If the opened thread is broad, the right rail/list can reload around child
   threads inside that broad cluster.
4. If the opened item is an entity such as Panama Canal, Atlas shows the active
   narratives involving that entity.
5. Evidence stays underneath, with source, geography, time, sentiment, and
   quality cues.

Example:

```text
Health
  Ebola deaths and border preparedness expand across Central Africa
  Hantavirus concern resurfaces in US public-health coverage
  Measles deaths drive Bangladesh WHO inquiry coverage
  Ebola treatment-center attacks complicate outbreak response
```

Example:

```text
Transport Corridors
  Strait closure risk pressures New Zealand fuel outlook
  Rail disruptions follow attacks in Nigeria
  Panama Canal coverage rises, but no disruption evidence yet
```

The third line can be valid as a parent/entity thread while not being promoted
as a disruption child thread.

## Revised Benchmark Standard

Future benchmark rows should include:

| Field | Purpose |
|---|---|
| `gold_decision` | Overall assignment correctness for the current anchor. |
| `gold_scope` | `domain`, `parent_thread`, `child_thread`, `entity_thread`, `evidence`, `context_signal`, `noise`. |
| `gold_error_type` | Why an assignment failed, if it failed. |
| `gold_primary_thread` | Human label for the thread the row actually supports. |
| `gold_parent_thread` | Parent cluster if applicable. |
| `gold_entity_refs` | Important entities/places if they are the real anchor. |

The existing harness only has `gold_decision`, `gold_topic_slug`, and
`gold_error_type`. That is enough for the first diagnostic, but not enough for
the model we now know Atlas needs.

## Quality Metric Implication

A future Atlas quality indicator should not be a single raw precision number.
It should decompose quality:

| Component | Measures |
|---|---|
| Assignment precision | Is the signal attached to the right anchor? |
| Scope precision | Is the signal at the correct semantic level? |
| Evidence precision | Is the signal primary evidence or just context? |
| Thread coherence | Do child signals describe one coherent movement? |
| Source diversity | Is the thread driven by multiple useful sources? |
| Geo coherence | Does location concentration make sense? |
| Movement integrity | Is acceleration real or syndicated/noisy repetition? |

This avoids the "one score hides everything" problem.

## What Not To Do

Do not continue with blind topic-by-topic patching.

Avoid these reactions:

- Do not delete broad terms just because they fail a specific child assignment.
- Do not treat low precision as proof that the broad concept is invalid.
- Do not train an encoder on labels that mix domain, parent, child, entity, and
  evidence levels.
- Do not expose `atlas_topics` as the user's mental model.
- Do not create a new UI taxonomy with visible technical labels.

## Immediate Next Work

### Phase 1: Model audit upgrade

Extend the benchmark schema and scorer to capture `gold_scope`,
`gold_primary_thread`, `gold_parent_thread`, and `gold_entity_refs`.

Goal: measure model failure modes, not just topic precision.

### Phase 2: Read-only thread hierarchy prototype

Build a read-only backend prototype above existing data:

- keep `atlas_topics` as anchors;
- infer candidate parent clusters from `parent_domain`, co-occurrence,
  entities, geography, and shared movement;
- infer child threads from tighter evidence clusters;
- expose hierarchy as additive fields in `/api/v2/threads`;
- do not add write tables until the contract is validated.

Goal: let Narrative Threads reload around a selected parent/thread without
breaking current UI.

### Phase 3: Evidence role model

Classify evidence rows as:

- primary evidence;
- context signal;
- repeated/syndicated evidence;
- entity-only mention;
- low-context candidate.

Goal: stop treating every matched headline as equal evidence.

### Phase 4: Promotion gates

Only after the above should Atlas consider:

- encoder training;
- ranking changes;
- persistent living-thread tables;
- UI changes beyond additive thread hierarchy.

## Decision

The next sprint should not be a migration that repairs individual topic terms.

The next sprint should be a model-level correction:

> Separate internal anchors from living narrative structure, then evaluate
> classification by semantic role and evidence level.

This is the root cause path out of repetitive patching.

The quality model should be answerability-first: Atlas should measure whether
each thread can answer the seven Atlas questions with relevant evidence,
correct semantic scope, enough coverage, and clear uncertainty.
