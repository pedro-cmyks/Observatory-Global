# Exploration Flywheel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Atlas from a set of surfaces that *capture* findings into an exploration flywheel where each finding renders the next as a live, one-click seed and the analyst's pins auto-organize into a building investigation.

**Architecture:** Invitation-rich (the app renders next-steps, never acts unprompted). New logic lands as **pure `src/lib/*.ts` modules** (node-env vitest, house style), consumed by thin JSX wiring that is verified via `npm run build` + browser (no React render tests exist). The spine is **compound focus** (the console holds `country ∧ theme ∧ person` instead of one-at-a-time); on top sit the **Frame** (Trail + classified pins), **capture-anywhere** (one `◆`), the **relationship detector**, **typed launchers**, and the **mobile reshape**.

**Tech Stack:** React + TypeScript (Vite), Vitest 4.1.5 (node env, globals OFF), vanilla CSS (dashboard). Design spec: `docs/superpowers/specs/2026-07-21-exploration-flywheel-design.md`. Code map: `docs/state/2026-07-21-analyst-journey-map.md`.

---

## Conventions (read once, apply everywhere)

**House test pattern** (from `frontend-v2/src/lib/threadOrder.test.ts`, `workbench.test.ts`, `aiRead.test.ts`):
- New logic → `frontend-v2/src/lib/<x>.ts` (named exports, **no React/DOM imports**) + co-located `frontend-v2/src/lib/<x>.test.ts`.
- Every test file starts: `import { describe, it, expect } from 'vitest'` (globals are OFF — omitting = ReferenceError). Add `vi, beforeEach, afterEach` as needed.
- Node env: `localStorage`/`fetch`/`window` are **undefined**. Stub localStorage with a `Map` **before** the module import (see Task 2.2). Stub fetch with `vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok:true, json:async()=>({})}))` + `afterEach(()=>vi.unstubAllGlobals())`.
- Components are **not** unit-tested (no jsdom/testing-library). Extract the decision into a pure lib fn, test that; verify the JSX wiring in the browser.

**Run commands** (all from `frontend-v2/`):
- One test file: `npx vitest run src/lib/<name>.test.ts`
- Whole suite: `npm test` (= `vitest run`)
- Build gate (typechecks `src` only — **excludes** test files): `npm run build`
- **TDD authority is `npx vitest run`, not the build** (tsconfig excludes `*.test.ts`).

**Commit rhythm:** one commit per task (test + impl together for pure libs; wiring change + browser-verify note for JSX). Conventional-commit subjects. Frequent.

**Honesty rails (non-negotiable, apply to every UI string added):** pins = deliberate evidence (a glance never becomes evidence); relationship detection labeled *measured, not asserted*; nothing paid/asserting fires without an explicit click; every scope legible + reversible.

---

## Phase map

| Phase | Ships (working, testable on its own) | Depends on | Core new pure libs |
|---|---|---|---|
| **1 Compound focus** | thread-open stops wiping the frame; `country ∧ theme ∧ person` co-exist; multi-chip indicator | — | `focusReducer.ts` |
| **2 The Frame** | pins auto-sort WHO/WHERE/WHAT; ambient Trail; citations attach under pins | 1 | `pinLanes.ts`, `ambientTrail.ts` (+ `workbench.ts` edits) |
| **3 Capture-anywhere** | one `◆` on universe / map / neighbor / biography / day-evidence / entity-coverage / thread person-chips | 2 | `capturePayloads.ts` |
| **4 Detector** | "these pins connect on X" over pins + brief headlines, threshold-gated, strongest-first | 2 | `briefRelationDetector.ts` |
| **5 Launchers** | gaps→fresh-query, tensions→corroborate, neighbors→open, leads→open+keep+re-run | (1) | `launcherVerbs.ts` |
| **6 Mobile** | reading-first seams: return-to-Brief, cockpit on-demand, carry-context (q/label) | 1 | `navParams.ts` |

Phases 1→2→(3,4) are the critical path. Phase 5 depends only loosely on Phase 1 (nav callbacks). Phase 6 depends on Phase 1's URL work. Each phase is independently shippable.

---

## PHASE 1 — Compound focus (the spine)

**Why first:** every "findings compound" behavior depends on the focus bus holding more than one dimension. Recon finding: `country+theme` already co-exist in `filter` today; the ONLY blockers are (a) `setPerson` nulls country+theme (`FocusContext.tsx:158-172`), and (b) the legacy single-`focus` collapse (`FocusContext.tsx:227-238`) that drives the map/summary/indicator. `SignalStream` already ANDs all three (`SignalStream.tsx:197-199`) — the cheapest proof surface.

### Task 1.1: Pure focus-transition reducer

**Files:**
- Create: `frontend-v2/src/lib/focusReducer.ts`
- Test: `frontend-v2/src/lib/focusReducer.test.ts`

The reducer encodes the current transition table (`FocusContext.tsx:97-224`) with **exactly three edits**: `country` and `theme` stop nulling `person`; `person` stops nulling `country`/`theme`/`themeLabel`. Everything else stays identical (thread/concept/region remain the "reset" dimensions; `entity` mirrors `person`).

- [ ] **Step 1: Write the failing test**

```ts
// frontend-v2/src/lib/focusReducer.test.ts
import { describe, it, expect } from 'vitest'
import { nextFocusDims, EMPTY_DIMS, type FocusDims } from './focusReducer'

const dims = (over: Partial<FocusDims> = {}): FocusDims => ({ ...EMPTY_DIMS, ...over })

describe('nextFocusDims — compound intersection', () => {
  it('person no longer clears country or theme (the core fix)', () => {
    const start = dims({ country: 'IL', theme: 'gaza-ceasefire', themeLabel: 'Gaza ceasefire' })
    const out = nextFocusDims(start, { dim: 'person', value: 'Netanyahu' })
    expect(out.person).toBe('Netanyahu')
    expect(out.entity).toBe('Netanyahu') // person mirrors entity
    expect(out.country).toBe('IL')       // KEPT
    expect(out.theme).toBe('gaza-ceasefire') // KEPT
    expect(out.themeLabel).toBe('Gaza ceasefire')
  })

  it('country no longer clears an active person', () => {
    const start = dims({ person: 'Netanyahu', entity: 'Netanyahu' })
    const out = nextFocusDims(start, { dim: 'country', value: 'EG' })
    expect(out.country).toBe('EG')
    expect(out.person).toBe('Netanyahu') // KEPT
    expect(out.entity).toBe('Netanyahu') // mirror KEPT
  })

  it('theme keeps country and person, sets label', () => {
    const start = dims({ country: 'EG', person: 'al-Sisi', entity: 'al-Sisi' })
    const out = nextFocusDims(start, { dim: 'theme', value: 'ceasefire', label: 'Ceasefire mediation' })
    expect(out.theme).toBe('ceasefire')
    expect(out.themeLabel).toBe('Ceasefire mediation')
    expect(out.country).toBe('EG')
    expect(out.person).toBe('al-Sisi')
  })

  it('all three compose from a deep-link order theme→country→person', () => {
    let s = nextFocusDims(EMPTY_DIMS, { dim: 'theme', value: 't', label: 'T' })
    s = nextFocusDims(s, { dim: 'country', value: 'US' })
    s = nextFocusDims(s, { dim: 'person', value: 'X' })
    expect([s.theme, s.country, s.person]).toEqual(['t', 'US', 'X'])
  })

  it('clearing person clears its entity mirror only', () => {
    const start = dims({ country: 'US', person: 'X', entity: 'X' })
    const out = nextFocusDims(start, { dim: 'person', value: null })
    expect(out.person).toBeNull()
    expect(out.entity).toBeNull()
    expect(out.country).toBe('US') // untouched
  })

  it('thread stays an exclusive reset dimension', () => {
    const start = dims({ country: 'US', theme: 't', person: 'X' })
    const out = nextFocusDims(start, { dim: 'thread', value: 'dynamic-topic-9' })
    expect(out.thread).toBe('dynamic-topic-9')
    expect([out.country, out.theme, out.person]).toEqual([null, null, null])
  })

  it('clear resets every dimension', () => {
    const out = nextFocusDims(dims({ country: 'US', theme: 't', person: 'X' }), { dim: 'clear' })
    expect(out).toEqual(EMPTY_DIMS)
  })

  it('does not mutate its input', () => {
    const start = dims({ country: 'US' })
    nextFocusDims(start, { dim: 'person', value: 'X' })
    expect(start.person).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/focusReducer.test.ts`
Expected: FAIL — "Cannot find module './focusReducer'".

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend-v2/src/lib/focusReducer.ts
// Pure focus-transition reducer. Encodes the FocusContext setter table with the
// compound-focus edits: country/theme no longer clear person; person no longer
// clears country/theme/themeLabel. thread/concept/region stay exclusive resets.
// ConceptFilter/RegionFilter are opaque here (typed as unknown) — the reducer
// only ever nulls or passes them through, never inspects them.

export interface FocusDims {
  thread: string | null
  country: string | null
  theme: string | null
  entity: string | null
  person: string | null
  themeLabel: string | null
  concept: unknown | null
  region: unknown | null
}

export const EMPTY_DIMS: FocusDims = {
  thread: null, country: null, theme: null, entity: null,
  person: null, themeLabel: null, concept: null, region: null,
}

export type FocusAction =
  | { dim: 'country'; value: string | null }
  | { dim: 'theme'; value: string | null; label?: string | null }
  | { dim: 'person'; value: string | null }
  | { dim: 'entity'; value: string | null }
  | { dim: 'thread'; value: string | null; label?: string | null }
  | { dim: 'concept'; value: unknown | null }
  | { dim: 'region'; value: unknown | null }
  | { dim: 'clear' }

export function nextFocusDims(prev: FocusDims, action: FocusAction): FocusDims {
  switch (action.dim) {
    case 'clear':
      return { ...EMPTY_DIMS }
    case 'country':
      // was: nulls thread, entity, person. NOW: keep person (+entity mirror) and theme.
      return { ...prev, country: action.value, thread: null }
    case 'theme':
      // was: nulls thread, entity, person. NOW: keep country, person.
      return {
        ...prev,
        theme: action.value,
        thread: null,
        themeLabel: action.value ? (action.label ?? (prev.theme === action.value ? prev.themeLabel : null)) : null,
      }
    case 'person':
      // was: nulls thread, country, theme, themeLabel, concept, region. NOW: keep country/theme.
      return {
        ...prev,
        person: action.value,
        entity: action.value, // person mirrors entity (both set/cleared together)
        thread: null,
      }
    case 'entity':
      // standalone entity (rare). Keep country/theme; drop person if it was the mirror.
      return {
        ...prev,
        entity: action.value,
        person: prev.person && prev.person === prev.entity ? null : prev.person,
        thread: null,
      }
    case 'thread':
      // exclusive reset dimension (unchanged). thread-open uses the 'theme' action instead (Task 1.3).
      return {
        ...EMPTY_DIMS,
        thread: action.value,
        themeLabel: action.value ? (action.label ?? null) : null,
      }
    case 'concept':
      return { ...prev, concept: action.value, thread: null, entity: null, person: null, themeLabel: null }
    case 'region':
      return { ...EMPTY_DIMS, region: action.value }
    default:
      return prev
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/focusReducer.test.ts`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/focusReducer.ts frontend-v2/src/lib/focusReducer.test.ts
git commit -m "feat(flywheel): pure focus-transition reducer for compound focus"
```

### Task 1.2: Rewire FocusContext setters through the reducer

**Files:**
- Modify: `frontend-v2/src/contexts/FocusContext.tsx:97-224` (setter bodies), keep the `useCallback` wrappers + `lockedBy`/`streamLevel` computation.

No new test (setters are React closures; the transition table is now tested in 1.1). This is a mechanical swap verified by build + browser.

- [ ] **Step 1: Replace each setter's inline nulling with `nextFocusDims`**

For each of `setCountry`, `setTheme`, `setPerson`, `setEntity`, `setThread`, `setConcept`, `setRegion`, `clearFilter`, compute the new dimension fields via `nextFocusDims(prev, {dim, value, label})`, then overlay the setter-specific `lockedBy` and preserve `streamLevel`. Example for `setPerson`:

```ts
const setPerson = useCallback((person: string | null) => {
  setFilterState(prev => ({
    ...prev,
    ...nextFocusDims(prev, { dim: 'person', value: person }),
    lockedBy: person ? prev.lockedBy : (prev.country || prev.theme ? prev.lockedBy : null),
  }))
}, [])
```

Keep `setTheme`/`setCountry`'s existing `lockedBy` ternaries (they already reference `prev.country`/`prev.theme`). Import: `import { nextFocusDims } from '../lib/focusReducer'`.

- [ ] **Step 2: Fix the legacy `focus` collapse to be compound-aware where it drives panels**

The collapse at `FocusContext.tsx:227-238` picks ONE dimension by priority. Leave the collapse itself (many consumers still read a single `focus`), but note in a comment that `filter.country`/`filter.theme`/`filter.person` are the source of truth for compound scope. The panel-open effects are re-keyed in Task 1.7.

- [ ] **Step 3: Verify build + browser**

Run: `cd frontend-v2 && npm run build` → expect success.
Browser: open `/app`, focus a country, then click a person chip → confirm both the country brief AND person scope hold (previously person wiped country). Confirm `SignalStream` shows the intersection (it already ANDs all three).

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/contexts/FocusContext.tsx
git commit -m "feat(flywheel): FocusContext setters keep country∧theme∧person (compound)"
```

### Task 1.3: Thread-open ADDS to focus instead of clearing it

**Files:**
- Modify: `frontend-v2/src/App.tsx:2034-2052` (`onThreadSelect`).

- [ ] **Step 1: Replace the frame-clear with an additive theme set**

Currently `onThreadSelect` does `setTheme(null); ...; clearFocus()`. Replace the `clearFocus()` + `setTheme(null)` with `setTheme(target.theme, undefined, target.thread?.label ?? undefined)` so the open thread's theme is set WHILE keeping any active `filter.country`/`filter.person` (the reducer now preserves them). Keep the local `setSelectedTheme(...)` + map fly. The list re-scope to siblings (`NarrativeThreads.tsx:285-320`) stays, but now composes with the retained country/person.

- [ ] **Step 2: Verify browser**

Focus person "Netanyahu" → open a Gaza thread from NarrativeThreads → confirm the person chip + the thread both remain, the map keeps the person scope, and ThemeDetail opens. Previously the person vanished.

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "feat(flywheel): thread-open composes with active focus instead of clearing"
```

### Task 1.4: Multi-chip focus indicator

**Files:**
- Modify: `frontend-v2/src/components/FocusIndicator.tsx:15-51`.

- [ ] **Step 1: Render one dismissible chip per active dimension**

Read `filter` directly (not the collapsed `focus`). Render a chip for each of `filter.country` / `filter.theme` (use `filter.themeLabel` for text) / `filter.person` that is non-null. Each chip's `✕` calls the matching single-dimension setter with `null` (`setCountry(null)` / `setTheme(null)` / `setPerson(null)`) — **not** `clearFilter()` which wipes all. Keep a final "clear all" affordance that calls `clearFilter()`.

- [ ] **Step 2: Verify browser**

With country∧theme∧person active, confirm three chips render; `✕` on the person chip drops only the person (country + theme stay); "clear all" drops everything.

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/components/FocusIndicator.tsx
git commit -m "feat(flywheel): multi-chip focus indicator with per-dimension deselect"
```

### Task 1.5: Per-dimension deselect in clearAll/popPanel

**Files:**
- Modify: `frontend-v2/src/App.tsx:942-949` (close-country effect), `:954-969` (`popPanel`).

- [ ] **Step 1: Guard the close-country effect**

The effect at `:942` closes CountryBrief whenever `filter.country` goes null. Since `setPerson` no longer nulls country, this no longer mis-fires — verify by inspection that only an explicit `setCountry(null)` closes the country panel. No code change if the guard already keys on `filter.country` alone; add a comment documenting the compound assumption.

- [ ] **Step 2: Make popPanel pop the most-recent dimension, not clearFocus everything**

In `popPanel` (`:954-969`), where it currently does `clearFocus()` for a person focus, change to `setPerson(null)` (drop only person) so a back gesture peels one layer. Keep the panel-close ordering. This preserves the compound frame on partial back.

- [ ] **Step 3: Verify browser + commit**

Browser: Esc/back with country∧person active drops person first, then country. Then:
```bash
git add frontend-v2/src/App.tsx
git commit -m "feat(flywheel): per-dimension back/deselect preserves the compound frame"
```

### Task 1.6: Compound-aware focus request key + map/summary scope

**Files:**
- Modify: `frontend-v2/src/lib/focusRequestKey.ts:12-18`, `frontend-v2/src/contexts/FocusDataContext.tsx:163-166,220-229`.
- Test: `frontend-v2/src/lib/focusRequestKey.test.ts` (extend existing).

- [ ] **Step 1: Extend the request key to all active dimensions (failing test first)**

```ts
// add to focusRequestKey.test.ts
it('keys on all active compound dimensions', () => {
  const a = buildFocusRequestKey({ isActive: true, country: 'US', theme: 't', person: 'X' })
  const b = buildFocusRequestKey({ isActive: true, country: 'US', theme: 't', person: 'Y' })
  expect(a).not.toBe(b) // different person must not dedupe to the same request
})
```

- [ ] **Step 2: Widen `buildFocusRequestKey` signature**

Change it to accept `{ isActive, country?, theme?, person? }` (keep the old single-focus overload if other callers rely on it, or migrate them) and return `focus=c:<country>|t:<theme>|p:<person>` for active dims, `focus=global` otherwise. Run: `npx vitest run src/lib/focusRequestKey.test.ts` → PASS.

- [ ] **Step 3: Pass multiple scope params to the map/summary fetch**

In `FocusDataContext.tsx`, build the `/api/v2/nodes` and `/api/v2/focus` requests from `filter.country` + `filter.theme` + `filter.person` (send whichever are set) instead of the single collapsed `focus_type/focus_value`. **Backend check:** confirm `/api/v2/nodes` and `/api/v2/focus` accept a `country_code` + `theme` + `person` combination; if the endpoint only accepts one `focus_type`, keep a documented precedence (person > country > theme) for the *map fly* while `SignalStream` (already compound) carries the true intersection — note this limitation in a comment and file a follow-up. Do not silently drop dimensions.

- [ ] **Step 4: Verify + commit**

```bash
git add frontend-v2/src/lib/focusRequestKey.ts frontend-v2/src/lib/focusRequestKey.test.ts frontend-v2/src/contexts/FocusDataContext.tsx
git commit -m "feat(flywheel): compound-aware focus request key + multi-dim map/summary scope"
```

### Task 1.7: Re-key the CountryBrief-open effect for compound focus

**Files:**
- Modify: `frontend-v2/src/App.tsx:921-927`.

- [ ] **Step 1: Open CountryBrief off `filter.country`, not the collapsed `focus.type`**

The effect at `:921` opens CountryBrief only when `focus.type==='country'`. Under a compound focus the collapse may resolve to `'theme'`/`'person'` even though `filter.country` is set. Re-key the effect to `filter.country` directly (mirror the ThemeDetail effect at `:930` which already keys on `filter.theme`+`filter.country`). Guard against re-opening when `selectedCountryCode` already matches.

- [ ] **Step 2: Verify browser + commit**

Browser: set person then country → CountryBrief opens even though the collapsed focus is 'person'. Then:
```bash
git add frontend-v2/src/App.tsx
git commit -m "fix(flywheel): open CountryBrief from filter.country under compound focus"
```

**Phase 1 done-check:** open a person, open a thread, open a country — all three chips persist; `SignalStream`, map, and NarrativeThreads all reflect the intersection; back peels one dimension at a time. Run `npm test` (whole suite green) + `npm run build`.

---

## PHASE 2 — The Frame (Trail + classified pins + citation unify)

**Why:** the Frame is the always-visible object that shows the compound focus AND the investigation you're building. Recon: `anchorType` is a free string (not a union) → the lane classifier MUST default-bucket unknowns; the ambient Trail needs its OWN localStorage key (it does NOT ride `investigationSync`, which only syncs `Investigation` records); citations unify by a render-time JOIN via a new optional `anchorId`, NOT by merging arrays.

### Task 2.1: `pinLanes.ts` — classify a pin into WHO / WHERE / WHAT

**Files:**
- Create: `frontend-v2/src/lib/pinLanes.ts` + `frontend-v2/src/lib/pinLanes.test.ts`.

Enumerated `anchorType` sources (recon): `PinnedItemType` = theme|person|country|signal|source|chokepoint|public_attention|temporal_snapshot|event|anomaly; plus research anchors thread|related_branch|coverage_gap; plus 'connections'. Classifier MUST tolerate unknown strings.

- [ ] **Step 1: Failing test**

```ts
// frontend-v2/src/lib/pinLanes.test.ts
import { describe, it, expect } from 'vitest'
import { pinLane, groupPinsByLane } from './pinLanes'

describe('pinLane', () => {
  it('WHO for person and source', () => {
    expect(pinLane('person')).toBe('who')
    expect(pinLane('source')).toBe('who')
  })
  it('WHERE for country, and for event/anomaly that carry a countryCode', () => {
    expect(pinLane('country')).toBe('where')
    expect(pinLane('event', { countryCode: 'US' })).toBe('where')
    expect(pinLane('event', {})).toBe('what') // no geo → default lane
  })
  it('WHAT for theme/thread/connections and unknown strings', () => {
    expect(pinLane('theme')).toBe('what')
    expect(pinLane('thread')).toBe('what')
    expect(pinLane('totally-new-kind')).toBe('what') // default-bucket
  })
  it('groups a pin list by lane preserving order', () => {
    const pins = [
      { anchorType: 'person', label: 'A' },
      { anchorType: 'country', label: 'B' },
      { anchorType: 'theme', label: 'C' },
    ] as any
    const g = groupPinsByLane(pins)
    expect(g.who.map(p => p.label)).toEqual(['A'])
    expect(g.where.map(p => p.label)).toEqual(['B'])
    expect(g.what.map(p => p.label)).toEqual(['C'])
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement**

```ts
// frontend-v2/src/lib/pinLanes.ts
export type Lane = 'who' | 'where' | 'what'
export interface LaneSnapshotHint { countryCode?: string }

const WHO = new Set(['person', 'source'])
const WHERE = new Set(['country'])
const GEO_IF_COUNTRY = new Set(['event', 'anomaly', 'signal'])

export function pinLane(anchorType: string, snapshot?: LaneSnapshotHint): Lane {
  if (WHO.has(anchorType)) return 'who'
  if (WHERE.has(anchorType)) return 'where'
  if (GEO_IF_COUNTRY.has(anchorType) && snapshot?.countryCode) return 'where'
  return 'what' // theme/thread/connections/related_branch/coverage_gap/public_attention/chokepoint/temporal_snapshot + unknowns
}

export interface LanePin { anchorType: string; snapshot?: { countryCode?: string } }
export function groupPinsByLane<T extends LanePin>(pins: T[]): { who: T[]; where: T[]; what: T[] } {
  const g = { who: [] as T[], where: [] as T[], what: [] as T[] }
  for (const p of pins) g[pinLane(p.anchorType, p.snapshot)].push(p)
  return g
}
```

- [ ] **Step 4: run (pass) → Step 5: commit** `feat(flywheel): pinLanes — classify pins into WHO/WHERE/WHAT`

### Task 2.2: `ambientTrail.ts` — the ambient exploration trail

**Files:**
- Create: `frontend-v2/src/lib/ambientTrail.ts` + `frontend-v2/src/lib/ambientTrail.test.ts`.
- Wire from: `frontend-v2/src/contexts/WorkspaceContext.tsx:206` (`trackVisit`), recording UNCONDITIONALLY **before** the active-investigation guard at `:207-208`.

Own localStorage key `atlas.frame.trail.v1`, ring-buffered (cap ~50). Does NOT sync (separate key; documented).

- [ ] **Step 1: Failing test (localStorage stubbed before import)**

```ts
// frontend-v2/src/lib/ambientTrail.test.ts
import { beforeEach, describe, it, expect, vi } from 'vitest'
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})
beforeEach(() => backing.clear())
import { recordTrailStep, readTrail, TRAIL_CAP } from './ambientTrail'

describe('ambientTrail', () => {
  it('records steps newest-first and dedupes the immediate repeat', () => {
    recordTrailStep({ surface: 'thread', kind: 'theme', value: 'a', label: 'A' })
    recordTrailStep({ surface: 'thread', kind: 'theme', value: 'a', label: 'A' })
    recordTrailStep({ surface: 'country', kind: 'country', value: 'US', label: 'US' })
    const t = readTrail()
    expect(t.map(s => s.value)).toEqual(['US', 'a'])
  })
  it('caps the ring buffer', () => {
    for (let i = 0; i < TRAIL_CAP + 10; i++) recordTrailStep({ surface: 's', kind: 'theme', value: `v${i}`, label: `${i}` })
    expect(readTrail().length).toBe(TRAIL_CAP)
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement**

```ts
// frontend-v2/src/lib/ambientTrail.ts
const KEY = 'atlas.frame.trail.v1'
export const TRAIL_CAP = 50
export interface TrailStep { surface: string; kind: string; value: string; label: string; at: string }
export type TrailInput = Omit<TrailStep, 'at'> & { at?: string }

export function readTrail(): TrailStep[] {
  try { const raw = localStorage.getItem(KEY); return raw ? (JSON.parse(raw) as TrailStep[]) : [] }
  catch { return [] }
}
export function recordTrailStep(input: TrailInput): void {
  try {
    const prev = readTrail()
    if (prev[0] && prev[0].kind === input.kind && prev[0].value === input.value) return // dedupe immediate repeat
    const step: TrailStep = { ...input, at: input.at ?? new Date(0).toISOString() } // caller may pass 'at'; tests fix it
    const next = [step, ...prev].slice(0, TRAIL_CAP)
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch { /* best-effort */ }
}
```

> Note: `new Date(0)` avoids the workflow `Date.now()` ban only in tests; in the app pass `at: new Date().toISOString()` from the caller (WorkspaceContext) so the trail carries real timestamps. Keep `recordTrailStep` accepting `at` so it stays pure/testable.

- [ ] **Step 4: run (pass) → Step 5: commit** `feat(flywheel): ambientTrail — ambient exploration trail (own store, no sync)`

- [ ] **Step 6: Wire from WorkspaceContext.trackVisit (JSX, browser-verify)**

In `WorkspaceContext.tsx:206`, at the top of `trackVisit` (before the active-investigation early-return at `:207`), call `recordTrailStep({ surface: item.type, kind: item.type, value: item.id, label: item.title, at: new Date().toISOString() })`. Verify in browser: open several surfaces without an active investigation, confirm `localStorage['atlas.frame.trail.v1']` accumulates. Commit `feat(flywheel): record ambient trail on every panel visit`.

### Task 2.3: Unify citations under pins (optional `anchorId` + render-time join)

**Files:**
- Modify: `frontend-v2/src/lib/workbench.ts` — `Citation` (`:38-64`), `CitationInput` (`:68`), `addCitation` (`:343`).
- Create: `groupCitationsByPin` in `workbench.ts` (exported) + tests in `frontend-v2/src/lib/workbench.test.ts`.

- [ ] **Step 1: Failing test (extend workbench.test.ts)**

```ts
it('groups citations under their anchor pin, unattached bucket for legacy', () => {
  const inv = createInvestigation('t')
  addPin(inv.id, { anchorId: 'theme-1', anchorType: 'theme', label: 'Gaza', pinnedAt: '' } as any)
  addCitation(inv.id, { headline: 'H1', gateStatus: 'verified', anchorId: 'theme-1' })
  addCitation(inv.id, { headline: 'H-orphan', gateStatus: 'unknown' }) // legacy, no anchorId
  const fresh = getInvestigation(inv.id)!
  const grouped = groupCitationsByPin(fresh.pins, fresh.citations)
  expect(grouped.byPin.get('theme-1')!.map(c => c.headline)).toEqual(['H1'])
  expect(grouped.unattached.map(c => c.headline)).toEqual(['H-orphan'])
})
```

- [ ] **Step 2: run (fail) → Step 3: implement**

Add optional `anchorId?: string` to `Citation` and `CitationInput`. In `addCitation` (`:350`) stamp `anchorId: input.anchorId` (do **not** fold it into `citationId` — keep the id url-derived so the same receipt under two pins doesn't collide; recon gotcha). Add:

```ts
export function groupCitationsByPin(pins: WorkbenchPin[], citations: Citation[]): {
  byPin: Map<string, Citation[]>; unattached: Citation[]
} {
  const known = new Set(pins.map(p => p.anchorId))
  const byPin = new Map<string, Citation[]>()
  const unattached: Citation[] = []
  for (const c of citations) {
    if (c.anchorId && known.has(c.anchorId)) {
      const list = byPin.get(c.anchorId) ?? []
      list.push(c); byPin.set(c.anchorId, list)
    } else unattached.push(c)
  }
  return { byPin, unattached }
}
```

- [ ] **Step 4: run (pass) → Step 5: commit** `feat(flywheel): unify citations under pins via optional anchorId + render join`

### Task 2.4: The Frame strip (desktop) — render the classified pins + trail

**Files:**
- Create: `frontend-v2/src/components/FrameStrip.tsx` + `frontend-v2/src/components/FrameStrip.css`.
- Mount in: `frontend-v2/src/App.tsx` (desktop layout, above the panels; hidden when zero pins per the prominence gradient — L2 "quiet until first pin").

JSX only (browser-verified). Reads the active investigation's pins via `useWorkspace()`, groups with `groupPinsByLane`, renders three lanes (WHO/WHERE/WHAT) of chips. Shows the active investigation title + pin count. Hidden entirely when the active investigation has 0 pins (prominence gradient). Vanilla CSS only.

- [ ] Step 1: Build `FrameStrip.tsx` consuming `groupPinsByLane(items.map(toPinShape))`; each chip clickable to open its pin (reuse `handleOpenPin` pattern). Step 2: mount in App desktop layout with `{activeInvHasPins && <FrameStrip/>}`. Step 3: `npm run build` + browser-verify lanes populate as you pin. Step 4: commit `feat(flywheel): Frame strip — classified WHO/WHERE/WHAT pins in L2`.

**Phase 2 done-check:** pinning classifies into lanes; the strip appears on first pin and hides at zero; citations render under their pins in the workbench/dossier; the ambient trail accumulates. `npm test` + `npm run build` green.

---

## PHASE 3 — Capture-anywhere (one `◆`)

**Why:** the discovery surfaces that most invite "what's that?" can't capture. Recon: two pin systems share one store — **entity** pins via `useWorkspace().pinItem` (universe body / neighbor / person), **receipt** pins via `PinReceiptButton` → `addCitation` (biography / day-evidence / entity-coverage / map marker). `gateStatus` is REQUIRED (`'unknown'` for un-gated). `EqualEarthMap` is read-only — thread a callback to App, don't import the store.

### Task 3.1: `capturePayloads.ts` — pure builders for entity + receipt pins

**Files:**
- Create: `frontend-v2/src/lib/capturePayloads.ts` + `frontend-v2/src/lib/capturePayloads.test.ts`.

- [ ] **Step 1: Failing test**

```ts
import { describe, it, expect } from 'vitest'
import { threadPin, personPin, countryPin, receiptFrom } from './capturePayloads'

describe('capturePayloads', () => {
  it('threadPin from a universe/neighbor node', () => {
    expect(threadPin('dynamic-topic-9', 'Gaza ceasefire')).toEqual({
      id: 'theme-dynamic-topic-9', type: 'theme', title: 'Gaza ceasefire', urlParams: '?theme=dynamic-topic-9',
    })
  })
  it('personPin encodes names with spaces/diacritics', () => {
    expect(personPin('José Ramírez')).toEqual({
      id: 'person-José Ramírez', type: 'person', title: 'José Ramírez', urlParams: '?person=Jos%C3%A9%20Ram%C3%ADrez',
    })
  })
  it('countryPin', () => {
    expect(countryPin('US', 'United States')).toEqual({
      id: 'country-US', type: 'country', title: 'United States', urlParams: '?country=US',
    })
  })
  it('receiptFrom always includes gateStatus unknown for un-gated rows', () => {
    const c = receiptFrom({ headline: '&amp;H', source: 'X', url: 'u', publishedDate: '2026-07-01' })
    expect(c.gateStatus).toBe('unknown')
    expect(c.headline).toBe('&H') // decoded
    expect(c.url).toBe('u')
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement** (`threadPin`/`personPin`/`countryPin` return `Omit<PinnedItem,'notes'|'timestamp'>` shapes; `receiptFrom` returns a `CitationInput` with `gateStatus:'unknown'` default and an entity-decoding helper for headlines — reuse the repo's `decodeEntities` if exported, else inline the minimal `&amp;`/`&#xNN;` decode and unit-test it). → **Step 4:** run (pass) → **Step 5: commit** `feat(flywheel): pure capture-payload builders (entity + receipt pins)`.

### Task 3.2–3.7: Wire `◆` onto each surface (JSX, browser-verified)

Each is a small wiring task using the Task 3.1 builders. Per surface: add the affordance, `stopPropagation` so it doesn't trigger the row's open handler, toggle via `isPinned`/`unpinItem` (entity) or `PinReceiptButton` (receipt). Commit each separately.

- [ ] **3.2 Universe body ◆** — `UniverseView.tsx` hover card (`:789-809`): `useWorkspace().pinItem(threadPin(node.id, node.label))`. Entity pin. `feat(flywheel): pin a thread from a universe node`.
- [ ] **3.3 Dossier neighbor ◆** — `DossierConnections.tsx` neighbor `<g>` (`:515-539`) + Nearby list (`:610-621`): inject an optional `onPinNeighbor(base_id, label)` prop into `InvestigativeUniverse` (so the report-export path stays inert) wired from `WorkbenchConstellation` → `useWorkspace().pinItem(threadPin(base_id, label))`. Lights up in both the report and the live constellation. `feat(flywheel): pin an unpinned bridge/neighbor story`.
- [ ] **3.4 NarrativeThreads person-chip ◆** — `NarrativeThreads.tsx:551-553`: turn dead `<span class="person-pip">` into a control → `pinItem(personPin(p))` (+ optional `setPerson(p)` focus, already imported). `feat(flywheel): pin/focus a person from a thread row`.
- [ ] **3.5 Biography + Day-evidence receipt ◆** — `NarrativeBiography.tsx:231-248` and `DayEvidencePanel.tsx:91-98`: mount `<PinReceiptButton citation={receiptFrom(row)} contextLabel={...} />` per `<li>`. Receipt pins. `feat(flywheel): pin receipts from biography + day-evidence`.
- [ ] **3.6 EntityPanel coverage-row ◆** — `EntityPanel.tsx:436-459`: add `PinReceiptButton` per coverage `<a>` (`receiptFrom(h)`, contextLabel = `displayName`). Entity-title pin already exists — leave it. `feat(flywheel): pin coverage receipts in EntityPanel`.
- [ ] **3.7 Map country/marker ◆** — `EqualEarthMap.tsx`: add `onPinCountry?(iso,name)` + `onPinMarker?(payload)` callback props (do NOT import the store — recon). App handlers call `pinItem(countryPin(iso,name))` / `PinReceiptButton` payload from `markerHoverContent.sourceLink`. Add the ◆ to the hover tooltip (`:1110-1148`). `feat(flywheel): pin a country/marker from the map`.

Each: `npm run build` + browser-verify the ◆ toggles and the pin lands in the correct lane (Phase 2 strip). 

**Phase 3 done-check:** a story spotted on the globe, in the universe, as a bridge, or as a thread person-chip can be kept in one gesture; each lands in its WHO/WHERE/WHAT lane.

---

## PHASE 4 — The relationship detector

**Why:** the ◎ "these pins connect on X" invitation. Recon: reuse the existing pure primitives in `lib/dossierConnections.ts` (`labelKeyTokens`, `headlineMentionTerm`, `edgeStrength`). Client-side reaches only `text` + `context` tiers ("strong" needs the backend rarity actor) → *measured-not-asserted* is enforced by the tier ceiling. Candidate pool = the brief's already-fetched `data.top_threads` (no new fetch) + active investigation pins.

### Task 4.1: `briefRelationDetector.ts` — pure detector

**Files:**
- Create: `frontend-v2/src/lib/briefRelationDetector.ts` + test. Imports `labelKeyTokens`, `headlineMentionTerm`, type `LinkStrength` from `./dossierConnections`.

- [ ] **Step 1: Failing test**

```ts
import { describe, it, expect } from 'vitest'
import { detectBriefRelations } from './briefRelationDetector'

const pin = (label: string, headlines: string[], countryCode?: string) => ({
  anchorId: 'p-' + label, anchorType: 'theme', label,
  snapshot: { countryCode, evidence: headlines.map(h => ({ headline: h })) },
} as any)
const thread = (thread_id: string, label: string, headlines: string[], top?: string[]) => ({
  thread_id, label, evidence_samples: headlines.map(h => ({ headline: h })), top_countries: top,
} as any)

describe('detectBriefRelations', () => {
  it('surfaces a text-mention relation above the ≥2-token gate, strongest-first', () => {
    const pins = [pin('Gaza ceasefire mediation', ['Egypt presses ceasefire framework'])]
    const threads = [
      thread('t1', 'Ceasefire mediation talks', ['Ceasefire mediation deal nears']),
      thread('t2', 'Unrelated football result', ['Team wins the cup']),
    ]
    const rels = detectBriefRelations(pins, threads)
    expect(rels[0].threadId).toBe('t1')
    expect(rels[0].tier === 'text' || rels[0].tier === 'context').toBe(true)
    expect(rels.find(r => r.threadId === 't2')).toBeUndefined()
  })
  it('never returns the strong tier (measured-not-asserted ceiling)', () => {
    const rels = detectBriefRelations([pin('Gaza mediation', ['x'])], [thread('t', 'Gaza mediation', ['Gaza mediation'])])
    expect(rels.every(r => r.tier !== 'strong')).toBe(true)
  })
  it('shared subject-country yields a context tier', () => {
    const rels = detectBriefRelations([pin('Border unrest', [], 'IL')], [thread('t', 'Something else', [], ['IL'])])
    expect(rels.some(r => r.tier === 'context')).toBe(true)
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement** — for each pin × thread, compute a text-mention (both directions via `headlineMentionTerm` over label+evidence headlines — the ≥2-token gate is the threshold) and a shared-country context tier (`pin.snapshot.countryCode` / evidence `country_code` ∩ `thread.top_countries` / `evidence_samples[].country_code`, using SUBJECT country only — never `source_origin_country`). Emit `{ threadId, threadLabel, tier: 'text'|'context', term?, sharedCountry? }`, `text` ranked above `context`, capped (e.g. 6). Never emit `'strong'`/`'weak'`. → **Step 4:** run (pass) → **Step 5: commit** `feat(flywheel): pure brief-time relation detector (text+context, measured-not-asserted)`.

### Task 4.2: Threshold-gate + strongest-first cluster helper

- [ ] Add `topBriefRelation(rels)` returning the single strongest relation and a `hasEnoughSignal(pins, rels)` gate (fires only when ≥N related pins accumulate — the "you've pinned a lot; these connect" debounce, NOT per-click). Test the gate boundaries. Commit `feat(flywheel): threshold gate + strongest-first for the detector`.

### Task 4.3: Wire the ◎ callout (JSX, browser-verified)

- [ ] In `BriefNewspaper.tsx` (near `allThreads` `:632` and the active-inv read `:541-545`), `useMemo` `detectBriefRelations(inv.pins, allThreads)` keyed on the pins set + `allThreads.map(t=>t.thread_id).join('|')` (mirror the `liveReceiptUrls` memo). Render the strongest passing relation as a quiet "connects to your investigation · measured, not asserted" affordance with **Scope** (Phase 1 setters) and **＋Report** actions. Degrade to nothing when no active investigation / no relation. Also surface the same ◎ in the Frame strip (Phase 2) and, on mobile, ONLY in the pull-up sheet (never interrupts the read — Phase 6). Commit `feat(flywheel): render the ◎ detected-relationship invitation`.

**Phase 4 done-check:** after pinning several related items, a quiet ◎ appears offering to scope / start a report; unrelated pins never trigger it; the label says "measured, not asserted"; no new network fetch.

---

## PHASE 5 — Typed launchers

**Why:** stop the report being terminal. Recon: launcher grammar → new pure `launcherVerbs.ts` mirroring `verdictChips.resolveVerdictAction`. `DossierView` currently receives NO nav callbacks — thread them from App → `WorkbenchPanel` (`:256-263`) → `DossierView`. Verb ceilings are dictated by the data: coverage gaps have no id → fresh-query only; cross-read/contested rows have no thread_id → corroborate only; semantic neighbors are signals (no thread_id) → need a new `onSignalOpen`; leads already carry a thread_id → open+keep+re-run.

### Task 5.1: `launcherVerbs.ts` — pure verb grammar

**Files:** Create `frontend-v2/src/lib/launcherVerbs.ts` + test.

- [ ] **Step 1: Failing test**

```ts
import { describe, it, expect } from 'vitest'
import { resolveLauncherVerbs } from './launcherVerbs'

describe('resolveLauncherVerbs', () => {
  it('coverage gap → fresh-query only', () => {
    expect(resolveLauncherVerbs('coverage-gap').map(v => v.verb)).toEqual(['fresh-query'])
  })
  it('cross-read tension + contested figure → corroborate', () => {
    expect(resolveLauncherVerbs('cross-read-tension').map(v => v.verb)).toContain('corroborate')
    expect(resolveLauncherVerbs('contested-figure').map(v => v.verb)).toContain('corroborate')
  })
  it('lead + connected-thread → open (+ keep)', () => {
    expect(resolveLauncherVerbs('lead').map(v => v.verb)).toEqual(expect.arrayContaining(['open', 'keep']))
    expect(resolveLauncherVerbs('connected-thread').map(v => v.verb)).toContain('open')
  })
  it('semantic neighbor → open (via signal), isolated pin → keep + drop', () => {
    expect(resolveLauncherVerbs('semantic-neighbor').map(v => v.verb)).toContain('open')
    expect(resolveLauncherVerbs('isolated-pin').map(v => v.verb)).toEqual(expect.arrayContaining(['keep', 'drop']))
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement** — `resolveLauncherVerbs(kind: LauncherKind): LauncherVerb[]` where `LauncherKind = 'coverage-gap'|'gaps-sentence'|'cross-read-tension'|'contested-figure'|'semantic-neighbor'|'connected-thread'|'lead'|'isolated-pin'` and `LauncherVerb = { verb: 'open'|'fresh-query'|'corroborate'|'keep'|'drop'; label: string; tip: string }`. Map per the ceilings above. → **Step 4:** run (pass) → **Step 5: commit** `feat(flywheel): pure launcher-verb grammar`.

### Task 5.2: Thread nav callbacks into the dossier (JSX)

- [ ] Add `onOpenThread` / `onOpenParams` / `onFreshQuery` (= `onStartInvestigation`) / `onCorroborate` to `DossierView` props (`:93`) and forward them from `WorkbenchPanel` (`:256-263`, which already receives them from App `:2278-2285`). Commit `feat(flywheel): thread navigation callbacks into DossierView`.

### Task 5.3–5.6: Wire each launcher (JSX, browser-verified)

- [ ] **5.3 Coverage gap → fresh-query** — `DossierView.tsx:974-983`: wrap each gap `<li>` as a button → `onFreshQuery(g.label)`. `feat(flywheel): coverage gaps launch a fresh query`.
- [ ] **5.4 Cross-read tension + contested figure → corroborate** — `DossierView.tsx:819-832` and `:766-790`: add a per-row corroborate action → `runCorroboration(true)` (+ optional open-external-url for the tension quotes). `feat(flywheel): tensions/contested figures launch corroboration`.
- [ ] **5.5 Semantic neighbor → in-app open** — `SignalDetailPanel.tsx:322-343`: replace external `<a target=_blank>` with an in-app open copying the connected-threads pattern (`:236`); add `onSignalOpen(signalId:number)` prop (`:70`) wired from `SignalStream.tsx:590` (parent re-fetches a full Signal → nested SignalDetailPanel), fallback `onCountryClick(n.country_code)`. Keep the url as a secondary "read original". `feat(flywheel): semantic neighbors open in-app`.
- [ ] **5.6 Leads → keep + open + re-run** — `WorkbenchPanel.tsx:482-497`: keep the current `addPin` (◆ keep) and add `open` (`onOpenThread(t.thread_id,label)`) + optional re-run (`runAiRead` after pin so the galaxy re-measures). `feat(flywheel): leads launch open + keep + re-run`.

**Phase 5 done-check:** a listed gap opens a query; a tension opens a corroboration; a semantic neighbor opens in-app; a lead can be opened and re-run — publishing is a turn of the wheel.

---

## PHASE 6 — Mobile reading-first + carry-context

**Why:** the phone seams (Brief→thread→close dumps into the cockpit; the WebGL... actually 2D-canvas cockpit stays alive while reading; category/label context dropped on navigation). Recon: extract pure `navParams` helpers; gate the cockpit by conditional render (`EqualEarthMap` has no pause prop); `useUrlSync` rebuilds the whole query string and will DELETE any `?q`/`?label` unless added to that writer.

### Task 6.1: `navParams.ts` — pure URL carry-context helpers

**Files:** Create `frontend-v2/src/lib/navParams.ts` + test.

- [ ] **Step 1: Failing test**

```ts
import { describe, it, expect } from 'vitest'
import { buildBriefParams, parseConsoleDeepLink } from './navParams'

describe('navParams', () => {
  it('buildBriefParams carries theme+label+q+country forward', () => {
    const qs = buildBriefParams({ country: 'US', theme: 'gaza', themeLabel: 'Gaza ceasefire', storyQuery: 'oil' })
    const p = new URLSearchParams(qs)
    expect(p.get('country')).toBe('US')
    expect(p.get('theme')).toBe('gaza')
    expect(p.get('label')).toBe('Gaza ceasefire')
    expect(p.get('q')).toBe('oil')
  })
  it('parseConsoleDeepLink reads q/theme/label/country/attention', () => {
    expect(parseConsoleDeepLink('?theme=gaza&label=Gaza&country=US&q=oil'))
      .toEqual({ theme: 'gaza', label: 'Gaza', country: 'US', q: 'oil', attention: null })
  })
})
```

- [ ] **Step 2: run (fail) → Step 3: implement** `buildBriefParams(state)` → query string (country, theme, label=themeLabel, q=storyQuery — only when present) and `parseConsoleDeepLink(search)` → `{ q, theme, label, country, attention }`. → **Step 4:** run (pass) → **Step 5: commit** `feat(flywheel): pure nav carry-context helpers`.

### Task 6.2: Wire carry-context (JSX, browser-verified)

- [ ] **openBrief carries theme/label/q** — `App.tsx:1287-1294`: build via `buildBriefParams({ selectedCountryCode, selectedTheme, storyQuery })`. `feat(flywheel): Brief-open carries the open thread + query`.
- [ ] **Deep-link consumes q + label** — `App.tsx:716-754`: use `parseConsoleDeepLink(location.search)`; add a `q` branch → `setStoryQuery(q)`; pass `label` as the 5th arg to `handleThemeSelect` (`:729`). **Guard the `useUrlSync` rebuild** (`useUrlSync.ts:42-55`): add `q`/`label` to that writer OR consume+clear them in the deep-link effect before write-back — pick one and comment it (recon: this is the #1 trap). `feat(flywheel): console consumes ?q and ?label deep-links`.
- [ ] **Fix stale entrySource** — `App.tsx:358-361`: read the reactive `location.search` (already bound `:260`) + add it to the `useMemo` deps, so `entry=brief` is seen after the first keep-alive mount. `feat(flywheel): entrySource reactive under keep-alive`.

### Task 6.3: Mobile reading-first seams (JSX, browser-verified)

- [ ] **Thread-close returns to Brief** — `App.tsx:967` (popPanel false path) / `:1977` (`closeAll`): when `isMobile` and closing the last reading panel AND `entrySource==='brief'` (now reactive), `navigate('/brief')` instead of dropping to the blank Stream tab. `feat(flywheel): mobile thread-close returns to the Brief`.
- [ ] **Gate the cockpit while reading** — `App.tsx:2170-2181`: only include `radarPanel`/`<EqualEarthMap>` when `mobileTab==='map'` (mobile), so the 2D-canvas RAF loop (`EqualEarthMap.tsx:841/1030`) stops while reading. Verify re-mount preserves `flyCountry`/reset on tab-return. `feat(flywheel): unmount the map cockpit while reading on mobile`.
- [ ] **Frame as pull-up sheet + quiet detection** — reuse `FrameStrip` (Phase 2) as a bottom sheet on mobile; the ◎ detected relation renders ONLY here (never a mid-read banner). `feat(flywheel): mobile Frame sheet with quiet detection`.

**Phase 6 done-check:** on a phone, read a Brief story → open a thread → the "keep going" seeds are inline → close returns to the Brief; the map isn't animating behind the read; a deep-link carries the label so the chip isn't the generic skeleton.

---

## Success criteria → task mapping

1. Findings compound → Phase 1 (all tasks).
2. Every "look here next" is live → Phase 5 + Phase 3 ◆.
3. Capture from any surface, one gesture → Phase 3.
4. Always know which investigation the pin lands in → Phase 2 (Frame strip shows active investigation + count).
5. The report launches the next investigation → Phase 5.
6. On a phone, a finding leads to the next → Phase 6.
7. No honesty regression → detector tier ceiling (Phase 4), measured-not-asserted labels, pins-only-are-evidence (Phase 2 Trail/Frame split), explicit-click on paid/asserting (unchanged).

## Self-review notes

- **Spec coverage:** every spec §4–§9 requirement maps to a phase (Frame §4→P2; capture §5→P3; detect §6→P4; launch §7→P5; mobile §8→P6; agency/honesty §2,§9→enforced across). The forward Brief-spine (§3 candidate pool) = Phase 4's `detectBriefRelations` over `data.top_threads` (no return-to-Brief navigation added — correct per the "forward only" decision).
- **Type consistency:** `pinLane`/`groupPinsByLane` (P2) reused by the Frame strip (P2) and mobile sheet (P6); `threadPin`/`personPin`/`countryPin`/`receiptFrom` (P3) reused across all capture wiring; `nextFocusDims` (P1) is the single transition source. Verb strings are one union in `launcherVerbs.ts`.
- **Known risk to watch:** Task 1.6 backend multi-dimension scope — if `/api/v2/nodes`/`/focus` reject a compound scope, the map falls back to a documented precedence while `SignalStream` carries the true intersection (never silently drop a dimension). Confirm the endpoint contract before Task 1.6.
- **Parked (not in this plan):** multi-hop transitive chains (separate task, already spawned); proactive auto-advance (rejected).
