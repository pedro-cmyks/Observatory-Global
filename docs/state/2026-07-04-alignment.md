# Atlas / Observatorio Global — Alignment "Where Are We" (2026-07-04)

Branch: `v3-intel-layer` · Purpose: ONE scannable map of every open thread of
work, whether they align, which is the single active track, what is parked, and
what roadmaps exist — so nothing gets lost. Read-only synthesis of open GitHub
issues, `docs/specs/*`, the paper master plan, `docs/state/*`, and the running
CLAUDE.md session log. Where a status could not be confirmed from code it is
marked **unclear — verify**.

---

## 1. The one active track

**Atlas as the spatial-intelligence layer over ONE unified narrative engine.**
Concretely, the live work is the convergence of three strands that have merged
into a single track: (a) the **Universe / Orbital visualization** — the whole
living story population rendered as a navigable vector field (`GET
/api/v2/universe`, `UniverseView.tsx`, `2026-07-02-universe-view.md`) with
per-thread "solar system" drill-down (`2026-07-02-orbital-thread-view.md`),
now iterating through V1–V9 polish (trajectories, moons/gravity, perspective
zoom, focus lens); (b) the **engine unification R3 / F-series** — kill the
atlas‖dynamic "split-brain," one typed `topic_members` table, unify
construction and separate at serving (`2026-07-01-atlas-engine-r3-unification.md`
CLOSED+VALIDATED, `2026-06-29-atlas-unified-engine.md` F0–F3 shipped, F4 cutover
gated); and (c) **substrate reliability** — the M1 cron chain (embed → cluster →
topic_members → movement) that everything above feeds on, which stalled
2026-07-04 and is the honest blocker under universe/movement/heating (CLAUDE.md
"SUBSTRATE #2 DIAGNOSED"). The visualization is the user-facing face; the engine
is its truth source; the substrate is whether either has fresh data. They are
aligned — one surface (the spatial index of Atlas), one engine, one data chain.

---

## 2. Product wedge & the open validation gap

**Wedge (from CLAUDE.md PRODUCT WEDGE block, master-consolidation T5.2):** Atlas
serves the **narrative analyst** — journalist, OSINT/conflict researcher,
newsroom desk, policy/NGO analyst — whose job is *honest situational awareness
on a specific event/topic/country*: the real story, who says what across
countries and languages, press vs. public, and what is missing — fast, with
receipts. Anti-goal: **no new surface/capability until telemetry shows users
reaching a value moment.**

**The open gap:** most viz + engine plumbing is shipped, but the **task-time /
value evaluation is still pending** — Pedro's own framing "**bacano ≠ eje**"
(it's cool, but is it the axis / does it do the job?). Telemetry was read once
(2026-07-01): 181 app_opens / 14 sessions but only **3 value moments, none since
06-28**; `brief_open`/`brief_thread_open` instrumentation was added but has not
been re-read. The anti-goal is ungoverned without weekly telemetry reading.
Repeated "NEXT" items name this: *task-time pass / Pedro eyeball / "qué falta
para ser eje"* (CLAUDE.md 2026-07-02–07-03). **This is the most important
un-closed thread and it is not a build task.**

---

## 3. Open work, grouped

Status legend: shipped (done, may have follow-ups) · open (active/actionable) ·
parked (deprioritized, reason in §5) · superseded · blocked.

### Engine / taxonomy
| Item | Status | What |
|---|---|---|
| R3 unification (`2026-07-01-...-r3-unification.md`) | shipped (spec CLOSED) | One story population: spine (category→event→story) + lenses; schema + typing + retirement shipped. |
| Unified engine F0–F3 (`2026-06-29-atlas-unified-engine.md`) | shipped | Typed `topic_members`, unified construction v2, A/B proven (v2 wins coherence/purity). |
| Unified engine **F4 cutover** | parked/gated | Flip serving to unified-v2 — gated on gold + new-topic labeling + read-path param (§5). |
| #204 taxonomy revision | open (living) | Measured ~40–52% on-topic ceiling = dominant precision lever; candidate-v2 built (96% agreement), needs crisis-only κ phase + wire into gate. |
| Recall / scoped clustering (`2026-06-30-...-recall-scoped-clustering.md`) | open (spec DRAFT) | Only 5.6% of embedded signals cluster; scoped country/region passes = the #1 engine lever (#229). |
| Attention + anomaly→movement roles (`2026-06-30-...-attention-anomaly-roles.md`) | open (DRAFT, sequenced after recall) | The 2 missing "brains"; attention HOLD (data-gated), movement ships cheap. |
| #219 Kalman movement feed | shipped | `topic_movement` populated (movement-kalman-v1); universe reads velocity/trend. Backtest (does velocity LEAD volume?) pending. |
| #185 corpus-mine lexicon | open | Mine vocabulary from transformer-tagged signals (recall enabler). |
| #248 evidence-noise classes | open | byline-persons + entertainment-about-crisis noise; discussion-attach quality (#248 class). |
| #251 GDELT GKG ORGANIZATIONS | open | Ingest signal-level org entities. |
| #159/#161 GDELT DOC/Event Mentions | open (research) | Query-time evidence enrichment / propagation evaluation. |

### Universe / visualization
| Item | Status | What |
|---|---|---|
| Universe View MVP + V2–V9 (`2026-07-02-universe-view.md`) | shipped | Vector field of 348 topics, exact 768-dim edges, time scrubber, trajectories, moons, perspective zoom, focus lens. |
| Orbital thread view (`2026-07-02-orbital-thread-view.md`) | shipped | Per-thread "solar system"; radius=semantic distance, drift-coded comet tails, R3 spine drill-down. |
| #234 focus propagation | shipped (core) | Country/person/thread focus re-scopes all surfaces; precise ?person= filter. Upgrades remain (rarity-weighted siblings done). |
| #173 Evidence Route panel | open | Visible information-pathway panel (rw-tier-a-core). |
| #233 reorderable panels | open | RGL regression; documented for revival. |
| Universe pending (CLAUDE.md review) | open | pseudo-3D tilt orbital; discussion-attach noise on dt-981. |

### Substrate / ops
| Item | Status | What |
|---|---|---|
| Cron chain reliability (CLAUDE.md 2026-07-04) | open (URGENT) | M1 crons stalled → thin/frozen data; durable fix = CHAIN embed→cluster + scoped-snapshot watchdog + harden restore-after-reindex. |
| #241 embed cron / HNSW INSERT bottleneck | open | HNSW INSERT (2.7/s) not embed (228/s) is the limiter; lever-1 bulk-reindex done. |
| #184 NLP throughput | blocked (infra) | NER stays EN-only gazetteer-typed; multilingual/parallel blocked on infra (§5). |
| #243 ops follow-ups checklist | open | multilingual drain, #241 lever 1, paper gaps, temporal-holdout, scoped-snapshot fire. |
| #221 data maturity contract | open | sealed-hour floor for aggregates + provisional badge. |
| #220 funnel observability ledger | open | stage-by-stage pipeline counts + drop causes. |
| #180 reliefweb blocked fetch | open (bug) | replace blocked Fly RSS with API/proxy path. |

### Search / research-workflow
| Item | Status | What |
|---|---|---|
| Research workflow Phases 1a/1b/1.5/2 (`2026-06-09-...-workbench.md`) | shipped | Intent parser, anchors, ranking, workbench, semantic lane live. |
| **Phase 4** (who-says-what dossier + evidence-quality/Paper-1 benchmark) | open | The T1.1/T1.2 depth track — NOT done; stays open. |
| Search engine plan P3/P4 (`2026-07-01-search-engine-plan.md`) | open | P1/P2 shipped; P3 semantic-on-submit + P4 telemetry remain. |
| #217 source credibility tiers | open | capability G, product face of Paper 2. |
| #154 source-quality audit | open | measure source quality/dominance/NLP backlog before scoring. |
| #166 analyst correction loop | open | calibrate confidence thresholds. |
| #156 newsapi quota / crisis queries | open | quota budget + dynamic queries. |
| #161 GDELT DOC 2.0 enrichment | open | (also engine). |

### Voice / diversity
| Item | Status | What |
|---|---|---|
| Diversity program (voice-mix, waves 5–16) | shipped | 219 feeds / 126 countries / 31 langs; voice_entropy 0.71 (above target); self-maintaining. |
| #235 every-country-domestic-voice | open | continue feed waves until no country at 0% self-coverage; FIPS edge codes. |
| #238 subject geography | open | chips/dedup/geo need subject-country not coverage-volume. |
| #230 China/East-Asia voice | open (in #235/#162) | zh/ja/ko press near-absent; acquisition + NLP dep. |

### Mobile
| Item | Status | What |
|---|---|---|
| #236 mobile visualization | open (roadmap) | phone-native (not shrunk desktop); tabbed IA shipped, per-surface polish ongoing. |
| #239 mobile/console load-time program | open | measure + reduce load times. |

### Papers (see §4)
| Item | Status | What |
|---|---|---|
| #226 markets L4 (M0 event study) | open (research) | do thread movements lead market moves? |
| #140 visual use-case manual | open (docs) | annotated real-Atlas screenshots/flows. |
| #106 octopus mascot / brand | blocked | needs design session (Pedro). |

---

## 4. Roadmaps that exist

### Paper track P1–P8 (`docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`, canon-active)
- **P1 — Evidence-role topic classification + distillation.** ACTIVE; RQ1 measured (Atlas v2 precision 41.6%, LLM 78–81%), manuscript open. Blocking evidence: theme-hint ablation, temporal hold-out, result skeleton. This is the split-brain-vs-unified experiment (the F3 A/B) + the taxonomy ceiling.
- **P2 — Cross-source source-quality scoring.** SEED. Product face = #217 credibility tiers.
- **P3 — Atlas heat: composite heat detection.** SEED. Volume≠importance discipline (heat = velocity+surprise+…).
- **P4 — Thread aggregation + evidence sampling.** SEED. Threads as first-class object; unified ranking + typed membership + relationship types live here.
- **P5 — Sentiment fusion + multilingual NLP calibration.** SEED. Blocked-adjacent to #184/#162.
- **P6 — Temporal model (hot/cold, processed historical, bucketing).** SEED. The §I time model (universe scrubber) draws on this.
- **P7 — Visualization + analyst workflow.** ACTIVE (evidence accruing) — the universe/orbital/focus-propagation method is written here; carries the honesty architecture (positions approximate · relations exact) + relation-quality ablation.
- **P8 — Open-set topic discovery + taxonomy evolution.** ACTIVE-adjacent — recall ceiling (0.2% coverage), orphan detection, taxonomy candidate-v2.

### Product roadmap
- **Master consolidation (`2026-06-26-atlas-master-consolidation.md`)** — the themed-tier close map. Tier 1 evidence-honesty (Phase 4 dossier OPEN), Tier 2 public-attention depth (#168/#172), Tier 3 legibility/UX, Tier 4 processing reliability, **Tier 5 demand-side (the real risk — validation)**, Tier 6 paper-adjacent.
- **Engine F-series** F0–F3 shipped → **F4 cutover** (gated) → F3.3 movement (event-source revival). 
- **R3 unification** spine+lenses+relations CLOSED; remaining = engineering with resolved decisions (movement, umbrella-fold, serving cutover).
- **#236 mobile** — phone-native presentation program (roadmap, not scheduled).

---

## 5. Parked / deferred (with reason)

- **F4 unified-v2 serving cutover** — gated on: recurring build (done), new-topic
  labeling (§6 step 5), a fixed precise gold label set, and parametrizing the
  read path. Verdict is "PASS effective" on structural metrics but topical
  precision is ~40–52% for BOTH engines, so cutover buys cleaner topics, not
  precision → not forced. (CLAUDE.md 2026-06-29 F3.2b.)
- **#172 silent-risk detector** — PARKED. Measure-first disproved the data source
  (wiki top-pageviews = sports/celebrity; forum pivot doesn't clearly improve;
  the phenomenon is rare in both). Real path = attention/coverage ratio or local
  sources. Scaffold exists, docs in `docs/methodology/silent-risk-detection.md`.
- **Multilingual NER (#162) / #184 throughput** — BLOCKED ON INFRA. Worker +
  embed share one M1 process (GIL); `xx_ent_wiki_sm` returns nothing for
  Persian/Arabic/CJK; xlm sentiment broken in mlvenv. Non-English subjects stay
  gazetteer-typed (honest, unverified) until a proper multilingual model + env.
- **Attention role (wiki/trends)** — HOLD, data-gated; do not run the hot-PK
  migration until recall makes the 68-topic surface worth enriching.
- **F3.3 movement (#232)** — event sources are DEAD (`acled_conflicts_v2` = 0
  rows); needs event-ingestion revival or co-occurrence schema, not an increment.
- **#46 ACLED** — blocked on Pedro's API registration.
- **#106 mascot** — blocked on a dedicated design session.
- **C3b semantic trends/wiki per-thread** — deferred (thin/stale data, low ROI).
- **#161/#159/#151/#156/#226 / gate-recall map / article bodies** — mapped/parked
  per the 2026-06-29 engine session (recall hypotheses disproved; do not re-run).

---

## 6. Recommended next 3 moves (honest read)

Given viz + engine plumbing are largely shipped and the validation gap is open:

1. **Fix + harden the substrate FIRST (blocking everything).** The M1 cron chain
   stalled 2026-07-04 and every downstream surface (universe/movement/heating) is
   noise-thin because of it. Build the durable fix named in CLAUDE.md: CHAIN
   embed→cluster (not independent schedules), add a scoped-snapshot watchdog, and
   harden restore-after-bulk-reindex. Nothing else is trustworthy on stale data.
2. **Close the validation gap — run a real task-time / value pass ("eje" test").**
   Read telemetry weekly (the anti-goal is ungoverned otherwise), and do a
   task-scoped walkthrough of the narrative-analyst job on the live surface. This
   is the pending "bacano≠eje" evaluation and it should gate any *new* surface
   work per the product anti-goal. Not a build task — a measurement + judgment
   pass.
3. **Attack the #1 measured engine lever: recall via scoped clustering (#229),
   then the #204 taxonomy wire-in.** Only 5.6% of embedded signals cluster; the
   universe is thin because most stories never form a topic. Scoped regional
   passes recover them (CI 238→0, China 8,720→4). Pair with wiring #204
   candidate-v2 (OUT_OF_SCOPE + excludes) into the gate — the two levers that
   actually move topical precision, unlike F4 or new roles. Defer F4 cutover and
   the attention role behind these (both gated / low-ROI until recall lands).

---

# EOD reconciliation (2026-07-04 night) — how today maps to the open tracks

Today's ships, placed in the standing structure. Verdict up front: **the tracks
are ALIGNED — nothing shipped today is off-roadmap; three recommended moves from
the morning version of this doc were executed the same day.**

## Against this doc's "recommended next 3 moves" (morning)

1. ~~Harden substrate crons~~ → **DONE** (freshness-watchdog + goldgrowth cron;
   substrate #2 closed).
2. ~~Run the eje/validation pass~~ → **DONE** (`docs/research/eval/
   2026-07-04-atlas-vs-websearch-eval.md`): Atlas = eje for DISCOVERY; the
   telemetry-value-moment gap now has its qualitative answer. Quantitative
   task-time telemetry still pending (search_story_open now emits — read weekly).
3. ~~Attack recall #229/#204~~ → **PARTIALLY DONE, honestly**: gate arc
   (OpenAI cutover + two-tier + mig 067 hint pruning = PR3-05 finally applied)
   shipped; gold-growth revealed the variance ceiling → accumulator cron armed;
   **still open**: #204 candidate-v2 wiring, semantic assignment lane, the
   retrain-at-200-positives.

## Specs touched or affected today

| Spec | Status after today |
|---|---|
| `2026-07-01-search-engine-plan.md` | **P3 (semantic-on-submit) DELIVERED in different form**: the story panel (Enter → research-plan anchors, semantic lane included) supersedes the planned dropdown-semantic approach. P4 telemetry partially live (`search_story_open`, `search_query` events). P2-focus-chip still open. |
| `2026-06-09-research-thread-builder-workbench.md` | The Workbench thesis ("search produces anchors, user pins") finally got its FRONT DOOR: search→story = the missing L2 entry to the L3 flow. Phase 3 (report from pins) unchanged/open. |
| ADR-0005 / EE map | **CLOSED COMPLETELY**: "retire MapLibre" (the last listed step) executed 2026-07-04. EE is the only map. |
| `2026-07-02-orbital-thread-view.md` | Perspective zoom (k^-0.55 counter-scale) shipped — moons detach. Spec's §7b moons arc now fully built + polished. |
| `2026-07-02-universe-view.md` | Unchanged today; §6 trajectory metrics got its FIRST backtest result (Kalman does NOT lead — the capture-rate/leading-heat hypothesis needs a different observable). |
| R3 unification / F-series | Unchanged; F4 cutover stays gold-gated. mig 067 is R3-adjacent hygiene (assignment candidate quality). |

## Paper track deltas (P1–P8)

- **P1 (classification/benchmark)**: THREE new method-grade artifacts:
  (a) two-tier serving = precision-tier framing (verified 90% / extended 75%)
  — an honest-serving pattern worth a paper §; (b) **gold-growth variance
  finding** (`gate-recall/2026-07-04-goldgrowth-round1.md`): per-topic
  threshold calibration is unstable below ~200 positives — a real
  small-n-calibration methods result, and the justification for the
  accumulator design; (c) mig 067 = PR3-05's REMOVE-OK finally implemented,
  with the surgical keep-rate rule (<2% @ n≥40) as the documented method.
- **P4 (threads/movement)**: Kalman backtest CLOSED the leading-indicator
  question negatively (velocity mean-reverts; `movement-backtest/`); ordering
  stays changed_10h. Denominator honesty (067) feeds the ranking-input story.
- **P7 (viz/analyst workflow)**: the Atlas-vs-web eval IS the P7 task-time
  evidence (discovery-radar vs answer-tool split, India case); search→story +
  keep-alive + warm-cache are the workflow-latency method (task-time ↓).
- **P8 (open-set/noise)**: #248 forum hobby damp (community-name-as-topic
  signal) joins the noise-class taxonomy.
- P2/P3/P5/P6: no movement today.

## Not aligned yet / honest debts

1. **#204 candidate-v2 is still unwired** (built 2026-06-29, OUT_OF_SCOPE
   policy + excludes never reached the gate/assignment prompts) — the biggest
   built-but-idle asset.
2. **Semantic assignment lane** (embedding candidate-generation; would catch
   the India-SIR class no lexicon matches) — designed in conversation, not spec'd.
3. **Telemetry weekly read** — the wedge anti-goal is ungoverned without it;
   new events (search_story_open) make the next read more informative.
4. **F4 cutover** — parked (correctly, gold-gated), but the v1‖v2 dual regime
   remains the standing consumer-bug class.
5. Hidden-pane polling under keep-alive (mobile battery) — noted in #239.
6. Universe spec §7 is a working section — the shipped state (free-nav,
   perspective, trajectories, moons) deserves a consolidation pass into the
   spec when the surface next changes.
