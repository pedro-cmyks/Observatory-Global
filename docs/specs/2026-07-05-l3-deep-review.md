# L3 Deep Review — the Investigation Layer

**Date:** 2026-07-05 (madrugada, parallel to the archive-embed session)
**Status:** REVIEW COMPLETE → WORK SPEC (§6). Pending Pedro's read + decisions (§7).
**Method:** 3 exhaustive code/docs sweeps (frontend, backend, specs/issues) + live
prod verification (endpoint smoke, `research_pin_events`, `telemetry_events`) +
manual verification of every load-bearing claim (agent claims were grep-checked;
two were wrong and are corrected here).

---

## 0. Verdict in one paragraph

L3 is **the most sophisticated unused surface in Atlas**. Construction quality is
high (honest ledgers, frozen snapshots, a shipped dossier, 7 backend test files,
degradable lanes) — the 07-01 "foundation sound" verdict holds. But it has three
diseases: (1) it is **two parallel systems that never reconcile** (Workbench ‖
Workspace — the same split-brain the engine had before unification); (2) its
backend is **frozen at the 2026-06-10/11 engine state** — it consumes none of the
last month of engine truth (R3 categories, typed `topic_members`, two-tier gate,
Kalman movement, OpenAI space); and (3) it is **unmeasured and unused**: 1 pin
ever recorded (ship-day dev test), 0 dossiers generated, and most L3 actions have
no telemetry event type at all. The work is consolidation + alignment +
instrumentation — not new capability. The wedge says the analyst's job is
"who is saying what across countries and languages, press vs public, what is
missing — with the receipts"; **L3 is the receipts layer**, and the engine
substrate that could finally power that job (roles, voice mix, categories,
archive) arrived AFTER this surface was built. Reconnecting them is the program.

---

## 1. What L3 is today (verified inventory)

### 1a. System A — "Workbench" (research-plan lineage, Phases 1a→3 SHIPPED)

| Piece | File | State |
|---|---|---|
| Data model | `frontend-v2/src/lib/workbench.ts` (193 LOC) | `Investigation{id,title,pins[],trail[]}`; `WorkbenchPin` carries `note` + **#227 frozen `snapshot`** (capturedAt, summary, metrics, evidence[≤3]); localStorage `atlas.workbench.v1`; multi-investigation, active-id in `atlas.workbench.active.v1` |
| Plan panel | `ResearchPlanPanel.tsx` (280 LOC) | anchors ranked + DIRECT/CONTEXT/WEAK/GAP badges, low-confidence tray, semantic-evidence section, downranking ledger, PIN (only when an investigation is active), #218 impression/open/pin events |
| Sidebar | `WorkbenchPanel.tsx` (204 LOC) | investigation list/create/switch/delete, pins w/ snapshot + per-pin note (blur-save), trail (last 20), EXPORT JSON, REPORT |
| Dossier | `DossierView.tsx` (110 LOC) + `lib/dossier.ts` | **Phase 3 v1 EXISTS and is wired** (REPORT button): exec summary, evidence from frozen snapshots, timeline, gaps; Copy/Download markdown; fires `dossier_generated` + `first_value_moment{kind:'dossier'}` |
| Entries | SearchBar "Start investigation" (query ≥8 chars) → `createInvestigation`; `ConnectionsSection` truncated-thread pin (auto-creates investigation); command-bar WORKBENCH toggle | |

**Docs are stale on this:** the 06-09 spec + inventory still say "Phase 3 report
deferred / interface prepped". Reality: `2d4d04e3` shipped DossierView; **#227 is
CLOSED** (snapshot + note implemented, client-side). Correct the record.

### 1b. System B — "Workspace" (force-graph lineage, session 6/13 era)

| Piece | File | State |
|---|---|---|
| Store | `contexts/WorkspaceContext.tsx` (224 LOC) | `PinnedItem{id,type,title,urlParams,notes,timestamp,meta}` — **separate model, separate localStorage `atlas-workspace`**, no snapshot, no investigation grouping |
| Canvas | `InteractiveWorkspace.tsx` (684 LOC) + `workspaceGraph.ts` (647 LOC) | dual force-graph (trail vs pinned), 8 node types, 7 link kinds, per-type detail fetches (`/theme`, `/country`, `/focus`, `/source/profile`, `/search/unified`), desktop-only (`!isMobile`), lazy-loaded |
| Pin affordances | ThemeDetail, CountryBrief, EntityPanel (person), SourceProfile, PublicAttentionPanel | all write **PinnedItem**, NOT WorkbenchPin |
| Export | `exportFormatters.ts` `buildWorkspaceMarkdown` | second, parallel export path |

### 1c. Backend (research stack, contract `research-plan-v0`)

- `research_plan.py` intent parser (deterministic, pure) → `research_anchor_discovery.py`
  lanes (country / threads / public-attention / semantic / branches / coverage-gaps,
  all degradable, never silent) → `research_ranking.py` (calibrated weights
  2026-06-10, relevance gate `0.5+0.5·intent_match`, DOWNRANK 0.30, ledger
  reconciles) → `research_semantic.py` (**multilingual-e5-base**, local-torch →
  `EMBED_SERVICE_URL` → visible gap; thresholds 0.80/0.86 centroid, 0.765/0.79
  atlas-description, 0.84 signal-headline, 0.82 thread-member — all measured
  2026-06-10/11).
- `POST /api/v2/research/plan` (Redis 120s, plan_id) + `POST /api/v2/research/events`
  (impression/open/pin/unpin/dismiss → mig 053 `research_pin_events`, **write-only,
  no read path anywhere**).
- Thread lane delegates to `thread_intelligence.fetch_threads` → **inherits serving
  improvements for free** (unified ranking 06-24, stories-only 07-04). This is the
  one place L3 stayed current.
- 7 test files ≈ 912 lines; walkthrough fixture at 3 layers + prod smoke script.

### 1d. Prod ground truth (measured tonight, 2026-07-05)

- Endpoint alive: fixture query → contract `research-plan-v0`, 6 anchors, plan_id ok.
- `research_pin_events` (all time): **30 impressions · 1 open · 1 pin** — the pin is
  2026-06-11 (ship-day). 8 distinct plans.
- `telemetry_events`: 475 app_open / 123 thread_open / 48 first_value_moment /
  13 search_query / **2 search_story_open (1 session)** / 0 dossier_generated.
  **No event type exists** for workbench_open, investigation_created, or any
  Workspace pin. L3 usage is not just zero — it is *unmeasurable* today.

---

## 2. Findings (evidence-backed, ranked)

### F1 — L3 split-brain (CRITICAL, structural)
Two pin models, two stores, two exports, no reconciliation:
- Pin a thread in ThemeDetail → PinnedItem → force-graph, **never reaches the
  dossier** (DossierView takes `Investigation`, not `PinnedItem[]`).
- Pin an anchor in ResearchPlanPanel → WorkbenchPin → dossier, **never reaches the
  graph**.
- System B pins have **no snapshot** → link-rot when dynamic topics retire/rebuild
  (#227 fixed this only for System A).
- User-visible incoherence: "I pinned it, where is it?" depends on WHERE you pinned.
Same disease the engine had (atlas ‖ dynamic ‖ discussion). Cure pattern known:
**one store, one pin model, views at serving.**

### F2 — Backend frozen at the 2026-06-10 engine (HIGH)
Grep-verified zero references in the research stack to: `topic_members`,
`topic_movement`, `crisis_relevant`, `gate_kept` two-tier, extended thresholds,
OpenAI. Concretely:
- **Semantic lane lives in e5 space** with running-mean centroids — the exact
  configuration the engine measured at the noise floor (06-29 ablations; 07-04
  anchor-cosine calibration failure, pos/neg p50 delta 0.024) and moved away from
  (gate, sem-assign, archive shards are all OpenAI 3-small now). L3 thresholds
  were honest when measured; the ground under them moved.
- **Pool-health coupling with no floor:** `fetch_topic_centroids` reads active
  `dynamic_topics`. Post-collapse pool = 16 active → the topic-semantic lane
  quietly degrades to near-nothing. Identical to the F4 A/B finding ("v2 quality
  is coupled to pool health with no floor") — L3 has the same exposure and no
  substrate-health guard.
- **Movement = raw `changed_10h`**, not the Kalman `topic_movement` field every
  other surface was unified onto (#219 shipped 07-03).
- **Gate labels = `assigned|below_gate`** — predates the two-tier
  verified/extended contract (07-04) and the OpenAI gate cutover.
- **No R3 category awareness**: anchors carry no category lens; coverage gaps
  can't say "no verified evidence in election-legitimacy for PE".
- What DID stay current: thread lane (via `fetch_threads`) and the honest-ledger
  discipline (which R3/serving later adopted everywhere — L3 was ahead here).

### F3 — Telemetry blind + #218 loop never closed (HIGH, cheapest to fix)
- Client: only DossierView is instrumented (0 events ever). No
  `workbench_open` / `investigation_created`; System B pins fire nothing.
- Server: `research_pin_events` was sold (#218, CLOSED) as "the future
  relevance-judgment dataset" — **nothing reads it**; ranking calibration
  (2026-06-10) never consumed it.
- Consequence: the wedge anti-goal ("no new surface until telemetry shows value")
  is **ungovernable for L3** — we cannot see reach, friction, or value here.

### F4 — Dossier v1 is a pin dump; the wedge job needs more, and the substrate NOW exists (MEDIUM→HIGH value)
DossierView renders summary/evidence/timeline/gaps from frozen pins. Missing —
and each miss now has a real engine primitive that did not exist on 06-12:
| Wedge need | Missing in dossier | Substrate that exists TODAY |
|---|---|---|
| who says what, press vs public | no roles split | `topic_members` roles (evidence/discussion/mood) + relationship endpoint |
| across countries and languages | no voice section | `voice_mix` service (self_voice by OWNERSHIP, soft-power bucket, entropy) |
| credibility of the receipts | no tiers (#217 OPEN) | `source_family`, `is_state_media`, self-voice — a minimal tier floor |
| what is missing | gaps = generic trail notes | real per-thread coverage_gaps + category-scoped gap logic |
| honest time | "frozen at pin time" only | `dynamic_topics` age/persistence; archive (time-as-dimension spec; OpenAI shards being built tonight) |

### F5 — Capture coverage gaps + fragile pin refs (MEDIUM)
- Not pinnable anywhere: **signals**, **NarrativeThreads rows**, **universe bodies**
  (the discovery entry!), Brief lead. The new **search→story panel — the main new
  L3 ramp — has no pin affordance and doesn't offer to create an investigation**;
  ResearchPlanPanel's PIN only renders when an investigation is already active.
  The ramp Pedro shipped 07-04 dead-ends exactly at the capture moment.
- Pins store ephemeral ids (`dynamic-topic-N`, umbrella ids rebuilt nightly,
  `u2-*`): opens break silently when identities rebuild. Snapshots (System A)
  mitigate; System B has nothing.

### F6 — Persistence is localStorage-only (LOW today)
No accounts/sync/server investigations; export manual JSON/MD. Consistent with the
local-first PWA posture. Becomes real when sharing/multi-device matters (Phase 2
accounts track). No action now; named so it's a decision, not an accident.

### F7 — Evidence-window contract (capability H) unfelt at pin-open (MEDIUM, rising)
Hot retention = 7d (fixed 07-04). A pin older than the hot window opens a surface
with thinner/no live data; the snapshot is the only memory. Time-as-dimension spec
promises archive-backed "click-a-past-peak" — **L3 pins are the natural first
consumer** of the archive shards being embedded tonight.

### F8 — L2↔L3 seams (MEDIUM)
- Workbench-opening a pin routes to the right panel but does **not** set the focus
  lens → the rest of L2 doesn't re-scope (the #234 machinery exists and is unused
  here).
- Story panel (search→story) ↔ investigation: no bridge (see F5).
- Mobile: workbench overlay reachable, force-graph hidden — fine; but "Start
  investigation" desktop-first assumption undocumented.

### Corrections to the record (docs stale)
- Phase 3 dossier: **BUILT** (v1), #227 **CLOSED** — 06-09 spec status section and
  the papers-inventory claim "generation deferred" are wrong.
- One mapping agent claimed the research stack uses `topic_members`/Kalman/
  crisis_relevant — **false** (grep-verified zero hits). Recorded here so it
  doesn't re-enter circulation.

---

## 3. Alignment map — L3 vs everything since 06-12

| Program (shipped) | L3 consumes it? | Gap |
|---|---|---|
| R1/R2/R3 spine, stories-only serving (07-04) | ✅ via `fetch_threads` | none (thread lane) |
| R3.1 categories as lens | ❌ | no category lens in plan/anchors/gaps (W2d) |
| Two-tier gate verified/extended + OpenAI gate (07-04) | ❌ | anchors still `assigned/below_gate` (W2b) |
| Semantic-assign lane method (wild-junk-quantile taus, 07-04) | ❌ | L3 taus from 06-10/11, e5 space (W2a — reuse the calibration METHOD) |
| Kalman `topic_movement` (#219, 07-03) | ❌ | ranking reads raw changed_10h (W2c) |
| `topic_members` typed roles (F0-F3) | ❌ | who-says-what never surfaced in dossier (W3) |
| voice_mix / self-voice ownership (06-22/23) | ❌ | dossier has no voice section (W3) |
| Universe view = discovery entry (07-02/03) | ❌ | bodies not pinnable; no investigation bridge (W4) |
| Time-as-dimension + archive embeds (07-04/05) | ❌ | pins hot-window-bound; archive = natural consumer (W4) |
| Crisis-as-dynamics (07-04) | ❌ | not applicable yet; note only |
| Honest-ledger discipline | ✅ (L3 invented it) | keep |
| Telemetry/value moments (T5.1) | ⚠ dossier only | W0 |

---

## 4. What "building an investigation" is today (the user path, honest)

1. Type ≥8-char query → "Start investigation" (SearchBar) → investigation created,
   Workbench opens, research plan loads with ranked anchors + ledger + gaps.
2. PIN anchors (freezes snapshot: summary, score, 3 evidence headlines) — or pin a
   truncated thread from SignalDetail's ConnectionsSection.
3. Add per-pin notes; trail logs search/open/pin/branch automatically.
4. REPORT → dossier (summary/evidence/timeline/gaps) → copy/download markdown.
5. **Separately and incompatibly:** pin themes/countries/people/sources from L2
   panels → force-graph canvas (desktop) — never joins 1–4.

Steps 1–4 are a real, coherent loop. Nobody has ever completed it (0 dossiers).
Friction points: PIN invisible without an active investigation; the new story
panel doesn't offer the loop; the two pin systems confuse the mental model.

---

## 5. Judgment

Not rot — **drift**. The layer was built to spec, the spec was honest, and then a
month of engine work (which L3's own honesty discipline partly inspired) happened
underneath it without a single read-path update. Meanwhile a second, older pin
system kept living beside it. Given the anti-goal, the correct program is:
**measure → unify → re-substrate → then deepen the dossier** — no new surfaces.
L3 is also where Atlas's differentiation is sharpest (a chatbot can summarize; it
cannot hand you frozen receipts, a downranking ledger, voice-mix and a
who-says-what matrix). The wedge argument says invest here — but only along the
consolidation path, and instrumented from day one.

---

## 6. Work spec

### W0 — Measure L3 + close the #218 loop (S, ~half-day, DO FIRST)
1. Client events: `workbench_open`, `investigation_created`, `pin` (one event,
   `props.system: 'plan'|'panel'`, `props.anchorType`), `report_open`. Add
   `first_value_moment{kind:'investigation'}` = created + ≥1 pin.
2. `backend/scripts/research_usage_report.py`: joins `research_pin_events` +
   `telemetry_events` → weekly L3 read (reach, pins/session, ramp conversion
   search→story→investigation). Fold into PB-8.
3. Docs: correct Phase-3/#227 status in the 06-09 spec header.
- **Acceptance:** events visible in prod table; report runs; first weekly read
  scheduled with the 07-11 telemetry read.

### W1 — Unify the two L3 systems (M, ~1-2 days, the structural fix)
1. `workbench.ts` Investigation = the ONLY store. Extend `WorkbenchPin.anchorType`
   to cover theme/country/person/source/public_attention.
2. Every System-B pin affordance writes a WorkbenchPin **with a frozen snapshot**
   (reuse the ResearchPlanPanel snapshot builder; per-surface summary/evidence).
3. `WorkspaceContext.PinnedItem` becomes a derived view (adapter) over the active
   investigation's pins; force-graph + trail read it. Delete the `atlas-workspace`
   write path after a one-time localStorage migration (merge into a "Migrated
   pins" investigation).
4. One export: dossier covers all pins; retire `buildWorkspaceMarkdown` or make it
   call the dossier formatter.
5. Pin refs hardened: store `identity_key`/slug + label alongside id; open falls
   back to label search with an honest "topic retired — snapshot preserved" state.
- **Acceptance:** pin in ThemeDetail → visible in WorkbenchPanel AND dossier AND
  graph; old workspace pins migrated; vitest suite green; no orphan store writes.

### W2 — Re-substrate the research plan (M-L, backend, contract `research-plan-v1`)
- **a. Semantic lane:** (i) NOW: re-measure the four e5 taus on the current corpus
  with the wild-junk-quantile method (the 07-04 calibration script generalizes);
  add a **substrate-health guard** — active-centroid pool < 80 → emit
  `lane_degraded` gap instead of serving noise. (ii) NEXT (gated on hot-corpus
  OpenAI embeddings — the archive pipeline running tonight builds the historical
  half): move topic+signal matching to OpenAI 3-small space, one space with the
  gate/sem-assign/robot.
- **b. Two-tier labels:** anchors + semantic evidence carry
  `verified|extended|below_gate` using `scope_gate_extended_thresholds.json`.
- **c. Movement:** read `topic_movement` (Kalman velocity/trend), `changed_10h`
  fallback; reason code names the source.
- **d. Category lens (R3):** intent → atlas categories; anchors grouped by
  category; coverage gaps become category-scoped ("no verified election-legitimacy
  evidence for PE — 12 extended available").
- **Acceptance:** walkthrough smoke (both forcing cases) passes; new fields
  contract-versioned `research-plan-v1`; pool-collapse fixture triggers the guard;
  thresholds ledgered like the sem-assign lane.

### W3 — Dossier v2: the wedge deliverable (L, after W1; who-says-what gated on discussion-lane data)
1. **Who-says-what section** per pinned thread: `topic_members` roles → press
   (evidence) vs public (discussion) counts + top outlets vs top communities;
   reuse/extend `GET /api/v2/topic/{id}/relationship`.
2. **Voice section:** `voice_mix?country=` for pinned countries/threads →
   self-voice %, dominant outsider, languages. "Covered BY whom, not just about whom."
3. **Credibility floor (#217 minimal):** tier chips from `source_family` +
   `is_state_media` + domestic/foreign origin. Label, never filter.
4. **Gaps:** real coverage_gaps of pinned threads (from W2d), not trail notes.
5. **Time:** "active since {first_seen}" + snapshot-vs-now delta per pin.
- Client-side from pins + existing endpoints; no new server render.
- **Acceptance:** fixture investigation (Peru election-legitimacy) → dossier with
  who-says-what + voice + tiers + category gaps; markdown export carries all of it.

### W4 — Capture coverage + time (M, after W1)
1. Pin affordances: universe body hover-card, NarrativeThreads row, signal (with
   snapshot), Brief lead story.
2. **Story-panel bridge (kills the F8/F5 friction):** first PIN in any surface
   with no active investigation offers one-tap "Start investigation from this" —
   and the search→story panel gets pin buttons on its anchors.
3. Workbench-open sets the focus lens (reuse #234 machinery) so L2 re-scopes.
4. **Archive-backed pin open** (time-as-dimension first consumer): pin older than
   hot window → that period's evidence from archive shards. Gated on the archive
   pipeline + a serving path for it (own mini-spec when substrate lands).

### W5 — Phase 4 (frames, contradiction role, hypothesis testing): stays PAPER-GATED
P1 contradiction class untrained; #217 full tiers = P2. Not scheduled; do not
start before W0-W3 telemetry justifies it.

### Order & gates
W0 → W1 → W2 (a-now/b/c/d) ∥ W3.1-3 prep → read telemetry → size W3/W4 by what it
says. W2a-OpenAI gated on hot-corpus OpenAI vectors; W3.1 honest about thin
discussion data (forum volume still ramping); W4.4 gated on archive serving path.
Anti-goal honored: zero new surfaces; everything is consolidation, alignment, or
instrumentation of what exists.

---

## 7. Decisions for Pedro

- **D1 Force-graph:** keep as a VIEW over the unified investigation (rec — cheap
  once W1 lands; invest nothing more until W0 shows usage) vs retire behind flag.
- **D2 Semantic-lane space:** recalibrate e5 now + OpenAI when hot vectors exist
  (rec) vs immediate dual-space (costs, complexity).
- **D3 Dossier stays client-side** from pins + existing endpoints (rec) vs
  server-side report endpoint now.
- **D4 Value-moment definition:** add `investigation` kind (created + ≥1 pin) —
  rec yes; it's the L3 value moment the anti-goal needs to see.
- **D5 Workspace localStorage migration:** merge old `atlas-workspace` pins into a
  "Migrated pins" investigation (rec) vs drop (they're likely only Pedro's).
