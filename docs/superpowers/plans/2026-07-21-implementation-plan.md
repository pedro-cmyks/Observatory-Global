# Implementation Plan — chains + markets + time-axis + flywheel (2026-07-21, post-validation)

**Basis:** a 3-agent validation (2026-07-21) of everything built in the parallel sessions.
Specs: `2026-07-21-multi-hop-transitive-chains.md`, `2026-07-21-time-axis-versioned-relationships.md`.
Sibling: `docs/state/2026-07-21-analyst-journey-map.md`.

## State of play (validated)

| Track | Where | Verdict | Tests |
|---|---|---|---|
| **Chains** (walked constellation) | MERGED `v3-intel-layer @730787e2`, NOT deployed | **faithful** core, every LOCKED number exact | 26 backend + 13 vitest green, build clean |
| **Markets L4** | worktree `elated-jang-27881b @8a497fa2` (+2 uncommitted), NOT merged | **faithful** (descriptive slice under #226 STOP); honesty CLEAN | 5 pure green |
| **Flywheel** | MERGED `v3-intel-layer` | closed §2/§3.1/§3.5/§3.7 journey gaps | 49/49 pure libs |

**Two facts that gate everything:**
1. **This worktree (`sharp-williamson`) is 0 ahead / 46 BEHIND `v3-intel-layer` and
   contains NEITHER chains-v1 nor the flywheel.** The specs here were written blind to both
   merges. A naive build in this worktree would DOUBLE-BUILD `constellation_walk.py` /
   `WalkConstellation`. **→ rebase before any build (P0).**
2. **Markets has a data-loss clock:** the Yahoo free feed only serves a ~4-month rolling
   window; every day the accumulator is not running is **permanently unrecoverable** price
   history. **→ start it now (U1).**

---

## P0 — Precondition (do first)
- **P0.** Rebase this worktree onto `v3-intel-layer` (or just work on `v3-intel-layer`).
  Otherwise chains re-builds itself and time-axis re-solves compound focus.

## U1 — URGENT, data-loss clock (Pedro decision + go)
- **U1a.** Commit the 2 uncommitted markets files (`markets/accumulate_prices.py`
  `resolve_symbols()`, `scripts/run-markets-accumulate.sh` MARKET_SYMBOLS pull) — else the
  DB-driven symbol scaling is silently lost.
- **U1b.** Install + load `com.atlas.markets-accumulate` and confirm first fire
  (`launchctl list | grep markets-accumulate`, `LastExitStatus 0`). Backfills the ~4mo
  window on first run, then appends daily. **Every day not captured is gone forever.**

---

## Track A — Chains (v1 shipped; finish the 3 followups)
- **A1 (Pedro decision).** Deploy chains v1 (Fly + Vercel) → then run the **§8 live
  acceptance** on prod: ≥1 genuine cross-story primo at 2º–3º with receipt on a real pin,
  and self-termination at the hop-cap on BOTH a tight and a diffuse real seed (Phase-0b
  used dt-31; the built endpoint has not been re-measured live). Reversible via `ATLAS_WALK_*`.
- **A2.** Wire `app/services/overmerge.py` **membership-multimodality** as the blob
  discriminator behind/above the shipped **category-entropy first-pass** (`constellation_walk.py:186-217`).
  Spec §2.4 names multimodality "the measured discriminator"; entropy-only can miss the
  under-merged fusions the 2-means catches. (Reduced-fidelity today, sanctioned but incomplete.)
- **A3.** Mount `WalkConstellation` on the **full** DossierConnections / DossierView report
  surface (spec §4 says compact + full; today it's compact-only in WorkbenchConstellation).
  The `onNodeClick`/`onNodePin` handlers already exist on `InvestigativeUniverse` → small.
- **A4 (optional).** Micro-cleanup: hoist the constant `rel_floor·bfh` recompute out of the
  `max_product_walk` loop (`:269`). No behavior change.
- **NOT to build:** clickable + pinnable walked nodes — **already DONE** by the flywheel
  (`pinKin → addPin`, retrievalLane `constellation-walk`). Remove from scope.

## Track B — Markets (faithful; merge + harden; deep part deferred)
- **B1.** (see U1a) commit the 2 files.
- **B2.** Merge markets → `v3-intel-layer` (low-conflict: `markets/` net-new, mig 088 is the
  correct next number, trivial `main_v2.py` import + additive `App.tsx`/`BriefNewspaper.tsx` wiring).
- **B3.** Add a backend contract test for `/api/v2/markets` (world / country / degraded
  shapes; `relation_status` stays `pending-validation-226`) + a couple of vitest tests
  locking the honesty-state rendering (dark relation slot, `price_pending` em-dash,
  degraded ≠ empty) — keeps the descriptive-vs-#226 boundary from eroding.
- **B4.** Verify prod `/api/v2/threads` returns `category` + `subject_countries` (the
  news-intensity substrate reads them; if absent it accumulates empty silently).
- **B5 (optional).** Run `build_country_universe.py` → emit migration 089 (all countries) +
  `country_universe_verified.json`; review before applying. (Today only US/CO/BR/MX + world basket.)
- **DEFERRED to #226 re-run (~Oct), substrate already laid:** the co-movement event STUDY
  that writes `comovement_result`, the reverse market→news study, and the market-`<SYMBOL>`
  node integration into the engine graph (dossier/universe/focus/movement) = the
  **bidirectional discovered axis**. Empty skeleton tables (`comovement_result`,
  `market_relation_public`) + both accumulation substrates are in place and dark.

## Track C — Time-axis (design done; build; compound-focus dep MET)
Its own spec (`2026-07-21-time-axis-versioned-relationships.md`). Sequence AFTER chains lands.
- **C1.** Edge-snapshot store (persist the derived edge set + degree + weight + basis + the
  entity backbone per pass; centroids already snapshot in `emergent_clusters`).
- **C2.** Versioned edges + **churn-vs-narrative** labeling via the two-layer anchor
  (`identity_key` + entities).
- **C3.** Replay (ambient — extend `map/replay` to EDGES) + Diff (focused — lives IN the
  activity timeline; one time-state, scrubber re-labels at the transition).
- **C4.** Combined chart: diverging volume bars (sentiment by position) + rarity-normalized
  key-subject lines + voice-mix band; NO marker layer; churn label in the line-endpoint hover.
- Universal: every focus type (thread/country/person/theme/anomaly/subject) gets the timeline.

## Track D — Flywheel remaining (journey gaps still OPEN; shared substrate)
The flywheel shipped several PURE, TESTED libs with **zero UI consumers** — these are the
remaining journey-map gaps, and D1 is the primitive chains + time-axis both need:
- **D1 (high leverage).** Wire `launcherVerbs.ts` → make coverage-gap / cross-read-tension /
  contested-figure / lead into **clickable seeds** (journey §3.3). This is the shared
  "make-it-a-launcher" primitive that **chains' `primo`s and time-axis' latent/dormant
  relationships plug into** — do it once, reuse thrice.
- **D2.** `navParams.ts` carry-context (journey §1/§8): the missing `q`-param + label; closes
  the L1↔L2 category-click intent drop and the asymmetric return trip.
- **D3.** Globe `◆` capture (journey §3.5): `EqualEarthMap` still has zero pin affordance.
- **D4.** `briefRelationDetector` surfacing: render "these pins connect to today's Brief on X."
- **D5.** LEADS self-advance (journey §3.4): pinning a lead should navigate + re-run `find_leads`.
- **D6.** Mobile flywheel (journey §5): FrameStrip desktop-only; Brief→thread→close one-way.

## Cross-cutting
- **X1.** Reconcile the relation VOCABULARY before any surface renders several together:
  `text`/`context` (briefRelationDetector) vs `hermano`/`primo Nº` (chains) vs
  `latent`/`dormant` (time-axis) → ONE honesty-labeled scheme.
- **X2.** Visual-verify: `WorkbenchConstellation` now STACKS two renders (`InvestigativeUniverse`
  compact + `WalkConstellation`) — confirm it doesn't read as two competing pictures (§1.5
  commits to one radial grammar).

---

## Suggested sequence
1. **P0 rebase** + **U1 markets accumulator** (URGENT, run in parallel — U1 has the clock).
2. **Track A** finish chains (A1 deploy + live acceptance, A2 blob multimodality, A3 full mount).
3. **Track B** merge + harden markets (B1–B4).
4. **D1 launcher primitive** — unblocks chains `primo`s + time-axis latent relations.
5. **Track C** time-axis build (C1–C4).
6. **D2–D6** remaining flywheel + **X1/X2** cross-cutting.

Deferred by design: markets bidirectional discovered axis → #226 re-run (~Oct); substrate ready.
