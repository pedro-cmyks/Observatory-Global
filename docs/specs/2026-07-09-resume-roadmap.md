# Atlas resume roadmap v2 — validated + corrected (2026-07-10)

v1 (2026-07-09) was stress-tested by three independent passes: a self-adversarial
read, a strategy/resource stress-test, and a domain validation of the anomaly
engine against real OSINT/early-warning practice AND this codebase's own measured
history. v2 bakes in every correction. Pairs with
`docs/specs/2026-07-08-narrative-intelligence-vision.md`.

## The three verdicts (summary)
| goal (v1) | verdict | core correction |
|---|---|---|
| G1 coverage 80/80 | NEEDS-CHANGE | "80% of firehose" is a SUPPLY metric decoupled from analyst value; the two halves fight (the last 40 points ARE the junk tail). Swap the metric. |
| G2 web corroboration | SOUND, RESEQUENCE | Closest thing to the sellable artifact but slotted last. Pull FIRST. Naive corroboration re-confirms syndicated wire as "consensus" — weight by source independence. |
| G3 anomaly engine | NEEDS-CHANGE | Right instinct, wrong architecture: C1-as-specified already FAILED our own 2026-07-03 backtest; C2 is the parked #172 dead end. Rebuild around proven patterns + two free detectors the plan missed. |
| G4 vision layers | SOUND north-star | Propagation/origin rests on INGEST timestamps ≠ first utterance — "coordinated vs organic" would be confidently wrong without a hard guardrail. |

Cross-cutting: the serving/batch **shared Supabase is the constraint that breaks
G1/G3/G4** — it gets its own workstream (v1 only "watched" it). The **dates gap**
from the Frank test (undated claims) was missing from v1 — restored.

---

## NEW SEQUENCE — wedge-test first
> The single highest-leverage act on resume: **put ONE complete, independence-
> corroborated report in front of a real analyst on a marquee story, with the
> engine as it stands today — and measure A0 in the same sitting.** Everything
> else optimizes a deliverable whose market value is still an assumption.

### Phase 0 — The wedge test + honest baseline (days, not weeks)
- **P0.1 Marquee dogfood:** pick a marquee story (English-ok; multilingual off
  the critical path for this). Build the investigation on the CURRENT engine.
- **P0.2 Corroboration lane v0 (G2 pulled forward):** run the deep-research web
  harness over the thesis + pinned actors. **Weight by source INDEPENDENCE**
  (cluster syndicated copies; count independently-operated outlets, not
  articles). Attach as a labeled "web corroboration" section.
- **P0.3 Dates fix (Frank-test debt):** evidence carries dates; synthesis
  attributes and dates contested outcomes. Small, unblocks "stands alone".
- **P0.4 A0 measurement:** 3-way split of 24h signals — useful-story / junk-typed
  / unclassifiable-noise (measured). Defines the honest denominator + floor.
- **P0.5 Show it** to a real analyst (or the coldest available proxy) + Frank
  test. Their reaction = the roadmap's steering signal.
- KILL/PIVOT: if independence-clustered corroboration collapses to ≈1 source
  (all wire), pivot corroboration to curated high-independence source lists.

### Phase 1 — Infra split (the constraint)
- **P1.1 NOW (cheap):** heavy-job mutex — clustering/embed/flag jobs never run
  concurrently against serving; stagger crons; keep serving queries light.
- **P1.2 NEXT:** separate batch workload from serving — read-replica or separate
  batch project; batch writes merged in bounded transactions.
- **P1.3 EVENTUAL:** local analytics store (e.g. DuckDB over the existing
  embedding/archive shards on the M1) so heavy scans never touch Postgres.
- KILL: if scoped passes (P2) breach serving-latency SLA without the split, stop
  scaling coverage until P1.2 lands.

### Phase 2 — Substrate quality (G1 rebuilt, metric swapped)
- **METRIC:** kill "80% of firehose". New primary metric = **query-conditional
  investigation recall**: for a gold set of ~20 real analyst queries (elections,
  disasters, conflicts, finance…), does Atlas have a clean thread answering each?
  Target: ≥80% of gold queries answered by a useful thread. Secondary: useful
  coverage % of the SUBSTANTIVE corpus (A0's denominator) + the honest floor,
  reported every run. Coverage stays a substrate-health metric, not the goal.
- **P2.1** Gold query set (the analyst-value yardstick + the eval harness seed).
- **P2.2** Scoped/regional + per-language passes (A2) — recall for mid-size real
  stories, gated on P1 capacity.
- **P2.3** Window pushes only to the measured plateau (A1); A4 cadence
  micro-optimization DELETED from the critical path.

### Phase 3 — Anomaly engine (G3 rebuilt on validated patterns)
Build order (domain-validated, formulas in the validation record):
- **P3.1 C4 novel relations** — generalize the PROVEN #234 rarity-weighted
  pattern: `score(a,b) = 1/sqrt(df(a)·df(b)) · log(1+c(a,b)) · source_diversity`,
  c() deduped at TOPIC level (kills syndication), diversity floor ≥2, exclude
  df=1 unless NER-verified, percentile threshold (top ~1%/7d), reason codes,
  label "first time in Atlas's corpus" (never "first time").
- **P3.2 C1 REDEFINED** — actor/category-level (never ephemeral topic — kills
  cold-start), input = distinct-(origin,outlet) volume (kills syndication),
  deseasonalized, ≥21-day eligibility ("new entrant" is a separate honest
  bucket), surprise_z percentile-thresholded. **Re-run the leading-indicator
  backtest on the corrected series BEFORE trusting it** (the raw version
  already failed 2026-07-03).
- **P3.3 C6 movement fusion (NEW, ~free):** flights/vessels/conflict feeds are
  ingested but viz-only (#232). Wire movement anomalies as leading triggers —
  the actual Bellingcat pattern; upstream of press, zero new ingestion.
- **P3.4 C7 voice-asymmetry detector (NEW):** formalize the LatAm-earthquake
  finding — high volume + language/origin concentration absent from the
  analyst's languages = standing under-the-radar flag. Built on the voice-mix
  infra no competitor has; operationalizes Pedro's anti-bias framing.
- C2 NOT rebuilt as specified (parked #172 negative) — its useful residue folds
  into C7 + per-keyword trends (a topic's OWN distinguishing keywords, never
  global top-N). C5 = a LENS over C1/C4 outputs (distant-from-focus ∩ flagged),
  never a standalone panel.
- **Validation (non-circular):** weekly pre-registered blind sample → web-
  corroborate (P0.2 lane) → classify artifact / real-but-mainstream / true
  under-the-radar; report precision honestly. KILL any detector <~30% eyeball
  precision. Plus retrospective replay of known under-covered cases with a
  shuffled-baseline negative control.

### Phase 4 — Vision layers (G4, guarded)
- 5W+H report, stance/framing, pin-carries-full-context, incremental
  constellation — per the vision doc.
- **HARD GUARDRAIL:** propagation/origin claims held until first-seen ordering
  beats the measured ingest-lag noise floor on a labeled case (ingest timestamp
  ≠ first utterance). Stance held until inter-annotator agreement clears a
  threshold. Until then: report sequence honestly as "first seen BY ATLAS".

## Deleted from v1 (low value / measured dead ends)
- The literal "80% of firehose" number (direction kept, metric swapped).
- C5 as a standalone workstream; C2 as specified; A4 cadence micro-opt;
  A3 multilingual OFF the wedge-test critical path (returns in Phase 2).

## Standing principles (unchanged)
Math/data first, LLM only for the brief (glass-box, cited). Honest floors are
results, not failures. Measure before build; kill criteria attached to every
phase. Engine-heavy work in isolated chats; consolidate to v3-intel-layer;
sync executed copies to ~/AtlasLocalWorker.

## First actions on resume (in order)
1. P0.4 A0 (the honest 3-way table) + P0.1 pick the marquee story — same sitting.
2. P0.2 corroboration lane v0 + P0.3 dates fix → generate THE report.
3. P0.5 cold-read (Frank) + analyst eyeball → steer.
4. P1.1 heavy-job mutex (one evening of ops).
5. P3.1 C4 novel-relations (the first anomaly detector, proven pattern).

## Phase X — Experience track (added 2026-07-11, runs PARALLEL, never blocks P0-P3)
Pedro's bar: the new Claude desktop shell — clean, smooth, professionally designed,
nothing "AI-made". Atlas today reads super-dense and hard to parse.
- **X.1 Resizable/movable panel grid** (revive #233 properly): drag/resize/rearrange
  console panels, persisted layouts, big-monitor presets (4K/60" wastes space today),
  without breaking the keep-alive/display-toggle architecture. → task_e03c57d5
- **X.2 De-densify pass**: hierarchy, whitespace, progressive disclosure, quieter
  chrome — reorganize how info is REVEALED, never remove it. → task_e03c57d5
- **X.3 Loading delight — SHIPPED 2026-07-11** (`9dc33602`+fixes, Fly+Vercel):
  shared `LoadingMoment` (procedural constellation + rotating facts, honesty-labeled
  measured/about-Atlas, reduced-motion aware) on app shell/Brief/universe/thread-
  hydration load states. Feed = `GET /api/v2/delight` (math-first templates over
  cheap aggregates, no LLM, Redis 15 min, per-fact guards) cached client-side in
  localStorage `atlas_delight_v1` → next load reads sync/offline; bundled evergreen
  facts = fallback. Deviation from spec, deliberate: live endpoint + client cache
  instead of nightly static JSON (M1 crons have died silently 3×; no delivery path
  to Vercel). Bundle delta ≈ +2 KB gz. → task_8a35aa03
Rationale: the wedge-test report sells the ANALYSIS; the experience track sells the
first 30 seconds. Both feed the same demo.

## Phase 2.5 — ACTOR/ENTITY QUALITY (named workstream, added 2026-07-11)
Pedro's standing question — "qué habla la gente, CON QUIÉN, por qué, dónde" —
decomposes into: QUÉ≈close (coverage healed), DÓNDE≈close (geo+voice), QUIÉN=
noisy, CON QUIÉN/POR QUÉ=unbuilt. The named blockers, in dependency order:
1. **Actor layer cleanup** (THE current bottleneck): "marea neagra"/"states
   states" as persons; trump missing from a NATO-summit thread's actors; junk
   actors leading CONFIRMED verdicts. Every relational feature (shared-actor
   edges, who-says-what, C4 novel relations, propagation) keys on actors —
   while actors are dirty, "with whom" stays mush. Levers: NER throughput +
   verified-path priority, junk-actor filters at serving, subject-typing broad
   set (person/org/place/phenomenon/system per the vision).
2. **Public voice volume**: press 166 / public 0 in the marquee report — "la
   gente" is currently a euphemism for "the press". Forum lanes exist but are
   starved; until they carry volume, press-vs-public is one-sided.
3. **Propagation/origin layer** (Phase 4, guarded) — answers "por qué/quién
   empezó"; buildable only after 1 (clean actors) and with the timestamp
   guardrail.
Honest position (2026-07-11): far in features, no longer far in foundations.
