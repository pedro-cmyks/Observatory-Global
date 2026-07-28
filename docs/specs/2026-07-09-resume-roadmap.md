# Atlas resume roadmap v2 — validated + corrected (2026-07-10)

## 2026-07-30 STATUS — Phase 2 metric LIVE; engine levers measured
Phase 2 below (P2.1/P2.2/P2.3) reads as not-yet-started. It is stale: the metric was
built, run twice, and followed by a full engine-lever measurement campaign. Ground
truth: CLAUDE.md top two blocks (2026-07-27, 2026-07-28..30); `docs/research/gold/`;
`docs/research/recall-229/`.

1. **P2.1 gold query set — DONE.** 20 anti-circular queries from RAW `signals_v2`
   headlines (never a `dynamic_topics` label), 6 negative controls that PASS on honest
   absence (`docs/research/gold/gold-query-set-v1.json` + `2026-07-27-gold-query-set-v1.md`).
   Harness `run_gold_query_eval.py`. **API-arm baseline: 7–14% answer rate (n=14,
   ±7pp/query)** — 07-27 run 14% (`2026-07-27-gold-query-eval.md`), 07-28 re-run 7% with
   labels restored (`2026-07-28-gold-query-eval.md`, `2026-07-28-rerun-comparison.md`);
   the label-blackout-confounder hypothesis was REFUTED by the re-run. **UI-pilot arm**
   (6 of 20 queries, real UI not curl): **40% answer / 0.67 honesty** vs the same 6 on
   the API arm (20% / 0.00) — `2026-07-30-ui-walkthrough-pilot.md` + content-first
   rubric `rubric-v2-ui.md`. Full-20 UI run IN FLIGHT, not yet landed. **STILL OPEN
   (Pedro):** his 5 hand-written + 5 external-agenda queries — the set has an
   ingestion-gap blind spot (#235) it cannot see without them.

2. **Engine-lever refutation campaign — 4 pre-registered kills + 1 in flight**
   (`docs/research/recall-229/`, every gate written before the run): whitening at the
   identity layer (anchor gap −0.547, destroys cross-lingual same-event pairs) ·
   evidence-overlap merge-to-fixpoint (NO-GO, 96.2% connected component — but
   REHABILITATES the SHIPPING cos≥0.90∧label≥0.80 rule, K2-safe, halves witness
   fragmentation) · DeepSeek judge-as-confirmer (dead at volume, 2.4×–1117× the nightly
   cap) · `used_t` removal (NO-GO, 2,247 false absorptions; **named the real disease:
   argmax dispersion — same-event fragments don't share a top-12 nearest-topic pick,
   today 11/54**). 5th gate (cluster-consolidation pre-projection under the surviving
   SHIPPING rule) IN FLIGHT at write time.

3. **Live fixes landed from the campaign** (see CLAUDE.md 07-27/07-28..30 for commits):
   L1 seal resilience (nullable label + `SNAPSHOT_UNLABELLED` counted, never silently
   dropped) · `/api/v2/stats` honesty (null + `degraded_metrics[]`, no fabricated 0) ·
   person-timeline rebuilt on mig-090 trigram (cost 319,329→3,020) · `/attention/eclipse`
   cached (24s→0.5s) · edge-snapshot weight clamp [-1,1] + atomic writes + 07-25 gap
   deleted honest · silent-risk endpoint deleted (−478 lines) · `/api/v2/universe`
   build/serve split, mig 091 (0%→200 in ~2.8s) · GDELT+RSS entity-decoding (#264 closed,
   both lanes) · `_norm_headline` non-Latin fix (Cyrillic/Arabic/Farsi dedup was reading
   digits only) · umbrella orphan-swallow fixed (`hydrate_topics` excludes umbrellas from
   matching) · trigram planner mis-estimate fixed via extended statistics (mig 092;
   index-stats-target tried first and REFUTED — partial-index stats are invisible to the
   planner) · `fetch_topic_centroids` full-pool fix (was serving ~3.7% of topics) ·
   ivfflat probes 20→10 + named `ann_timeout` degradation (was silent `[]`).

4. **Where the metric says the bottleneck is now:** NOT ingestion volume, and NOT
   retrieval-by-API-protocol — the UI pilot finds MORE than the frozen harness, not less
   (GQ-02 Berlin Pride: 0 via API, 2 via UI — the story sat in 5 labelled threads the
   search bar found on the first keystroke). Real bottlenecks: **fragmentation** (one
   event, 8 live threads for the France/Spain wildfires, no surface says so) and the
   **identity-layer geometry** (raw e5 cosine overlaps same-story/different-story
   distributions — shreds one event into 8-33 clusters AND lets stale identities absorb
   unrelated ones), plus a **UX-defect list**: invisible auto-scope silently
   empties/hides thread detail, systematically wrong category chips on every receipt,
   NAV-LOSS between search's related-thread list and the detail panel it opens.

---

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
- **P0.1 Marquee dogfood — ✅ DONE 2026-07-10** (`c6b7bdf4` NATO-Ankara marquee
  dossier, `docs/research/flagship/`): investigation built on the current
  engine; the run exposed 3 defects that became the week's fix list.
- **P0.2 Corroboration lane v0 (G2 pulled forward) — ✅ DONE 2026-07-10 (manual
  run, `01148f88`):** deep-research harness over NATO-Ankara thesis + pinned
  actors, independence-weighted — all 4 Atlas claims established; two-sided
  coverage asymmetry found (Erdoğan-framing vs Trump-drama). Productized as the
  P0.6b in-product button 2026-07-12 (see v2.1 below).
- **P0.3 Dates fix (Frank-test debt) — ✅ SHIPPED 2026-07-12** (`cbac24c1` fix
  #3): frozen evidence carries signal date ("— outlet, Jul 8" in report +
  export), synthesis receives dated evidence, header + pin cards show story
  window (first_seen → last activity).
- **P0.4 A0 measurement — ✅ SHIPPED 2026-07-09** (`b2bab22b`
  `a0_coverage_split.sql`, repeatable): 3-way split useful-story / junk-typed /
  unassigned, unassigned split into syndication-dup ‖ junk-headline ‖
  real-unclustered. Fed the useful-coverage gate
  (`docs/state/2026-07-09-useful-coverage-gate.md`).
- **P0.5 Show it — Frank v2 RUN 2026-07-10** (`b69bdfc3`): verdict
  usable-with-caveats + 6 precise blockers — all 6 fixed same week
  (`cbac24c1`). Editor-persona loop continues under P0.6; real-analyst eyeball
  still pending.
- KILL/PIVOT: if independence-clustered corroboration collapses to ≈1 source
  (all wire), pivot corroboration to curated high-independence source lists.

### Phase 1 — Infra split (the constraint)
- **P1.1 NOW (cheap):** heavy-job mutex — clustering/embed/flag jobs never run
  concurrently against serving; stagger crons; keep serving queries light.

  **SHIPPED 2026-07-12 (`scripts/heavy-job-lock.sh` + serving-side
  degradation + G5 UI).** Fourth incident of the week forced it: `GET
  /api/v2/signals` returned raw 500 `TimeoutError` (Supabase statement
  timeout) whenever M1 batch jobs (embed cron 17:30/23:30/05:30, scoped/
  emergent clustering, matview refresh, goldgrowth, hot-cold catchup) hammered
  the shared DB at once. Prior victims: the dataviz audit, the A0 measurement,
  the research plan — same root cause each time (concurrent batch load →
  serving statement-timeout → 500). Three-layer fix:
  1. **Mutex** — atomic-mkdir lockfile shared by ALL six heavy runners (macOS
     has no flock). `atlas_heavy_lock <job> <wait|skip> [ttl] [wait-max]`.
     Snapshots/embed/goldgrowth/catchup QUEUE (wait); matview SKIPs (its 30-min
     cadence self-heals). One heavy DB job at a time — never two concurrently.
     Stale-lock recovery: dead-PID → reclaim; age > TTL → reclaim + LOUD log
     (a legit job past TTL is itself the incident to surface). Verified: skip,
     release, dead-PID reclaim, TTL reclaim, and end-to-end through the real
     matview runner (skips + exit 0 + holder's lock preserved).
  2. **Serving degradation** — `main_v2.py` global exception handlers map
     asyncpg `QueryCanceledError` / `TimeoutError` / pool-saturation errors to
     an honest **503 `{"reason":"db_busy"}`** (Retry-After: 10) instead of a
     raw 500. Flows back through rate-limit + CORS cleanly (the rate_limit.py
     traceback was just the propagation path, not the fault). 5 pytest.
  3. **G5 error ≠ empty (UI)** — SignalStream + NarrativeThreads now
     distinguish a fetch failure (503/500/network) from an honest empty-200:
     amber "feed unavailable — retrying" with exponential backoff (SignalStream
     3→30s) instead of a fake "No signals found" / "No active narratives".
     UniverseView already rendered "unavailable (reason)" — left as-is.

  **Stagger analysis (why no plist time-shift was needed):** the mutex makes
  exact-minute coincidence SAFE by construction (matview skip-mode; heavy
  calendar jobs queue), and wall-clock-staggering an interval-based matview
  (`StartInterval 1800`, phase = launchd-load-relative, non-deterministic)
  against calendar jobs is unreliable. Among the six mutex jobs no two share an
  identical trigger minute; any window overlap is serialized. Intentionally
  LEFT UNLOCKED: the 30-min atlas-topic-classifier (gate-scoring is the
  serving-freshness cadence — must not queue behind a 1.5h snapshot) and
  3vendor-calibration (API/LLM-bound, tiny DB sample). Known cost: during the
  nightly scoped snapshot (~1.5h) matview skips ~3 refresh cycles →
  country_hourly_v2 + person_vocab up to ~1.5h stale off-peak — an acceptable
  trade vs serving 500s. Runners synced to ~/AtlasLocalWorker.
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
- **X.1 Resizable/movable panel grid — ✅ SHIPPED 2026-07-11** (`55e58722`, #233
  CLOSED): react-grid-layout v2 grid (drag by header, SE resize), layout
  persisted per width bucket (laptop/desktop/big ≥2400 — big = 4 full-height
  columns), reset in ··· menu; keep-alive holds by construction (RGL transforms,
  never unmounts). Pure model `lib/consoleLayout.ts`, 14 vitest.
- **X.2 De-densify pass — ✅ SHIPPED 2026-07-11** (`521bd79d`+`78e08097`):
  batch A quieter chrome + big-monitor type scale (≥2200, scoped under
  `.terminal-layout-grid`, not `:root`); batch B thread rows summary-first with
  hover/focus progressive disclosure (≤768 / hover:none keeps all visible).
- **X.3 Loading delight — SHIPPED 2026-07-11** (`9dc33602`+fixes, Fly+Vercel):
  shared `LoadingMoment` (procedural constellation + rotating facts, honesty-labeled
  measured/about-Atlas, reduced-motion aware) on app shell/Brief/universe/thread-
  hydration load states. Feed = `GET /api/v2/delight` (math-first templates over
  cheap aggregates, no LLM, Redis 15 min, per-fact guards) cached client-side in
  localStorage `atlas_delight_v1` → next load reads sync/offline; bundled evergreen
  facts = fallback. Deviation from spec, deliberate: live endpoint + client cache
  instead of nightly static JSON (M1 crons have died silently 3×; no delivery path
  to Vercel). Bundle delta ≈ +2 KB gz. → task_8a35aa03
- **X.4 Dataviz honesty audit (added 2026-07-11, `d82173ee`) — PARTIAL:** expert
  audit `docs/specs/2026-07-11-dataviz-expert-audit.md` (findings ranked
  misleading > illegible > wasteful, code-cited); 3 smallest fixes applied
  (legend heat gradient mirrors map alphas; unknown source family → honest
  'Unclassified' badge; whole-percent confidence). REMAINDER in the audit doc:
  degenerate 90/100% confidence encoding, unlabeled count lineages (92/544/107),
  rainbow heat-ramp luminance inversion.
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

## v2.1 (2026-07-11) — the objective SHARPENED: publishable-as-news dossier
Pedro: "el objetivo de Atlas es entregar un dossier que sirva para PUBLICARSE
como una noticia" + the deep wish: "cómo nos conectamos, qué mueve el mundo en
verdad, si algo diverso está pasando". Two products in one sentence: (A) the
PUBLISHABLE ARTIFACT, (B) the DISCOVERY ENGINE that feeds it. Alignment check
ran ~85%; three corrections:

1. **P0.6 — the PUBLISHABLE bar (new exit criterion).** "Usable-with-caveats"
   is not the goal; "an editor would publish it with a byline" is. Two builds:
   (a) **narrative synthesis** ✅ SHIPPED 2026-07-12 (`3818eb25`, deployed
   Fly+Vercel) — dossier-synthesis-v2: lede → cited body (every claim ends with
   an inline [n] receipt; citations resolved SERVER-SIDE against the
   request-built numbered evidence table, an invented receipt can never enter)
   → "what we don't know" (carries the coverage lens + metadata-only +
   isolated/text-linked caveats); browser-verified on NATO-Ankara 3-pin, cold
   editor: publishable with minor edits; (b) **in-product corroboration ✅
   SHIPPED 2026-07-12** (`027db2a9`) — CORROBORATE button in dossier +
   workbench: per pin 1-2 focused queries → GDELT DOC 2.0 (free) →
   independence weighting (syndicated copies collapse; outlets counted, not
   articles) → status established/contested/unverified + linked citations +
   coverage-asymmetry note (only LLM use, glass-box); carried into MD export,
   degrades honestly when search path unavailable. Validated on NATO-Ankara:
   all 3 pins ESTABLISHED. Frank loop continues with an EDITOR persona;
   exit = a cold editor says "publishable with minor edits".
2. **P3 reorder — C7 (voice-asymmetry) FIRST, with C4.** Cheapest detector,
   unique infra (voice-mix), directly answers "algo está pasando que no veo",
   and every C7 hit is itself a publishable story (proven by hand on NATO-Ankara:
   mainstream told Trump-drama, the multilingual set told Erdoğan-centrality).
   Then C4 → C1-redefined → C6.
3. **Promotion gap = named workstream (P2.4):** engine assigns ~52% of 24h
   signals but only ~10% reaches ACTIVE served threads. Diagnosed (A0), not
   owned. A gate recalibration, not architecture — doubles what the user sees.

Standing honest answer to the deep wish: Atlas measures the INFORMATION SPHERE
(global press + thin public lanes). "What really moves the world" is INFERRED
from coverage dynamics (C7: who speaks/who is silent), anomalies (C4/C1), and
propagation (P4) — and Atlas's structural honesty is that it LABELS the proxy
instead of selling it as ground truth. That labeling is itself the product.
