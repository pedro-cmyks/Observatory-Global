# Console Panel Grid Revival (#233) + De-Densify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revive drag/resize/rearrange panel grid for the L2 console (persisted, preset-per-screen-class, reset affordance) and run a de-densify visual-calm pass — without breaking the display-toggle/keep-alive architecture.

**Architecture:** Desktop (>768px) console panels (radar, stream, threads, dock) render inside `react-grid-layout` v2 (already a dep at ^2.2.3, previously proven in commit e6fbecf). Panels stay mounted during drag/resize (RGL positions via transforms — never unmounts children). Mobile keeps the existing 4-tab IA untouched. Layout presets bucket by container width (laptop/desktop/big) with per-bucket localStorage persistence and a reset in the ··· overflow menu. De-densify = token/CSS calm pass + big-screen type scale + hover-revealed secondary metadata; no API changes, no information removal.

**Tech Stack:** React 19, react-grid-layout 2.2.3, vanilla CSS (Tailwind forbidden outside Landing), vitest.

---

## Tech decision note (grid library)

**Chosen: react-grid-layout v2.2.3 (already installed).** Rationale:

- **Keep-alive safe by construction.** RGL positions children with CSS transforms; children are never unmounted during drag/resize/rearrange. This is exactly the constraint the console lives under (map must never unmount; EqualEarthMap already carries a ResizeObserver for hidden→visible + size changes, `EqualEarthMap.tsx:110`).
- **Requirement fit.** The ask = drag + resize + rearrange + persist + presets. RGL does all five natively (`LayoutItem`, `onLayoutChange`, `dragConfig.handle/cancel`, `resizeConfig.handles`, `minW/minH`).
- **Already proven in-repo.** Commit e6fbecf shipped this exact integration (v2 API: `gridConfig`, `useContainerWidth`, localStorage persist, viewport-fit rowHeight). The regression was a product decision, not a library failure. Dep is still in package.json; zero new install risk.
- **Alternatives rejected:**
  - `react-resizable-panels` — split panes only; no drag-to-rearrange, no 2D grid. Would deliver half the ask.
  - CSS grid + `interactjs` — hand-rolling collision/compaction/persistence; weeks of bespoke code for what RGL gives free, and hand-rolled DOM mutation is *higher* risk near the keep-alive constraints.
  - `dockview`/`react-mosaic` — full docking frameworks; heavier bundle, opinionated chrome, overkill for 4 panels.

---

### Task 0: BEFORE screenshots (evidence baseline)

- [ ] Start dev server (preview_start via launch.json), screenshot console at 1440×900 and 2560×1330. Save mental/file baseline for before/after comparison.

### Task 1: `lib/consoleLayout.ts` — pure layout model (TDD)

**Files:**
- Create: `frontend-v2/src/lib/consoleLayout.ts`
- Test: `frontend-v2/src/lib/consoleLayout.test.ts`

Pure module. Exports:

```ts
import type { LayoutItem } from 'react-grid-layout'

export type LayoutBucket = 'laptop' | 'desktop' | 'big'
export const GRID_COLS = 24
export const GRID_ROWS = 24
export const LAYOUT_STORAGE_KEY = 'atlas.console-layout.v2'
export const PANEL_IDS = ['radar', 'stream', 'threads', 'dock'] as const

export function bucketForWidth(w: number): LayoutBucket
// <1600 laptop · 1600–2399 desktop · >=2400 big

export function defaultLayoutFor(bucket: LayoutBucket): LayoutItem[]
// laptop:  radar x0y0 w9h16 · stream x9y0 w9h16 · threads x18y0 w6h16 · dock x0y16 w24h8
// desktop: radar x0y0 w10h16 · stream x10y0 w8h16 · threads x18y0 w6h16 · dock x0y16 w24h8
// big (4K): four full-height columns — radar x0y0 w9h24 · stream x9y0 w6h24 · threads x15y0 w5h24 · dock x20y0 w4h24
// all items: minW 3, minH 4

export function loadSavedLayouts(storage?: Pick<Storage,'getItem'>): Partial<Record<LayoutBucket, LayoutItem[]>>
export function saveLayout(bucket: LayoutBucket, layout: readonly LayoutItem[], storage?: Pick<Storage,'setItem'|'getItem'>): void
export function clearSavedLayouts(storage?: Pick<Storage,'removeItem'>): void
export function isValidLayout(l: unknown): l is LayoutItem[]
// valid = array of 4 items whose `i` set === PANEL_IDS, numeric x/y/w/h
export function layoutForBucket(bucket: LayoutBucket, saved: Partial<Record<LayoutBucket, LayoutItem[]>>): LayoutItem[]
// saved-and-valid wins, else preset
export function rowHeightFor(availableHeightPx: number, marginY: number, paddingY: number): number
// Math.max(16, floor((h - 2*paddingY - (GRID_ROWS-1)*marginY) / GRID_ROWS))
```

- [ ] Step 1: Write failing tests (bucket boundaries 1599/1600/2399/2400; presets cover all 4 ids, no overlap for big bucket, max(y+h)<=GRID_ROWS; save→load roundtrip w/ fake storage; corrupt JSON → {}; invalid (missing id) rejected; layoutForBucket fallback; rowHeightFor formula + floor 16).
- [ ] Step 2: `npx vitest run src/lib/consoleLayout.test.ts` → FAIL (module missing).
- [ ] Step 3: Implement module.
- [ ] Step 4: vitest → PASS.
- [ ] Step 5: no commit yet (commits with Task 2 as one grid-revival unit — Task 1 alone ships no user-visible software).

### Task 2: App.tsx grid wiring + CSS

**Files:**
- Modify: `frontend-v2/src/App.tsx` (layout region ~1341–1877; command-bar overflow menu ~1300s)
- Modify: `frontend-v2/src/App.css` (grid container styles 587–640 region; RGL handle styles already at 612–622)

Approach:
- Extract the four panel JSX blocks into local consts inside App render: `radarPanel`, `streamPanel`, `threadsPanel`, `dockPanel` (byte-identical JSX, unchanged classNames/handlers). CorrelationMatrix (`.matrix`, display:none everywhere = retired) renders OUTSIDE the grid in both branches, unchanged markup.
- Branch on `isMobile`:
  - mobile: existing `<div className={'terminal-layout mobile-tab-'+mobileTab}>…all panels…</div>` untouched.
  - desktop: `<div ref={gridContainerRef} className="terminal-layout-grid"><ReactGridLayout width={gridWidth} layout={layout} gridConfig={{cols: GRID_COLS, rowHeight, margin:[6,6], containerPadding:[6,6], maxRows: Infinity}} dragConfig={{handle:'.panel-header', cancel:'button, input, a, [data-nodrag]'}} resizeConfig={{handles:['se']}} onLayoutChange={handleLayoutChange}><div key="radar" className="grid-slot">{radarPanel}</div>…</ReactGridLayout></div>`
- State: `const { width: gridWidth, containerRef: gridContainerRef } = useContainerWidth({ initialWidth: 1280 })`; bucket = `bucketForWidth(gridWidth)`; `savedLayouts` state initialized from `loadSavedLayouts()`; layout memo = `layoutForBucket(bucket, savedLayouts)`; `handleLayoutChange` saves under current bucket + setState. rowHeight from measured available height (window.innerHeight − container top offset), recomputed on resize.
- Reset: `resetLayout()` clears storage + state; button row in the ··· overflow menu ("⊞ Reset layout").
- CSS: `.terminal-layout-grid { height: calc(100vh - 48px); margin-top: 48px; overflow-y:auto; overflow-x:hidden; background: var(--color-bg-primary); }` `.grid-slot > .terminal-panel { height:100%; width:100%; }` Import `react-grid-layout/css/styles.css` in App.tsx. Keep `.terminal-layout` CSS (mobile + fallback). Delete dead `.terminal-layout-container`/`.terminal-layout-rgl` rules.

- [ ] Step 1: implement as above.
- [ ] Step 2: `npm run build` green; `npx vitest run` green.
- [ ] Step 3: browser-verify 1440: default laptop preset ≈ today's cockpit; drag stream by header → moves; resize threads → map/list reflow; reload → layout persists; reset → preset restored; GLOBE/UNIVERSE toggle still works mid-layout; map never unmounts (scrub/zoom state survives drag).
- [ ] Step 4: browser-verify 2560: big preset = 4 full-height columns; dock as right column.
- [ ] Step 5: browser-verify 375: mobile tab IA identical to before (grid code not mounted).
- [ ] Step 6: commit `feat(console): revive resizable/movable panel grid (#233)`.

### Task 3: De-densify batch A — chrome calm + big-screen scale

**Files:**
- Modify: `frontend-v2/src/styles/variables.css` (border/panel tokens)
- Modify: `frontend-v2/src/App.css` (.terminal-panel, .panel-header, .panel-subtitle, dock-tabs, layer-btn)

Changes (respect #247 contrast floors — calm ≠ dimmer text; reduce non-text chrome only):
- Panel borders → subtler (border-subtle alpha down ~30%), box-shadow glow removed/reduced on `.terminal-panel`; radius via token.
- `.panel-header`: one consistent spec — 10px/600/0.08em uppercase, `--color-text-muted` (AA-floor respected since #247 raised muted), consistent 8px vertical padding, single bottom hairline; `.panel-subtitle` normalized (10px, muted, no wrap).
- Buttons/chips in headers (`.layer-btn`, `.dock-tab`): quieter idle state (transparent bg, hairline border only on hover/active), active state = accent text + underline/soft tint instead of filled boxes.
- Big-screen scale: `@media (min-width: 2200px)` scoped to `.terminal-layout-grid` descendants (NOT `:root` — ThemeContext writes inline vars on documentElement which would override): panel font-size bump (+1px base), header 11px, panel padding 18px, gap already handled by RGL margin.

- [ ] Step 1: implement; build + vitest green.
- [ ] Step 2: browser-verify 1440 + 2560 (chrome quieter, text contrast unchanged, 4K type legible).
- [ ] Step 3: commit `style(console): de-densify batch A — quieter chrome, unified headers, big-screen type scale`.

### Task 4: De-densify batch B — progressive disclosure of secondary metadata

**Files:**
- Modify: `frontend-v2/src/components/NarrativeThreads.css` (+ .tsx only if a class hook is missing)
- Modify: `frontend-v2/src/components/SignalStream.css` (+ .tsx only if a class hook is missing)

Changes (reveal-on-hover, information never removed — satisfies "reorganize how it's revealed"):
- Thread rows: primary line (label + trend + count) full weight; secondary chip row (country chips, sibling ↔ chips, category badge) at reduced opacity/size at rest, full opacity on row hover/focus-within; row spacing +2–4px.
- Signal stream rows: headline primary; meta line (source, time, badges) muted at rest, full on hover; row padding +2px, hairline separators instead of boxed rows if boxed.
- Keyboard/touch safety: `:focus-within` mirrors hover; mobile (≤768) rest-state opacity stays 1 (no hover there) via media query.

- [ ] Step 1: implement; build + vitest green.
- [ ] Step 2: browser-verify 1440 (hover reveals; nothing lost), 375 (full opacity, unchanged).
- [ ] Step 3: commit `style(console): de-densify batch B — progressive metadata disclosure in stream + threads`.

### Task 5: Final verification + push

- [ ] `npm run build` + `npx vitest run` full green.
- [ ] Browser pass at 1440 / 2560 / 375; AFTER screenshots per surface; compare with Task 0 baselines.
- [ ] Push branch for Vercel.
- [ ] If anything keep-alive-risky surfaced and was deferred, document it in the commit body + this plan.

---

## Self-review notes

- Spec coverage: drag/resize/rearrange ✓ (Task 2), persist ✓ (consoleLayout storage), presets ✓ (bucketForWidth + defaults), reset ✓ (overflow menu), keep-alive ✓ (RGL transform positioning; mobile branch untouched; map always mounted), tool justification ✓ (note above), de-densify hierarchy/whitespace/quiet-chrome/disclosure/consistent-headers ✓ (Tasks 3–4), tokens respected ✓ (variables.css edits, no Tailwind), 3-size verify + build/vitest ✓ (Tasks 2–5), split commits ✓.
- Risk register: (1) ThemeContext inline :root vars override stylesheet — big-screen scale must be class-scoped, noted in Task 3. (2) `.panel-header` becomes drag handle — interactive children need `cancel` selector, included. (3) Media queries at 1100 that hid `.threads` targeted `.terminal-layout` children; grid path uses `.terminal-layout-grid` so they no longer apply — intended (users resize instead); 769–1100 desktop-grid window gets laptop preset.
