# Atlas Narrative Intelligence Framework

Date: 2026-05-25  
Status: active product/model canon  
Related: #203, #204, #207  

## Decision

Atlas is both:

1. a narrative intelligence model; and
2. a visualizer for inspecting that model.

The model turns high-volume global media signals into evidence-backed
Narrative Threads. The visualizer exposes those threads through the globe,
thread list, focus panels, stream, source integrity, and workspace.

This is the core product definition:

> Atlas is a live narrative intelligence model and visualizer that turns global
> media signals into answerable, evidence-backed Narrative Threads.

Atlas is not a fixed topic dashboard. `atlas_topics` remains an internal anchor
vocabulary for measurement, benchmarks, backfills, and precision gates. The
visible object is the living Narrative Thread.

## External Model Lessons

The field review in
`docs/research/topic-quality/2026-05-25-narrative-intelligence-field-review.md`
found useful adjacent models:

- event-centric narrative graphs and extraction surveys
  ([Narrative extraction survey](https://link.springer.com/article/10.1007/s10462-022-10338-7),
  [event-based news narrative extraction](https://arxiv.org/abs/2302.08351));
- narrative maps
  ([Narrative Maps](https://arxiv.org/abs/2009.04508),
  [narrative maps and framing](https://arxiv.org/abs/2405.02677));
- dynamic topic modeling
  ([Dynamic Topic Models](https://www.cs.columbia.edu/~blei/papers/BleiLafferty2006a.pdf),
  [BERTopic topics over time](https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html));
- topic detection and tracking
  ([TDT topic overview](https://www.nist.gov/itl/iad/mig/topic-detection-and-tracking-tdt));
- media framing analysis
  ([media framing survey](https://aclanthology.org/2024.acl-long.822/));
- media attention platforms such as Media Cloud
  ([MIT overview](https://www.media.mit.edu/projects/media-cloud/overview/),
  [ICWSM platform paper](https://ojs.aaai.org/index.php/ICWSM/article/view/18127));
- interactive narrative analytics
  ([Interactive Narrative Analytics](https://arxiv.org/abs/2601.11459));
- narrative visualization systems such as StoryAtlas
  ([StoryAtlas](https://chi.anp.casl.cal.msu.edu/2024/05/02/explore-storyatlas/)).

The common lesson is that narratives are not flat labels. They are graph-like,
temporal, source-dependent, evidence-backed structures.

Atlas should borrow these ideas without becoming any one of them:

- from event graphs: events, entities, places, time, and relations;
- from narrative maps: parent/child routes through complex stories;
- from dynamic topic models: drift, emergence, split, and merge detection;
- from topic tracking: lifecycle states;
- from framing analysis: source interpretation and contrast;
- from attention platforms: volume, source spread, and coverage peaks;
- from visual analytics: inspectability and human sensemaking.

## Core Objects

The Atlas model should separate these objects instead of forcing them into a
single topic assignment:

| Object | Meaning | User-facing? |
|---|---|---|
| `signal` | Raw or enriched media row. | Only as evidence. |
| `evidence_item` | Signal selected because it supports a thread answer. | Yes, in Signal Focus/Stream. |
| `domain_anchor` | Stable internal measurement area, often backed by `atlas_topics`. | Usually no. |
| `parent_thread` | Broad live narrative region, e.g. climate-health, mining safety, migration pressure. | Yes. |
| `child_thread` | Specific current storyline under a parent, e.g. coal mine explosion coverage in Shanxi. | Yes. |
| `entity_thread` | Entity-centered participation lens, e.g. a person, company, government, or organization across threads. | Yes, as Entity Focus. |
| `geo_lens` | Country/region concentration and movement lens. | Yes, as Country Focus/Globe. |
| `source_lane` | Source mix, concentration, source family, and provenance lane. | Yes, as Source Integrity/Voice Mix. |
| `relation` | Typed edge connecting threads/entities/geographies/evidence. | Yes, through related threads and workspace. |
| `quality_envelope` | Confidence, coverage, evidence strength, and uncertainty. | Yes, eventually as product quality. |

## Thread Relations

Atlas should model relationships explicitly. Minimum relation types:

| Relation | Example use |
|---|---|
| `contains` | Parent thread contains child thread. |
| `evolves_into` | A thread changes frame or center of gravity. |
| `splits_into` | One broad movement becomes several child threads. |
| `merges_with` | Separate threads converge into one coverage cluster. |
| `shares_entity_with` | Threads involve the same entity. |
| `shares_geography_with` | Threads concentrate in the same countries/regions. |
| `source_overlap_with` | Threads are driven by the same source lane. |
| `frame_contrast_with` | Same event, different interpretive frame. |
| `supports` | Evidence item supports a thread answer. |
| `context_for` | A signal is context, not direct evidence. |

These relations should eventually power related threads, drill-down, graph
workspace, and evidence routes.

## Movement Drivers

Atlas should explain why a thread is moving. Candidate drivers:

| Driver | Meaning |
|---|---|
| `volume_delta` | Coverage increased relative to baseline. |
| `source_shift` | New source families or regions entered the thread. |
| `geo_shift` | Geographic concentration moved. |
| `entity_spike` | An entity suddenly became central. |
| `sentiment_swing` | Atlas sentiment changed meaningfully. |
| `public_attention` | Search/Wikipedia/social attention moved. |
| `evidence_novelty` | New evidence differs from prior thread evidence. |
| `syndication_burst` | Volume is high but driven by repeated wire/syndicated coverage. |
| `frame_shift` | Language/source framing changed. |

Movement is not the same as raw volume. A small thread can be important if the
driver is sharp, evidence-backed, and coherent.

## Seven-Question Harness

Every thread-capable object should be evaluated against the seven Atlas
questions:

1. Why is this moving now?
2. What changed in the last 10h?
3. Where is it concentrated?
4. Which subthreads are forming?
5. Which sources are driving it?
6. What evidence supports it?
7. What related thread does it connect to?

The harness should measure answerability, not only classifier precision.

| Question | Required evidence |
|---|---|
| Why moving now? | Movement driver plus comparison baseline. |
| What changed? | Timeline or before/after feature delta. |
| Where concentrated? | Country/region distribution and coherence. |
| Which subthreads? | Child clusters with distinct evidence. |
| Which sources? | Source diversity, concentration, and lane. |
| What evidence? | Representative evidence with role labels. |
| Related thread? | Typed relation, not just co-occurrence. |

## Quality Envelope

Atlas quality should be computed at thread level. It should combine:

- assignment precision;
- semantic scope correctness;
- evidence role correctness;
- source breadth and concentration;
- geo coherence;
- movement integrity;
- sentiment coverage/provenance;
- answerability of the seven questions.

Recommended user-facing bands:

| Band | Meaning |
|---|---|
| `high` | Thread answers most questions with coherent evidence and good coverage. |
| `medium` | Thread is useful but missing one or two important answers. |
| `thin` | Thread may be real, but evidence or coverage is narrow. |
| `degraded` | Thread is likely noisy, contradictory, or poorly supported. |

This gives Atlas a path toward a visible product quality indicator without
pretending that raw volume equals truth.

## Benchmark Schema Direction

Path B should evolve from binary topic correctness into semantic/evidence role
labels. This follows the narrative-extraction literature's emphasis on
annotation schemes, narrative elements, relation extraction, and standard
evaluation frameworks rather than raw clustering alone
([Santana et al. 2023](https://link.springer.com/article/10.1007/s10462-022-10338-7)).
Future labeled rows should support fields like:

```json
{
  "gold_relevant": true,
  "gold_scope": "child_thread",
  "gold_evidence_role": "primary_event",
  "gold_parent_thread": "mining-resource-safety",
  "gold_child_thread": "china-coal-mine-explosion",
  "gold_supported_questions": ["why_moving", "where_concentrated", "evidence"],
  "gold_error_type": null
}
```

Allowed `gold_scope` values:

- `domain`;
- `parent_thread`;
- `child_thread`;
- `entity_thread`;
- `geo_context`;
- `source_context`;
- `evidence`;
- `context_signal`;
- `noise`.

Allowed `gold_evidence_role` values:

- `primary_event`;
- `followup`;
- `background`;
- `reaction`;
- `analysis`;
- `public_attention`;
- `source_amplification`;
- `not_evidence`.

This preserves the useful part of broad terms. For example, `Panama Canal` can
be a valid parent/entity thread while still failing as evidence for a specific
transport-disruption child thread unless the signal shows closure, drought,
shipping delay, blockade, or operational impact.

## Product Surface Contract

All focus surfaces should be lenses over Narrative Threads:

| Surface | Contract |
|---|---|
| Narrative Threads | Entry point into moving parent/child threads. |
| Thread Focus | Deep view of one thread: movement, subthreads, source lanes, evidence, relations. |
| Country Focus | Which threads live here and how geography changes their meaning. |
| Entity Focus | Which threads an entity participates in, with role and evidence. |
| Signal Focus | Why a signal matters as evidence, context, or noise. |
| Globe | Spatial manifestation of active threads. |
| Signal Stream | Evidence stream, not a generic raw feed. |
| Source Integrity | Which sources drive, narrow, or distort the thread. |
| Workspace | Analyst route through related threads, evidence, and focus objects. |

This keeps the UI natural. Users do not need to understand "canonical Atlas
topics"; they inspect living threads and the evidence behind them.

## First Implementation Direction

Do not add persistent tables as the next move. First build a read-only layer
above current data and benchmarks:

1. Extend benchmark labels to semantic scope and evidence role.
2. Generate a larger statistically meaningful sample across active threads.
3. Produce a thread graph candidate report from existing assignments, signals,
   entities, countries, sources, timelines, and related-topic co-occurrence.
4. Score each candidate against the seven-question harness.
5. Promote only the parts that clear quality gates into `/api/v2/threads`.
6. Add persistence only after the graph objects and quality envelope prove
   stable in reports and contract smokes.

## Non-Goals

- Do not expose `atlas_topics` as the main user taxonomy.
- Do not train or promote an encoder before benchmark quality clears the gate.
- Do not interpret GDELT theme matches as validated Atlas topics.
- Do not create user-facing topic-correction UI yet.
- Do not use visual polish as a substitute for data/model quality.

## Next Work

The next concrete work block is:

1. update the Path B harness schema for semantic role and evidence role;
2. sample a larger cross-thread set;
3. score answerability support per row/thread;
4. generate the first read-only Narrative Thread Graph report;
5. use that report to decide which API additions belong in `/api/v2/threads`.
