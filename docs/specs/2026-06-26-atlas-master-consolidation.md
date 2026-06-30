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

## 1. Source-spec → close map

A source spec closes when all its rows below are `[x]`.

| Source spec | Remaining items here | Closes when |
|---|---|---|
| `2026-06-26-truncated-narrative-thread` | T1.3, T1.4 | both done |
| `2026-06-09-research-thread-builder-workbench` | T1.1, T1.2 (Phase 4) | Phase-4 row done |
| `2026-06-24-community-signal-layer` (#237) | T2.1 | T2.1 done (Phase-2 forum stays deferred by design) |
| `2026-06-26-l2-deep-review` | T2.2, T3.1, T3.2, T1.5 | A3✅ A4✅ C3-forum✅ (C3b trends/wiki deferred); B4 gate-recall re-run pending (gate-adjacent) |
| `2026-06-11-surfaces-editorial-review` (#225) | T3.4 (gap box) | done — *body already executed; close on read* |
| `2026-06-12-l2-l3-deep-review` | — | **closeable now** (executed; #227 closed) |
| `2026-06-25-mobile-multilevel-review` | T3.3 | done — *IA executed; close on read* |
| `2026-05-23-ai-assisted-taxonomy` (#204) | T6.1 | T6.1 done |

Foundational/living (do NOT close — they evolve): `living-narrative-threads`
(Paper 4), `atlas-focus-model`, `atlas-narrative-intelligence-framework`,
`voice-relation-plan`.

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

- [ ] **T1.6 Engine attention + anomaly→movement roles (the 5-brains fix).**
  Post-consolidation (2026-06-30): the unified engine closed 3 of the split-brain's
  5 pipelines; add the last 2 — `attention` (wiki/trends → topic centroid,
  verified=false; subsumes C3(b)/T2.2) + `anomaly→movement` (per-topic
  volume-baseline; retires the orphaned country-anomaly-as-lead = the CI
  fake-disaster + finding E). Closes the §3 split-brain at the root; makes #168
  types real. *Spec:* `2026-06-30-atlas-engine-attention-anomaly-roles.md`
  (executable, phases G0–G4; heavy steps off-peak). *Decisions pending Pedro:*
  D1 (member-ref schema vs separate table), D2 (attention in ranking?), D3
  (movement replaces vs augments country anomaly). *Papers:* 1/3/7.

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
