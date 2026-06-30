# Master Spec — Atlas Open-Spec Consolidation

Date: 2026-06-26 · Branch: `v3-intel-layer` · Status: DRAFT for Pedro's review.
Author: Claude (Opus 4.8), from the spec-driven verification sweep of the full
open-spec corpus.

> **Purpose.** One spec that gathers the REMAINING actionable work scattered
> across the open specs into themed, attackable tiers — so we attack *this* doc
> and each source spec **closes** when its items here are checked off. This is a
> consolidation/roadmap, not new design: every item traces to an already-approved
> spec + issue.

---

## 1. Source-spec → close map  ·  **VALIDATED 2026-06-30** (each claim checked vs code/live, not trusted)

| Source spec | Validated status (2026-06-30) |
|---|---|
| `2026-06-26-truncated-narrative-thread` | ✅ **CLOSED** — T1.4 SignalDetail "Where this fits" (`connected_threads`) verified LIVE this session (RELATED 86% + Semantic Neighbors, GDELT collapsed); T1.3 done. |
| `2026-06-09-research-thread-builder-workbench` | ⏳ **OPEN** — Phases 0.5/1a/1b/2 shipped, but **Phase 4 (T1.1 who-says-what dossier + T1.2 evidence-quality/Paper-1 benchmark) NOT done.** Stays open. |
| `2026-06-24-community-signal-layer` (#237) | ⏳ **OPEN** — forum lane shipped, but **T2.1 lead-time-vs-coverage NOT done.** Stays open. |
| `2026-06-26-l2-deep-review` | 🔵 **LIVING** — A3/A4/C3-forum/B4(T1.5) done, C3b deferred; now also carries the live connectivity audit + the unified-engine 5-brains analysis. Keep open as the L2 reference. |
| `2026-06-11-surfaces-editorial-review` (#225) | ✅ **CLOSED** — Brief L1 rebuild verified (`lib/briefLead.ts` + `Briefing.tsx`, commits `3369e29`/`ae855f4`, no Math.random template essays). T3.4 gap box → tracked at #172/#145. |
| `2026-06-12-l2-l3-deep-review` (#228) | ✅ **CLOSED** — verified: SignalDetail rebuild, `AtlasHeatList.tsx` mounted, `rank_key_people` wired (`thread_packet.py`). #227 closed. |
| `2026-06-25-mobile-multilevel-review` (#236) | ✅ **CLOSED (IA)** — tabbed IA (Map/Threads/Stream/Pulse, `App.tsx:2092` mobile-tabbar) verified LIVE this session. Per-surface polish ongoing in T3.3 (not a re-open). |
| `2026-05-23-ai-assisted-taxonomy` (#204) | 🔵 **LIVING** — v2 reject gate + gold base 2,134/κ0.775 shipped (engine chat); gold-growth pass + quarterly revision ongoing. Keep open. |

Foundational/living (do NOT close — they evolve): `living-narrative-threads`
(Paper 4), `atlas-focus-model`, `atlas-narrative-intelligence-framework`,
`voice-relation-plan`, plus the engine specs (`2026-06-29-atlas-*`,
`2026-06-30-atlas-engine-attention-anomaly-roles`).

---

## 2. The work, by theme

### Tier 1 — Finish the "Atlas accounts" moat (evidence honesty)
- [ ] **T1.1 Who-says-what + frame comparison in the dossier.** Enrich
  `PinSnapshot.evidence` with framed source rows (source · stance · sentiment) at
  pin time; the DossierView sections then populate. *Spec:* research-workbench
  Phase 3 deferred + Phase 4. *Files:* `lib/workbench.ts` (snapshot shape),
  `ResearchPlanPanel`/`ConnectionsSection` (capture), `DossierView`.
- [ ] **T1.2 Phase-4 evidence/frame quality bound to Paper 1.** Benchmark
  evidence-role precision (≥85% direct vs context/noise on a reviewed sample);
  confidence bands; syndication/duplication detection surfaced. *Spec:*
  research-workbench Phase 4. *Paper:* 1.
- [x] **T1.5 B4 gate-recall by language.** ✅ Measured (`docs/research/gate-recall/
  2026-06-26-...`). FINDING: en kept_rate 0.33 (strict for all); detected
  non-English barely ENTERS scoring (fr=4, es=7 scored) — the bottleneck is
  upstream English-centric ASSIGNMENT, not gate bias; the real bias is the `xx`
  bucket (6921 scored, 0.10 kept). Fix = semantic assignment (T2 route, language-
  agnostic) + #162, NOT per-language gate recalibration. Paper 1 = English-
  conditioned caveat.

- [ ] **T1.6a Engine RECALL (#229) — the lead engine lever. SPEC WRITTEN 2026-06-30:**
  `2026-06-30-atlas-engine-recall-scoped-clustering.md` (executable, phases
  R0–R3, evidence-grounded). Measured: only **13,354 of 239,233 embedded signals
  land in a topic = 5.6%**; per-country **<1%** even for 24K-signal countries
  (US 24,709→136, CN 8,720→4). Bottleneck = clustering assignment (global HDBSCAN
  drops ~94% as noise), NOT embedding or promotion. Lever = **scoped passes** over
  the persisted corpus (partition by country — 15+ countries have 5K–29K embedded,
  US 28,847 = the R0 test case — cluster within, merge + #224 anchor-guard).
  Fixes the L2 §3 split-brain at the ROOT (CI gets a topic). Heavy → STRICTLY
  off-peak M1; R0 measures one country first before any cron change.
- [ ] **T1.6b Taxonomy precision (#204) — the measured ceiling.** F3.2b: shared
  members 40–52% on-topic by LLM judge = the dominant precision lever, NOT the
  engine. Gold base 2,134/κ0.775 shipped; gold-growth pass (lift gate balanced
  61.5%→~80%) pending off-peak. Pairs with T6.1.
- [ ] **T1.6c Engine `anomaly→movement` role (cheap honest win).** Per-topic
  volume-vs-baseline as a topic property (countable from `topic_members`, ships
  WITHOUT the #232 event-ref blocker). Retires the fake *lead* (below-gate thread
  shown critical); leaves the honest coverage gap (does NOT fix CI root — that's
  T1.6a). *Spec:* `2026-06-30-atlas-engine-attention-anomaly-roles.md` §2.2/G2.
- [ ] **T1.6d Engine `attention` role — HOLD (data-gated).** wiki/trends → topic
  centroid, `verified=false`. Self-eval: only binds to the 68 topics + wiki is
  thin (1700/7d/17c) though trends has volume (24.9K/24h/99c). Build the trends
  half AFTER recall (T1.6a); skip wiki until #104. Do NOT run the hot-PK migration
  for this yet. *Spec:* same, §2.1/D1.

### Tier 2 — Public-attention / discussion depth
- [ ] **T2.1 Lead-time-vs-coverage.** "Seen in forum/search Nh before media
  coverage" — compute the discussion/attention timestamp vs the thread's first
  media signal. *Spec:* #237 §4 + #172 silent-risk. *Files:* `public_attention`
  service + thread serving.
- [~] **T2.2 C3 — per-thread Public Attention.** FORUM lane SHIPPED: backend
  `GET /api/v2/public-attention?thread=dynamic-topic-<id>` returns social-lane
  discussion that is a SEMANTIC neighbor of the thread centroid (signal_embeddings
  ANN, language-blind), always `verified=false`/discussion, degrades to empty when
  no centroid/embeddings. ThemeDetail renders "PUBLIC ATTENTION · THIS THREAD"
  (DISCUSSION · UNVERIFIED badge, subreddit + similarity %, translatable headline)
  for dynamic-topic threads only. *Files:* `public_attention.py` service+router,
  `ThemeDetail.tsx`, CSS. REMAINING — C3(b) semantic (not lexical) trends/wiki
  match: **DEFERRED (Pedro 2026-06-30).** Today still lexical `/trends/match`+
  `/wiki/match` (GDELT-theme-code → ~dead for dynamic threads). Deferred because
  trends/wiki coverage is thin/stale (#104 cloud-IP rate-limit → low ROI) and
  the live path embeds ~100 candidates per ThemeDetail-open on the shared Fly
  embed box; the cheap pre-embed-in-cron path touches the reserved
  AtlasLocalWorker tree. Pick up when #104 improves coverage OR pre-embed
  trends/wiki off-peak (see l2-deep-review §"Execution status" impl note).

### Tier 3 — Legibility / UX
- [x] **T3.1 A3 scope strips.** ✅ "Scoped to <X>" strip with `✕` on
  NarrativeThreads (country + person focus → clearCountryFilter/setPerson(null),
  replaced the silent "filtered by quality gates" notice) + the stream-slot header
  (blank SignalStream scoped to active country/person → clearAll). *Files:*
  `NarrativeThreads.tsx`+css, `App.tsx`+`App.css`. Build+types+tests green;
  browser eyeball pending (port-3000 busy in another session).
- [x] **T3.2 A4 first-click walkthrough.** ✅ 2026-06-30. New
  `CountryFocusWalkthrough.tsx` (NOT OnboardingCoachmark — own component, reuses
  the `.onboarding-*` chrome) fires once on the first `handleCountryClick` (own
  `atlas_country_walkthrough_v1` key, guarded so it never stacks on the
  first-session tour). 2 steps teaching select → deselect; step 2 highlights the
  focus-chip ✕ on desktop. Mobile-essentially-different (Pedro): centered card
  (`cfw-card-mobile`, NOT the bottom sheet — it collided with the tab bar +
  floating chip) + tab-model copy ("opened in the Stream tab… Map/Threads/Pulse
  re-scoped", "Tap ✕ above the tabs"). Browser-verified desktop (1440) + mobile
  (375). *Files:* `CountryFocusWalkthrough.tsx`+css, `App.tsx`, `FocusIndicator.tsx`.
- [~] **T3.3 #236 mobile visualization polish.** Phone-native per-surface (not a
  shrunk desktop) — the L2 tabbed IA is done; remaining is per-surface shaping.
  Progress 2026-06-30: A4 walkthrough given a mobile-native treatment (centered
  card + tab-model copy, above). **CountryBrief "Top Publishers" — two passes:**
  (1) was a dead `<div>` (`onSourceClick` received but unused as `_onSourceClick`);
  (2) Pedro: the panel-jump was inconsistent with the rest — now matches
  ThemeDetail's EXPAND pattern (click → recent coverage headlines inline + "Full
  source profile ↗" → SourceProfile). Verified live (manilatimes.net → 8 inline
  headlines, no panel-jump). *Files:* `CountryBrief.tsx`+css.
- [ ] **T3.4 Brief gap box (#172/#145).** The reserved "what Atlas can't answer"
  box on the Brief. *Spec:* surfaces-editorial.

### Tier 4 — Processing reliability (the moat's delivery)
- [x] **T4.1 Embed-service uptime (#240).** ✅ `embed-service-watchdog.sh` +
  launchd `com.atlas.embed-watchdog` (15-min) restarts the MAIN nlp_worker if it
  stops (never the standby). Installed + verified ('embed-service up').
- [~] **T4.2 Embed throughput steady-state (#241).** 10x parallel-write fix
  SHIPPED; validation = the next nightly drain (pending, not a build).
- [ ] **T4.3 NER throughput (#184).** Adaptive M1 fleet shipped; flip typed
  subjects unverified→verified as coverage grows; multilingual NER (#162).

### Tier 5 — Demand side (founder-review pivot — NOT a spec, but the real risk)
- [x] **T5.1 Instrument time-to-value.** ✅ `telemetry_events` (mig 056) + POST
  /api/v2/telemetry (best-effort) + `lib/telemetry.ts`. Wired: app_open,
  thread_open, dossier_generated, once-per-session first_value_moment. Verified
  live (app_open firing from prod).
- [x] **T5.2 Define the wedge user + job.** ✅ Pedro chose "all four" personas;
  unified into ONE wedge (the *narrative analyst* — journalist/OSINT/desk/policy)
  whose job is honest situational awareness on a specific event/topic/country.
  Written atop CLAUDE.md as the operational guide + anti-goal. (Landing marketing
  copy = a small follow-up.)
- [ ] **T5.3 Persist→deliver→alert loop.** Accounts + one saved watch + one alert
  — converts a browse tool into a returning product. *Spec:* product-gap doc.

### Tier 6 — Paper-adjacent / later
- [ ] **T6.1 #204 LLM-assisted taxonomy revision** (quarterly label quality).
- [ ] **T6.2 Movement→narrative inputs (#219 Kalman, #232 vessels/aircraft/
  conflict, #226 markets).** Make the viz-only layers feed threads. Paper 3/4.

---

## 3. Recommended attack order

1. **T4.1 + T4.2** (embed uptime + drain) — the moat is honesty/connectedness;
   it's worthless if the pipeline is down. Cheap, high-leverage. *(½–1 day.)*
2. **T5.1 + T5.2** (instrument + wedge) — the founder review's verdict: we're
   demand-blind. One event + one sentence unblocks every later prioritization.
3. **T1.5 B4 gate-recall** (measurement) — tells us if the gate honesty claim is
   English-only; one experiment, big paper + product implication.
4. **T2.2 C3 + T3.1 A3** — the two highest-felt UX/depth items.
5. **T1.1 who-says-what + T1.2 Phase 4** — finish the dossier + the evidence-
   quality moat (bound to Paper 1).
6. **T5.3 persist→deliver→alert** — the real product build (accounts/watch/alert).
7. **T6** — paper-adjacent, when the above lands.

## 4. Out of scope (explicit)
- #237 Phase-2 human-contribution forum (needs a userbase Atlas lacks).
- A 5th map layer / 6th source family / new surface — the founder-review
  anti-goal. No new capability until T5.1 produces a usage signal.

## 5. Self-review
- *Coverage:* every open spec's remaining item is a row in §2 + a close-trigger
  in §1. Review docs whose work shipped are marked closeable.
- *Traceability:* each item names its source spec + issue.
- *Honest scope:* T5 (demand) is flagged as the real risk even though it has no
  prior spec — the founder review surfaced it.
