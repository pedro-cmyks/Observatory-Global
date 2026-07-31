# Mobile L0–L3 Audit + Redesign Plan — 2026-07-13

**Scope:** audit the mobile (≤768px) experience of all four Atlas surfaces (L0
Landing, L1 Brief, L2 Console, L3 Workbench) by reading the code, classify every
major element, identify where mobile should surface *different* information /
commands (owner's thesis), and produce a prioritized mobile-native redesign plan.

**This is an audit + plan only. No product code was changed.**

Method: read the frontend directly (`frontend-v2/src`) with three parallel
deep-reads (L1/L2/L3) cross-checked against my own reads of L0, the CSS media
queries, `App.tsx`, and the prior mobile specs. Every claim below carries a
`file:line`. Where I could not verify a behavior without running the app (visual
occlusion, live gesture feel), I say so explicitly.

---

## 0. TL;DR

- **Mobile is a real IA, not an accident.** L2 early-returns a JS-driven 4-tab
  full-screen shell (**Map ◍ · Threads ⌗ · Stream ≋ · Pulse ◎**,
  `App.tsx:1982-2032`), and there are genuinely mobile-native touches: a
  swipe-from-edge back gesture (`App.tsx:855-876`), an Android/iOS install prompt
  (`InstallPrompt.tsx`), a separate mobile onboarding tour (`OnboardingCoachmark.tsx:75-96`),
  and a full-screen touch-sized thread reader (`ThemeDetail.css:1276-1300`).
- **But almost all *content* inside those shells is desktop, shrunk.** The
  divergence is astonishingly thin: only **5 files** consume `useIsMobile`
  (App, ThemeDetail, InstallPrompt, OnboardingCoachmark, CountryFocusWalkthrough).
  L1 Brief has **zero** viewport awareness (100% CSS re-stack). The L3 Workbench
  and its six files have **zero** mobile code — its inner 168px sidebar never
  collapses, so the "frozen route" column is ~180px wide on a phone and the
  constellation shrinks to illegibility.
- **Mobile carries the *same commands* as desktop, just wrapped.** The command
  bar keeps Search + time + WORKBENCH + UNIVERSE (`App.tsx:1260-1332`); nothing
  is re-conceived for a phone. This is the crux of the owner's thesis: mobile is
  a smaller desktop, not a different tool.
- **Two documented "truths" are stale.** CLAUDE.md says the map is *unmounted*
  on mobile — it is not; the SVG `EqualEarthMap` stays mounted and is
  `display`-toggled (`App.tsx:1987`, `App.css:1695-1705`, survival hack
  `EqualEarthMap.tsx:196-214`). And there is dead/superseded mobile CSS
  (`App.css:908-923`, `889-906`).
- **Recommended first slice:** an L2 per-tab content pass (make the four tabs
  full-height and touch-first) + fix the tab-bar/reader occlusion — the surface
  that gets the most mobile use and is closest to done.

---

## 1. What I could and couldn't verify

**Verified from code (high confidence):** which components branch on `isMobile`;
the tab-shell render path and CSS; the command-bar collapse; the Brief's
CSS-only re-stack; the Workbench's missing mobile layout; z-index values;
telemetry viewport-independence; the store being localStorage-only.

**Inferred but NOT visually confirmed (flagged inline as ⚠ VERIFY):**
- The bottom tab bar (`z-9500`, `App.css:1713`) renders *over* the full-screen
  thread reader (`.theme-detail-overlay z-9000`, `ThemeDetail.css:1280`) and the
  country drill-in (`z-9100`, `CountryThemePanel.css:278`). Those overlays are
  `position:fixed; inset:0` and reserve only 16px bottom padding
  (`ThemeDetail.css:1288`), while the tab bar is 56px + safe-area. The CSS math
  implies the last ~40–56px of a thread read is occluded by the tab bar. Needs a
  device screenshot to confirm whether this is deliberate (keep nav reachable) or
  a content-occlusion bug.
- The swipe-back gesture "feel" (`App.tsx:855-876`) and the map "toasts on mobile"
  note (`EqualEarthMap.tsx` ~706) are runtime behaviors I read but did not drive.
- Whether the `X6` mobile pass scheduled for 2026-07-11 (CLAUDE.md) actually ran;
  I audited the code as it stands on 2026-07-13.

---

## 2. The shared mobile substrate (all four surfaces)

**Breakpoint.** `MOBILE_MAX = 768`, inclusive (`useIsMobile.ts:6,9-10`). One
number, no tablet tier. `useIsMobile` re-evaluates on resize (`:14-25`).

**Keep-alive shell.** `main.tsx:32-54` (`AppBriefKeepAlive`): `/app` (L2+L3) and
`/brief` (L1) each mount **once** and are then hidden with `display:none` on route
switch (never unmounted). Landing (`/`) and Docs (`/docs`) are ordinary routes.
So on a phone, hopping Brief↔Console keeps both trees + all state alive.

**Who is actually mobile-aware.** Only these consume `useIsMobile`:

| File | Mobile-aware? | What it does on mobile |
|---|---|---|
| `App.tsx` | ✅ | 5 divergences: tab shell + tab bar + auto-stream + skip-grid + hide-reset |
| `ThemeDetail.tsx` | ✅ | full-screen overlay + body-scroll lock (`:258-265`) |
| `InstallPrompt.tsx` | ✅ | Android/iOS install paths (`:113`) |
| `OnboardingCoachmark.tsx` | ✅ | separate `MOBILE_STEPS` tour (`:75-96,135-136`) |
| `CountryFocusWalkthrough.tsx` | ✅ | centered card, not the colliding bottom sheet |
| `BriefNewspaper.tsx` (L1) | ❌ | **zero** — 100% CSS media queries |
| Workbench ×6 (L3) | ❌ | **zero** — only external `App.css` overlay stacking |
| Everything else | ❌ | pure-CSS responsive or desktop-shrunk |

**Genuinely mobile-native elements that already exist** (credit where due):
1. The 4-tab full-screen IA (`App.tsx:1982-2032`) — "fewer decisions per screen."
2. Swipe-right-from-left-edge = back (`App.tsx:855-876`, `x<40 && dx>70`).
3. PWA install (Android `beforeinstallprompt`, iOS Share→Add-to-Home;
   `InstallPrompt.tsx:35,139-227`) + offline-last-Brief banner
   (`BriefNewspaper.tsx:580`, `OfflineBanner.tsx`).
4. A phone-specific onboarding tour that teaches the tab model, not the desktop
   panels (`OnboardingCoachmark.tsx:70-96`).
5. Touch-sized full-screen thread reader: 44px source rows, `touch-action:pan-y`,
   body-scroll lock (`ThemeDetail.css:1276-1291`, `ThemeDetail.tsx:260-265`).
6. Focus chip floats above the tab bar so it's never buried
   (`FocusIndicator.css:71-77`).

**The mobile "travel" model (important).** On a phone you do not stack overlays.
Secondary panels render **inline inside the Stream slot** via a state machine
(`App.tsx:356-363`, `1760-1840`), and any drill-in **auto-switches you to the
Stream tab** (`App.tsx:881-891`). So: tap a country on the Map tab → you land on
the Stream tab showing `CountryBrief` → tap a thread → `ThemeDetail`/`ThreadFocusPanel`
in the same slot → tap a source → `SourceProfile`. Back = Escape / edge-swipe /
in-panel "← STREAM" (`App.tsx:832-876`). **The three non-Stream tabs (Map,
Threads, Pulse) are entry surfaces; everything you open funnels into Stream.**

---

## 3. Per-surface audit + classification

Classification key: **(a) mobile-native** = different info/interaction built for a
phone; **(b) shrunk-works** = desktop element that re-flows acceptably; **(c)
shrunk-breaks** = desktop element that fights the mobile model (touch, legibility,
occlusion, wasted taps).

### L0 — Landing (`/`, `pages/Landing.tsx` + `Landing.css`)

**Current mobile behavior.** A standard Tailwind responsive marketing page:
single-column stacks via `grid-cols-1 → md/lg:grid-cols-*` and
`flex-col md:flex-row` (`Landing.tsx:179,205,229,258,281,316,332`). Hero scales
`text-5xl md:text-7xl` (`:135`). `Landing.css` has no mobile media query at all
(only `prefers-reduced-motion`, `:104-107`) — all responsiveness is Tailwind
utilities. Data (live signals, movers, voice-mix stats) is fetched and shown
identically at every width.

| Element | Class | Note |
|---|---|---|
| Hero, section stacks, CTA | **(b)** | Clean single-column; no horizontal overflow. Prior spec called L0 "flawless-enough" (2026-06-25 review). |
| Top nav links (Moving/How/Docs/Support) | **(c)** | `hidden md:flex` (`:113`) — **hidden on mobile with NO hamburger/menu replacement** (grep: no drawer/Sheet/menu-toggle in `Landing.tsx`). Only the Atlas logo + "Read the brief" CTA (`:120`) survive. In-page anchors are reachable only through hero body copy. |
| "Moving right now" lead cards | **(b)** | Deep-link to `/app?theme=…&entry=landing` (`:180`); fine on tap. |
| Hero mini-graph caption | **(c)** | Prior spec flagged it "near-illegible at phone size" (2026-06-25 review §L0). |

**Verdict:** L0 is a legitimately responsive page and the *lowest priority*. The
one real gap is the missing mobile nav (links vanish). A landing page is also the
surface where the owner's "different commands" thesis matters least.

### L1 — Brief (`/brief`, `pages/BriefNewspaper.tsx` + `.css`)

**Current mobile behavior.** `BriefNewspaper.tsx` has **zero** viewport detection
(the only `768` is a country code, `:42`). 100% of mobile behavior is 5 CSS media
blocks over one identical DOM tree. It re-stacks to a single column: lead story,
watchlist, Heating-Up strip (→ horizontal scroll `:1297`), coverage-gaps box, and
"Most Active" list; the 4-col back-matter collapses to 1 (`:1283`).

| Element | Class | Evidence |
|---|---|---|
| Single-column re-stack, tap targets, font bumps | **(b)** | Competent: `min-height:56px` rows (`:1292`), heat strip becomes a horizontal scroller (`:1297`), serif bumped to 13–15px (`:1317-1322`), 375px sideways-overflow bug fixed (`:1307-1314`). |
| Choropleth map | **(b)/(c)** | `display:none` on mobile (`:1278`, "a choropleth is not a phone surface") — good call — **but the `<ComposableMap>` still renders and the world GeoJSON still downloads** (`BriefNewspaper.tsx:953-987`); hidden, not skipped → wasted mobile bytes/paint. |
| Watchlist per-row headline (incl. `TranslatableHeadline`) | **(c) BUG** | `.brief-thread-headline { display:none }` at **≤720px** (`:1241`); the 768 block only resizes it, never restores display. So on a real 375px phone the **watchlist rows lose their headline/translation** — visible only in the narrow 721–768 band. |
| "Full-screen mobile thread read" | **n/a here** | Not in the Brief. `openThread` (`:468-481`) **navigates away** to `/app` (`goToAtlas`, `:459-466`); the full-screen reader is the console's `ThemeDetail`. The Brief has no in-place reader. |
| Telemetry | **(b)** | `brief_open` (`:310`), `brief_scroll_depth` (`:313-323`), `brief_section_click` (`:435,462`), `brief_thread_open` (`:474`) — all viewport-independent; mobile is measured. |
| Legacy dead CSS | cleanup | `.brief-atlas-list` (`:638-640`) and `.brief-columns` rules target markup the current TSX no longer renders. |

**Verdict:** a carefully-done **responsive re-stack, not mobile-native**. Same
sections, same data, same interactions; only reflow differs. The one genuinely
mobile interaction it promises (full-screen read) is delegated to L2. Real bugs:
the hidden watchlist headline (≤720) and the still-downloaded hidden map.

### L2 — Console (`/app`, `App.tsx` + `App.css`)

**Current mobile behavior.** At ≤768 the render forks (`App.tsx:1982` early
return): all five panels stay mounted; a `mobile-tab-${mobileTab}` class shows one
at a time (`App.css:1695-1705`); react-grid-layout is bypassed entirely
(`App.tsx:1217,1996`). A fixed bottom tab bar (`App.tsx:2016-2032`) switches
Map/Threads/Stream/Pulse (default **stream**, `:315`).

| Element | Class | Evidence / note |
|---|---|---|
| 4-tab full-screen IA + tab bar | **(a)** | `App.tsx:1982-2032`; one surface at a time, safe-area aware (`App.css:1708-1722`). Good bones. |
| Swipe-back + inline Stream travel model | **(a)** | `App.tsx:855-876` (edge swipe), `881-891` (auto-stream). Coherent phone navigation. |
| Map tab = `EqualEarthMap` | **(b)/(c)** | **Mounted, not unmounted** (`App.tsx:1520,1987`; CLAUDE.md note is stale). SVG survives `display:none` via rAF box-poll (`EqualEarthMap.tsx:196-214`). But it's a desktop pan/zoom/**hover** map on a touch screen; layer tabs include dead PLANE / sparse SHIPS (2026-06-25 spec §L2). |
| Stream tab = `SignalStream` (the default) | **(b)** | Only 3 lines of mobile CSS — height caps (`SignalStream.css:441-444`). Otherwise desktop. |
| Threads tab = `NarrativeThreads` | **(b)** | One genuinely touch-aware rule: `@media (…768px),(hover:none)` un-hides the hover-only labels (`NarrativeThreads.css:516-522`). Rest is desktop. |
| Pulse tab = intel dock (`AnomalyPanel` + `SourceIntegrityPanel`) | **(c)** | `App.tsx:1926-1980,1991`. **`AnomalyPanel.css` has zero media queries** — the phone's Public-Attention surface is pure desktop-shrunk (matches the L2 review "verify Pulse content at 375px" concern). |
| Full-screen thread reader (`ThemeDetail`) | **(a)** | `ThemeDetail.css:1276-1300` + scroll-lock; the funnel destination of the travel model. The best-adapted content surface. ⚠ VERIFY tab-bar occlusion (§1). |
| Command bar | **(b)/(c)** | Wraps to a full-width column (`App.css:842-875`); stats + UTC clock hidden (`:789-792,828-831`); time → compact dropdown (`:1627-1628`); WATCH/BRIEF icon-only (`:1633`). **UNIVERSE + WORKBENCH stay visible** (`App.tsx:1317-1332`) — i.e. **same commands as desktop, just cramped**. |
| UNIVERSE view + Orbital view | **(c)** | Reachable on mobile (`App.tsx:1326-1332`, GLOBE\|UNIVERSE tab `:1446`). `UniverseView.tsx`/`OrbitalThreadView.tsx` have **no mobile awareness** — full-screen SVG clouds driven by drag/zoom/hover/twist; the "universe gestures" were flagged unfinished on touch (#236 / L2 review). |
| Dead / superseded mobile CSS | cleanup | `.terminal-layout` single-column grid (`App.css:908-923`) is out-specified by the tab-toggle block (`:1683-1705`); `.time-controls` mobile rules (`:889-906`) are dead behind `display:none` (`:1627`). |

**Verdict:** the **shell is mobile-native; the contents are mostly desktop-shrunk.**
The Stream/Threads/Pulse/Map panels were built for a mouse and re-flowed, not
re-conceived. Pulse (zero mobile CSS) and the heavy SVG viz (Universe/Orbital) are
the clearest "shrunk-breaks."

### L3 — Workbench (overlay inside `/app`)

**Current mobile behavior.** The six Workbench files (`WorkbenchPanel`,
`ResearchPlanPanel`, `WorkbenchConstellation` ×tsx/css + `lib/workbench.ts`)
contain **zero** mobile code. All adaptation is external `App.css`: overlay →
full-screen (`:1535-1545`), outer two columns stack at ≤900 (`:1530-1533`), the
model-explainer strip hides ≤1100 (`:1861-1863`).

| Element | Class | Evidence |
|---|---|---|
| Reaching the Workbench | **(c)** | Only via the command-bar **WORKBENCH** pill or search "Start investigation" (`App.tsx:1317-1325,1270-1276`). **Not in the bottom tab bar** — the investigation surface is a second-class citizen on the phone IA. |
| Full-screen overlay + outer-column stacking | **(b)** | `App.css:1535-1545,1530-1533`; the two outer columns split height ~1.1:1 and scroll internally. |
| Inner `WorkbenchPanel` (168px sidebar + main) | **(c) BREAKS** | `WorkbenchPanel.css:8` fixed `width:168px`, no `max-width`/768 rule → on 375px the "frozen route" column is **~180–200px** (the "154px apretado / colapsable" note). |
| `WorkbenchConstellation` | **(c) BREAKS** | `viewBox 640×460` (`DossierConnections.tsx:479`), no mobile branch; inside the ~180px column it renders ~180×130 with 2–3px labels → **illegible**; no "too small" placeholder. |
| Per-pin note textarea | **(c)** | Auto-grows and wraps (usable), but `font-size:11px` (`WorkbenchPanel.css:231`) → **iOS auto-zoom on focus**; sits in the cramped column. |
| Store / durability | **(b)** | localStorage-only (`workbench.ts:67-68`); **no cross-device sync**; export JSON is the bridge (`:249-261`). Expected, but worth surfacing to phone users. |

**Verdict:** **desktop-oriented, minimally shimmed.** The overlay opens and the
outer columns stack, but the inner two-column layout is untouched, so the actual
investigation content (route + constellation) is cramped-to-illegible on a phone.
Note: the old force-graph mobile concern (2026-06-25 spec §L3) is **obsolete** —
`InteractiveWorkspace`/force-graph was retired (W1); the constellation replaced it.

---

## 4. The owner's thesis: where mobile should be *different*, not smaller

The product owner's position — mobile interaction is fundamentally different
(different commands, different navigation, different information) — is
**correct and largely unmet**. Concretely, today:

1. **Same command set, cramped.** The mobile command bar keeps Search + time +
   WORKBENCH + UNIVERSE (`App.tsx:1260-1332`). A phone should offer *fewer,
   bigger, different* commands. On a phone the primary verbs are **search, follow
   a thread, and glance at what's moving** — not "arrange panels," "toggle map
   layers," or "drive a semantic universe cloud."
2. **Desktop metaphors that don't translate.** The Map (pan/zoom/hover), the
   Universe/Orbital clouds (drag/twist/hover), and the reorderable grid are
   mouse metaphors. A phone wants a **ranked list / card feed** and **tap-to-pivot**,
   not a spatial canvas. The map's value on a phone is "where is hot" — better
   served by the existing "Most Active" list pattern (already used in the Brief,
   `BriefNewspaper.tsx:989-1001`) than by a shrunk choropleth.
3. **Different information density.** Desktop shows five panels at once so the
   analyst can correlate. A phone should show **one decision at a time** with a
   *summary-first* payload: lead thread, what moved, what's missing — the Brief's
   instinct — and let drill-in fetch detail. Several panels already carry
   summary-vs-detail (NarrativeThreads de-densify `:516-522`); mobile should lead
   with the summary, not reveal-on-hover (there is no hover).
4. **Investigation is a phone-second-class citizen.** The Workbench is reachable
   but not in the tab bar, and its content is cramped. If capturing/pinning on the
   go is a real mobile job, it needs a first-class, single-column mobile treatment
   (or an explicit "best on desktop" stance — an owner decision).
5. **The travel model is the one thing that IS phone-shaped** — funnel-to-Stream +
   edge-swipe-back (`App.tsx:855-891`). Build *with* it, not against it: the
   redesign should lean into "one surface, tap to pivot, swipe to go back."

---

## 5. Redesign plan per surface (scoped, component-referenced)

Principle: **keep the mobile-native shell, re-conceive the contents surface by
surface.** Prefer small vertical slices that ship independently.

### L2 Console — highest leverage (most mobile use, best bones)

- **L2-1 · Tab content full-height + touch-first (per tab).**
  - *Stream* (`SignalStream`): remove the desktop height caps (`SignalStream.css:441-444`),
    make the list fill the tab, add pull-to-refresh affordance; it's the default
    tab and deserves to feel native.
  - *Threads* (`NarrativeThreads`): lead summary-first at rest (already touch-aware
    at `:516-522`); make rows ≥48px, tap = open, no hover dependency.
  - *Pulse* (`AnomalyPanel` + `SourceIntegrityPanel`): author the **missing**
    mobile CSS (`AnomalyPanel.css` has none) — single-column, big tap rows for
    trends/wiki/forum.
  - *Map* (`EqualEarthMap`): on mobile, demote pan/zoom; surface a **"what's hot"
    ranked list** overlay (reuse the Brief "Most Active" pattern) as the primary
    read, with the SVG as a secondary glance. Hide dead PLANE / sparse SHIPS layer
    tabs on mobile.
- **L2-2 · Fix the tab-bar/reader occlusion (⚠ VERIFY first).** Either raise the
  full-screen overlays above the tab bar and give the reader a bottom "close" bar,
  or add `padding-bottom: calc(56px + safe-area)` to `.theme-detail-overlay` /
  `.country-theme-panel` so the last lines clear the tab bar
  (`ThemeDetail.css:1276`, `CountryThemePanel.css:272`).
- **L2-3 · Mobile command reduction.** Move UNIVERSE (and the grid-only bits) out
  of the mobile command bar; keep Search + time + a single "Investigate" affordance.
  Decide whether UNIVERSE belongs on a phone at all (owner call — see §6).
- **L2-4 · Dead-CSS cleanup.** Delete the superseded `.terminal-layout` single-col
  grid (`App.css:908-923`) and dead `.time-controls` mobile rules (`:889-906`);
  correct the stale "unmounts map on mobile" claim in CLAUDE.md.

### L1 Brief — second (already decent, cheap wins)

- **L1-1 · Fix the hidden watchlist headline** (`BriefNewspaper.css:1241`): restore
  `.brief-thread-headline` display in the ≤768 block (or lift the hide to a
  narrower band) so phones keep watchlist headlines + translations.
- **L1-2 · Actually skip the map on mobile.** Gate the `<ComposableMap>` render on
  a viewport check (introduce `useIsMobile` in `BriefNewspaper.tsx`, or an
  IntersectionObserver) so the world GeoJSON doesn't download on phones — it's
  `display:none` today (`:1278`) but still fetched.
- **L1-3 · Optional mobile-native lead treatment.** A swipeable lead-story card and
  a "tap to read" that opens the reader *without a full route change* (today
  `openThread` navigates to `/app`, `:468-481`) — reduces the jump. Owner call on
  whether the read should stay in-Brief.

### L3 Workbench — third (needs the most, used least on mobile)

- **L3-1 · Collapse the inner sidebar on mobile.** Author a `≤768` treatment in
  `WorkbenchPanel.css` that turns the 168px sidebar (`:8`) into a top dropdown /
  drawer so the frozen-route column gets full width.
- **L3-2 · Constellation mobile fallback.** In `WorkbenchConstellation`, below a
  container-width threshold render a **relations list** (topic → connected topics)
  instead of the illegible ~180×130 SVG (`DossierConnections.tsx:479`), or show an
  explicit "open on desktop for the map" placeholder.
- **L3-3 · Textarea 16px on mobile** (`WorkbenchPanel.css:231`) to kill iOS
  auto-zoom.
- **L3-4 · (owner decision) Tab-bar entry.** If mobile capture matters, add a 5th
  tab or a persistent "＋ pin / investigation" affordance; otherwise state "Workbench
  is best on desktop" explicitly.

### L0 Landing — lowest (one real gap)

- **L0-1 · Mobile nav.** Add a small menu (or move the four links into the CTA area)
  so Moving/How/Docs/Support aren't unreachable on a phone (`Landing.tsx:113`).
- **L0-2 · Hero caption legibility** at phone size (2026-06-25 spec §L0).

### Recommended build order

1. **L2-1 + L2-2** (tab content + occlusion fix) — the phone's core loop.
2. **L1-1 + L1-2** (watchlist headline + real map skip) — cheap, high-quality-signal.
3. **L2-3** (command reduction) — enacts the "different commands" thesis.
4. **L3-1 + L3-2 + L3-3** (Workbench mobile layout) — the biggest build; do after
   the owner decides L3's mobile ambition (§6).
5. **L0-1**, **L2-4**, docs — cleanup.

---

## 6. Decisions that need the owner

1. **Is the Universe/Orbital view a phone surface at all?** It's a spatial,
   hover/drag metaphor. Options: (a) keep + build touch gestures (big), (b) replace
   with a ranked list on mobile, (c) hide on mobile with "best on desktop." Affects
   L2-3.
2. **How ambitious is L3 on mobile?** First-class capture (tab-bar entry + full
   mobile layout) vs. an honest "Workbench is a desktop tool." Affects L3-1..4.
3. **Should the Brief read happen in-place on mobile** or keep routing to the L2
   `ThemeDetail`? (Affects L1-3 and whether the Brief becomes self-contained.)
4. **Map on a phone:** ranked "what's hot" list as primary (my recommendation) vs.
   keep the shrunk choropleth. Affects L2-1 (Map).
5. **The tab-bar-over-reader question** (⚠ VERIFY): is the tab bar meant to stay
   visible over a thread read (nav always reachable), or should the reader be
   truly full-screen? Affects L2-2.

---

## 7. Recommended first 2–3 build slices

1. **Slice 1 — L2 "make the four tabs feel native" + occlusion fix.**
   Author mobile CSS for the Pulse dock (`AnomalyPanel.css`, currently none), let
   Stream/Threads fill full height and lead summary-first, and resolve the
   tab-bar/reader overlap (`ThemeDetail.css:1276`, `CountryThemePanel.css:272`,
   tab bar `App.css:1713`). Ship the map-as-list overlay if the owner greenlights
   (§6.4). *Scoped, high-traffic, no new IA.* First: a device screenshot pass at
   375×812 to confirm the occlusion (§1).

2. **Slice 2 — L1 Brief two bug-fixes.**
   Restore the watchlist headline below 720px (`BriefNewspaper.css:1241`) and
   truly skip the choropleth download on mobile (`BriefNewspaper.tsx:953-987`,
   `:1278`). Small, correctness-improving, measurable (telemetry already fires).

3. **Slice 3 — L2 command reduction (the thesis, concretely).**
   Trim the mobile command bar to the phone verbs (Search + time + one
   "Investigate" entry), pending the §6.1 UNIVERSE decision; delete the dead mobile
   CSS (`App.css:908-923`, `889-906`) in the same pass. This is the smallest change
   that starts making mobile a *different tool*, not a smaller desktop.

**Deliberately deferred to its own brainstorm:** the full L3 Workbench mobile
layout (L3-1..4) and any Universe/Orbital touch-gesture build — both are scoped
redesigns that need an owner decision (§6.1, §6.2) before code.
