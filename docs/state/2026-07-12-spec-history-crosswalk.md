# Atlas L1/L2/L3 — spec-history crosswalk

**Date:** 2026-07-12
**Status:** canonical reconciliation for the Investigation Graph program
**Question:** what in the approved L1/L2/L3 design is genuinely new, what is
already built, and what must be reused or superseded to reach a publishable
daily Brief and Workbench dossier without inventing a parallel Atlas?

## Verdict

The approved Investigation Graph spec is the right **product contract**, but
most of its technical primitives already exist. The delivery is therefore a
consolidation and extension program, not a greenfield graph, ranking, dossier,
or narrative-intelligence engine.

The genuinely new work is the composition:

1. normalize every pinnable L2 object into one typed investigation node;
2. adapt the existing thread constellation, membership, event, voice, history,
   and corroboration contracts into typed relation engines;
3. make the constellation visible and inspectable while pins accumulate;
4. wrap the existing dossier receipts and synthesis in one deterministic
   publication package shared by system-authored L1 and analyst-authored L3;
5. make L1 select a finite daily edition from a fully reconciled candidate
   universe using measured dynamics, with no content-category importance gate;
6. make L2 focus and time semantics consistent enough that a single story is a
   complete standalone investigation surface.

Anything that creates a second semantic edge engine, a second who-says-what
implementation, a second corroboration lane, or a second publication writer is
architectural regression.

## 1. Decision lineage

| Date | Decision | What survives now |
|---|---|---|
| 2026-06-09 | Research Workflow + Workbench | Search returns anchors and suggestions; the user opens and pins. Separate investigations do not silently mix. Search does not produce a finished dossier. |
| 2026-06-24/29 | One ranked Narrative Thread population + unified engine | `dynamic_topics` is the story spine; `topic_members` is the typed substrate (`evidence`, `discussion`, `mood`, `movement`, `attention`). Serving projections must reuse it. |
| 2026-07-01 | R3 spine + orthogonal lenses + deferred relations | Category, crisis, geography, source, and quality are lenses on stories, not peer product objects. Preserve existing serving contracts; do not rebuild shipped components. |
| 2026-07-02/04 | Universe + time as a dimension | `topic_movement` is the shared current-state measure; time changes the view of a persistent story instead of deleting the story. Globe/Universe/Orbital share replay semantics; archive receipts extend history. |
| 2026-07-04 | Crisis as dynamics | Crisis/category/harm do not decide importance. Measured movement/surprise are content-agnostic lenses. Movement is current state, not a forecast. |
| 2026-07-05 | L1/L2/L3 deep reviews | L1 is the day; L2 is the healthiest standalone explorer; L3's cure is consolidation, instrumentation, re-substrating, and dossier depth rather than a new surface. |
| 2026-07-06 | Constellation Assembly | L3 offers multiple relation lenses instead of imposing one thesis. Structural/category, coverage-dynamics, geopolitical, entity, and semantic relations remain distinguishable. Umbrella collapse + typed facets shipped in `dossier-connections-v1`. |
| 2026-07-07 | Dossier trust loop | Frozen receipts, basis-weighted connections, citation-safe synthesis, coherence guard, and cold-editor testing are the wedge method. The dossier already exists; improve it rather than replace it. |
| 2026-07-08/10 | Narrative-intelligence vision + archive tier | A pin should carry a whole story context; Workbench should show the constellation incrementally; 5W+H is the report readiness model. Historical story anchors and receipts live on disk/compact summaries, not in a giant Supabase vector store. |
| 2026-07-09/12 | Roadmap v2.1 + subject geography | Publishable-as-news is the exit bar. Subject, coverage, and outlet-origin geography are separate. C7 is read-only until subject geography is reliable. Full-universe processing uses cursor batches, never semantic top-N ceilings. |
| 2026-07-12 | Investigation Graph contract | L1 is a system-composed investigation; L2 is a complete single-focus explorer; L3 is a heterogeneous multi-focus composer; L1 and L3 share one publication-quality contract. |

## 2. Reuse map — already built versus actual gap

### 2.1 Shared engine spine

**Already built**

- `dynamic_topics` is the user-facing Narrative Thread backing record.
- `topic_members` provides typed provenance lanes.
- umbrellas, children, facets, stories-only serving, quality envelopes, and
  stable thread-detail contracts exist.
- `topic_movement` supplies Kalman velocity, surprise, uncertainty, trend, and
  observation count; relative `changed_10h` is the same-lineage fallback.

**Actual gap**

- some consumers still use legacy inline `changed_10h`, raw-volume weighting,
  or category/editorial dampers;
- movement membership/events and source freshness are not uniformly available;
- the graph/publication layer needs adapters over this spine, not new tables or
  a parallel topic population.

### 2.2 Relations and constellation

**Already built**

- `/api/v2/dossier/connections` (`dossier-connections-v1`) measures whitened
  semantic proximity, shared distinctive actors, shared countries, explicit
  evidence-text references, typed facets, umbrella collapse, distributions,
  neighboring bridge stories, and per-pin connectedness.
- `topic_members` exact membership and `/topic/{id}/relationship` expose typed
  press/public/movement/attention roles.
- event bindings, `related_threads`, signal context, Focus relation algebra,
  and Deep History provide additional relation-specific substrates.
- Workbench already renders an incremental mini-constellation for resolvable
  topic pins.

**Actual gap**

- the connection endpoint accepts thread IDs only;
- its edge vocabulary predates explicit truth tiers and completion receipts;
- heterogeneous pins remain flat;
- country overlap is coverage context and must never be promoted to subject or
  story identity;
- existing relation providers need typed adapters and independent degradation,
  then one graph assembler can reconcile them.

### 2.3 Workbench and pins

**Already built**

- one unified Workbench store, multiple named investigations, frozen snapshots,
  notes, trail, JSON/Markdown export, L2 pin affordances, L1 save bridge,
  Workbench constellation, REPORT and CORROBORATE flows;
- local-first persistence is an explicit decision, not missing infrastructure.

**Actual gap**

- current stored pins are not yet the complete `atlas-investigation-v2` node
  contract;
- only story/topic pins enrich the live connection graph;
- the pin does not yet carry all connected threads/entities/facets at capture;
- the inspector cannot explain every edge, unresolved adapter, or frozen-versus-
  live difference;
- L3 time lens does not re-measure the whole graph while preserving frozen pins.

### 2.4 Dossier and publication

**Already built**

- dossier v2/v3 sections, frozen evidence, dates, who-says-what distributions,
  voice and source tiers, connection summary, coverage gaps, constellation
  visuals, Markdown export, and telemetry;
- `dossier-synthesis-v2` writes a standalone cited mini-article from numbered
  receipts and measured connections;
- server-side citation resolution rejects invented receipt numbers;
- `dossier-corroboration-v0` performs independence-weighted web corroboration
  and exports established/contested/unverified results;
- NATO-Ankara has a real cold-editor and corroboration record.

**Actual gap**

- no single deterministic serializer currently gathers all of those existing
  parts into a versioned `PublicationPackage`;
- 5W+H readiness is not a first-class ledger;
- visuals/method/reproducibility are not one portable publication artifact;
- synthesis currently consumes a dossier-specific request rather than the same
  package used by L1;
- L1 does not yet use the dossier quality/citation/corroboration path.

The publication package must therefore be an **adapter/wrapper around these
shipped contracts**, not a simplified replacement that reconstructs sources,
public voice, corroboration, or relation truth from generic snapshots.

### 2.5 L1 daily edition

**Already built**

- fixed 24-hour product role; lead/watchlist, gap box, heat, category lens,
  translation, Brief→L2 and Brief→L3 bridges, provider fallback, offline cache,
  click telemetry;
- `fetch_threads` gives L1 the same story population as L2;
- country heat already demonstrates volume-independent anomaly measurement:
  velocity, surprise, diversity, and voice against each country's own baseline.

**Actual gap**

- the edition is still a layout over the served thread ranking plus a short
  aggregate Editor's Analysis, not a system-built investigation;
- the existing thread ranking includes log-volume and legacy editorial/category
  dampers, conflicting with the later crisis-as-dynamics decision and Pedro's
  explicit objection to semantic importance filters;
- a finite page needs selection, but selection must reconcile every candidate
  and disclose why it is shown or deferred;
- daily material must pass through the same receipts, relations, readiness,
  corroboration, citation, and synthesis contract as L3.

### 2.6 L2 standalone depth

**Already built**

- Equal Earth Globe, Universe/Orbital, thread focus, signals, country/source/
  entity panels, anomaly alerts, public attention, conflict/hazard markers,
  history/replay, Deep History, hover cards, and pin bridges;
- focus propagation exists and major errors degrade honestly.

**Actual gap**

- there is no single `FocusLens` contract consumed by every focus-dependent
  panel;
- event counts do not always open the exact bound events and their binding
  receipts;
- related-thread labels can expose geographic coincidence as if explanatory;
- historical replay does not yet reconstruct actors, voice, countries, events,
  and edges together;
- structured hover receipts (#255) and binding freshness (#256) remain active
  prerequisites for trustworthy L2→L3 capture.

## 3. Decisions superseded or narrowed

1. **Legacy rank-by-volume/editorial lane is not the L1 editorial contract.**
   `rank_threads` remains a compatibility serving order until deliberately
   recalibrated, but L1's new daily investigation cannot copy its 0.45 volume
   weight or category/lifestyle damp. Content class is descriptive, not a
   measure of importance. Sports, culture, or markets may lead when their
   measured state and evidence warrant it.
2. **Movement is not prediction.** The July 4 leading-indicator backtest was
   negative. `topic_movement` may say accelerating, surprising, decaying, or
   uncertain now; it may not say what will grow next.
3. **No LLM classification or relation judgment in the production path.** The
   July 7 note that proposed an LLM as the edge-label “reference ceiling” is
   narrowed by Pedro's later decision and the July 12 math-first spec: use
   deterministic fixtures, data, ablations, stability, and transparent
   uncertainty. LLM use is reserved for glass-box publication prose and
   coverage-language phrasing after facts are fixed.
4. **Crisis/category is a lens, not a gate.** Older category typing and
   editorial-lane decisions cannot silently remove, damp, or promote daily
   candidates by content class.
5. **Dynamic and Atlas topics are not peer product populations.** R3's one
   story population supersedes old dual-serving mental models.
6. **Thread IDs are not durable story identity.** A story anchor combines query,
   actors, evidence, time, and subject context; a rebuilt thread enriches the
   investigation rather than invalidating it.
7. **Search is not the investigation owner.** The research plan remains one
   suggestion source. Pins and interactions from all L2 surfaces compose L3.
8. **Arbitrary semantic caps are invalid.** Query batch sizes, evidence samples,
   and visual disclosure may be finite, but completion/selection/omission
   ledgers must reconcile the requested universe. Existing `MAX_PINS`, per-topic
   sample caps, and neighbor caps are operational/UI constraints that must be
   labeled, paged, or made expandable when the contract claims completeness.

## 4. Correct implementation shape

```text
dynamic_topics + topic_members + movement + events + voice + archive
                              |
                    existing serving contracts
                              |
       relation adapters (dossier/events/history/voice/exact/semantic)
                              |
                  typed graph assembler + ledgers
                              |
             shared deterministic PublicationPackage
                       /                         \
          L1 system selection                 L3 analyst pins
                       \                         /
          one citation-safe publication synthesis interface
```

The graph assembler owns normalization, truth tiers, completion, unresolved
work, and reproducibility. It does **not** reimplement relation math.

The publication package owns a portable editorial input/output boundary. It
does **not** replace dossier connection analysis, voice, corroboration, or
server-side citation validation.

## 5. Daily selection correction

L1 cannot avoid finite presentation, but it can avoid pretending that one
handwritten “investigative usefulness” scalar is objective. The safer design is
a measured, content-agnostic selection ledger:

1. cursor-exhaust every eligible story in the 24-hour edition;
2. compute a vector, not an opaque verdict: velocity, surprise, uncertainty,
   persistence, evidence sufficiency, independent source/origin breadth,
   coherence/noise, attention divergence, and gap/anomaly flags;
3. build a Pareto frontier and diversity-aware story constellation so no single
   dimension (especially raw volume) owns the page;
4. choose the finite visual spine from that measured frontier and expose every
   deferred candidate with its vector and reason codes;
5. keep category, crisis, country, and language as descriptive lenses and
   diversity diagnostics with zero importance weight;
6. evaluate the selector on frozen daily universes for stability, duplication,
   evidence quality, geographic/language concentration, and comparison with
   volume-only and current `rank_threads` baselines;
7. only after the deterministic package is fixed, let the publication LLM name
   the through-line and phrase the edition with numbered receipts.

This preserves Pedro's correction: Atlas measures how the information sphere
moves; it does not decide that a topic is “investigative” because of its
semantic class.

## 6. Current evidence and gates

- Subject geography Stage 1 completed all 1,442 rows with cursor exhaustion,
  but inferred only 140 (9.7%). That is a useful conservative harness, not a
  serving contract. Stage 2 must recalibrate on a real gold sample and add
  stronger semantic/structured-event evidence before chips or C7 depend on it.
- C7 inspected 100 topics and produced review hints, but documented false
  subject-country proxies. It stays read-only.
- NATO-Ankara established the citation/corroboration/synthesis foundation and
  reached “publishable with minor edits” after the v2.1 fixes, but the current
  Workbench still does not produce the full portable 5W+H package.
- L1 production can present daily threads and prose, but the observed ranking
  includes noisy/global-sports rows and is not yet a publishable daily
  investigation.
- L2 and L3 load cleanly in production, but no current end-to-end run has yet
  demonstrated heterogeneous pins + time-remeasured edges + exported package.

## 7. Open issues aligned to the program

| Issue | Role in current goal | Closure evidence required |
|---|---|---|
| #256 event-binding freshness | L2 exact movement/event edges | autonomous binding run + fresh receipts in production |
| #255 structured marker hover | event/hazard/anomaly node capture | inspectable hover receipts + pin adapter + browser smoke |
| #253 NER throughput | actor/subject quality | throughput and verified-actor coverage measurement |
| #248 byline/noise classes | actor/evidence precision | fixtures + prod sample show bylines/non-story entities excluded |
| #238 subject geography | where/voice/edge honesty | Stage 2 persist/serve + chips/dedup/navigation smokes |
| #237/#168 community layer | real public voice | discussion volume and relationship differentiation, never corroboration |
| #221 maturity contract | temporal honesty | sealed/provisional labels on live aggregates |
| #220 funnel ledger | reliability/coverage | stage-by-stage counts and drop causes visible |
| #173 Evidence Route | L2/L3 receipt path | relation/receipt inspector covers visible information route |
| #180/#46 hazard/conflict sources | structured event depth | source path live and bound; ACLED remains access-dependent |

#247, #236, and #106 are experience/brand tracks; important, but they do not
define the truth contract. No open issue should be closed solely because a spec
mentions it or a partial endpoint exists.

## 8. Revised delivery order

1. Preserve the already-shipped reliability and typed-node slices.
2. Refactor the provisional graph/package work into adapters over
   `dossier-connections-v1`, membership, voice, event, history, and corroboration
   contracts; do not merge a parallel simplified truth model.
3. Build and backtest the content-agnostic daily selection ledger on frozen
   universes before connecting it to production L1.
4. Ship the shared package as a compatibility wrapper around the current
   dossier synthesis/citation/corroboration path.
5. Wire L1 to the system package, retaining the existing Brief as a fully honest
   fallback while the new lane degrades independently.
6. Ship FocusLens/event receipts and time-slice behavior in L2.
7. Migrate Workbench storage and UI to heterogeneous nodes, incremental typed
   edges, inspector, and time lens.
8. Export one daily edition, one Iran investigation, and one NATO-Ankara dossier;
   grade all three against the same rubric and run the cold-editor loop.
9. Only then close issues, publish the LinkedIn artifact, and schedule the
   external analyst gate.

## 9. Acceptance test for this reconciliation

Future implementation plans must answer “which existing contract is reused?”
for every relation, receipt, voice, history, corroboration, citation, movement,
and synthesis task. A task that cannot answer that question must prove the
capability is absent before adding code.
