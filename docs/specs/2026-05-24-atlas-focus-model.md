# Atlas Focus Model

**Status:** canonical product model for focus surfaces.
**Date:** 2026-05-24.
**Scope:** product/data design for thread, country, entity, signal, and workspace focus.

## Decision

Atlas should treat every selected object as a **focus**, but not every focus
should carry the same analytical weight.

The strongest analytical unit is the **Narrative Thread**. Countries, people,
organizations, places, climate phenomena, and individual signals should become
lenses into threads, not isolated mini-dashboards that repeat the same generic
counts.

Current product correction:

- `NarrativeThreads` is the strongest surface today and should remain the main
  explanatory layer.
- `Country Focus` should answer how active global threads manifest in that
  country, plus which local-only threads are emerging there.
- `Person Focus` should evolve into `Entity Focus`. A person is one entity
  type, but Atlas also needs organizations, places, events, climate phenomena,
  diseases, and ambiguous names.
- `Signal Focus` should stay the atomic evidence view.
- `Workspace` and `Reading Mode` should be the analyst route through selected
  focus evidence.

## Focus Hierarchy

| Focus | Product job | Primary question |
|---|---|---|
| `thread` | Explain the phenomenon. | Why is this moving now? |
| `country` | Localize threads. | Which threads are active here? |
| `entity` | Explain participation. | Which threads does this entity participate in, and with what role? |
| `signal` | Show evidence. | What specific evidence supports this? |
| `workspace` | Preserve reasoning. | What did the analyst collect and conclude? |

Legacy `theme` focus remains as a compatibility bridge while thread focus is
introduced. It should not be the final mental model.

## Entity Focus

The current person experience is too raw because it behaves like a mention
counter. Entity Focus should become thread-aware and typed.

An entity focus should expose:

| Field | Meaning |
|---|---|
| `entity_id` | Stable normalized identity when available. |
| `label` | Display label. |
| `entity_type` | `person`, `organization`, `place`, `event`, `climate`, `disease`, `product`, `other`, or `ambiguous`. |
| `confidence` | Confidence that mentions refer to the same entity. |
| `active_threads` | Threads where the entity appears in the selected window. |
| `roles_by_thread` | Actor/source/victim/location/object-of-action style role hints. |
| `changed_10h` | Movement in recent mentions or thread participation. |
| `top_countries` | Event geography, not only publisher geography. |
| `top_sources` | Source lanes driving the entity's visibility. |
| `evidence_samples` | Deduped signals supporting the entity-thread relation. |
| `quality_flags` | Ambiguous name, untyped entity, source aggregation, weak evidence, etc. |

`El Niño` and `Pacific Ocean` are valid examples of why this matters. They can
be meaningful entities in climate or environmental threads, but they must not
be presented as people.

## Country Focus

Country Focus should not be a generic country summary. It should answer:

1. Which global threads are active in this country?
2. Which threads are unusually concentrated here?
3. Which local-only threads are emerging?
4. Which sources and voice lanes drive the country view?
5. What evidence supports each country-thread relation?

This keeps the country surface close to the product's strongest analytical
unit: threads.

## Thread Focus

Thread Focus is the canonical explanation view. It should include:

- why now;
- 10h movement;
- geography concentration;
- subthreads;
- source mix;
- evidence samples;
- related threads;
- participating entities;
- confidence and quality flags.

The current `ThemeDetail` can become a transitional shell, but the final target
is Thread Focus.

## UI Rule

Do not create separate mental models for each focus. The user should feel one
interaction pattern:

> I clicked something, Atlas shows the threads that make it meaningful.

For example:

- click a country -> active threads in that country;
- click a person/entity -> threads involving that entity;
- click a thread -> evidence, subthreads, entities, related threads;
- click a signal -> why this signal supports the current focus.

## Data Rule

Every focus response should carry provenance and quality:

- method / source table;
- confidence;
- evidence count;
- source diversity;
- geography quality;
- entity typing quality;
- degraded segments.

This prevents focus panels from looking equally authoritative when the data
quality differs.

## Near-Term Implication

Do not deepen Person Focus by adding more generic person facts. First, build
the thread association layer:

1. typed entities or at least typed/ambiguous entity buckets;
2. entity-to-thread participation query;
3. country-to-thread query;
4. focus summary adapter that can render `active_threads`;
5. UI copy that treats all focus panels as thread lenses.

