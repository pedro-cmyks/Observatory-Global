# Living Narrative Threads

**Status:** canonical product direction for the next Atlas intelligence layer.
**Date:** 2026-05-24. Updated 2026-05-24 PM with implementation status M1+M2+M3a.
**Scope:** product/data design; no backend schema is required by this document.

## Implementation Status

| Milestone | What | PR | State |
|---|---|---|---|
| M1 | Read-only `/api/v2/threads` + `/api/v2/threads/{id}` beta endpoints | [#209](https://github.com/pedro-cmyks/Observatory-Global/pull/209) | MERGED |
| M2 | Brief consumes `top_threads` via `fetch_threads(conn=conn)` reuse | [#210](https://github.com/pedro-cmyks/Observatory-Global/pull/210) | MERGED |
| M3a | `/api/v2/threads` enriched with `parent_domain`, `avg_confidence`, `first_seen`, raw entity signal, `hourly_timeline`, `trend` + Redis cache | [#211](https://github.com/pedro-cmyks/Observatory-Global/pull/211) | OPEN, NEEDS QUALITY PATCH |
| M3b | Frontend `NarrativeThreads.tsx` swaps from `/api/v2/narratives` to `/api/v2/threads` | — | BLOCKED BY QUALITY GATES |
| M4 | Real ThreadDetail panel + `'thread'` focus type in `FocusContext` | — | LATER |

**Product clarification (2026-05-24 PM):** all Narrative Threads are live by
definition because Atlas keeps ingesting and reprocessing signals. "Living" is
descriptive, not a separate product category or UI surface. The existing
`NarrativeThreads.tsx` is the visible product surface. Backend work enriches
the data feeding it; M3b is a data-source swap only after quality gates pass,
not a new panel.

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

Thread focus, country focus, entity focus, signal focus, and workspace focus
are defined in `docs/specs/2026-05-24-atlas-focus-model.md`. The core rule is:
countries and entities should become lenses into active threads, not isolated
summary panels.

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

## Beta Contract: `/api/v2/threads`

The first technical increment is live in code as a read-only beta contract. It
does not add tables and does not replace existing UI routes.

Collection:

```http
GET /api/v2/threads?hours=24&limit=10
```

Response shape:

```json
{
  "beta": true,
  "hours": 24,
  "contract": "living-narrative-threads-v0",
  "threads": [
    {
      "thread_id": "fuel-subsidy-unrest--ng-pe",
      "label": "Fuel subsidy unrest intensifies in Nigeria and Peru",
      "summary": "Fuel subsidy unrest intensifies in Nigeria and Peru",
      "anchor_topics": ["fuel-subsidy-unrest"],
      "signal_count": 120,
      "source_count": 18,
      "country_count": 3,
      "changed_10h": 47,
      "sentiment_swing_10h": -0.24,
      "top_countries": ["NG", "PE"],
      "top_country_names": ["Nigeria", "Peru"],
      "source_mix": {
        "top_sources": ["reuters.com", "elcomercio.pe"],
        "source_count": 18
      },
      "confidence": "high",
      "why_now": "47 more signals in the last 10h, concentrated in Nigeria and Peru.",
      "subthreads": [],
      "related_threads": [],
      "evidence_samples": []
    }
  ]
}
```

Detail:

```http
GET /api/v2/threads/{thread_id}?hours=24
```

The detail endpoint returns the same thread object with up to eight
representative `evidence_samples`.

Current limitations:

- Thread rows are assembled from atlas-topic anchors, so this is still a bridge,
  not full clustering.
- `subthreads` is reserved and empty until we add entity/geography/source
  component detection.
- `source_mix` starts with top sources and source count; voice lanes come next.
- UI should consume this only after manual inspection of live top-10 output.

## M3a Enriched Fields (PR #211)

The contract was extended additively for `NarrativeThreads.tsx` parity. Existing
M1 clients continue to work; new clients gain the following per-thread fields:

| Field | Type | Meaning |
|---|---|---|
| `parent_domain` | string | Anchor topic's `atlas_topics.parent_domain` (e.g. `conflict-security`). Drives the cluster badge. |
| `avg_confidence` | float (3 dp) | Mean atlas-assignment confidence across the thread's signals. Numeric backing for the existing % pill. |
| `first_seen` | ISO timestamp | Earliest `signals_v2.timestamp` in the assigned window. Drives the `Started Xh ago` pill. |
| `top_entities` | string[] (<=5) | Raw values from `unnest(signals_v2.persons)` grouped by topic. Useful for audit only until entities are typed. |
| `top_people` | string[] | Intentionally empty until typed entity support exists. Prevents raw `persons` values from being treated as validated people. |
| `hourly_timeline` | array of `{hour, count}` | Per-hour signal count for the assignment window. Drives the sparkline. |
| `trend` | `surging` / `stable` / `fading` | Derived in Python from `changed_10h / signal_count` ratio. >= +5% → surging, <= -5% → fading, else stable. |
| `quality` | object | Additive quality metadata: `lex_pct`, `method_mix`, `source_flags`, `geo_flags`, and `entity_flags`. Blocks frontend promotion when evidence is weak or untyped. |

Performance notes:

- `COUNT(*)` replaces `COUNT(DISTINCT signal_id)` in `topic_agg` because the
  `signal_topic_assignments` PK already guarantees uniqueness within each
  (topic, model_version) group.
- The `scoped` CTE (assignments JOIN signals_v2 JOIN atlas_topics over ~25k 24h
  rows) is the floor cost at ~700 ms in production.
- Threads router caches responses in Redis: 5 min on `/threads`, 3 min on
  `/threads/{id}`. Brief calls `fetch_threads(conn=...)` directly and is
  independently cached at 15 min.

Known data quality issues from the quality audit:

- `signals_v2.persons` is not safe to expose as a person chip row without
  typing. `El Niño` and `Pacific Ocean` can be valid climate/geographic
  entities, but they are not persons. `Jesus Christ` may be a named phrase, but
  it is not reliable evidence for a gender-rights thread.
- `countries_v2` has rows where `name == code` for non-FIPS codes (e.g.
  RB="RB", BW="BW"). Labels degrade gracefully via `COALESCE(c.name, s.country_code)`.
- `top_sources` is dominated by aggregator domains like `zazoom.it`. Source
  ranking should weight against aggregator domains.
- `gender-violence-rights` and `transport-corridor-disruption` are not ready
  for UI promotion. See
  `docs/research/2026-05-24-thread-quality-audit.md`.

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

---

## 2026-06-23 — Thread-model evolution (decisions, Pedro review)

Live-corpus review of served threads surfaced the gaps below. These are the
agreed direction; they extend (do not replace) the split/merge/child-subthread
model already specified above — which was spec'd but never implemented.

### Findings (prod, 168h)
- **Noise-gate suppression.** Promotion requires evidence-role `noise_rate <
  0.50`, but the student over-flags coherent high-volume threads: *Trump Warns
  Netanyahu on Iran* (1390 signals, cohesion 0.96, noise 0.79) and *Mundial 2026*
  (813 signals, es, noise 0.58) sat as candidates ~12 days. The 44 served
  threads are small/recent; the biggest ongoing stories are hidden.
- **Fragmentation.** US–Iran appears as ~7 flat threads, Russia–Ukraine as 3.
  No parent/child; the anchor guard (0.93) + fresh per-snapshot DeepSeek labels
  shatter an evolving story.
- **Generic labels = labeling failure, not roundup.** *Iraqi News and Culture*
  (cohesion 0.97) is a coherent cluster with a lazy DeepSeek name; the
  content-roundup classifier correctly does NOT flag it. Fix = re-label, not gate.
- **Reddit dead.** 0 social signals (datacenter-IP block on the public JSON).

### Decisions
1. **Drop noise_rate as a hard promotion gate.** Rely on cohesion + the #224
   content-entropy roundup classifier (no-shared-subject AND single-outlet).
   Noise stays a displayed signal, not a blocker.
2. **No language suppression in promotion.** English is a real lingua franca;
   gate/weight by ORIGIN, not language. Volume-as-quality is wrong for serving;
   the weighted distribution lives in Atlas heat (Paper 3), not the thread gate.
3. **Hierarchical threads.** A big story (Trump–Iran) is one parent with child
   sub-threads, each with its own narrative + movement. Implement the spec's
   `splitting`/`merged` states with evidence-driven parent/child links.
4. **Re-label generic-but-coherent clusters** instead of killing them.
5. **On-demand, any-window thread construction.** Open at 1h → show the last
   hour; zoom a big topic into a 1h window; build the thread for the requested
   window, not only the 6h batch.
6. **Reddit + per-thread directed search.** Revive Reddit ingestion from a
   residential IP (M1), not Fly datacenter. When a thread grows, search what the
   public says about THAT thread specifically (per-country/topic subreddits).

### Architecture note (Pedro) — raw-local vs served-processed
Hot/cold is the wrong axis. Cold archive isn't used for live calc. Proposed:
all raw INGESTION + processing local (M1 + external disk; residential IP dodges
the datacenter blocks that kill Reddit and ~30% of feeds); the served DB
(Supabase/Fly) holds only PROCESSED, query-ready artifacts. Migrate
incrementally, blocked-sources first; GDELT stays on Fly as an always-on
baseline. (This is Paper 6 territory.)

---

## 2026-06-24 — Unified ranking (decision, Pedro review) — supersedes living/aggregate

Live review of the served list: the **living vs aggregate two-tier was a source
label dressed as quality** — `dynamic_topics` always ranked first, `atlas_topics`
filled below by raw volume. Pedro's call: a persistent atlas topic that keeps
**growing is a live thread too**; demoting it by origin is wrong, and
"newest dynamic first" buried the biggest ongoing stories.

### Decision
- **One population, one ranking, no source tier.** `fetch_threads` merges
  `dynamic + atlas` (deduped by label, dynamic kept on collision) and ranks with
  `app/services/thread_ranking.rank_threads`.
- **Score = 0.45·log-volume + 0.35·relative-movement(`changed_10h`) +
  0.20·coherence(`avg_confidence`)**, min-max normalised, source-agnostic.
  Volume is **log-damped** so a 3K-signal category cannot bury a 50-signal story
  by count alone; movement lets a heating thread rise; coherence is the guardrail
  against loose taxonomy bins.
- **Frontend:** the `LIVING`/`AGGREGATE` badge is removed; the trend arrow
  carries movement, the count its weight.

### Cross-reference (Paper 3 / Paper 4)
This operationalises the 2026-06-23 decision #2 — *"volume-as-quality is wrong
for serving; the weighted distribution lives in Atlas heat (Paper 3), not the
thread gate."* The log-damp + coherence weight enact exactly that: volume informs
but does not dominate. Weights are a **calibratable v1** (Paper 4 will need an
ablation: ranking-quality vs the gold orderings, the way
`calibrate_research_ranking.py` did for anchors). Still OPEN from 2026-06-23:
hierarchical parent/child threads (US–Iran as ~7 flat threads), generic-label
re-labeling, on-demand any-window construction.

### #234 focus propagation (Paper 7 — visualization/analyst workflow)
Focus is a global lens: focusing a country/person/thread re-scopes the map heat
to the focus's relations + flies to its dominant country, and (2026-06-24)
NarrativeThreads now surfaces the threads mentioning a focused person. Remaining:
dock (anomaly/sources) + public-attention re-scoping; backend `threads?person=`
filter for precise (non-`top_entities`-capped) person→thread relations.

### Typed membership + relationship types (2026-06-29 — Unified Engine F0, Paper 4)
The split-brain (atlas-lexical ‖ dynamic-embedding ‖ discussion-attach, three
pipelines that never reconcile) is replaced by ONE typed-membership table
`topic_members(role ∈ evidence|discussion|mood|movement, basis, engine_version)`
— construction unifies, serving separates by role (spec
`docs/specs/2026-06-29-atlas-unified-engine.md`). **New Paper-4 contributions:**
- **Typed membership** as the thread substrate: the evidence spine (press, gated)
  is one role; discussion/mood (social, `verified=false`) and movement (events)
  are separate roles never folded into `evidence_count` — the honesty invariant
  becomes a schema property, not a serving convention.
- **The 5 relationship types** (`media-led / public-led / social-led /
  silent-risk / uncoupled-attention`) computed from role-count ratios
  (`classify_relationship`, `app/services/topic_relationship.py`), NOT a new
  pipeline. This is the press-vs-public structure of a thread as a measured
  projection — the analyst can ask "is this story media-driven or
  public-driven?" from the same membership model. (Serving lives at P7; the
  typed-membership method + the silent-risk-as-ratio reframe are P4/P1.)
- **F0.3 measured-cutover discipline:** the unified read path ships behind a
  read-flag with an A/B parity gate (`engine_serving_parity.py`) proving
  byte-exact list parity before the flip — the same calibrate-then-prove method
  this spec used for ranking, now applied to a serving-layer swap. The A/B over
  v1-compat vs unified-v2 (F3) IS Paper 1's split-brain-vs-unified experiment.

## 2026-06-30 — R-track engine work operationalizes decisions 3 + 5 (pointer)
The #229 recall engine work (`docs/specs/2026-06-30-atlas-engine-recall-scoped-
clustering.md`, Paper 8) is the implementation path for the two thread-model
decisions taken 2026-06-23 that were spec'd-not-built:
- **Decision 3 (hierarchical threads)** = **R2**: cluster the scoped-cluster
  *centroids* (embedding-of-embeddings) into parent **umbrella** topics with the
  per-country/regional clusters as children. This is what collapses the
  cross-country duplication R1 introduces (same global story once per country)
  and fixes the "US–Iran ≈ 7 flat threads" fragmentation — the umbrella IS the
  parent, the scoped clusters ARE the children. R2 spec authored after R1.
- **Decision 5 (on-demand any-window)** = the three-speed cadence: **formation**
  (R1 HDBSCAN, nightly, discovers new topics) / **assignment** (nearest-centroid,
  every 30min with ingest, existing topics grow + velocity moves — the
  `build_unified_topics` ≥0.88 path) / **umbrella** (cheap centroid re-cluster,
  hourly / on-read, re-scoped per requested window). Movement numbers = Kalman
  #219 (the "stock ticker"). "Instant/live like a market" = assignment + movement
  + umbrella-on-read; full streaming clustering is NOT required.
- **Evolution-graph reframe (2026-06-30, Pedro):** the thread evolution graph
  should be fed by the engine's own substrate (`signal_embeddings` +
  `topic_members` roles), not signal metadata — see the master plan Paper 7
  addition. A larger thread renders as its umbrella + children entering/leaving
  across time buckets. Build after R2. Desktop-only today (`ThemeDetail:744`);
  needs a mobile-native shape (#236).
R1 (production per-country former) is the foundation all three sit on — it is in
flight 2026-06-30/07-01; R2/graph are built ON its output.
