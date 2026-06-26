# Mobile multi-level review (L0–L3) — 2026-06-25

Same exercise as the #225/#228 desktop surface reviews, now for mobile: walk
every level at 375px, compare to the desktop ("normal") intent, and drive each
toward *flawless*. Audited live in the preview at 375×812.

Goal: leave mobile **listo, flawless, hermoso**.

## Level map (mobile vs desktop)

| Level | Route | Desktop intent | Mobile state (this audit) |
|---|---|---|---|
| **L0 Landing** | `/` | Marketing hero + CTAs | ✅ **Good.** Tailwind, fully responsive — clean masthead, big hero "Follow the thread.", readable copy, CTAs. No horizontal overflow. |
| **L1 Brief** | `/brief` | Front-page narrative read | ✅ **Good** (MVP work). Single-column feed, choropleth hidden, readable lead + watchlist, honest chips, offline banner. |
| **L2 Console** | `/app` | Desktop cockpit (3-col grid: map + stream + panels) | ⚠️ **Was cramped; now improved.** Mobile stacks the grid (radar → stream → threads → dock, internal scroll). Fixed this session. Still a long scroll. |
| **L3 Workbench / Workspace** | `/app` overlay + force-graph | Investigation memory + connection map | ❌ **Desktop-oriented.** Workbench overlay renders; the force-graph connection map (`InteractiveWorkspace`) is heavy + touch-unfriendly. Needs a mobile treatment. |

## What this session fixed (L2)
- **Map Key legend overlap (the worst bug):** the expanded legend
  (`position:fixed` bottom-left) floated over the stream AND the workbench on
  mobile. Now **collapsed by default below 768px** (a small "MAP KEY" button) —
  never overlaps; user can still expand. (`Legend.tsx`)
- **Map-as-hero too tall:** the radar row was 52vh and buried the live stream.
  **40vh** now surfaces the stream much sooner. (`App.css`)
- Result: the live stream (the L2 value) is visible and readable; items show
  the new "age since it appeared" timestamps.

Earlier this session (phone feedback): thread read no longer drags sideways;
signal stream capped (internal scroll); timestamps stamped once on arrival; map
key gradient matches the real ramp.

## Remaining for *flawless* (prioritized)

### L2 Console — the long-scroll vs tabbed IA decision
The mobile stack (radar → stream → threads → dock) works but is a long scroll
of dense desktop panels. Two directions:
- **(A) Bottom-nav / tabbed mobile IA** (recommended for flawless): one
  full-screen view at a time — **Map · Stream · Threads** (+ Focus) — instead
  of a 4-section scroll. Each becomes clean and full-height; matches modern
  mobile-app IA (the 2026 research: "fewer decisions per screen"). Bigger build.
- **(B) Polish the scroll-stack:** keep the stack, tighten each section
  (command-bar height, dead map layers, dock density). Cheaper, less elegant.

Concrete L2 polish regardless of direction:
- Map layer tabs on mobile: **PLANE is dead, SHIPS sparse** (#232/#196) — hide
  or mark degraded on mobile so the tabs aren't misleading.
- `stream-filter-tab` row slightly overflows — make the filter bar
  horizontally scrollable on mobile.
- Command bar + coverage-bias banner eat vertical space — compact on mobile.

### L3 Workbench / Workspace — needs a mobile treatment
- The **force-graph connection map** (`InteractiveWorkspace`, react-force-graph)
  is desktop + pointer-oriented; on a phone it's hard to pan/zoom/tap. Options:
  a mobile-simplified relations **list** (entity → related entities/threads), or
  hide the graph on mobile with a "best on desktop" affordance.
- The **investigation panels** (sidebar, research plan, pins) need a mobile
  layout pass (full-screen stacked, not the desktop side panels).

### L0 Landing — tiny polish
- The hero mini-graph caption ("Migration and border pressure in United States
  and Haiti") is near-illegible at phone size — enlarge or drop the caption.

## Recommendation
L0/L1 are flawless-enough. L2's worst issues are fixed (legend, map height);
the **tabbed mobile IA (A)** is the move that makes L2 genuinely flawless, and
**L3 needs a force-graph mobile treatment**. Both are scoped redesigns (a brief
brainstorm → build each), in the spirit of #228. The cheap L2 polish (dead-layer
tabs, filter-bar scroll, compact command bar) can land immediately.

Verified live at 375px throughout; fixes deployed to Vercel.

---

## Execution status (2026-06-26, spec-driven sync)

Implemented: the mobile tabbed IA (bottom nav Map · Threads · Stream · Pulse),
full-screen mobile thread read, focus chip floating above the tab bar, map
crash-loop guard + resize-on-tab, country-brief sideways-scroll fix, country
drill-in z-order. Pulse tab restored Public Attention (Trends+Wiki+Forum) on
mobile. Remaining mobile polish tracks under the L2 review (A3/A4) and #236.
