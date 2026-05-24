# Living Narrative Threads

**Status:** canonical product direction for the next Atlas intelligence layer.
**Date:** 2026-05-24.
**Scope:** product/data design; no backend schema is required by this document.

## Decision

Atlas should not expose a fixed topic table as the user's mental model. The
product should expose **living Narrative Threads**: evidence-backed clusters
that can grow, split, merge, fade, and connect to related threads as signals
arrive.

`atlas_topics` remains important, but its role is internal:

- anchor vocabulary for stable measurement;
- precision gates for automated classification;
- historical aggregate compatibility;
- benchmark labels for later encoder or LLM-assisted classifiers;
- a reference "Bible" for Atlas, not a product taxonomy users must learn.

The visible product language should be natural:

- good: `Fuel price protests intensify in Nigeria and Peru`;
- internal anchor: `fuel-subsidy-unrest`;
- bad as primary UI: asking users to reason from `fuel-subsidy-unrest`.

## Atlas Questions

Every thread-capable surface should help answer at least one of these seven
questions:

1. Why is this moving now?
2. What changed in the last 10h?
3. Where is it concentrated?
4. Which subthreads are forming?
5. Which sources are driving it?
6. What evidence supports it?
7. What related thread does it connect to?

These are the product feel of Atlas. They are more important than whether a
row came from a fixed topic label, a co-occurrence pair, a cluster, or a future
encoder score.

## Thread Contract

A living thread should eventually have this product contract:

| Field | Meaning |
|---|---|
| `thread_id` | Stable identifier for the current thread run/version. |
| `label` | Natural-language label generated from current evidence. |
| `summary` | Short explanation of why the thread matters now. |
| `anchor_topics` | Internal `atlas_topics` slugs that support the thread. |
| `subthreads` | More specific clusters inside the thread. |
| `velocity_10h` | Movement vs prior comparable window. |
| `sentiment_swing_10h` | Atlas sentiment change, not a competing GDELT Tone value. |
| `geo_concentration` | Countries/regions where the thread is concentrated. |
| `source_mix` | Voice lanes driving the thread. |
| `evidence_samples` | Representative signals, sources, and timestamps. |
| `related_threads` | Adjacent threads linked by co-occurrence, entities, or geography. |
| `confidence` | Confidence that the thread is coherent and evidence-supported. |
| `why_now` | Plain-language reason for current movement. |

The first implementation can compute most of this from existing tables:

- `signal_topic_assignments`;
- `atlas_topics`;
- `signals_v2`;
- `theme_country_hourly_v2`;
- `country_hourly_v2`;
- `historical_topic_country_daily`;
- `historical_source_daily`;
- briefing `related_topics` and `topics_by_domain`.

## Lifecycle

Threads should be living, but not chaotic. Atlas needs explicit lifecycle
states:

| State | Meaning | UI treatment |
|---|---|---|
| `emerging` | Low history, rising quickly, thin evidence. | Show as watchable, with confidence. |
| `active` | Enough volume/evidence to lead a panel. | Normal thread card/detail. |
| `splitting` | Subclusters are becoming distinct. | Show child subthreads. |
| `merged` | Two clusters are better explained together. | Preserve aliases/related links. |
| `fading` | Volume and velocity are declining. | Keep accessible but de-emphasized. |
| `archived` | No longer active in the hot window. | Available through historical views. |

Splits and merges should be evidence-driven. A topic label alone is not enough.
Candidate triggers:

- high volume with two or more country/entity clusters;
- sentiment or velocity diverges by geography;
- source mix differs meaningfully between subclusters;
- co-occurrence graph forms separate dense components;
- analyst benchmark or SQL review confirms mixed semantics.

## Confidence Model

Thread confidence is a product confidence, not just classifier confidence. It
should combine:

- topic assignment confidence;
- evidence count;
- source diversity;
- geographic coherence;
- entity coherence;
- recency/velocity stability;
- NLP/sentiment coverage;
- social/public-attention provenance limits.

Suggested first-pass bands:

| Band | Use |
|---|---|
| `high` | Can lead Brief and Narrative Threads. |
| `medium` | Can appear with coverage/provenance cues. |
| `thin` | Watchable, but not a headline insight. |
| `degraded` | Provider, coverage, or method limitation affects interpretation. |

## Panel Responsibilities

| Surface | Primary thread question |
|---|---|
| Brief | Why this is moving now; what changed in the last 10h. |
| Globe / Heat | Where it is concentrated. |
| Narrative Threads | Which subthreads are forming; related connections. |
| Signal Stream | What evidence supports it. |
| Country Focus | How global threads manifest locally. |
| Theme/Thread Focus | Why this thread exists and how it is changing. |
| Person/Entity Focus | Which thread a person/entity participates in. |
| Workspace / Reading Mode | Evidence route and analyst dossier. |

## Near-Term Technical Direction

Do not replace the current atlas-topic classifier immediately. Build a thread
layer above it.

Recommended first technical increment:

1. Add a read-only backend thread assembler around existing hot-window data.
2. Expose `/api/v2/threads` and `/api/v2/threads/{thread_id}` as beta endpoints.
3. Generate thread labels from deterministic evidence first:
   `{anchor label} + {top geography/entity/change}`.
4. Reuse existing `NarrativeThreads` UI but feed it thread-shaped data.
5. Keep the old theme-based path as fallback until smoke-tested.

## Guardrails

- GDELT themes are hints, not proof.
- `atlas_topics` are anchors, not the visible taxonomy.
- Atlas sentiment is the single product sentiment.
- Social/public attention can support early detection, but it is not the same
  as independent reporting.
- A high-volume cluster is not automatically meaningful; it needs evidence,
  source mix, and a coherent explanation.
- Do not add a user-facing "this topic is wrong" correction UI yet. Use
  controlled review sets, SQL sample checks, and benchmark labels first.

## Taxonomy Implications From Path A

Path A validated multilingual lex expansion, but also proved that fixed labels
are insufficient:

- `armed-conflict-escalation` improved precision but should not absorb local
  armed incidents just to clear a recall gate.
- `mining-royalty-risk` currently captures a coal-mine-disaster/resource-risk
  cluster, so the label should split or broaden.
- `food-price-stress` and `housing-cost-pressure` need more evidence before
  aggressive recall expansion.

These are good signs. Atlas should learn which clusters the world is actually
producing, then map them back to internal anchors where useful.
