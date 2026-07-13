# Atlas Investigation Graph and L2/L3 Product Contract

**Date:** 2026-07-12  
**Status:** approved in product-design review  
**Canonical branch:** `v3-intel-layer`  
**Roadmap objective:** a Workbench dossier that an editor would publish with minor edits

## 1. Decision

Atlas will use a typed **Investigation Graph** as the shared truth between L2
exploration, L3 Workbench composition, time travel, and dossier generation.

The product is not `search -> generated dossier`. Search is one entry into L2.
An investigation grows because the user explores Atlas and pins useful objects
from any surface. The Workbench connects those pins, keeps their receipts and
history, and exposes the resulting graph as an editorial workspace. The dossier
is a publication view of that graph.

The design has four independent value contracts:

- **L0 — expectation:** communicate what Atlas can reveal and why its information-
  sphere model is different.
- **L1 — context:** a standalone 24-hour world newspaper: what happened, what is
  moving, and what coverage is missing.
- **L2 — exploration:** a standalone instrument for understanding one story,
  subject, country, event, actor, source, anomaly, or attention signal.
- **L3 — editing:** a multi-focus workspace for composing a thesis, checking
  relations, corroborating claims, and publishing a dossier.

Moving up a level increases agency. A higher level must not be required to make
the level below it useful.

## 2. Why this change is necessary

Atlas already contains most of the required pieces, but they do not share one
relationship model.

Verified against production and current code on 2026-07-12:

- A thread detail can expose evidence, countries, sources, key subjects,
  movement, Deep History, and a related-thread list.
- The Iran forcing case showed `76 conflict events in Iran this window`, but the
  UI explicitly labels them `related by country, not by story` and does not show
  which events explain the relation.
- Related threads can be labeled `Related ... via Iran <-> Iran`, which is a
  geographic co-occurrence, not an explanatory story relation.
- Deep History returns approximate archive story-unit matches and receipts, but
  does not reconstruct how the selected story's actors, countries, sources,
  events, and relations changed through time.
- Globe, Universe, thread history, and the header time lens currently have
  distinct temporal behavior. The header explicitly says looking back does not
  re-filter the present.
- Workbench accepts several pin types, freezes evidence snapshots, and renders
  an incremental constellation, but its relationship endpoint only accepts
  thread/topic IDs. Signals, people, countries, sources, events, anomalies, and
  public attention remain flat dossier material instead of graph participants.
- Conflict events, natural hazards, and anomaly alerts do not all have a common
  first-class Workbench pin contract.

An operational defect was also reproduced during the review:

- `/api/v2/threads` computes dynamic story rows, then always executes the legacy
  atlas-topic aggregate query even when stories-only mode immediately discards
  those rows. Under production pressure that unnecessary 8-second query times
  out and blanks both the thread feed and the research-plan thread lane.
- The semantic research lane is wrapped as one failure domain. A timeout in its
  signal-headline ANN query can discard otherwise valid centroid/taxonomy
  results instead of degrading only that sub-lane.

These availability fixes are enabling work, not the product architecture itself.

## 3. Product principles

1. **The user composes; Atlas structures.** Atlas may suggest neighboring nodes,
   but it never silently adds them to the investigation.
2. **Pins select the editorial material.** Relationships between pinned nodes
   are measured automatically and remain inspectable.
3. **Frozen observation plus live reference.** A pin preserves what the user saw
   and also retains a stable reference that can be re-measured later.
4. **Math/data first.** Embeddings, whitening, entity overlap, temporal
   co-movement, graph statistics, and deterministic rules are allowed throughout.
   An LLM does not classify nodes, create relations, or decide whether two things
   are connected.
5. **LLM only for glass-box prose.** The dossier LLM receives the graph,
   frozen receipts, measured relations, corroboration, and gaps. It may connect
   and phrase those inputs, but cannot introduce facts or citations.
6. **No silent omission.** Operational batching is allowed; semantic top-N
   ceilings are not. Completion receipts, downranking ledgers, and unresolved
   trays disclose what was processed, suggested, omitted, or degraded.
7. **Coincidence is not causality.** Geographic overlap, temporal overlap,
   semantic similarity, and attention co-movement remain distinct relation types.
8. **Actors are broad subjects.** A subject can be a person, organization,
   place, event, phenomenon, object, or system.
9. **External analyst validation is an exit gate, not a development blocker.**
   The internal editorial loop continues until the artifact is coherent; an
   external narrative analyst is recruited after the product reaches that bar.

## 4. L2: standalone narrative explorer

L2 answers a complete single-focus job without requiring an investigation.

### 4.1 Focus Lens

All focus-dependent L2 surfaces consume one shared lens:

```text
FocusLens
  focus_ref       story | thread | signal | subject | country | event | source
  range_start     inclusive observation start
  range_end       inclusive observation end
  cursor_at       optional replay instant
  scope           global plus optional country/language/source filters
  mode            live | historical
```

With no focus, L2 remains the global live radar. With a focus, moving the time
control updates the focus-dependent data together:

- evidence and timeline;
- subject and coverage geography;
- countries and languages of voice;
- actors and entities;
- sources and source families;
- conflict/disaster events;
- anomalies and public attention;
- neighboring stories and relation edges;
- Globe and Universe highlighting.

This does not require every global panel to become a historical snapshot. It
requires every panel making a claim about the selected focus to use the same
time range and to label unavailable history honestly.

### 4.2 L2 relationship receipts

Counts without inspectable members are insufficient. A relationship summary
must open a receipt list.

For example, a thread's event context returns:

- exact `topic_members(role='movement', member_kind='event')` bindings first;
- geo-temporal candidates in a separate contextual tier;
- event type, time, place, severity/action, source URL, freshness, and binding
  method;
- the matched story evidence or rule that created the edge;
- an explicit statement when the only relation is `same_country`.

Related-thread rows must expose their edge basis instead of labels such as
`Iran <-> Iran`. At minimum the row distinguishes shared subject, explicit text
mention, event membership, temporal co-movement, semantic proximity, and
coverage-only context.

### 4.3 Deep History

Deep History remains approximate when archive story units are matched
semantically. It must not imply identity continuity without evidence.

The next contract uses a story anchor rather than only a display label:

- query/label;
- stable thread/story reference when available;
- top actors/entities;
- representative frozen evidence;
- subject geography;
- active observation window.

Historical results expose match basis, similarity, receipts, and ambiguity.
Time travel reconstructs the observed graph dimensions available for that
period; missing dimensions remain missing.

## 5. The Investigation Graph

### 5.1 Node contract

Every pin normalizes into one common node shape:

```text
InvestigationNode
  node_id             stable investigation-local ID
  node_type           story | evidence | subject | country | source |
                      event | anomaly | attention | asset | temporal_slice
  subtype             thread, signal, person, org, place, conflict_event, ...
  label
  live_ref            Atlas route/table identity used for re-measurement
  pinned_at
  observation_window  range visible when pinned
  snapshot            immutable summary, metrics, evidence, URLs, provenance
  analyst_note
  quality             confidence/tier/reason codes available at capture
  resolution_status   resolved | partial | metadata_only | unavailable
```

Initial adapters cover:

- Narrative Thread / story / umbrella;
- signal or article;
- person or any typed subject/entity;
- country;
- source;
- conflict event;
- natural hazard;
- anomaly/baseline spike;
- public-attention item;
- aircraft/vessel observation or strategic chokepoint;
- explicit historical slice.

Unsupported or failed enrichment never prevents a pin. It produces a
`metadata_only` or `partial` node with a retryable resolution receipt.

### 5.2 Edge contract

```text
InvestigationEdge
  edge_id
  source_node_id
  target_node_id
  relation_type
  truth_tier           measured | inferred | contextual | analyst
  direction            directed | undirected
  strength             normalized score when meaningful
  method               exact membership, NER mention, whitened cosine, ...
  valid_from / valid_to
  receipts             signal/event/source references supporting the edge
  reason_codes
  caveats
  measured_at
```

Relation families include:

- **Measured:** `member_of`, `mentions`, `published_by`, `occurred_in`,
  `reported_by`, `movement_context`, `same_verified_subject`, `observed_at`.
- **Inferred:** `semantic_near`, `co_moves`, `precedes_in_atlas`,
  `shared_frame_candidate`.
- **Contextual:** `same_country`, `overlaps_in_time`, `attention_near`,
  `geo_temporal_event_candidate`, `near_chokepoint`, `movement_near_event`.
- **Analyst:** `supports`, `contradicts`, `include_as_angle`, `exclude_as_noise`.

LLM output is never an edge type.

### 5.3 Editorial use of edge tiers

- `measured` and explicit `analyst` edges may form the dossier's narrative spine.
- `inferred` edges may be described with method and uncertainty.
- `contextual` edges are exploration prompts or caveated context, not proof of a
  connected story.
- Causal language is prohibited unless an analyst supplies a sourced assertion.

## 6. Pin lifecycle and data flow

1. The user explores any L2 surface.
2. `PIN` creates an investigation if none exists or adds to the active one.
3. The client writes an immediate minimal frozen node so pinning never waits on
   the network.
4. A node adapter asynchronously captures the visible snapshot and live reference.
5. The graph service resolves new pairwise and higher-order relations against
   all existing pins.
6. The Workbench updates the graph and exposes any unresolved or degraded work.
7. Suggested neighbors remain outside the graph until the user pins them.

Existing investigations remain local-first for this build:

- browser storage holds the active editable investigation;
- JSON export provides durable, reproducible transfer;
- the graph backend is stateless over supplied node references and snapshots;
- accounts/server-side investigation persistence are a separate product decision.

The storage format becomes `atlas-investigation-v2` and includes a lossless
migration from existing `atlas.workbench.v1` pins.

## 7. L3: standalone editorial Workbench

The Workbench remains a three-region surface, with corrected responsibilities:

- **Left — investigations:** separate named investigations, history, import,
  export, duplication, and active selection.
- **Center — investigation field:** typed graph, touched-country map, shared
  timeline, pinned route, and relation filters. This is the primary workspace.
- **Right — inspector:** selected node/edge receipts, relation reason, caveats,
  frozen-vs-live comparison, and suggested adjacent material.

The research plan can appear as one suggestion source, but it no longer owns
the right panel or defines the investigation. Suggestions derive from the graph
and current inspector selection as well as from an optional query.

### 7.1 Time in L3

Two truths coexist:

- **As pinned:** the immutable observation and evidence captured by the analyst.
- **Time Lens:** the re-measured state of the graph for a selected date/range.

Moving time never deletes or rewrites pins. Nodes with no observed activity in
the selected interval remain present but visually recede. Edges recompute for
the interval and retain their measurement timestamp. Sequence language is
`first seen by Atlas`, not `originated`, until ingest-lag validation proves more.

## 8. Dossier and publication package

The dossier can be generated at any point. There is no artificial minimum pin
count. A deterministic readiness ledger tells the analyst what the graph can
answer:

- who;
- what;
- when;
- where;
- how it is covered/framed;
- why it may be moving, explicitly separated into measured precursors and
  analyst/LLM inference.

The publication package contains:

1. **Article:** headline, dated lede, connected body, and inline receipts.
2. **Visuals:** exportable map, graph, and timeline with date/method legends.
3. **Who-says-what:** source, language, origin, actor, press/public, and frame.
4. **Corroboration:** established/contested/unverified claims with independence
   weighting.
5. **Gaps:** unknowns, silent/absent voices, weak links, and missing time ranges.
6. **Receipts:** numbered sources, URLs, dates, tiers, and frozen evidence.
7. **Method:** relation methods, thresholds, reason codes, and timestamps.
8. **Reproducibility:** `atlas-investigation-v2` JSON graph and snapshots.

The LLM receives only this structured package. Server-side citation resolution
continues to reject invented references.

## 9. Service architecture

### 9.1 Focus and graph services

The first stable backend interfaces are:

```text
POST /api/v2/investigation/resolve-node
POST /api/v2/investigation/graph
POST /api/v2/investigation/time-slice
```

`resolve-node` normalizes one L2 object into an `InvestigationNode` snapshot.

`graph` accepts the full typed node ledger and requested time lens, then returns:

- resolved nodes;
- typed edges;
- suggestions outside the investigation;
- receipts and caveats;
- unresolved ledger;
- completion metadata.

`time-slice` returns the observable node/edge state for another range without
mutating the investigation.

Implementation boundaries:

- node adapters per object type;
- relation engines per relation family;
- receipt resolver;
- graph assembler;
- completion/downranking ledger;
- dossier serializer.

These units remain independent and testable. The graph assembler does not know
how a specific relation is calculated.

### 9.2 Performance and completeness

- Graph work scales from pinned nodes and explicit suggestion expansion, not a
  scan of every product row on each interaction.
- Database work is operationally batched and cached, with a heavy-job/serving
  budget. Batch size is not a semantic ceiling.
- Every response states whether requested nodes, pairs, time ranges, and
  relation engines completed.
- Suggestions may be ranked, but the omission/downranking ledger remains
  inspectable.
- Expensive enrichment is asynchronous; the frozen node and existing graph stay
  usable while it runs.

## 10. Degradation and error handling

- A failing lane degrades independently and names the unknown coverage.
- A failed pin snapshot leaves a metadata-only node and retry action.
- An unresolved edge remains a gap; semantic similarity does not substitute for
  a missing exact relation.
- Historical absence is labeled `not observed by Atlas`, not `did not happen`.
- LLM failure preserves the graph, readiness ledger, visuals, receipts, and
  deterministic dossier outline; only generated prose is unavailable.
- Database saturation returns cached data or honest `503 db_busy` with retry,
  never a false empty result.
- Frozen snapshots remain authoritative for what the user saw, even when live
  enrichment later changes.

## 11. Validation loop

### 11.1 Automated invariants

- every supported L2 object normalizes to a valid typed node;
- pin snapshots are immutable under time travel and live remeasurement;
- every edge has a truth tier, method, reason code, and receipt or an explicit
  missing-receipt caveat;
- contextual/semantic relations cannot be promoted to measured or causal;
- node and edge completion metadata reconciles with the request;
- investigation migrations preserve existing pins and notes;
- LLM output cannot add graph IDs or citation numbers absent from its input;
- one failing relation engine does not blank other edges or the Workbench;
- no result is silently truncated by an arbitrary semantic cap.

### 11.2 Product forcing cases

**Iran L2/L3 case**

- Start from `Israel Plot to Kill Iran Negotiators`.
- Inspect the actual 76 Iran conflict events and distinguish exact movement
  bindings from country-only context.
- Compare and pin `Trump Ends Iran Accord` and `Condemnation of Damascus Bombing`.
- Pin at least one actor, signal, country/source, and event or anomaly.
- Move time backward and verify that countries, voices, actors, events, and
  relations update together while frozen pins remain intact.
- Open Workbench and understand why each pair is or is not connected.

**NATO-Ankara publication case**

- Rebuild the investigation through L2 interactions, not a pre-baked search-to-
  dossier shortcut.
- Pin stories, actors, evidence, countries/sources, and relevant temporal/event
  context.
- Corroborate load-bearing claims.
- Export the publication package.
- Run a cold-editor review using only the exported artifact.

### 11.3 Gates

1. **L1 gate:** a reader contextualizes the day without L2.
2. **L2 standalone gate:** the Iran focus can be understood without creating a
   Workbench investigation.
3. **L3 composition gate:** the Iran multi-pin graph explains relationships and
   their evidence over time.
4. **Dossier gate:** a cold editor says publishable with minor edits; every
   factual claim resolves to a receipt.
5. **External analyst gate:** after the internal gates, a narrative analyst who
   is not Pedro uses the workflow and identifies value/errors.

## 12. Delivery slices

This architecture is too broad for one undifferentiated code pass. It will ship
as vertical, independently verified slices:

1. **Reliability precondition:** remove the discarded atlas query from stories-
   only `/threads`; isolate research semantic sub-lane failures; restore the Iran
   and NATO entry flows.
2. **Typed graph foundation:** `atlas-investigation-v2`, node adapters, edge
   contract, stateless graph endpoint, migration from current pins.
3. **L2 standalone depth:** shared Focus Lens, inspectable event/thread receipts,
   related-thread reasons, and honest Deep History anchoring.
4. **L3 composer:** graph-centered Workbench, inspector, suggestions, time lens,
   and heterogeneous pin connections.
5. **Dossier v4:** readiness ledger, graph-derived narrative package, visuals,
   method/receipt appendix, and export.
6. **Editorial loop:** Iran and NATO forcing cases, automated grading, repeated
   cold-editor review, then external analyst validation.

Each slice gets a focused implementation plan and must pass its own product gate
before the next slice becomes the priority.

## 13. Non-goals

- Search does not automatically create a finished investigation or dossier.
- L2 does not require an active investigation.
- The graph does not assert real-world causality from media co-occurrence.
- Propagation does not claim true origin until ingest-lag validation exists.
- LLMs do not classify, connect, rank graph truth, or generate gold labels in
  the production path.
- Accounts and server-side collaborative investigation persistence are not part
  of this delivery sequence.
- C7 voice-asymmetry remains read-only until subject geography Stage 2 is
  sufficiently calibrated.
- L4 Markets remains outside this roadmap.

## 14. Approved product statement

> L1 tells the reader what the world looks like today. L2 lets the reader dive
> into one story and understand how the information sphere speaks about it. L3
> lets the analyst combine those observations into a connected, sourced, and
> publishable investigation. Atlas measures and exposes the relations; the user
> chooses the story; the dossier communicates it with receipts.
