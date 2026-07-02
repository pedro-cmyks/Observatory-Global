# Orbital Thread View ("Sistema Solar") — E2/L11 replacement for the Evolution Graph

Status: PROTOTYPE SHIPPED (ThemeDetail, toggle next to Evolution Graph)
Origin: Pedro L11 + L11-extended (2026-07-02 live review capture); assessment §"L11 — Claude's honest assessment" — constraints there are settled, not re-litigated here.
Paper track: P7 (evolution-graph-as-engine-truth).

## 1. E2 diagnosis (why the old graph "never loads") — RESOLVED

Three layers, worst first:

1. **Dispatch-order bug (data, prod-verified, FIXED `b3fcfa79` + deployed):**
   `get_theme_details` ran the processed-history branch (`use_processed_history(hours) and "-" in theme_code`) BEFORE the `dynamic-topic-<id>` resolver. Every dynamic thread id contains "-", so at any window >24h the whole detail returned `total=0, no_processed_topic_history` — empty panel, no graph, no signals. Verified: `dynamic-topic-981?hours=72` → total 0 before, total 78 after.
2. **Silent gate (frontend):** the historical atlas payload returns `graphSignals: []` with non-empty `signals`; ThemeDetail's gate `(data.graphSignals?.length ?? data.signals.length) > 0` evaluates `0 > 0` → section silently absent (`??` only falls through on null/undefined). Atlas threads at >24h with processed history never show the graph. Not fixed in the old component — the orbital view supersedes it and fetches its own data.
3. **At 24h the old graph actually renders** (browser-verified in dev: canvas, nodes, scrubber). But the default bucket = the latest single hour, typically 1 signal → a near-empty force graph that reads as broken. Conceptual weakness, not a load failure.

Conclusion: "never loads" = (1) for dynamic threads at long windows, (3) perceived at short windows. The replacement below is justified on concept, and the data bug is fixed regardless.

## 2. Concept (decided)

Thread at CENTER. Entities (typed subjects) and countries ORBIT it.
- **Orbit radius = semantic distance** — mean cosine distance of the body's member signals to the topic centroid (`signal_embeddings.vec` ↔ `dynamic_topics.centroid_vec`; for atlas topics, mean-of-member-embeddings as centroid, labeled computed). Same-story bodies orbit close and together.
- **Angular velocity = interaction intensity** — a body's angle advances with its CUMULATIVE signal count up to the scrubbed time. Scrubbing time visibly spins active bodies; dormant bodies stand still.
- **Entry/exit = the §I time dimension** — a body is invisible before its `first_seen`; after its last activity its opacity DECAYS (no cliff), matching the §I criticality-decay model.
- **Comets** = transient bodies: presence span < 25% of the thread's lifespan (and few signals). Drawn with a tail; they swing by, they don't belong to the permanent system.
- **Size = volume** (sqrt of signal count). **Color = body type** (person/org/place/event/country); center chip carries the R3.1 category + crisis flag.
- **2D radial. Static rings. NO perpetual animation** — all motion is driven by the TIME SCRUBBER (interaction). Analyst reads a still image by default (scrubber parked at "now").

## 3. Data (all existing; nothing invented)

| Visual DOF | Source |
|---|---|
| membership + assigned_at | `topic_members` (v1-compat evidence; sample_signal_ids fallback) |
| semantic distance | `signal_embeddings.vec` ↔ `dynamic_topics.centroid_vec` (halfvec 768 vs real[] → cast to vector(768), `<=>`) |
| body typing | persons array + `classify_subject` gazetteer (person/org/place/event) |
| first/last seen, per-body timeline | member signal timestamps |
| category / crisis | `dynamic_topics.category`, `crisis_relevant` (R3.1) |

Measured on dt-981 (Lebanon-Israel Framework Agreement): 58 members, 58/58 embedded, distance band 0.031–0.048 → **normalize per-thread (min-max)** for radius; comets present in real data (marco rubio: 2-day window; donald trump: 1 signal).

## 4. Contract

`GET /api/v2/theme/{theme_code}/orbital?hours=N` → `orbital-thread-v0`
- center: `{label, category, crisis_relevant, member_count, window: {start, end}}`
- bodies: `[{id, label, type: person|org|place|event|country, n, dist, first_seen, last_seen, timestamps: [iso…]}]` — timestamps raw (n small); ALL layout math client-side and pure (`lib/orbitalLayout.ts`, vitest-covered).
- Honest empties: no embeddings / no members → `{bodies: [], reason}` — frontend renders an explanatory empty state, never fabricates.
- Dynamic topics: stored centroid (engine truth). Atlas topics: `avg(vec)` computed centroid, `centroid_basis: "computed"` in payload.

## 5. Frontend

`OrbitalThreadView.tsx` + `.css` (vanilla CSS, `data-tip`), SVG (≤ ~30 bodies, no rAF loop). Toggle `ORBITS | GRAPH` in the section header; ORBITS default (the old graph stays one click away). Hover → overlay card (label, type, n, entered/left, distance). Click person → person focus; click country → country drill (reuses ThemeDetail handlers). Desktop only (same `!isMobile` gate as the old graph).

## 6. Acceptance (the bar it must beat)

"¿Quién entró a esta historia esta semana?" — answerable faster than from the list: scrub back one week and watch bodies appear; new entrants are the bodies that materialize. If this reads slower than the signal list, the view failed (assessment risk #2). Evaluate with Pedro on live threads; measure task time informally before any wider rollout.

## 7. Phase 2 — L3 Universe Builder (SPEC ONLY, not built)

The Workbench (L3) reuses the same visual language: the INVESTIGATION QUESTION at center; pinned threads/entities/countries = bodies captured into YOUR orbit. Atlas's galaxy is the shared sky; an investigation carves its own solar system from it. Mapping: radius = semantic distance of pinned item to the investigation query embedding (research_semantic already embeds queries); velocity = pin-interaction recency (`research_pin_events` exists, #218); entry/exit = pin/unpin history. Same component, second consumer — build only after the ThemeDetail prototype survives Pedro's task-time evaluation (wedge anti-goal: no new surface until value moment).

## 7b. Round-2 evolution (Pedro live review, 2026-07-02 PM — SHIPPED unless noted)

- **Tail = MEASURED semantic drift** (`415ed1fd`): late-half vs early-half mean
  centroid-distance per body. Outward = receding from the story, inward =
  converging. 4% noise floor of the thread's distance span (measured dt-981).
  Comet demoted to a dashed ring. Pedro's own reading of the tail, made literal.
- **Rim = tone** (`547662db`): body fill stays TYPE, rim carries mean tone of
  the body's coverage (raw signals scale, neutral band ±1.0). Unifies the
  tone/avg-sentiment naming split in this surface.
- **R3 spine drill-down** (`547662db`): atlas topics are CATEGORIES; every R3.1
  category-typed dynamic story under one is served as `memberStories` — "los
  temas grandes dejan ver los temas pequeños". First surface slice of the
  atlas‖dynamic unification; the engine cutover (R3.2/F4) stays gold-gated.
- **Gate case logged**: election-legitimacy kept 1/1,066 in 24h (0.1%) —
  below-gate fallback extended to near-zero keeps (<5 of ≥20); the keep-rate
  itself = engine program (gate recall), NOT a surface fix.
- **MOONS + GRAVITY FIELDS (Pedro concept — SPEC ONLY, next session):** bodies
  need not be lone planets. (a) *Moons*: sub-entities that co-occur tightly
  with ONE body (an org/place appearing almost only alongside a person within
  the thread) orbit that body, not the center — computable from co-occurrence
  + shared-signal ratio. (b) *Gravity fields*: body↔body semantic attraction —
  each body's position embeds as the mean of its member-signal vectors, so
  pairwise body distances are measurable in full space (same method as
  universe edges, one level down); strong pairs could curve toward each other
  or link. Both are REAL quantities, no fabricated physics; assess against the
  legibility budget before building (assessment risk #2: must not turn the
  system into a hairball — moons probably need a hover/expand gesture, not
  always-on).

## 8. Out of scope (v1)

Subthread bodies (umbrella children orbit only for umbrella topics — later); galaxy view (threads orbiting categories); MapLibre-style zoom; mobile.
