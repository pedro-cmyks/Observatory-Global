# L2 Deep Review — the Console, plus the layer-connectivity map

**Date:** 2026-07-05 (madrugada — closes the three-surface review: L3 → L1 → L2)
**Status:** REVIEW COMPLETE → WORK SPEC (§6). Pending Pedro's read + decisions (§7).
**Method:** 3 exhaustive sweeps (console surfaces, backend serving layer,
docs/issues/telemetry) synthesized against the two PRIOR L2 reviews (06-12,
06-26) and the 07-01 foundation audit. L2 is the most-reviewed surface in
Atlas; this review's job is different from L3/L1's: verify the repairs held,
name what is STILL structurally open, and draw the inter-layer map Pedro asked
for.

---

## 0. Verdict in one paragraph

L2 is the **healthiest of the three surfaces** — because it has been reviewed
and repaired twice already. The 06-26 split-brain (alert layer ↔ evidence layer
never reconciling) is fixed at the serving seams (A1-A4 legibility, B1-B3
honesty, C1-C3 forum lane all SHIPPED and verified); the map is Equal Earth;
the universe view became the spatial index; focus propagation (#234) re-scopes
every panel. What remains is not rot but four structural opens: (1) **the gate
is still language-biased** (0/43 Spanish kept — engine-level, the sem-lane +
gold retrain are the fix in flight, and the measurement needs a re-run); (2)
**time-as-dimension is adopted in spec, unbuilt on the globe** (S1-S4 queued);
(3) **L2 telemetry is thread-open-only** — panel swaps, country clicks,
scrubber use are all invisible; (4) a **dual serving regime** (v1-compat ‖
unified-v2) waits on the F4 flip, correctly gated on pool health ≥80. Plus a
small dead-code/half-wired sweep. The layer map (§5) shows every bridge now
exists L0→L3 — tonight's work closed the last one (L1→L3).

---

## 1. What held (verified against the prior reviews)

| Prior finding (06-12 / 06-26 / 07-01) | State today |
|---|---|
| Alert↔evidence split-brain (CI case: 26× spike → empty thread) | ✅ FIXED — B1 velocity-own mark, B2 #214 gated counts + UNVERIFIED tray, B3 rank_key_people |
| No deselect / silent stream scoping | ✅ FIXED — A1 focus chip, A2 single source of truth, A3 scope strips, A4 walkthrough |
| Public attention dark (Reddit invisible) | ✅ C1/C2/C3-forum SHIPPED (Pulse tab mobile); C3b semantic trends/wiki deferred (thin data) |
| SignalDetail dishonest leaf | ✅ rebuilt (thread chips + semantic neighbors + ConnectionsSection pin) |
| 16:9 dock crush | ✅ dock tabs |
| Design debt (142 WCAG fails, alien palettes) | ✅ batches A/B/C shipped; adoption residuals = #247 C1/C2 |
| Map heat = volume rank | ✅ composite atlas_heat + rank^1.6 normalize |
| MapLibre crash class | ✅ DEPRECATED (Equal Earth full parity, −1MB) |
| Universe/orbital program (§7.x) | ✅ all shipped through V9+perspective; trajectories-with-scrub residual |
| Stories-only /threads (07-04) | ✅ serving; kill-switch ATLAS_THREADS_CATEGORY_ROWS |

## 2. Serving layer (agent-mapped, condensed)

- ~55 endpoints, 8 versioned contracts; per-endpoint Redis TTLs (threads 300s,
  detail 180s, search 120s, insight 900s, universe 600s in-proc); statement
  timeouts tiered 5-25s (honest degradation everywhere).
- **Two-tier gate** (verified/extended/candidate + below-gate fallback) live on
  theme detail; extended thresholds from `app/data/scope_gate_extended_thresholds.json`
  — **no test coverage on the tier/fallback logic** (risk on retuning; noted).
- **Kill-switches:** `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` (off),
  `ATLAS_TOPIC_MEMBERS_ENGINE_VERSION` (v1-compat), `ATLAS_THREADS_CATEGORY_ROWS`
  (off) — the F4 cutover is one env-var, correctly parked behind PB-5
  (pool ≥80 + A/B re-run).
- Movement: universe reads Kalman `topic_movement` w/ changed_10h fallback;
  threads-panel ordering still inline changed_10h (deliberate, gated on A/B).
- Refresh cadences: focus data 5min, aircraft 60s, vessels 30s, disasters
  15min (72h fixed window — documented, honest), heat on range change.

## 3. Still open (the real list)

- **F-L2-1 (HIGH, engine): gate multilingual bias.** 0/43 Spanish kept
  (Peru case). In-flight fixes: OpenAI gate cutover + gold retrain (v3-mega
  deployed 07-04) + semantic lane. **The measurement was never re-run** on the
  current gate — `gate_recall_by_language.py` exists; run it, that's the whole
  task. Until measured, L2's "verified, multilingual" claim is unproven.
- **F-L2-2 (HIGH, product): time-as-dimension unbuilt on the globe.** The
  07-04 spec mandates S1 globe scrubber → S2 thread AGE chip → S3 peak
  drill-down (archive-backed) → S4 demote the time dropdown to a VIEW control.
  Universe + orbital have scrubbers; the globe and ThemeDetail don't. NOTE:
  Pedro fixed L1 at 24h today — which sharpens the division: **time belongs to
  L2** (the interrogation surface). S4 is the big semantic change (D-L2-1).
- **F-L2-3 (MEDIUM, cheap): L2 telemetry is thread_open-only.** No events for
  country click, panel swaps, universe/orbital scrubber use, dock tab use,
  layer toggles. The three-surface funnel now measures L1 (B1) and L3 (W0);
  L2 — the middle — is the blindest. Same pattern as before: instrument before
  building more.
- **F-L2-4 (MEDIUM): country view still serves the R1 merge** — the 07-04
  stories-only change explicitly deferred `?country_code=` (CountryBrief
  contract). Queued follow-up, unowned.
- **F-L2-5 (LOW): dead/half-wired code.** DiscoveryPanel + AtlasHeatList
  unmounted (delete); CrisisToggle imported-but-hidden; GlobalFilter's
  `streamLevel`/`entity`/`concept`/`region` setters exist but are not wired to
  serving (wire or delete — they're mental-model debt).
- **F-L2-6 (LOW): two-tier/fallback logic untested** (backend agent finding) —
  a retune of gate thresholds could silently flip serving; add contract tests.
- **F-L2-7 (verify-first): mobile Pulse tab** — one agent calls it a
  placeholder, the 06-30 record says it mounts the intel dock. Eyeball at
  375px before believing either. #236 tap-target pass (29 <32px) stands.

## 4. Corrections to the record

- Nearly everything the 06-12/06-26 reviews queued is DONE — those docs should
  not be read as open work-lists anymore; this doc supersedes them.
- `AtlasHeatList`/`DiscoveryPanel` referenced in old execution orders are dead
  code today, not pending mounts.

## 5. The layer map (Pedro's ask: interconnectivity L0→L4)

**Scale: superficial → specific.** Each layer's job + every bridge, as of tonight:

| From → To | Bridge | State |
|---|---|---|
| L0 Landing → L1 Brief | nav + hero CTA; `prefetchBriefing(24)` warms the cache | ✅ |
| L0 → L2 | "Moving now" cards deep-link `?theme=&country=&entry=landing` (#244) | ✅ |
| L1 → L2 | every section click → `/app?…&entry=brief` (now instrumented per-section, B1) | ✅ |
| **L1 → L3** | **◇ Save on lead/watchlist → investigation with frozen snapshot (B4, TONIGHT)** | ✅ NEW |
| L2 → L1 | BRIEF button (+ watches count) | ✅ |
| L2 → L3 | pins on every panel (unified store W1) + Start investigation + story panel PIN auto-create (W4) | ✅ |
| L3 → L2 | pin open → `handleOpenParams` routes + re-scopes focus | ✅ |
| L2 ↔ L2 spatial | universe ↔ orbital travel; thread → country drill; focus lens re-scopes all panels (#234) | ✅ |
| L3 → L3.5 | REPORT → dossier v2 (who-says-what/voice/categories, W3) | ✅ |
| L4 (markets) | FUTURE — `markets/` folder + L4 doc (2026-06-12); evidence-gated, event-study M0 = #226; Atlas-as-API end state | spec only |

**Time across layers (settled tonight):** L0 static → **L1 = the day (24h
fixed)** → **L2 = time as a dimension** (selector today; scrubbers per the
time-as-dimension spec = the queued work) → **L3 = frozen time** (pin
snapshots, "frozen at pin time") + measured-at-generation sections. Each layer
has a distinct, honest temporal contract.

## 6. Work spec

- **X0 — Instrument L2 (S, first):** `panel_swap{to}`, `country_click{via}`,
  `scrubber_used{surface}`, `layer_toggle{layer}`, dock tab events; value
  moment stays thread-based. Fold into the weekly read. Closes the middle of
  the L0→L3 funnel.
- **X1 — Gate-recall re-run (XS, engine-adjacent):** run
  `gate_recall_by_language.py` against the current OpenAI gate; publish the
  number next to the 06-12 baseline (0/43). If still biased → input to the
  gold/retrain track, not new L2 work.
- **X2 — Time-as-dimension S1+S2 (M):** globe time scrubber (reuse the
  universe pattern; heat/markers replay from existing dailies) + thread AGE
  chip ("active since {first_seen}") + full-life sparkline in ThemeDetail.
  S3 (peak drill, archive-backed) gated on the archive serving path; S4
  (demote the dropdown) = D-L2-1.
- **X3 — Country view stories-only (S-M):** finish the 07-04 deferral —
  `?country_code=` serves R1-scoped STORIES (same lens as global), CountryBrief
  contract updated; kill-switch like the global one.
- **X4 — Dead-code + half-wired sweep (S):** delete DiscoveryPanel,
  AtlasHeatList, CrisisToggle remnants; decide streamLevel/entity/concept/
  region (wire or delete — D-L2-2).
- **X5 — Two-tier contract tests (S):** pytest freezing verified/extended/
  candidate + below-gate fallback behavior against fixture thresholds.
- **X6 — Mobile pass (#236) (M, after X0 read):** verify Pulse tab content at
  375px; tap-target pass (29 <32px); universe gestures already spec'd.

Order: X0+X1 (same day, tiny) → X2 ∥ X3 → X4+X5 → X6. F4 flip stays PB-5
(pool ≥80), not this spec's call.

## 7. Decisions for Pedro

- **D-L2-1 Time dropdown → VIEW control (S4):** the deepest change in the
  time-as-dimension spec — data stops being windowed by the selector; the
  selector drives the scrubber default instead. Rec: do it WITH X2, one
  coherent time story; but it changes what every panel shows by default.
- **D-L2-2 Half-wired filters:** wire `concept`/`region` into serving (they
  have SearchBar affordances) and delete `streamLevel`/`entity`, vs delete all
  four. Rec: wire concept/region, delete the other two.
- **D-L2-3 X6 scope:** mobile pass now vs after the X0 telemetry read shows
  mobile L2 usage. Rec: after the read.
