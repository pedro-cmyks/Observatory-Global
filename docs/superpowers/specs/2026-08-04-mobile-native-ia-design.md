# Mobile-Native IA — phone as a lens, not a smaller desktop

**Issue:** #236 (open since 2026-06-24, deferred through four sweeps)
**Date:** 2026-08-04
**Status:** SPEC — approved section by section with Pedro in session
**Supersedes as the actionable plan:** `docs/state/2026-07-13-mobile-l0-l3-audit.md`
(that audit's findings are re-verified live below; its proposed sequencing is
replaced by §9 because the owner chose a different IA)

---

## 1. Why now, and what changed

The 07-13 audit read the code and concluded: *"mobile carries the same commands
as desktop, just wrapped."* This spec re-measured the same four surfaces **live
at 375×812 against the production API** on 2026-08-04. Every number here is from
the running app.

The audit's thesis held. Two of its claims went stale and are corrected below.

### 1.1 The measurement

**L0 Landing.** No horizontal overflow (`scrollWidth == clientWidth == 375`).
The four nav links are `hidden md:flex` with no menu replacing them. Lowest
priority — confirmed.

**L1 Brief.** The first news headline lands at **1707px — 2.1 phone screens
down.** Vertical ledger, measured from the DOM:

| block | height |
|---|---|
| masthead | 302 |
| freshness / publication-state | 141 |
| **6 stat cards (`.brief-instrument`)** | **542** |
| **markets band** | **463** |
| country search | 34 |
| section tabs | 95 |
| → lead story starts | at 1707 |
| lead card | 1021 |
| following cards | 478–679 each |
| minimap (`.brief-minimap`) | 213 |

The two bolded blocks are desktop horizontal strips collapsed into a 1005px
wall. The genuinely phone-shaped element — the "Most Active" ranked list — sits
at 10,842px.

**L2 Console.**
- Command bar 139px tall; its buttons measure **23–25px** (iOS minimum 44).
  `WORKBENCH` is a full-width 359×23 pill.
- **Stream** (default tab): first row at 244px; rows **39px**; the lane strip
  has `scrollWidth 524` vs `clientWidth 365`, so `DISASTER` is off-screen with
  no affordance.
- **Threads**: ~290px per row, and **the thread title is what gets truncated or
  dropped** while the sparkline, confidence bar, "peak 2/h", "Started 62d ago"
  and five entity chips survive at full size. A hover tooltip was caught stuck
  open on touch, covering a title.
- **Map**: the world does not fit a portrait phone — it renders zoomed into
  Africa/Europe. Dead `PLANE` and sparse `SHIPS` lanes still occupy the chip bar,
  which clips.
- **Pulse**: `AnomalyPanel.css` has **0 media queries**. Two desktop columns
  survive at ~185px each. Country names truncate to `Camero… Guatem… St. Vi…
  Maurit… Uzbeki…`.
- **Thread reader** (`ThemeDetail`): the best-adapted surface in the app.

**L3 Workbench.** `WorkbenchPanel.css:10` is `width: 168px` with no `≤768` rule
in any of its six files. Both inner columns survive at 375px.

**Scale of divergence.** Exactly **5 files** consume `useIsMobile` — unchanged
since 07-13.

### 1.2 Corrections to the 07-13 audit

1. **Reader occlusion: CONFIRMED, and worse than described.** The audit flagged
   it ⚠ VERIFY. Measured: `.theme-detail-overlay` is `z-index 9000, inset 0`,
   `.theme-detail-panel` has `padding: 56px 16px 16px` (`ThemeDetail.css:1288`),
   while `.mobile-tabbar` is `z-index 9500, height 57px` at `top 755`. The last
   ~41px of every read, plus whatever the focus chip covers, sits under the tab
   bar. Visually confirmed: a receipt line rendered cut in half.
2. **The Brief choropleth is NOT hidden on mobile.** `.brief-minimap` renders
   at 213px on a phone. The audit's `display:none` reading is stale.

---

## 2. The owner's answers

Asked in session, recorded verbatim in intent:

**What do you do on the phone?** — *Glance: Brief plus reader.* But the reader
must absorb what L2 already connects: "cuando abre un thread... muestra el mapa,
las conexiones que tiene, los países que se conectan... todas las otras cosas
que ya hemos venido diciendo que se conectan entre sí en la app general." Light
discover stays; heavy discover — walking the constellation, driving the map —
must remain a reason to open the laptop. *"Es un c que tiene b y a, pero es un c."*

**Workbench on mobile?** — **Light capture.** Pin from the lens, see the current
investigation's pins. Constellation, research plan and dossier get an honest
"this is worked on the computer" state plus export.

**Universe / Orbital on mobile?** — **Hidden**, "pero que salgan las
constelaciones en la búsqueda" — the measured neighbourhood surfaces through
**search**, not through a canvas.

---

## 3. The model — one anatomy, N scopes

The phone stops being four sibling global surfaces and becomes **one surface
that re-scopes**. This is #234 (focus propagation) promoted from a behaviour
into the mobile information architecture.

**The Lens has five sections, always in this order, at every scope:**

1. **identity** — title, the measured line (signals · countries · tone · active
   since), honesty chips (court, degraded, tier)
2. **what it says** — the read: receipts, source language, tier chips
3. **where it lives** — mini-map scoped to this thing + country rows with counts
4. **connected** — measured siblings, each carrying its receipt
   (`↔ 2 countries shared`, `↔ rare actor shared`)
5. **attention** — forum / wiki scoped to this thing, labelled `UNVERIFIED`

**Scopes:** *field* (nothing focused — the global version of the same five
sections) · *thread* · *country* · *person* · *signal*.

**Movement:** every row in `connected` and every country in `where it lives` is
a tap that **re-scopes the same lens in place** — it does not stack an overlay.
The header carries a breadcrumb; the existing edge-swipe-back
(`App.tsx:855-876`) walks it.

**What this absorbs, rather than deletes:**

| today | becomes |
|---|---|
| Map tab | §3 `where it lives`, always scoped |
| Threads tab | §2 `what it says` at *field* scope — `NarrativeThreads` still renders it, so its title-first mobile fix is still required |
| Pulse tab | §5 `attention`, always scoped |
| Universe / Orbital | §4 `connected` — the constellation as tappable measured rows with receipts |
| Thread reader overlay | the Lens itself |

**Returning to the tab.** The Lens remembers its scope. Leaving for `Brief` or
`Live` and coming back returns you to what you were looking at, with the
breadcrumb intact — it does not reset to *field*. Scope resets only when you
walk the breadcrumb out or explicitly clear the focus (the existing focus-chip
`✕`).

---

## 4. The shell

**Three tabs: `Brief ◈ · Lens ◎ · Live ≋`.**

The Brief becomes the phone's home. `Lens` and `Live` are the console.

**Routing.** The `Brief` tab **navigates to `/brief`**; it is not re-mounted
inside `/app`. `main.tsx`'s `AppBriefKeepAlive` already keeps both trees mounted
and toggles them with `display`, so the switch is instant with no remount, and
deep links, the PWA `start_url` and offline-last-Brief all keep working
unchanged. The tab bar becomes a **shared component rendered by both routes**
under 768px.

**Desktop is untouched.** Every change in this spec is inside a `≤768px` branch
or a `useIsMobile` guard. Any diff that alters desktop rendering is a bug in the
slice, not a design decision.

---

## 5. Per-surface design

### 5.1 L1 Brief — the home (news at ~400px, down from 1707)

Nothing is deleted. Every full-width block that is not news becomes **a single
line that expands on tap**.

| block | today | proposed | how |
|---|---|---|---|
| masthead | 302 | ~140 | title + date + MEASURED chip in one band; HOME / OPEN CONSOLE / SHARE move into a top-bar overflow |
| freshness | 141 | ~44 | collapses to `sealed 11h ago · full text 1/48 ▸`, tap expands the full wording |
| 6 stat cards | 542 | ~120 | sideways-scrolling vitals strip; all six survive, none truncated |
| markets band | 463 | ~44 | one line, expands on tap — it already labels itself "live overlay, not part of the sealed edition" |
| section tabs | 95 | ~48 | single scrolling row |
| story cards | 478–1021 | ~200 collapsed | title, measured line, why-now, **one** receipt; `+11 receipts` expands in place |
| minimap | 213 | 0 | not rendered on phone, and the world GeoJSON stops downloading; "Most Active" list stays |

Tapping a story goes to the **Lens tab**, not to a full route change with a
cold reader.

The freshness line, the vitals and the coverage-gaps box are honesty rails.
They compress; they do not disappear.

### 5.2 L2 Lens — the pivot surface

Built by promoting `ThemeDetail` from a covered overlay into the tab's own
surface, and adding the two sections it lacks (`where it lives`, `connected`).
It already serves `attention` scoped to the thread, and already has the
best-adapted mobile CSS in the app (`ThemeDetail.css:1276-1300`) — 44px source
rows, `touch-action: pan-y`, body-scroll lock.

Per-scope data sources, all existing endpoints:

| scope | identity + what it says | where it lives | connected | attention |
|---|---|---|---|---|
| field | `/briefing` top threads | `/heat/countries` + Most Active | — (needs a focus, stated honestly) | `/public-attention` global |
| thread | `/theme/{id}` | thread country counts | measured siblings + receipt | `/public-attention?topic=` |
| country | `/country-edition` / `/threads?country_code=` | co-occurring countries | co-occurrence with receipt | `/public-attention?country=` |
| person | `/focus` | focus countries | threads via `?person=` | scoped via `useFocusRelation` |
| signal | `/signal/{id}/context` | signal country | connected threads + semantic neighbours | — |

An empty section renders an **honest empty state with its reason**, never a
blank or a fabricated filler. A degraded lane says so.

### 5.3 L2 Live — the stream

- Rows 39px → **≥48px**; headline gets **two lines** instead of one truncated
  line; country and time drop to a compact meta line.
- The lane strip keeps **all six lanes** and scrolls sideways with a visible
  fade edge. Dropping lanes to fit would be silent filtering — forbidden.
- Tapping a signal re-scopes the Lens to that signal.

### 5.4 Search — where the constellation lives on a phone

Search becomes a primary verb: an icon in the top bar of all three tabs opening
a full-screen sheet. Thread results carry **their measured neighbours as rows**,
each with its receipt. Any row taps into the Lens.

This is the mobile answer to Universe: the constellation stated as measured
rows, not as a cloud that cannot be driven with a thumb.

### 5.5 L3 Workbench — light capture

- `◆ pin` works from the Lens at every scope.
- The current investigation's pin list is readable on the phone.
- Constellation, research plan and dossier render an **honest state**
  ("this investigation is worked on the computer") plus the existing JSON
  export.
- Reachable from the `···` overflow. **Not a tab.**
- `WorkbenchPanel.css` textareas go to 16px so iOS stops auto-zooming.

### 5.6 L0 Landing

One real gap: the four nav links vanish under `md` with nothing replacing them.
Add a minimal menu or fold them into the CTA area. Lowest priority; last slice.

---

## 6. Shared mobile primitives

These are cross-cutting and apply to every surface above.

- **44px minimum** for anything that navigates. Decorative chips may stay small.
- **No hover-only affordances.** `data-tip` tooltips are suppressed under
  `(hover: none)`. This kills the tooltip caught stuck open over a thread title.
- **Bottom reservation.** Every full-screen surface reserves
  `calc(57px + env(safe-area-inset-bottom))` at the bottom, from one shared CSS
  custom property. This is where the reader occlusion dies.
- **16px inputs** (iOS zoom).
- **Honesty rails are untouchable.** Tier chips, label-court chips, `degraded`,
  `UNVERIFIED`, "measured, not asserted", state-media marks. **If a chip does
  not fit, it wraps — it does not disappear.** Removing an honesty label to gain
  pixels is forbidden by this spec.
- **One breakpoint: 768**, inclusive (`useIsMobile.ts:6`). No tablet tier.

---

## 7. The honest boundary — what the phone does not do

Stated in the product, never silently missing:

- **Universe / Orbital** are not mounted under 768px. The Lens's `connected`
  section is the mobile answer, and the app says the semantic field is walked on
  the computer.
- **Heavy discover** — chaining hops, driving the map, arranging panels — stays
  a deliberate reason to open the laptop. This is a product position, not a gap.
- **Workbench analysis** (constellation, plan, dossier) is desktop. Capture is
  mobile.
- **Panel grid** is already bypassed on mobile.

---

## 8. Out of scope

- Any backend change. Every surface above is served by an existing endpoint.
- Desktop layout changes of any kind.
- Option C from the brainstorm (tab-less single document). It is this design
  with the tab bar removed and can be revisited once this model is proven.
- Universe touch gestures.
- Full mobile Workbench analysis.

---

## 9. Acceptance

Every slice must pass **both** before the next one starts:

1. **375×812 browser verification** — screenshot the changed surface, and where
   the claim is a measurement (a height, a tap target, an occlusion), verify it
   with a DOM measurement, not by eye.
2. **1440 desktop regression check** — the same surface, unchanged.

Plus, per slice: `npm run build` green (not just `tsc`), and the existing vitest
suite green.

**Spec-level acceptance, measured the same way it was diagnosed:**

| claim | measurement |
|---|---|
| Brief leads with news | first story `top` < 500px at 375 wide |
| Reader is never covered | reader content bottom ≤ tab-bar top |
| Touch targets | no navigating element < 44px |
| Lens re-scopes | thread → country → back, breadcrumb correct, no overlay stack |
| Pulse readable | no truncated country name at 375 |
| Map fits | world visible in portrait, or replaced by the scoped section |
| Honesty survives | tier / court / degraded / UNVERIFIED all present at 375 |
| Divergence grew | `useIsMobile` consumer count > 5 |

---

## 10. Risks

- **The Lens is the whole design.** If `connected` cannot be assembled cheaply
  per scope, the lens degrades to a nicer reader. Mitigation: the section is
  honest-empty by construction, and thread siblings already exist behind
  `GET /api/v2/story/{id}/siblings` (live) plus co-occurrence in the dossier
  path.
- **Story-lens interaction.** `STORY_LENS_AUTO` ships dark after its own gate
  said no over false neighbours. This spec's `connected` section must inherit
  that verdict: it renders **measured** siblings with receipts, and it does not
  turn the story lens on. If the underlying ranking is not trustworthy at a
  given scope, the section says so rather than rendering it.
- **Keep-alive shell.** Sharing a tab bar across two routes touches
  `main.tsx`'s mount-once contract. The mitigation is that the tab bar only
  *navigates*; it holds no state.
- **Scope creep into desktop.** Guarded by the 1440 regression check on every
  slice.

---

## 11. Open, deliberately

- Whether `Live` earns a permanent tab or eventually folds into the Lens's field
  scope. Measure after the model ships.
- Whether the Brief's section tabs (World / Under the Radar / Culture) survive
  as tabs or become in-page anchors once the page is 400px shorter.
