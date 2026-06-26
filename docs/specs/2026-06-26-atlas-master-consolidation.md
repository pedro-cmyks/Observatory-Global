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
| `2026-06-26-l2-deep-review` | T2.2, T3.1, T3.2, T1.5 | A3/A4/B4/C3 rows done |
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
- [ ] **T1.5 B4 gate-recall by language (re-run).** Run the existing
  `gate_recall_by_language.py` on the current corpus; if non-English recall is
  the bottleneck (likely, per the CI/Peru cases), re-prioritize #162. *Spec:*
  L2 review B4. Measurement, not a build.

### Tier 2 — Public-attention / discussion depth
- [ ] **T2.1 Lead-time-vs-coverage.** "Seen in forum/search Nh before media
  coverage" — compute the discussion/attention timestamp vs the thread's first
  media signal. *Spec:* #237 §4 + #172 silent-risk. *Files:* `public_attention`
  service + thread serving.
- [ ] **T2.2 C3 — per-thread Public Attention.** A "Public Attention for this
  thread" block (trends/wiki/forum scoped to the thread, with the forum-vs-media
  sentiment already served). *Spec:* L2 review C3. *Files:* ThemeDetail +
  `useFocusRelation`.

### Tier 3 — Legibility / UX
- [ ] **T3.1 A3 scope strips.** A persistent `"Scoped to <X>"` strip with `✕` on
  NarrativeThreads + the stream header so silent re-scopes are legible.
- [ ] **T3.2 A4 first-click walkthrough.** 2-step `OnboardingCoachmark` teaching
  the select/deselect model once.
- [ ] **T3.3 #236 mobile visualization polish.** Phone-native per-surface (not a
  shrunk desktop) — the L2 tabbed IA is done; remaining is per-surface shaping.
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
- [ ] **T5.1 Instrument time-to-value.** One event: "user got a first useful
  answer" (opened a thread's evidence / generated a dossier). Flying blind today.
- [ ] **T5.2 Define the wedge user + job** in one sentence; put it atop CLAUDE.md
  + the Landing; cut features that don't serve it.
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
