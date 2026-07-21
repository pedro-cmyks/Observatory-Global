# Exploration Flywheel — Design (2026-07-21)

**Status:** design approved by Pedro (brainstorming session, 2026-07-21). Next: implementation plan.

**Companion input:** `docs/state/2026-07-21-analyst-journey-map.md` (the friction/flywheel-gap
diagnosis with file:line evidence). Read that first; this spec answers the 8 design questions it posed.

---

## 1. Goal

Atlas's data/engine are strong (Label-Court ~24%, over-merge detector, lineage, corroboration,
enrichment). The bottleneck is no longer *what we show* — it is the **journey**. The app captures
findings but does not **compound** them: opening a thread empties the frame you built, the surfaces
that draw "look here next" (bridge stars, leads, gaps) make the click inert, and the report is a
terminal file. The wheel turns one click at a time, by hand.

This design makes Atlas an **exploration flywheel** — each finding renders the next as a live,
one-click seed, and the app organizes the analyst's trail into a building investigation. That
flywheel is what makes Atlas an *axis*, not just a nice tool.

## 2. The one decision that colors everything — the agency dial

**Invitation-rich, analyst-driven.** The app **never acts unprompted.** It *renders* every
next-step live and obvious, but the analyst's hand is always on the wheel.

- Cheap, math-first signals (relationship detection, bridges, siblings, gaps) may be **auto-rendered**
  — rendering is not acting.
- Anything **paid** (LEADS / AI-READ) or **asserting a direction** stays one honest, explicit click away.

Rejected: proactive auto-advance (app pulling the next thing on its own, firing paid calls without a
press). That would tax honesty and spend without consent.

## 3. The product model (the levels this design sits inside)

The flywheel machinery is **level-aware**. It must never intrude on a reader or a one-off browser.

| Level | Who / when | Role | Frame presence |
|---|---|---|---|
| **L0 Landing** | first contact | explains what Atlas is, how info is counted, what data exists | **none** |
| **L1 Daily Global Brief** | *no time* — enter and go | the day's most important, top-down (relationships, threads, evolution); filter to your country | **none** — pure read, zero exploration burden |
| **L2 Console** | *one-off* | a vast ocean; the surfaces (universe, map, threads, stream, anomaly) are different ways to see the **same** information; look one-shot **or** pin as things catch your eye | **present but quiet** — a one-off explorer is unburdened; the Frame wakes only on the first pin |
| **L3 Workbench** | *sat down to play* | build your own investigation; watch it assemble, get recommended relationships, pin more, deliver | **central** — it is the brief you're building |

**Product thesis (explicit):** L1 = **Atlas's** edition (what you read). L3 Workbench = **your**
brief (what you build). **The whole flywheel's job is to move findings from the edition into the
brief you are building.** The Workbench is a brief-*builder*; the dossier is the brief you publish.
"Returning to the Brief" is not the goal — pulling the Brief's content **forward** is.

## 4. The Frame — the spine object

One always-visible object that is, at once, the **compound-focus lens**, the **"investigation
you're building,"** and the **bridge-detector**. Desktop: a top strip. Phone: a pull-up sheet.

### 4.1 Two records (never one)

- **Trail** — ambient, automatic, ordered. Every surface you open leaves a light breadcrumb of
  *where you went*. **Not classified.** Powers backtrack + "you passed by X, pin it?" nudges.
- **Frame** — deliberate, built from **pins only**. Pins auto-sort into **WHO / WHERE / WHAT**
  lanes (person→WHO, country→WHERE, thread/topic→WHAT). Each lane holds *multiple* chips.

This split holds the honest line: **a glance is never evidence.** Exploration compounds as a
*lens*; only a deliberate pin joins the investigation.

### 4.2 Auto-classification

The analyst never files anything by hand. The app reads each pin's type and drops it into the
right lane. Chips are individually removable; removal is legible (no silent scoping).

### 4.3 Prominence gradient

L0/L1: absent. L2: minimal until the first pin, then a quiet strip. L3: central. The Frame never
appears to a no-time reader or burdens a one-off explorer.

## 5. Capture — the input (one gesture, entity-rich)

**A pin is not a flat reference to a surface. A pin is a rich entity that carries all its
representations.** The globe, universe, constellation, connections map, country maps are **lenses
over the same underlying entities** — not separate pinnable things. A pinned narrative thread
*already is* a universe sector (3D, its neighbors around it), a constellation, a map region, a set
of connection edges, and its receipts.

- **One ◆ gesture, on everything, context-aware:**
  - ◆ a person / country / thread node → becomes a classified **chip** in the Frame.
  - ◆ a headline / receipt row → attaches as **evidence under** its most-related chip (cheap math
    finds the anchor; the link is shown + removable). If nothing relates yet, it sits as loose evidence.
- **Pinning once lights the entity across every lens** — its universe sector glows, its map region
  marks, its constellation lights — because it is the same object seen through different glass. The
  pin's representations *are* the flywheel surface (its sector's neighbors, its connection edges are
  the next-discovery field).
- **Unifies the split:** today's separate `pins` (anchors) and `citations` (receipts) arrays become
  **one investigation object** — anchors with evidence hanging off them.

## 6. Detect — the relationship engine

Runs over the **pinned Frame** (+ the daily-brief candidate pool, §6.2). Cheap semantic /
co-occurrence math → auto-rendered, never auto-scoped.

### 6.1 Behavior

- **Threshold-gated, not per-click.** Fires only when a genuine relationship accumulates across
  pins — *"you've pinned a lot; these connect →"*. Never nags.
- **Strongest-first.** When several relationships exist, show the strongest as the primary ◎
  callout; the rest expandable behind it. Never spam all.
- **Measured, not asserted.** Labeled explicitly. The callout offers two live invitations:
  **◎ scope every surface to this** and **＋ start investigation from it** — both the analyst's click.
- **Direct relationships only.** Multi-hop *transitive* chains (e.g. Netanyahu → Gaza ceasefire →
  Hormuz → oil transport → oil price) are **parked** — a separate, deeper feature (spawned as its
  own task/chat). Detection here uses the rarity-weighting discipline from #234 (a common actor
  must not glue unrelated pins).

### 6.2 Candidate pool

The pool is **the daily brief's already-fetched headlines** (the Brief already does a large
fetch of titulares) **+ the analyst's pins**. The detector reuses that loaded data — no new heavy
fetch — so *"today's edition covers this — look / ＋add to your investigation"* comes for free and
**forward** (never a "go back to the Brief").

## 7. Launch — the output (typed verbs, no dead labels)

With the entity-rich principle, "look here next" is uniform — *the neighbors of your pins, in any
representation, are the seeds* — but the **verb is typed to what the seed is**. Every previously
inert signal gets one primary verb + ◆ as the secondary keep:

| Seed type | Primary verb | Notes |
|---|---|---|
| neighbor / bridge star / lead | **open & focus** it | a real thread → explore it |
| coverage gap ("trade-export: 72 raw, none verified") | **spin up a fresh query / investigation** | an *absence*; the one place the app **generates** rather than navigates |
| cross-read tension ("death toll 13 vs 16") | **open both sources / make a corroboration task** | a discrepancy |

Consequence: **the report stops being terminal.** Gaps, tensions, bridges, unpinned leads in L3
all become launchers — publishing is a turn of the wheel, not an exit.

## 8. Mobile — reading-first

On a phone you see one surface at a time, so the flywheel travels **with the read**, never in
buried tabs.

- **Read is primary** (Brief card / thread article, full screen). Header carries `← Brief`
  (return trip fixed) + context (label · why_now · source counts) — context traveled, not just an id.
- **Every read ends in an inline "Keep going" rail:** the ◎ detected relationship (if any),
  *"who else covers this,"* *"next unread in your trail,"* and ◆ keep.
- **The Frame = a quiet pull-up sheet** (badge shows count; pull up for WHO/WHERE/WHAT + the ◎
  callout + Scope / ＋Report). **Detection never interrupts the read** — quiet in the sheet only.
- **The WebGL cockpit (map/universe) is on-demand** — spun up only when tapped, not always alive
  draining battery while you read.

Net: you move *forward* through seeds (read → next-rail → read) instead of ejecting into cockpit tabs.

## 9. Honesty rails (non-negotiable)

- **Pins = deliberate evidence.** A glance (Trail) never becomes evidence (Frame).
- **Detection is labeled measured-not-asserted;** never implies coverage = corroboration, or
  attention = verified.
- **Nothing paid or asserting fires without an explicit click** (LEADS / AI-READ / corroboration).
- **Every scope is legible and reversible** — chips removable, "Scoped to X ✕" strips, no silent filtering.
- Preserve the existing honesty stack: gate tiers, taxonomy-not-evidence labels, metadata-only
  flags, the prose validator, frozen-vs-measured-at-generation labeling.

## 10. What already works — preserve, don't rebuild

(From journey map §4.) The theme+country deep-link carrier; `prefetchBriefing(24)`; the keep-alive
shell; the unified `WorkspaceContext`/`workbench.ts` store; the frozen #227 snapshot spine;
receipt Citations; auto-create-investigation; UniverseView travel; the person-focus chain
(`setPerson` → EntityPanel + precise `?person=` highlight + universe re-scope + map fly + anomaly);
rarity-weighted sibling surfacing with reason chips; ThemeDetail drill-down; SignalDetail
connected-threads; LEADS (the engine — it exists, it's just gated and doesn't self-advance);
FocusIndicator strips; the 5W+H readiness panel; the Markdown export.

The design **extends** these — it does not replace them.

## 11. Scope

**In scope:** the Frame (Trail + classified pins + prominence gradient); compound focus replacing
the mutually-exclusive setters and the thread-open frame-clear; ◆-anywhere entity-rich capture with
receipt auto-attach; the threshold-gated strongest-first detector reading the daily-brief pool;
typed launchers across L2 and the L3 report; the mobile reading-first reshape; the forward
Brief-spine; carry-context on navigation (label / why_now / provenance) + return-trip + category
`q`-handler.

**Parked (explicitly not this design):**
- **Multi-hop transitive relationship chains** — spawned as its own task/chat.
- **Proactive auto-advance** — rejected (contradicts invitation-rich).

## 12. Primary code touch-points (from the journey map, to ground the plan)

Not an implementation plan — orientation for the next step.

- **Compound focus / thread-open frame-clear:** `FocusContext.tsx:115-166` (mutually-exclusive
  setters), `App.tsx:2042-2050` (thread-open `clearFocus`), `App.tsx:942` / `App.tsx:680` (divergent
  thread-open paths).
- **The Frame object (new):** consumes `WorkspaceContext` / `lib/workbench.ts`; classification over
  pin types; a Trail record (new, ambient).
- **Capture ◆ anywhere:** add to the discovery surfaces missing it — `UniverseView.tsx`,
  `EqualEarthMap.tsx`, `DossierConnections.tsx`/`WorkbenchConstellation.tsx`, `NarrativeBiography.tsx`,
  `DayEvidencePanel.tsx`, thread-row person chips (`NarrativeThreads.tsx:551-553`); unify
  `pins`/`citations` (`workbench.ts:133-139`).
- **Detector:** reuse the bridge computation (`DossierConnections.tsx:388-403` `nbGroups.bridges`)
  lifted to run over the live Frame + the Brief's fetched headlines.
- **Launchers:** make clickable — `DossierConnections.tsx:363,520-523,552-555` (bridge stars),
  `DossierView.tsx:968,987,749-836` (gaps/tensions/contested), `SignalDetailPanel.tsx:322-343`
  (semantic neighbors leak external), `WorkbenchPanel.tsx:486-495` (lead pin doesn't navigate/re-run).
- **Carry-context / return:** `App.tsx:722-739` (no `q` handler), `App.tsx:729` (no `labelHint`),
  `App.tsx:1287-1294` (return drops theme), `entrySource` stale under keep-alive (`App.tsx:358-361`).
- **Mobile:** `App.tsx:959` (Brief→thread→close dumps into cockpit), `App.tsx:1003-1013` (secondary
  panels hijack Stream tab), keep-alive WebGL always-alive (`main.tsx:43-49`).

## 13. Success criteria

The design succeeds when:

1. **Findings compound.** Opening a thread while focused on a person/country **keeps** that frame
   (compound lens), and the surfaces state exactly what they're scoped to.
2. **Every "look here next" is live.** No bridge star, gap, tension, lead, or neighbor is a dead
   label — each has a typed verb + ◆.
3. **Capture works from any surface with one gesture,** and a pin is visibly present across all its
   representations.
4. **The analyst always knows which investigation their next pin lands in,** without opening a modal.
5. **The report launches the next investigation** — a gap becomes a query, a tension a corroboration
   task, a bridge an open+pin.
6. **On a phone, a finding leads to the next one in the reading flow** — no ejection into cockpit tabs.
7. **No honesty regression** — every new suggestion is labeled measured-not-asserted; nothing paid
   or asserting fires without a click.

## 14. Decision log (this session)

- Agency dial → **invitation-rich, analyst-driven** (render, never act unprompted).
- Exploration vs investigation → **two layers** (ephemeral compound lens above deliberate pins).
- Lens shape → **auto-classified bounded slots** (WHO/WHERE/WHAT) built from **pins**, with a
  separate ambient **Trail**; detection **threshold-gated, strongest-first**.
- Capture → **one ◆, entity-rich** (all representations), **receipt auto-attach**, pins+citations unified.
- Launchers → **typed verbs** (open / fresh-query / corroborate) + ◆.
- Mobile → **reading-first**, inline seeds, Frame as quiet sheet, detection never interrupts, cockpit on-demand.
- Brief-spine → **forward-only candidate pool** (reuse daily-brief fetched headlines), not a return target.
- Frame prominence → **level-aware gradient** (absent L0/L1, quiet-until-pin L2, central L3).
- Transitive chains → **parked** (own task). Proactive auto-advance → **rejected**.
