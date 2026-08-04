# Mobile-Native IA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Atlas phone experience from four shrunk desktop panels into three tabs where one re-scoping Lens carries the map, the connections and the attention for whatever you are looking at.

**Architecture:** Three tracks, executed in order. **Track A (Tasks 1–5)** fixes the measured defects on the surfaces that survive the IA change — every one of these fixes is still required after the IA switch, so none of it is throwaway. **Track B (Tasks 6–8)** performs the IA switch: a shared 3-tab bar across both routes, `ThemeDetail` promoted from a covered overlay into the Lens tab, and the two new Lens sections. **Track C (Tasks 9–11)** draws the honest boundary: search-with-constellation, Universe hidden with Workbench reduced to capture, and the Landing nav.

**Tech Stack:** React 19 + TypeScript, Vite, vanilla CSS (Tailwind is `Landing.tsx` only), vitest (node environment — **no jsdom, no testing-library**), MCP browser tools for visual verification.

---

## How to test in this repo (read before Task 1)

**There is no DOM test environment.** `vitest` runs in node and every existing test is a **pure-function unit test** (see `src/hooks/useIsMobile.test.ts`, `src/lib/briefLead.test.ts`). Do not attempt to render components in tests — there is no `@testing-library/react` and adding one is out of scope.

Therefore every task follows this shape:

1. **Extract the decision into a pure module** under `src/lib/` and TDD that module.
2. **Wire the module into the component** (or write plain CSS, when the change is purely presentational).
3. **Verify in the browser at 375×812** — screenshot, and where the claim is a number (a height, a tap target, an occlusion) **measure it in the DOM**, do not eyeball it.
4. **Regression-check at 1440×900** — the same surface must be unchanged.
5. **Commit.**

**Starting the dev server** (proxies to the production API, so data is live):

```bash
npm run dev --prefix frontend-v2
```

Then use the MCP browser tools: `preview_start` with name `frontend-v2`, `resize_window` to 375×812, `navigate` to `http://localhost:3000/app`.

**Measuring in the DOM** — use `javascript_tool` with an IIFE (the evaluation context is shared between calls, so a bare `const` will throw `already declared` on the second call):

```js
(()=>{const e=document.querySelector('.narrative-row');return JSON.stringify({h:Math.round(e.getBoundingClientRect().height)})})()
```

**Gate for every task:** `npm run build --prefix frontend-v2` green (**not** `tsc --noEmit` — Vite's `tsc -b` is stricter) and `npm test --prefix frontend-v2` green.

---

## File Structure

**New pure modules (each one file, one responsibility, all unit-tested):**

| file | responsibility |
|---|---|
| `src/lib/mobileNav.ts` | The 3-tab model: tab ids, which route each tab lives on, how a console tab maps to a bar tab |
| `src/lib/lensScope.ts` | The Lens scope value, the breadcrumb stack, push/pop, and the title+subtitle for each scope |
| `src/lib/lensSections.ts` | Given a scope and its payload, produce the five sections — including the honest-empty reason when a section has nothing |
| `src/lib/threadRowMobile.ts` | Which entity chips a thread row shows at rest on a phone, and the hidden count |
| `src/lib/briefMobileBands.ts` | Which Brief bands start collapsed on a phone, and their one-line summary text |
| `src/lib/searchConstellation.ts` | Merge search hits with their measured neighbours into a flat tappable row list |

**New components:**

| file | responsibility |
|---|---|
| `src/components/MobileTabBar.tsx` + `.css` | The shared 3-tab bar, rendered once at root, navigating only |
| `src/contexts/MobileNavContext.tsx` | Holds the active bar tab + the Lens scope stack; consumed by `App` and `BriefNewspaper` |
| `src/components/LensPanel.tsx` + `.css` | The Lens tab surface: renders the five sections for the current scope |
| `src/components/SearchSheet.tsx` + `.css` | Full-screen mobile search with constellation rows |

**Modified:**

| file | change |
|---|---|
| `src/styles/variables.css` | `--mobile-bottom-reserve` |
| `src/lib/tooltips.ts` | Suppress `[data-tip]` under `(hover: none)` |
| `src/components/ThemeDetail.css` | Bottom reserve; stop being covered |
| `src/components/AnomalyPanel.css` | Mobile single column (currently **0** media queries) |
| `src/components/SourceIntegrityPanel.css` | Mobile single column |
| `src/components/NarrativeThreads.tsx` / `.css` | Title-first rows, chip collapse |
| `src/components/SignalStream.css` | 48px rows, 2-line headline, lane fade |
| `src/pages/BriefNewspaper.tsx` / `.css` | Collapsible bands, vitals strip, skip minimap on phone |
| `src/App.tsx` | Mobile shell renders Lens/Live; tab bar removed (moves to root) |
| `src/main.tsx` | `MobileNavProvider` + `<MobileTabBar />` at root |
| `src/pages/Landing.tsx` | Mobile nav menu |

---

# TRACK A — the measured defects

## Task 1: Shared mobile primitives

Kills the confirmed reader occlusion and the stuck-on-touch tooltip. Pure CSS + one small logic change in `tooltips.ts`.

**Files:**
- Modify: `frontend-v2/src/styles/variables.css`
- Modify: `frontend-v2/src/lib/tooltips.ts`
- Modify: `frontend-v2/src/components/ThemeDetail.css:1288`
- Modify: `frontend-v2/src/components/CountryThemePanel.css`
- Create: `frontend-v2/src/lib/hoverCapable.ts`
- Create: `frontend-v2/src/lib/hoverCapable.test.ts`

- [ ] **Step 1: Write the failing test for the hover-capability helper**

Create `frontend-v2/src/lib/hoverCapable.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { hoverIsAvailable } from './hoverCapable'

describe('hoverIsAvailable', () => {
  it('is true when the device reports a hover-capable pointer', () => {
    expect(hoverIsAvailable(() => ({ matches: true }))).toBe(true)
  })
  it('is false when the device reports (hover: none)', () => {
    expect(hoverIsAvailable(() => ({ matches: false }))).toBe(false)
  })
  it('defaults to true when matchMedia is unavailable', () => {
    expect(hoverIsAvailable(undefined)).toBe(true)
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- hoverCapable`
Expected: FAIL — `Failed to resolve import "./hoverCapable"`.

- [ ] **Step 3: Implement the helper**

Create `frontend-v2/src/lib/hoverCapable.ts`:

```ts
/**
 * Does this device have a hovering pointer?
 *
 * A phone does not. Every `data-tip` tooltip in the app is a hover affordance,
 * and on a touch screen the browser fires a synthetic hover on tap — which is
 * how a tooltip was caught stuck open over a thread title during the mobile
 * audit. Under `(hover: none)` we simply never show tips.
 *
 * The matcher is injected so this is testable without a DOM.
 */
export type MediaMatcher = (query: string) => { matches: boolean }

export function hoverIsAvailable(matchMedia?: MediaMatcher): boolean {
  if (!matchMedia) return true
  return matchMedia('(hover: hover)').matches
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- hoverCapable`
Expected: PASS, 3 tests.

- [ ] **Step 5: Wire it into the tooltip controller**

In `frontend-v2/src/lib/tooltips.ts`, add the import at the top of the file:

```ts
import { hoverIsAvailable } from './hoverCapable'
```

and make `show()` return immediately on a touch device. Find `function show(trigger: Element) {` and insert as its first statement:

```ts
  if (!hoverIsAvailable(typeof window !== 'undefined' ? (q) => window.matchMedia(q) : undefined)) {
    hide()
    return
  }
```

- [ ] **Step 6: Add the bottom-reserve custom property**

In `frontend-v2/src/styles/variables.css`, inside the existing `:root` block, add:

```css
    /* #236 — every full-screen mobile surface reserves the tab bar's height so
       its last lines are never covered. The bar is 57px; the safe-area inset
       covers the iOS home indicator. Desktop never reads this. */
    --mobile-bottom-reserve: calc(57px + env(safe-area-inset-bottom, 0px));
```

- [ ] **Step 7: Apply the reserve to the reader and the country drill-in**

In `frontend-v2/src/components/ThemeDetail.css`, replace line 1288:

```css
    .theme-detail-panel { padding: 56px 16px 16px; overflow-x: hidden; touch-action: pan-y; }
```

with:

```css
    .theme-detail-panel {
        padding: 56px 16px calc(16px + var(--mobile-bottom-reserve));
        overflow-x: hidden;
        touch-action: pan-y;
    }
```

In `frontend-v2/src/components/CountryThemePanel.css`, inside its `@media (max-width: 768px)` block, add to the `.country-theme-panel` rule:

```css
        padding-bottom: calc(16px + var(--mobile-bottom-reserve));
```

- [ ] **Step 8: Add the touch-target and input floors**

Append to `frontend-v2/src/App.css`:

```css
/* #236 mobile primitives — one place, applies to every surface.
   44px is the iOS minimum; the audit measured command-bar buttons at 23-25px
   and signal rows at 39px. `font-size:16px` on inputs stops iOS auto-zooming
   the whole page on focus. */
@media (max-width: 768px) {
    .command-bar button,
    .command-bar a,
    .mobile-tabbar button {
        min-height: 44px;
    }
    input,
    textarea,
    select {
        font-size: 16px;
    }
}
```

- [ ] **Step 9: Verify in the browser at 375×812**

Start the server, resize to 375×812, open `http://localhost:3000/app`, open a thread from the Threads tab, then measure:

```js
(()=>{const p=document.querySelector('.theme-detail-panel');const b=document.querySelector('.mobile-tabbar');return JSON.stringify({panelPadBottom:getComputedStyle(p).paddingBottom,barTop:Math.round(b.getBoundingClientRect().top),panelBottom:Math.round(p.getBoundingClientRect().bottom)})})()
```

Expected: `panelPadBottom` is at least `73px`. Then tap a `data-tip` element and screenshot — **no tooltip appears**.

Also measure the command bar buttons:

```js
(()=>{return JSON.stringify([...document.querySelectorAll('.command-bar button')].map(e=>Math.round(e.getBoundingClientRect().height)))})()
```

Expected: every value ≥ 44.

- [ ] **Step 10: Regression-check at 1440×900**

Resize to 1440×900, reload `/app`. Screenshot. Expected: the desktop grid, tooltips working on hover, command bar unchanged.

- [ ] **Step 11: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/hoverCapable.ts frontend-v2/src/lib/hoverCapable.test.ts frontend-v2/src/lib/tooltips.ts frontend-v2/src/styles/variables.css frontend-v2/src/components/ThemeDetail.css frontend-v2/src/components/CountryThemePanel.css frontend-v2/src/App.css
git commit -m "fix(mobile): reader is no longer covered by the tab bar, and tips stop sticking on touch (#236)"
```

---

## Task 2: Pulse — one column, whole country names

`AnomalyPanel.css` has **zero** media queries. `.anomaly-body-grid` is `grid-template-columns: 1fr 1fr` at line 74-75, which on a 375px screen gives two ~185px columns and truncates every country name.

**Files:**
- Modify: `frontend-v2/src/components/AnomalyPanel.css`
- Modify: `frontend-v2/src/components/SourceIntegrityPanel.css`

- [ ] **Step 1: Add the mobile block to AnomalyPanel.css**

Append to `frontend-v2/src/components/AnomalyPanel.css`:

```css
/* #236 — the phone's Public Attention surface had no mobile CSS at all, so the
   desktop two-column grid survived at 375px: ~185px per column, and every
   country name truncated ("Camero…", "Guatem…", "Uzbeki…"). One column, and
   rows big enough to hit. */
@media (max-width: 768px) {
    .anomaly-body-grid {
        grid-template-columns: 1fr;
    }
    .anomaly-col.col-right-border {
        border-left: 0;
        border-top: 1px solid rgba(var(--color-neutral-rgb), 0.18);
    }
    .anomaly-col > * {
        min-width: 0;
    }
    .anomaly-col button,
    .anomaly-col a,
    .anomaly-col li {
        min-height: 44px;
    }
}
```

- [ ] **Step 2: Add the matching block to SourceIntegrityPanel.css**

Append to `frontend-v2/src/components/SourceIntegrityPanel.css`:

```css
/* #236 — same reason as AnomalyPanel: the Pulse tab is one column on a phone. */
@media (max-width: 768px) {
    .source-integrity-grid,
    .source-integrity-body {
        grid-template-columns: 1fr;
    }
    .source-integrity-row {
        min-height: 44px;
    }
}
```

If either selector does not exist in the file, grep for the element that sets `grid-template-columns` in that file and use its class instead — the intent is one column below 768.

- [ ] **Step 3: Verify at 375×812**

Open `/app`, tap the **Pulse** tab, screenshot, then measure that no label is truncated:

```js
(()=>{const t=[...document.querySelectorAll('.anomaly-col *')].filter(e=>e.children.length===0&&e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.trim().slice(0,24));return JSON.stringify({truncated:t.length,sample:t.slice(0,6)})})()
```

Expected: `truncated: 0`.

- [ ] **Step 4: Regression-check at 1440×900**

Resize, reload, screenshot the dock. Expected: two columns, unchanged.

- [ ] **Step 5: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/components/AnomalyPanel.css frontend-v2/src/components/SourceIntegrityPanel.css
git commit -m "fix(mobile): Pulse goes single-column — country names stop truncating (#236)"
```

---

## Task 3: Threads — the title wins

Today a thread row is ~290px and the **title** is what gets truncated or dropped, while the sparkline, the confidence bar, "peak 2/h", "Started 62d ago" and five entity chips all survive full-size. Invert that.

**Files:**
- Create: `frontend-v2/src/lib/threadRowMobile.ts`
- Create: `frontend-v2/src/lib/threadRowMobile.test.ts`
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx` (the row body around `:758-790`)
- Modify: `frontend-v2/src/components/NarrativeThreads.css`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/threadRowMobile.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { visibleEntities, MOBILE_ENTITY_CAP } from './threadRowMobile'

describe('visibleEntities', () => {
  const five = ['donald trump', 'abbas araghchi', 'takahiro asaoka', 'faisal ben', 'ali larijani']

  it('shows every entity on desktop', () => {
    expect(visibleEntities(five, false)).toEqual({ shown: five, hiddenCount: 0 })
  })

  it('caps the list on mobile and reports the remainder', () => {
    expect(visibleEntities(five, true)).toEqual({
      shown: five.slice(0, MOBILE_ENTITY_CAP),
      hiddenCount: five.length - MOBILE_ENTITY_CAP,
    })
  })

  it('never reports a negative remainder when the list is short', () => {
    expect(visibleEntities(['solo'], true)).toEqual({ shown: ['solo'], hiddenCount: 0 })
  })

  it('handles an empty list', () => {
    expect(visibleEntities([], true)).toEqual({ shown: [], hiddenCount: 0 })
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- threadRowMobile`
Expected: FAIL — cannot resolve `./threadRowMobile`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/threadRowMobile.ts`:

```ts
/**
 * A thread row on a phone leads with its title.
 *
 * The mobile audit measured ~290px per row where the title truncated while five
 * entity chips wrapped over three lines. Chips are context; the title is the
 * story. We cap the chips and state the remainder — a count, never a silent
 * drop.
 */
export const MOBILE_ENTITY_CAP = 2

export interface VisibleEntities {
  shown: string[]
  hiddenCount: number
}

export function visibleEntities(entities: string[], isMobile: boolean): VisibleEntities {
  if (!isMobile) return { shown: entities, hiddenCount: 0 }
  return {
    shown: entities.slice(0, MOBILE_ENTITY_CAP),
    hiddenCount: Math.max(0, entities.length - MOBILE_ENTITY_CAP),
  }
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- threadRowMobile`
Expected: PASS, 4 tests.

- [ ] **Step 5: Wire it into the row**

In `frontend-v2/src/components/NarrativeThreads.tsx`:

1. Import at the top: `import { visibleEntities } from '../lib/threadRowMobile'` and `import { useIsMobile } from '../hooks/useIsMobile'`.
2. Inside the component body, add `const isMobile = useIsMobile()`.
3. Find where the row maps its `top_entities` into chips. Replace the direct `.map(...)` over the entity array with:

```tsx
{(() => {
  const { shown, hiddenCount } = visibleEntities(entityList, isMobile)
  return (
    <>
      {shown.map((e) => (
        /* keep the existing chip JSX exactly as it is, with `e` as the entity */
      ))}
      {hiddenCount > 0 && (
        <span className="narrative-entity-more" data-tip="More entities in this thread">
          +{hiddenCount}
        </span>
      )}
    </>
  )
})()}
```

where `entityList` is whatever local the existing map iterated over. **Do not change the chip markup itself** — only what is iterated and the `+N` suffix.

- [ ] **Step 6: Make the title lead in CSS**

Append to `frontend-v2/src/components/NarrativeThreads.css`:

```css
/* #236 — on a phone the title is the content. Give it the full row width and
   its own line before anything else, clamp it to two lines instead of
   truncating to nothing, and demote the instrumentation (sparkline, peak,
   started-ago) to a quieter second tier. */
@media (max-width: 768px) {
    .narrative-row {
        min-height: 44px;
    }
    .narrative-header {
        flex-wrap: wrap;
    }
    .narrative-label {
        flex: 1 1 100%;
        min-width: 0;
        order: -1;
        font-size: 15px;
        line-height: 1.25;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
    }
    .narrative-sparkline-wrap,
    .narrative-spark-peak {
        opacity: 0.6;
    }
    .narrative-entity-more {
        font-size: 11px;
        opacity: 0.7;
        padding: 0 4px;
    }
}
```

- [ ] **Step 7: Verify at 375×812**

Open `/app`, tap **Threads**, screenshot. Then measure that every row shows a non-empty title and rows got shorter:

```js
(()=>{const rows=[...document.querySelectorAll('.narrative-row')].slice(0,5);return JSON.stringify(rows.map(r=>({h:Math.round(r.getBoundingClientRect().height),title:(r.querySelector('.narrative-label')?.textContent||'').trim().slice(0,32)})))})()
```

Expected: every `title` non-empty; heights meaningfully below the ~290px baseline.

- [ ] **Step 8: Regression-check at 1440×900**

Resize, reload, screenshot the Threads panel. Expected: all entity chips present (no `+N`), rows unchanged.

- [ ] **Step 9: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/threadRowMobile.ts frontend-v2/src/lib/threadRowMobile.test.ts frontend-v2/src/components/NarrativeThreads.tsx frontend-v2/src/components/NarrativeThreads.css
git commit -m "fix(mobile): thread rows lead with the title, chips collapse to a counted +N (#236)"
```

---

## Task 4: Live — readable rows, honest lane strip

Rows are 39px with the headline truncated to one line. The lane strip overflows (`scrollWidth 524` vs `clientWidth 365`) so `DISASTER` is off-screen with no affordance that it exists.

**Files:**
- Modify: `frontend-v2/src/components/SignalStream.css`

- [ ] **Step 1: Add the mobile block**

Append to `frontend-v2/src/components/SignalStream.css`:

```css
/* #236 — the stream is the phone's default surface. 39px rows with a headline
   truncated mid-word is a desktop density on a touch screen. Two lines of
   headline, 48px minimum, and a fade on the lane strip so the lanes that scroll
   off the edge announce themselves instead of vanishing. No lane is removed —
   dropping one to fit would be silent filtering. */
@media (max-width: 768px) {
    .signal-row {
        min-height: 48px;
        align-items: flex-start;
        padding-top: 6px;
        padding-bottom: 6px;
    }
    .signal-row .signal-headline {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
        line-height: 1.3;
    }
    .stream-filter-bar {
        position: relative;
        overflow-x: auto;
        scroll-snap-type: x proximity;
        -webkit-overflow-scrolling: touch;
        mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent 100%);
    }
    .stream-filter-bar > * {
        scroll-snap-align: start;
        min-height: 44px;
    }
}
```

If the headline element does not carry `.signal-headline`, grep `SignalStream.tsx` for the row's text element class and substitute it — the rule must land on the element that currently truncates.

- [ ] **Step 2: Verify at 375×812**

Open `/app`, stay on **Stream**, screenshot, then measure:

```js
(()=>{const r=[...document.querySelectorAll('.signal-row')].slice(0,4).map(e=>Math.round(e.getBoundingClientRect().height));const b=document.querySelector('.stream-filter-bar');return JSON.stringify({rowHeights:r,laneScroll:b.scrollWidth,laneClient:b.clientWidth})})()
```

Expected: every row height ≥ 48. The lane strip still scrolls; the fade is visible in the screenshot.

- [ ] **Step 3: Regression-check at 1440×900**

Resize, reload, screenshot the stream. Expected: single-line rows, no fade, unchanged.

- [ ] **Step 4: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/components/SignalStream.css
git commit -m "fix(mobile): stream rows get two headline lines and a 48px floor; lane strip fades (#236)"
```

---

## Task 5: Brief — news at ~400px instead of 1707px

Measured chrome before the first story: masthead 302 · freshness 141 · **stat cards 542** · **markets band 463** · search 34 · tabs 95. Nothing is deleted; the non-news blocks become one-line bands that expand on tap, and the minimap stops rendering on a phone.

**Files:**
- Create: `frontend-v2/src/lib/briefMobileBands.ts`
- Create: `frontend-v2/src/lib/briefMobileBands.test.ts`
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`
- Modify: `frontend-v2/src/pages/BriefNewspaper.css`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/briefMobileBands.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { freshnessSummary, bandStartsCollapsed } from './briefMobileBands'

describe('bandStartsCollapsed', () => {
  it('collapses the secondary bands on mobile', () => {
    expect(bandStartsCollapsed('markets', true)).toBe(true)
    expect(bandStartsCollapsed('freshness', true)).toBe(true)
  })
  it('never collapses anything on desktop', () => {
    expect(bandStartsCollapsed('markets', false)).toBe(false)
    expect(bandStartsCollapsed('freshness', false)).toBe(false)
  })
})

describe('freshnessSummary', () => {
  it('states seal age and full-text yield in one line', () => {
    expect(freshnessSummary({ sealedHoursAgo: 11, fullTextOk: 1, fullTextTotal: 48 }))
      .toBe('sealed 11h ago · full text 1/48')
  })
  it('omits the yield when it is unknown', () => {
    expect(freshnessSummary({ sealedHoursAgo: 3, fullTextOk: null, fullTextTotal: null }))
      .toBe('sealed 3h ago')
  })
  it('says so honestly when the seal age is unknown', () => {
    expect(freshnessSummary({ sealedHoursAgo: null, fullTextOk: 2, fullTextTotal: 40 }))
      .toBe('seal time unknown · full text 2/40')
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- briefMobileBands`
Expected: FAIL — cannot resolve `./briefMobileBands`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/briefMobileBands.ts`:

```ts
/**
 * Which Brief bands start collapsed on a phone, and what their one-line
 * summary says.
 *
 * The mobile audit measured 1707px of chrome before the first headline. The fix
 * is NOT to delete the freshness box or the markets band — both are honesty
 * surfaces (one states how stale the edition is, the other states that it is a
 * live overlay outside the sealed edition). They collapse to a line that still
 * carries the honest fact, and expand on tap.
 */
export type BriefBand = 'freshness' | 'markets'

export function bandStartsCollapsed(band: BriefBand, isMobile: boolean): boolean {
  if (!isMobile) return false
  return band === 'freshness' || band === 'markets'
}

export interface FreshnessFacts {
  sealedHoursAgo: number | null
  fullTextOk: number | null
  fullTextTotal: number | null
}

export function freshnessSummary(f: FreshnessFacts): string {
  const parts: string[] = []
  parts.push(f.sealedHoursAgo === null ? 'seal time unknown' : `sealed ${f.sealedHoursAgo}h ago`)
  if (f.fullTextOk !== null && f.fullTextTotal !== null) {
    parts.push(`full text ${f.fullTextOk}/${f.fullTextTotal}`)
  }
  return parts.join(' · ')
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- briefMobileBands`
Expected: PASS, 5 tests.

- [ ] **Step 5: Introduce viewport awareness in the Brief**

`BriefNewspaper.tsx` currently has **zero** viewport detection. Add at the top:

```tsx
import { useIsMobile } from '../hooks/useIsMobile'
import { bandStartsCollapsed, freshnessSummary } from '../lib/briefMobileBands'
```

and inside the component:

```tsx
const isMobile = useIsMobile()
const [freshnessOpen, setFreshnessOpen] = useState(!bandStartsCollapsed('freshness', isMobile))
const [marketsOpen, setMarketsOpen] = useState(!bandStartsCollapsed('markets', isMobile))
```

- [ ] **Step 6: Collapse the freshness band**

Wrap the existing `.brief-publication-state` content so the phone gets a summary line. Keep the full markup for desktop and for the expanded state:

```tsx
<section className="brief-publication-state is-rebuilding">
  {isMobile && !freshnessOpen ? (
    <button type="button" className="brief-band-summary" onClick={() => setFreshnessOpen(true)}>
      {freshnessSummary({ sealedHoursAgo: sealedHoursAgo, fullTextOk: fullTextOk, fullTextTotal: fullTextTotal })} ▸
    </button>
  ) : (
    /* the existing freshness markup, unchanged */
  )}
</section>
```

Bind `sealedHoursAgo`, `fullTextOk` and `fullTextTotal` to the values the existing markup already renders in that block — do not fetch anything new.

- [ ] **Step 7: Collapse the markets band the same way**

```tsx
{isMobile && !marketsOpen ? (
  <button type="button" className="brief-band-summary" onClick={() => setMarketsOpen(true)}>
    World markets · descriptive · last close ▸
  </button>
) : (
  /* the existing <BriefMarkets /> block, unchanged */
)}
```

- [ ] **Step 8: Skip the choropleth on a phone**

Find the `<ComposableMap>` render inside `.brief-minimap` and gate it:

```tsx
{!isMobile && (
  /* the existing <ComposableMap> … </ComposableMap> block */
)}
```

This stops the world GeoJSON downloading on a phone — today it is rendered at 213px and merely hard to read. The "Most Active" list next to it stays.

- [ ] **Step 9: Compress the masthead, vitals and tabs in CSS**

Append to `frontend-v2/src/pages/BriefNewspaper.css`:

```css
/* #236 — the news used to start 1707px down, 2.1 phone screens. Nothing is
   deleted: the six vitals become a sideways strip (all six survive, none
   truncated), the masthead loses its button row to the overflow, the section
   tabs become one scrolling line. */
@media (max-width: 768px) {
    .brief-band-summary {
        display: flex;
        align-items: center;
        width: 100%;
        min-height: 44px;
        padding: 0 12px;
        background: transparent;
        border: 1px solid rgba(var(--color-neutral-rgb), 0.2);
        border-radius: 6px;
        font: inherit;
        font-size: 12px;
        text-align: left;
        color: inherit;
        cursor: pointer;
    }
    .brief-instrument {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        gap: 8px;
        -webkit-overflow-scrolling: touch;
        scroll-snap-type: x proximity;
        mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent 100%);
    }
    .brief-instrument > * {
        flex: 0 0 auto;
        min-width: 132px;
        scroll-snap-align: start;
    }
    .brief-tablist {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        gap: 6px;
    }
    .brief-tablist > * {
        flex: 0 0 auto;
        min-height: 44px;
    }
    .brief-masthead {
        padding-bottom: 8px;
    }
    .brief-minimap {
        display: none;
    }
}
```

- [ ] **Step 10: Verify at 375×812 — the headline number**

Open `http://localhost:3000/brief`, then measure where the news starts:

```js
(()=>{const lead=document.querySelector('.brief-lead');const w=document.querySelector('.brief-content');const kids=[...w.children].map(c=>({cls:(c.className+'').slice(0,40),top:Math.round(c.getBoundingClientRect().top+scrollY),h:Math.round(c.getBoundingClientRect().height)}));return JSON.stringify({leadTop:Math.round(lead.getBoundingClientRect().top+scrollY),kids})})()
```

Expected: `leadTop` < 500. Screenshot to confirm the vitals strip scrolls sideways and both collapsed bands read as one line each.

- [ ] **Step 11: Regression-check at 1440×900**

Resize, reload `/brief`, screenshot. Expected: full stat cards, full markets band, full freshness box, choropleth present.

- [ ] **Step 12: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/briefMobileBands.ts frontend-v2/src/lib/briefMobileBands.test.ts frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/pages/BriefNewspaper.css
git commit -m "feat(mobile): Brief leads with news — chrome collapses to expandable bands (#236)"
```

---

# TRACK B — the Lens

## Task 6: The shared 3-tab bar

The tab bar currently lives inside `App.tsx:2519-2534` and only exists on `/app`. It moves to the root so `/brief` carries it too, and it drops from four tabs to three: `Brief · Lens · Live`.

**Files:**
- Create: `frontend-v2/src/lib/mobileNav.ts`
- Create: `frontend-v2/src/lib/mobileNav.test.ts`
- Create: `frontend-v2/src/contexts/MobileNavContext.tsx`
- Create: `frontend-v2/src/components/MobileTabBar.tsx`
- Create: `frontend-v2/src/components/MobileTabBar.css`
- Modify: `frontend-v2/src/main.tsx`
- Modify: `frontend-v2/src/App.tsx:2461-2478` and `:2518-2534`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/mobileNav.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { MOBILE_TABS, routeForTab, tabForRoute, consoleTabFor } from './mobileNav'

describe('MOBILE_TABS', () => {
  it('is exactly three tabs in reading order', () => {
    expect(MOBILE_TABS.map((t) => t.id)).toEqual(['brief', 'lens', 'live'])
  })
})

describe('routeForTab', () => {
  it('sends the Brief tab to its own route', () => {
    expect(routeForTab('brief')).toBe('/brief')
  })
  it('sends the console tabs to /app', () => {
    expect(routeForTab('lens')).toBe('/app')
    expect(routeForTab('live')).toBe('/app')
  })
})

describe('tabForRoute', () => {
  it('resolves the Brief route', () => {
    expect(tabForRoute('/brief', 'live')).toBe('brief')
  })
  it('keeps the remembered console tab on /app', () => {
    expect(tabForRoute('/app', 'live')).toBe('live')
    expect(tabForRoute('/app', 'lens')).toBe('lens')
  })
  it('falls back to the lens on an unknown route', () => {
    expect(tabForRoute('/docs', 'live')).toBe('lens')
  })
})

describe('consoleTabFor', () => {
  it('maps a bar tab to the console surface it shows', () => {
    expect(consoleTabFor('lens')).toBe('lens')
    expect(consoleTabFor('live')).toBe('live')
  })
  it('leaves the console on the lens while the Brief route is active', () => {
    expect(consoleTabFor('brief')).toBe('lens')
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- mobileNav`
Expected: FAIL — cannot resolve `./mobileNav`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/mobileNav.ts`:

```ts
/**
 * The phone's three-tab model.
 *
 * Brief is the home (the glance). Lens is the one surface that re-scopes to
 * whatever you are looking at. Live is the raw stream. Map, Threads, Pulse and
 * Universe are not tabs any more — they are absorbed as sections of the Lens.
 *
 * The bar only NAVIGATES. It holds no data, which is what makes it safe to
 * render at the root across both keep-alive routes.
 */
export type MobileTab = 'brief' | 'lens' | 'live'
export type ConsoleTab = 'lens' | 'live'

export interface MobileTabDef {
  id: MobileTab
  label: string
  glyph: string
}

export const MOBILE_TABS: MobileTabDef[] = [
  { id: 'brief', label: 'Brief', glyph: '◈' },
  { id: 'lens', label: 'Lens', glyph: '◎' },
  { id: 'live', label: 'Live', glyph: '≋' },
]

export function routeForTab(tab: MobileTab): string {
  return tab === 'brief' ? '/brief' : '/app'
}

export function tabForRoute(pathname: string, rememberedConsoleTab: ConsoleTab): MobileTab {
  if (pathname === '/brief') return 'brief'
  if (pathname === '/app') return rememberedConsoleTab
  return 'lens'
}

export function consoleTabFor(tab: MobileTab): ConsoleTab {
  return tab === 'live' ? 'live' : 'lens'
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- mobileNav`
Expected: PASS, 8 tests.

- [ ] **Step 5: Create the context**

Create `frontend-v2/src/contexts/MobileNavContext.tsx`:

```tsx
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { ConsoleTab } from '../lib/mobileNav'

interface MobileNavValue {
  consoleTab: ConsoleTab
  setConsoleTab: (t: ConsoleTab) => void
}

const Ctx = createContext<MobileNavValue>({ consoleTab: 'lens', setConsoleTab: () => {} })

export function MobileNavProvider({ children }: { children: ReactNode }) {
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>('lens')
  const value = useMemo(() => ({ consoleTab, setConsoleTab }), [consoleTab])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useMobileNav() {
  return useContext(Ctx)
}
```

- [ ] **Step 6: Create the tab bar component**

Create `frontend-v2/src/components/MobileTabBar.tsx`:

```tsx
import { useLocation, useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { useMobileNav } from '../contexts/MobileNavContext'
import { MOBILE_TABS, routeForTab, tabForRoute, consoleTabFor } from '../lib/mobileNav'
import './MobileTabBar.css'

/**
 * Rendered ONCE at the root, outside <Routes>, so both keep-alive panes
 * (/app and /brief) carry the same bar. Switching to Brief is a route change
 * the keep-alive shell answers instantly — no remount, no refetch.
 */
export function MobileTabBar() {
  const isMobile = useIsMobile()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { consoleTab, setConsoleTab } = useMobileNav()

  if (!isMobile) return null
  if (pathname !== '/app' && pathname !== '/brief') return null

  const active = tabForRoute(pathname, consoleTab)

  return (
    <nav className="mobile-tabbar" aria-label="Atlas sections" data-tour="mobile-tabs">
      {MOBILE_TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          className={active === t.id ? 'active' : ''}
          aria-current={active === t.id ? 'page' : undefined}
          onClick={() => {
            if (t.id !== 'brief') setConsoleTab(consoleTabFor(t.id))
            const route = routeForTab(t.id)
            if (route !== pathname) navigate(route)
          }}
        >
          <span className="mobile-tab-glyph">{t.glyph}</span>
          {t.label}
        </button>
      ))}
    </nav>
  )
}
```

- [ ] **Step 7: Move the bar's styles into its own file**

Create `frontend-v2/src/components/MobileTabBar.css` and move the existing `.mobile-tabbar` rules out of `App.css` into it verbatim (grep `App.css` for `.mobile-tabbar`). Add nothing new — the 44px floor already came from Task 1.

- [ ] **Step 8: Mount it at the root**

In `frontend-v2/src/main.tsx`, add the imports:

```tsx
import { MobileNavProvider } from './contexts/MobileNavContext'
import { MobileTabBar } from './components/MobileTabBar'
```

wrap the existing tree — put `<MobileNavProvider>` immediately inside `<StoryLensProvider>` — and render the bar next to `<InstallPrompt />`:

```tsx
<InstallPrompt />
<MobileTabBar />
```

- [ ] **Step 9: Reduce the console to two mobile surfaces**

In `frontend-v2/src/App.tsx`:

1. Delete the whole `{isMobile && (<nav className="mobile-tabbar" …>…</nav>)}` block at `:2518-2534` — the bar now lives at the root.
2. Replace the `mobileTab` local state with the shared one. Remove `const [mobileTab, setMobileTab] = useState<…>('stream')` (`:394`) and add `const { consoleTab, setConsoleTab } = useMobileNav()`.
3. Rewrite the mobile shell at `:2461-2478`:

```tsx
        if (isMobile) {
          // #236: the phone has two console surfaces. The Lens is whatever is
          // focused (see LensPanel, Task 7); Live is the raw stream. The map
          // is no longer a tab — it is a section INSIDE the Lens — so the
          // radar panel is not mounted here at all and its rAF loop never runs
          // on a phone.
          return (
            <div className={`terminal-layout mobile-tab-${consoleTab}`}>
              {consoleTab === 'live' && streamPanel}
              {consoleTab === 'lens' && lensPanel}
              {matrixPanel}
            </div>
          )
        }
```

For this task only, define `lensPanel` as the existing `threadsPanel` so the app stays usable; Task 7 replaces it with the real Lens. Add a comment marking it.

4. Every existing `setMobileTab('stream')` call (e.g. `:1182`) becomes `setConsoleTab('lens')` — under the new model a drill-in lands in the Lens, not the stream.

- [ ] **Step 10: Verify at 375×812**

Open `/app`. Screenshot: the bar reads `Brief · Lens · Live`. Tap **Brief** — the Brief renders **with the bar still visible**. Tap **Lens** — back to the console instantly. Confirm no remount:

```js
(()=>{return JSON.stringify({tabs:[...document.querySelectorAll('.mobile-tabbar button')].map(b=>b.textContent.trim()),path:location.pathname})})()
```

Expected: three labels; `path` follows the tab.

- [ ] **Step 11: Regression-check at 1440×900**

Resize, reload `/app` and `/brief`. Expected: **no tab bar on either** (the component returns `null` when not mobile), desktop grid unchanged.

- [ ] **Step 12: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/mobileNav.ts frontend-v2/src/lib/mobileNav.test.ts frontend-v2/src/contexts/MobileNavContext.tsx frontend-v2/src/components/MobileTabBar.tsx frontend-v2/src/components/MobileTabBar.css frontend-v2/src/main.tsx frontend-v2/src/App.tsx frontend-v2/src/App.css
git commit -m "feat(mobile): three tabs — Brief, Lens, Live — with one shared bar across both routes (#236)"
```

---

## Task 7: The Lens surface and its scope stack

`ThemeDetail` is promoted from a covered overlay into the Lens tab's own surface, and gains a *field* scope for when nothing is focused.

**Files:**
- Create: `frontend-v2/src/lib/lensScope.ts`
- Create: `frontend-v2/src/lib/lensScope.test.ts`
- Create: `frontend-v2/src/components/LensPanel.tsx`
- Create: `frontend-v2/src/components/LensPanel.css`
- Modify: `frontend-v2/src/contexts/MobileNavContext.tsx`
- Modify: `frontend-v2/src/App.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/lensScope.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { FIELD_SCOPE, pushScope, popScope, scopeTitle, scopeKey } from './lensScope'

const thread = { kind: 'thread' as const, id: 'dynamic-topic-8057', label: 'Hamas Disarmament Deal' }
const country = { kind: 'country' as const, id: 'IL', label: 'Israel' }

describe('pushScope', () => {
  it('starts from the field', () => {
    expect(pushScope([], thread)).toEqual([FIELD_SCOPE, thread])
  })
  it('appends onto an existing trail', () => {
    expect(pushScope([FIELD_SCOPE, thread], country)).toEqual([FIELD_SCOPE, thread, country])
  })
  it('does not stack the same scope twice in a row', () => {
    expect(pushScope([FIELD_SCOPE, thread], thread)).toEqual([FIELD_SCOPE, thread])
  })
  it('rewinds instead of looping when you revisit an earlier scope', () => {
    expect(pushScope([FIELD_SCOPE, thread, country], thread)).toEqual([FIELD_SCOPE, thread])
  })
})

describe('popScope', () => {
  it('walks back one step', () => {
    expect(popScope([FIELD_SCOPE, thread, country])).toEqual([FIELD_SCOPE, thread])
  })
  it('never pops past the field', () => {
    expect(popScope([FIELD_SCOPE])).toEqual([FIELD_SCOPE])
    expect(popScope([])).toEqual([FIELD_SCOPE])
  })
})

describe('scopeTitle', () => {
  it('names the field honestly', () => {
    expect(scopeTitle(FIELD_SCOPE)).toBe('The world')
  })
  it('uses the label for a focused thing', () => {
    expect(scopeTitle(thread)).toBe('Hamas Disarmament Deal')
    expect(scopeTitle(country)).toBe('Israel')
  })
})

describe('scopeKey', () => {
  it('is stable and unique per scope', () => {
    expect(scopeKey(thread)).toBe('thread:dynamic-topic-8057')
    expect(scopeKey(FIELD_SCOPE)).toBe('field:*')
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- lensScope`
Expected: FAIL — cannot resolve `./lensScope`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/lensScope.ts`:

```ts
/**
 * The Lens is one anatomy at N scopes. This module owns the scope value and the
 * breadcrumb trail between scopes.
 *
 * Re-visiting an earlier scope REWINDS the trail instead of appending, so
 * pivoting thread → country → back to the same thread cannot grow an unbounded
 * breadcrumb.
 */
export type LensScopeKind = 'field' | 'thread' | 'country' | 'person' | 'signal'

export interface LensScope {
  kind: LensScopeKind
  id: string
  label: string
}

export const FIELD_SCOPE: LensScope = { kind: 'field', id: '*', label: 'The world' }

export function scopeKey(s: LensScope): string {
  return `${s.kind}:${s.id}`
}

export function pushScope(trail: LensScope[], next: LensScope): LensScope[] {
  const base = trail.length ? trail : [FIELD_SCOPE]
  const at = base.findIndex((s) => scopeKey(s) === scopeKey(next))
  if (at >= 0) return base.slice(0, at + 1)
  return [...base, next]
}

export function popScope(trail: LensScope[]): LensScope[] {
  if (trail.length <= 1) return [FIELD_SCOPE]
  return trail.slice(0, -1)
}

export function scopeTitle(s: LensScope): string {
  return s.label
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- lensScope`
Expected: PASS, 9 tests.

- [ ] **Step 5: Hold the trail in the nav context**

In `frontend-v2/src/contexts/MobileNavContext.tsx`, extend the value:

```tsx
import { FIELD_SCOPE, pushScope, popScope, type LensScope } from '../lib/lensScope'
```

```tsx
interface MobileNavValue {
  consoleTab: ConsoleTab
  setConsoleTab: (t: ConsoleTab) => void
  trail: LensScope[]
  focusLens: (s: LensScope) => void
  unfocusLens: () => void
}
```

```tsx
const [trail, setTrail] = useState<LensScope[]>([FIELD_SCOPE])
const focusLens = useCallback((s: LensScope) => setTrail((t) => pushScope(t, s)), [])
const unfocusLens = useCallback(() => setTrail((t) => popScope(t)), [])
const value = useMemo(
  () => ({ consoleTab, setConsoleTab, trail, focusLens, unfocusLens }),
  [consoleTab, trail, focusLens, unfocusLens],
)
```

Import `useCallback` alongside the existing hooks. The trail lives here, not in `App`, so it survives the Brief↔console hop — that is the spec's "the Lens remembers its scope".

- [ ] **Step 6: Create the Lens surface**

Create `frontend-v2/src/components/LensPanel.tsx`:

```tsx
import type { ReactNode } from 'react'
import { useMobileNav } from '../contexts/MobileNavContext'
import { scopeTitle, type LensScopeKind } from '../lib/lensScope'
import './LensPanel.css'

/**
 * One renderer per scope kind. `App` owns every panel's props, so it supplies
 * the elements and the Lens only decides WHICH one is showing and how you got
 * there. That keeps this component free of five different prop contracts.
 */
export type ScopeRenderers = Record<LensScopeKind, ReactNode>

interface LensPanelProps {
  renderers: ScopeRenderers
}

/**
 * The Lens tab. One anatomy, five scopes. At *field* scope it shows the ranked
 * field (what the Threads tab used to be); at any focused scope it shows that
 * thing's read. Sections `where it lives` and `connected` arrive in Task 8;
 * `attention` is already rendered by the scope's own panel.
 */
export function LensPanel({ renderers }: LensPanelProps) {
  const { trail, unfocusLens } = useMobileNav()
  const scope = trail[trail.length - 1]

  return (
    <div className="lens-panel">
      {trail.length > 1 && (
        <button type="button" className="lens-breadcrumb" onClick={unfocusLens}>
          ← {scopeTitle(trail[trail.length - 2])}
        </button>
      )}
      {renderers[scope.kind]}
    </div>
  )
}
```

**The five renderers, all existing components:**

| scope kind | renderer |
|---|---|
| `field` | `NarrativeThreads` — the ranked field that was the Threads tab |
| `thread` | `ThemeDetail` — the read, which already carries `PUBLIC ATTENTION · THIS THREAD` |
| `country` | `CountryBrief` |
| `person` | `EntityPanel` |
| `signal` | `SignalDetailPanel` — which already serves connected threads + semantic neighbours |

If any of these is a default export, adjust the import in `App.tsx` accordingly — grep the component file for `export`.

- [ ] **Step 7: Style it**

Create `frontend-v2/src/components/LensPanel.css`:

```css
.lens-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow-y: auto;
    padding-bottom: var(--mobile-bottom-reserve);
}

.lens-breadcrumb {
    position: sticky;
    top: 0;
    z-index: 2;
    display: flex;
    align-items: center;
    min-height: 44px;
    padding: 0 12px;
    background: var(--color-bg-secondary);
    border: 0;
    border-bottom: 1px solid rgba(var(--color-neutral-rgb), 0.18);
    font: inherit;
    font-size: 12px;
    color: inherit;
    cursor: pointer;
}
```

- [ ] **Step 8: Render it in the mobile shell**

In `frontend-v2/src/App.tsx`, replace the Task-6 placeholder (`lensPanel = threadsPanel`) with the real thing:

```tsx
const lensPanel = (
  <PanelErrorBoundary panelName="LENS">
    <LensPanel
      renderers={{
        field: threadsPanel,
        thread: themeDetailElement,
        country: countryBriefElement,
        person: entityPanelElement,
        signal: signalDetailElement,
      }}
    />
  </PanelErrorBoundary>
)
```

where each `*Element` is the JSX `App` already builds for that panel — extract the existing expressions into locals rather than re-deriving their props. `threadsPanel` already exists as a local.

Then make focusing route through the Lens: wherever `handleThemeSelect` currently opens the overlay, also call `focusLens({ kind: 'thread', id: threadId, label })` and `setConsoleTab('lens')` when `isMobile`. Leave the desktop overlay path untouched.

- [ ] **Step 9: Verify at 375×812**

Open `/app`, tap **Lens** — the ranked field renders. Tap a thread — the read renders with a `← The world` breadcrumb. Tap the breadcrumb — back to the field. Then hop to **Brief** and back to **Lens** and confirm the scope survived:

```js
(()=>{const c=document.querySelector('.lens-breadcrumb');return JSON.stringify({breadcrumb:c?c.textContent.trim():null,heading:(document.querySelector('.lens-panel h2')?.textContent||'').trim().slice(0,40)})})()
```

Expected: the breadcrumb and heading are the ones you left on.

- [ ] **Step 10: Regression-check at 1440×900**

Resize, reload `/app`, open a thread. Expected: the desktop `ThemeDetail` overlay behaves exactly as before; no `.lens-panel` in the DOM.

- [ ] **Step 11: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/lensScope.ts frontend-v2/src/lib/lensScope.test.ts frontend-v2/src/components/LensPanel.tsx frontend-v2/src/components/LensPanel.css frontend-v2/src/contexts/MobileNavContext.tsx frontend-v2/src/App.tsx
git commit -m "feat(mobile): the Lens tab — one surface that re-scopes, with a breadcrumb (#236)"
```

---

## Task 8: The two new Lens sections

`where it lives` and `connected` — the sections that absorb the Map tab and Universe.

**Files:**
- Create: `frontend-v2/src/lib/lensSections.ts`
- Create: `frontend-v2/src/lib/lensSections.test.ts`
- Modify: `frontend-v2/src/components/LensPanel.tsx`
- Modify: `frontend-v2/src/components/LensPanel.css`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/lensSections.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { buildSections, type LensPayload } from './lensSections'

const full: LensPayload = {
  countries: [{ code: 'IL', name: 'Israel', count: 68 }, { code: 'PS', name: 'Gaza Strip', count: 31 }],
  connected: [{ id: 'dynamic-topic-99', label: 'Gaza aid corridor', receipt: '2 countries shared' }],
  attention: [{ source: 'politics@lemmy.world', title: 'Trump says Iran facing last chance', score: 0.89 }],
}

describe('buildSections', () => {
  it('renders a populated section with its rows', () => {
    const s = buildSections(full)
    expect(s.whereItLives.state).toBe('ok')
    expect(s.whereItLives.rows).toHaveLength(2)
    expect(s.connected.state).toBe('ok')
    expect(s.attention.state).toBe('ok')
  })

  it('states an honest reason instead of hiding an empty section', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] })
    expect(s.whereItLives).toEqual({ state: 'empty', reason: 'No country resolved for this scope.', rows: [] })
    expect(s.connected).toEqual({ state: 'empty', reason: 'No measured neighbour cleared the bar.', rows: [] })
    expect(s.attention).toEqual({ state: 'empty', reason: 'No public attention matched this scope.', rows: [] })
  })

  it('marks a lane degraded rather than pretending it is empty', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'db_timeout' })
    expect(s.connected.state).toBe('degraded')
    expect(s.connected.reason).toBe('Neighbours could not be measured right now.')
  })

  it('never drops a receipt from a connected row', () => {
    const s = buildSections(full)
    expect(s.connected.rows[0]).toMatchObject({ label: 'Gaza aid corridor', receipt: '2 countries shared' })
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- lensSections`
Expected: FAIL — cannot resolve `./lensSections`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/lensSections.ts`:

```ts
/**
 * The Lens's five sections, built from whatever the current scope resolved.
 *
 * Two rules, both from the spec:
 *  - An empty section renders its REASON. It never renders blank and it never
 *    renders filler.
 *  - A `connected` row always carries its receipt. This section is the mobile
 *    stand-in for the Universe, and the story-lens gate refused to ship a lens
 *    that showed neighbours without honest receipts — that verdict is inherited
 *    here.
 */
export interface CountryRow { code: string; name: string; count: number }
export interface ConnectedRow { id: string; label: string; receipt: string }
export interface AttentionRow { source: string; title: string; score: number }

export interface LensPayload {
  countries: CountryRow[]
  connected: ConnectedRow[]
  attention: AttentionRow[]
}

export type LaneStatus = Partial<Record<'countries' | 'connected' | 'attention', string>>

export interface Section<T> {
  state: 'ok' | 'empty' | 'degraded'
  reason?: string
  rows: T[]
}

export interface LensSections {
  whereItLives: Section<CountryRow>
  connected: Section<ConnectedRow>
  attention: Section<AttentionRow>
}

function section<T>(rows: T[], emptyReason: string, degradedReason: string, degraded?: string): Section<T> {
  if (degraded) return { state: 'degraded', reason: degradedReason, rows: [] }
  if (!rows.length) return { state: 'empty', reason: emptyReason, rows: [] }
  return { state: 'ok', rows }
}

export function buildSections(payload: LensPayload, lanes: LaneStatus = {}): LensSections {
  return {
    whereItLives: section(
      payload.countries,
      'No country resolved for this scope.',
      'Geography could not be measured right now.',
      lanes.countries,
    ),
    connected: section(
      payload.connected,
      'No measured neighbour cleared the bar.',
      'Neighbours could not be measured right now.',
      lanes.connected,
    ),
    attention: section(
      payload.attention,
      'No public attention matched this scope.',
      'Public attention could not be measured right now.',
      lanes.attention,
    ),
  }
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- lensSections`
Expected: PASS, 4 tests.

- [ ] **Step 5: Render the sections in the Lens**

In `frontend-v2/src/components/LensPanel.tsx`, widen the context destructure to
`const { trail, unfocusLens, focusLens } = useMobileNav()`, add
`import { buildSections, type LensPayload, type LaneStatus } from '../lib/lensSections'`
and two new props (`payload: LensPayload` and `lanes?: LaneStatus`) supplied by
`App`. Then, below the scope's read, add:

```tsx
{scope.kind !== 'field' && (
  <>
    <section className="lens-section">
      <span className="lens-section-label">where it lives</span>
      {sections.whereItLives.state === 'ok' ? (
        sections.whereItLives.rows.map((c) => (
          <button key={c.code} type="button" className="lens-row"
            onClick={() => focusLens({ kind: 'country', id: c.code, label: c.name })}>
            <span>{c.name}</span><span className="lens-row-meta">{c.count}</span>
          </button>
        ))
      ) : (
        <p className="lens-empty">{sections.whereItLives.reason}</p>
      )}
    </section>

    <section className="lens-section">
      <span className="lens-section-label">connected · measured</span>
      {sections.connected.state === 'ok' ? (
        sections.connected.rows.map((r) => (
          <button key={r.id} type="button" className="lens-row"
            onClick={() => focusLens({ kind: 'thread', id: r.id, label: r.label })}>
            <span>↔ {r.label}</span><span className="lens-row-meta">{r.receipt}</span>
          </button>
        ))
      ) : (
        <p className="lens-empty">{sections.connected.reason}</p>
      )}
    </section>
  </>
)}
```

Build `sections` with `const sections = buildSections(payload, lanes)`, where `payload.countries` comes from the thread's existing country counts, `payload.connected` from `GET /api/v2/story/{id}/siblings` for a thread scope (and from co-occurring countries at country scope), and `payload.attention` from the public-attention data `ThemeDetail` already fetches. Pass a lane status of `{ connected: 'db_timeout' }` when the siblings request fails, so the section degrades honestly instead of reading as empty.

- [ ] **Step 6: Style the rows**

Append to `frontend-v2/src/components/LensPanel.css`:

```css
.lens-section {
    border-top: 1px solid rgba(var(--color-neutral-rgb), 0.18);
    padding: 8px 12px 10px;
}

.lens-section-label {
    display: block;
    margin-bottom: 4px;
    font-size: 10px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    opacity: 0.62;
}

.lens-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    min-height: 44px;
    padding: 0 4px;
    background: transparent;
    border: 0;
    border-bottom: 1px solid rgba(var(--color-neutral-rgb), 0.1);
    font: inherit;
    font-size: 13px;
    text-align: left;
    color: inherit;
    cursor: pointer;
}

.lens-row-meta {
    flex: 0 0 auto;
    font-size: 11px;
    opacity: 0.6;
    white-space: nowrap;
}

.lens-empty {
    margin: 0;
    font-size: 12px;
    opacity: 0.7;
}
```

- [ ] **Step 7: Verify at 375×812**

Open `/app`, Lens tab, open a thread. Screenshot: both sections render. Tap a country row — the Lens re-scopes to that country and the breadcrumb grows. Tap a connected row — it re-scopes to that thread. Then confirm every connected row shows a receipt:

```js
(()=>{const rows=[...document.querySelectorAll('.lens-section')].map(s=>({label:s.querySelector('.lens-section-label').textContent,rows:[...s.querySelectorAll('.lens-row')].map(r=>r.textContent.trim().slice(0,50)),empty:(s.querySelector('.lens-empty')?.textContent||null)}));return JSON.stringify(rows)})()
```

Expected: no `connected` row without a receipt suffix; empty sections carry a reason string, never `null` with no rows.

- [ ] **Step 8: Regression-check at 1440×900**

Resize, reload, open a thread. Expected: the desktop overlay unchanged, no `.lens-section` present.

- [ ] **Step 9: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/lensSections.ts frontend-v2/src/lib/lensSections.test.ts frontend-v2/src/components/LensPanel.tsx frontend-v2/src/components/LensPanel.css
git commit -m "feat(mobile): Lens gains 'where it lives' and 'connected' — the map and the constellation, scoped (#236)"
```

---

# TRACK C — the honest boundary

## Task 9: Search with the constellation

The owner's call: hide Universe, "pero que salgan las constelaciones en la búsqueda". Search becomes a full-screen sheet whose thread hits carry their measured neighbours as tappable rows.

**Files:**
- Create: `frontend-v2/src/lib/searchConstellation.ts`
- Create: `frontend-v2/src/lib/searchConstellation.test.ts`
- Create: `frontend-v2/src/components/SearchSheet.tsx`
- Create: `frontend-v2/src/components/SearchSheet.css`
- Modify: `frontend-v2/src/App.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/searchConstellation.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { flattenConstellation } from './searchConstellation'

const hits = [
  {
    id: 'dynamic-topic-1',
    label: 'Hamas Disarmament Deal',
    neighbours: [
      { id: 'dynamic-topic-9', label: 'Gaza aid corridor', receipt: '2 countries shared' },
      { id: 'dynamic-topic-7', label: 'Iran nuclear talks', receipt: 'rare actor shared' },
    ],
  },
  { id: 'dynamic-topic-2', label: 'Ceuta Migration Crisis', neighbours: [] },
]

describe('flattenConstellation', () => {
  it('puts each hit above its neighbours', () => {
    expect(flattenConstellation(hits).map((r) => r.id)).toEqual([
      'dynamic-topic-1', 'dynamic-topic-9', 'dynamic-topic-7', 'dynamic-topic-2',
    ])
  })
  it('marks depth so the UI can indent without re-deriving it', () => {
    const rows = flattenConstellation(hits)
    expect(rows[0].depth).toBe(0)
    expect(rows[1].depth).toBe(1)
    expect(rows[3].depth).toBe(0)
  })
  it('carries the receipt on every neighbour row', () => {
    expect(flattenConstellation(hits)[1].receipt).toBe('2 countries shared')
  })
  it('gives a hit no receipt of its own', () => {
    expect(flattenConstellation(hits)[0].receipt).toBeNull()
  })
  it('drops a neighbour that arrives without a receipt', () => {
    const bad = [{ id: 'a', label: 'A', neighbours: [{ id: 'b', label: 'B', receipt: '' }] }]
    expect(flattenConstellation(bad).map((r) => r.id)).toEqual(['a'])
  })
})
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test --prefix frontend-v2 -- searchConstellation`
Expected: FAIL — cannot resolve `./searchConstellation`.

- [ ] **Step 3: Implement**

Create `frontend-v2/src/lib/searchConstellation.ts`:

```ts
/**
 * Search results carry their measured neighbourhood.
 *
 * This is the phone's replacement for the Universe cloud: the constellation
 * stated as rows you can hit with a thumb. A neighbour with no receipt is
 * DROPPED rather than rendered — the story-lens gate shipped dark precisely
 * because a lens over unreceipted neighbours is a false claim.
 */
export interface SearchNeighbour { id: string; label: string; receipt: string }
export interface SearchHit { id: string; label: string; neighbours: SearchNeighbour[] }

export interface ConstellationRow {
  id: string
  label: string
  depth: 0 | 1
  receipt: string | null
}

export function flattenConstellation(hits: SearchHit[]): ConstellationRow[] {
  const rows: ConstellationRow[] = []
  for (const hit of hits) {
    rows.push({ id: hit.id, label: hit.label, depth: 0, receipt: null })
    for (const n of hit.neighbours) {
      if (!n.receipt) continue
      rows.push({ id: n.id, label: n.label, depth: 1, receipt: n.receipt })
    }
  }
  return rows
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `npm test --prefix frontend-v2 -- searchConstellation`
Expected: PASS, 5 tests.

- [ ] **Step 5: Build the sheet**

Create `frontend-v2/src/components/SearchSheet.tsx`:

```tsx
import { useState } from 'react'
import { flattenConstellation, type SearchHit } from '../lib/searchConstellation'
import './SearchSheet.css'

interface SearchSheetProps {
  onPick: (id: string, label: string) => void
  onClose: () => void
  /** Runs the existing unified search and attaches measured siblings. */
  fetchHits: (q: string) => Promise<SearchHit[]>
}

export function SearchSheet({ onPick, onClose, fetchHits }: SearchSheetProps) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle')

  async function run(next: string) {
    setQ(next)
    if (next.trim().length < 2) { setHits([]); setState('idle'); return }
    setState('loading')
    try {
      setHits(await fetchHits(next))
      setState('idle')
    } catch {
      setHits([])
      setState('error')
    }
  }

  const rows = flattenConstellation(hits)

  return (
    <div className="search-sheet" role="dialog" aria-label="Search Atlas">
      <div className="search-sheet-bar">
        <input
          className="search-sheet-input"
          value={q}
          autoFocus
          placeholder="Topics, countries, people…"
          onChange={(e) => run(e.target.value)}
        />
        <button type="button" className="search-sheet-close" onClick={onClose} aria-label="Close search">✕</button>
      </div>
      <div className="search-sheet-rows">
        {state === 'error' && <p className="search-sheet-note">Search could not be reached right now.</p>}
        {state === 'idle' && q.trim().length >= 2 && rows.length === 0 && (
          <p className="search-sheet-note">Nothing matched.</p>
        )}
        {rows.map((r) => (
          <button
            key={`${r.depth}-${r.id}`}
            type="button"
            className={`search-row depth-${r.depth}`}
            onClick={() => onPick(r.id, r.label)}
          >
            <span>{r.depth === 1 ? `↔ ${r.label}` : r.label}</span>
            {r.receipt && <span className="search-row-receipt">{r.receipt}</span>}
          </button>
        ))}
      </div>
    </div>
  )
}
```

`fetchHits` is supplied by `App`: call the same unified-search endpoint `SearchBar.tsx` already uses, then for each live-thread hit request `GET /api/v2/story/{id}/siblings` and map each sibling into `{ id, label, receipt }`, where `receipt` is the sibling's stated basis. A sibling with no basis string gets an empty `receipt` and `flattenConstellation` drops it.

Create `frontend-v2/src/components/SearchSheet.css`:

```css
.search-sheet {
    position: fixed;
    inset: 0;
    z-index: 9400;
    display: flex;
    flex-direction: column;
    background: var(--color-bg-secondary);
}

.search-sheet-bar {
    display: flex;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(var(--color-neutral-rgb), 0.18);
}

.search-sheet-input {
    flex: 1;
    min-height: 44px;
    font-size: 16px;
    padding: 0 10px;
    background: transparent;
    border: 1px solid rgba(var(--color-neutral-rgb), 0.25);
    border-radius: 6px;
    color: inherit;
}

.search-sheet-close {
    min-width: 44px;
    min-height: 44px;
    background: transparent;
    border: 0;
    color: inherit;
    font-size: 16px;
    cursor: pointer;
}

.search-sheet-rows {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-bottom: var(--mobile-bottom-reserve);
}

.search-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    min-height: 44px;
    padding: 0 12px;
    background: transparent;
    border: 0;
    border-bottom: 1px solid rgba(var(--color-neutral-rgb), 0.1);
    font: inherit;
    font-size: 13px;
    text-align: left;
    color: inherit;
    cursor: pointer;
}

.search-row.depth-1 {
    padding-left: 28px;
    font-size: 12px;
    opacity: 0.85;
}

.search-row-receipt {
    flex: 0 0 auto;
    font-size: 11px;
    opacity: 0.6;
    white-space: nowrap;
}

.search-sheet-note {
    margin: 12px;
    font-size: 12px;
    opacity: 0.7;
}
```

- [ ] **Step 6: Wire the entry point**

In `frontend-v2/src/App.tsx`, under `isMobile`, replace the inline command-bar search field with a search **button** that opens `SearchSheet`. Leave the desktop `SearchBar` untouched.

- [ ] **Step 7: Verify at 375×812**

Open `/app`, tap search, type `gaza`. Screenshot: hits at depth 0 with indented neighbour rows carrying receipts. Tap a neighbour — the Lens opens on it.

- [ ] **Step 8: Regression-check at 1440×900**

Resize, reload. Expected: the desktop search bar unchanged; no `SearchSheet` in the DOM.

- [ ] **Step 9: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/lib/searchConstellation.ts frontend-v2/src/lib/searchConstellation.test.ts frontend-v2/src/components/SearchSheet.tsx frontend-v2/src/components/SearchSheet.css frontend-v2/src/App.tsx
git commit -m "feat(mobile): search carries the constellation — neighbours as receipted rows (#236)"
```

---

## Task 10: The boundary — Universe hidden, Workbench reduced to capture

**Files:**
- Modify: `frontend-v2/src/App.tsx`
- Modify: `frontend-v2/src/components/WorkbenchPanel.tsx`
- Modify: `frontend-v2/src/components/WorkbenchPanel.css`

- [ ] **Step 1: Do not mount Universe or Orbital below 768**

In `frontend-v2/src/App.tsx`, guard both the `GLOBE | UNIVERSE` toggle and the `UniverseView` / `OrbitalThreadView` renders with `!isMobile`. Where the toggle used to be, on mobile render nothing — the Lens's `connected` section is the mobile answer and Task 8 already ships it.

- [ ] **Step 2: State the boundary where a user would look for it**

In `frontend-v2/src/components/WorkbenchPanel.tsx`, when `useIsMobile()` is true, render the pin list and the export button, and replace the constellation, the research plan and the dossier with:

```tsx
<p className="wb-desktop-only">
  The constellation, the research plan and the dossier are worked on the computer.
  Pins you capture here sync to that session; export is below.
</p>
```

- [ ] **Step 3: Fix the two measured Workbench defects**

In `frontend-v2/src/components/WorkbenchPanel.css`, append:

```css
/* #236 — on a phone the Workbench is capture only: the 168px sidebar becomes a
   full-width strip, and the note textarea goes to 16px so iOS stops zooming the
   page when it takes focus. */
@media (max-width: 768px) {
    .wb-sidebar {
        width: 100%;
    }
    .wb-note-input {
        font-size: 16px;
    }
    .wb-desktop-only {
        margin: 12px;
        font-size: 12px;
        opacity: 0.75;
    }
}
```

Substitute the real sidebar class if `.wb-sidebar` differs — it is the rule at `WorkbenchPanel.css:10` carrying `width: 168px`.

- [ ] **Step 4: Verify at 375×812**

Open `/app`, open the Workbench from the `···` overflow. Screenshot: full-width sidebar, honest desktop-only note, export present. Confirm `◆` pin from a Lens row lands in the pin list.

- [ ] **Step 5: Regression-check at 1440×900**

Resize, reload, open the Workbench. Expected: 168px sidebar, constellation, plan, dossier — all unchanged.

- [ ] **Step 6: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/App.tsx frontend-v2/src/components/WorkbenchPanel.tsx frontend-v2/src/components/WorkbenchPanel.css
git commit -m "feat(mobile): honest boundary — Universe off the phone, Workbench is capture only (#236)"
```

---

## Task 11: Landing mobile nav

The four nav links are `hidden md:flex` (`Landing.tsx:113`) with nothing replacing them.

**Files:**
- Modify: `frontend-v2/src/pages/Landing.tsx`

- [ ] **Step 1: Add the menu**

`Landing.tsx` is the **one** file where Tailwind is allowed. Lift the four links into a single array so labels and hrefs live in one place, then render them twice — the existing desktop row, and a mobile dropdown.

```tsx
const NAV_LINKS = [
  { href: '#moving', label: 'Moving' },
  { href: '#how', label: 'How it works' },
  { href: '/docs', label: 'Docs' },
  { href: '#support', label: 'Support' },
]
```

```tsx
const [navOpen, setNavOpen] = useState(false)
```

Next to the existing `hidden md:flex` link row (`Landing.tsx:113`), add:

```tsx
<button
  type="button"
  className="md:hidden min-h-[44px] min-w-[44px] px-3 text-xl"
  aria-expanded={navOpen}
  aria-label="Menu"
  onClick={() => setNavOpen((o) => !o)}
>
  ☰
</button>
{navOpen && (
  <nav className="md:hidden absolute right-4 top-16 z-50 flex flex-col rounded-lg border border-emerald-900/20 bg-white shadow-lg dark:bg-neutral-900">
    {NAV_LINKS.map((l) => (
      <a
        key={l.href}
        href={l.href}
        className="min-h-[44px] px-5 py-3 text-sm"
        onClick={() => setNavOpen(false)}
      >
        {l.label}
      </a>
    ))}
  </nav>
)}
```

Replace the hard-coded links inside the existing `hidden md:flex` row with `NAV_LINKS.map(...)` so the two lists cannot drift. Confirm the four `href` values against the current markup before committing — the array above must mirror what is already there, not invent new anchors.

- [ ] **Step 2: Verify at 375×812**

Open `http://localhost:3000/`. Screenshot: the `☰` button is present, tapping it reveals Moving / How / Docs / Support, and each one navigates.

- [ ] **Step 3: Regression-check at 1440×900**

Expected: the horizontal link row, no `☰`.

- [ ] **Step 4: Build, test, commit**

```bash
npm run build --prefix frontend-v2 && npm test --prefix frontend-v2
git add frontend-v2/src/pages/Landing.tsx
git commit -m "fix(mobile): Landing nav links reachable on a phone (#236)"
```

---

## Final acceptance sweep

Run once, after Task 11, at 375×812 on a fresh load of `/brief` and `/app`:

- [ ] Brief leads with news — `document.querySelector('.brief-lead').getBoundingClientRect().top + scrollY < 500`
- [ ] Reader is never covered — the Lens content bottom is above `.mobile-tabbar`'s top
- [ ] No navigating element under 44px — `[...document.querySelectorAll('button,a,.lens-row,.signal-row,.narrative-row')].filter(e=>e.getBoundingClientRect().height>0 && e.getBoundingClientRect().height<44).length === 0`
- [ ] Lens re-scopes thread → country → back with a correct breadcrumb and no stacked overlay
- [ ] No truncated country name in the Lens's `where it lives`
- [ ] Universe and Orbital are absent from the mobile DOM
- [ ] Honesty survives — tier chips, court chips, `degraded`, `UNVERIFIED` all present at 375
- [ ] `useIsMobile` consumer count is above 5: `grep -rl useIsMobile frontend-v2/src | wc -l`
- [ ] 1440×900 desktop unchanged across `/`, `/brief`, `/app`, Workbench open
- [ ] `npm run build --prefix frontend-v2` and `npm test --prefix frontend-v2` both green

Then update `docs/superpowers/specs/2026-08-04-mobile-native-ia-design.md` with a status line, and comment the outcome on issue #236.
