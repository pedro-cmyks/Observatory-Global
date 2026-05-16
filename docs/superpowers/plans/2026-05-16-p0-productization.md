# P0 Productization Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the three highest-trust P0 issues from the 2026-05-16 video UX review — prefetch the Brief so it loads instantly, replace the opaque "Coverage Analysis unavailable" with data-derived context, and prevent investigation context from vanishing when the user pivots between panels.

**Architecture:**
- #136 adds a `briefingPrefetch` lib that Landing calls on mount; BriefNewspaper reads the sessionStorage cache before fetching.
- #137 adds a data-derived fallback sentence in ThemeDetail when AI insight is unavailable, and `data-tip` methodology tooltips on "global mood" and "signal density" in BriefNewspaper.
- #138 extends `PrevCtx` in App.tsx with a `country` variant and saves it when NarrativeThreads triggers a country pivot while a theme is active.

**Tech Stack:** React 19, TypeScript, vitest, Vite 7, vanilla CSS, react-router-dom v7. Backend FastAPI. No new dependencies.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend-v2/src/lib/briefingPrefetch.ts` | Cache read/write helpers for sessionStorage briefing prefetch |
| Create | `frontend-v2/src/lib/briefingPrefetch.test.ts` | Unit tests for `readBriefingCache` |
| Modify | `frontend-v2/src/pages/Landing.tsx` | Call `prefetchBriefing(24)` on mount |
| Modify | `frontend-v2/src/pages/BriefNewspaper.tsx` | Consume cache in `fetchData`; add methodology tooltips |
| Modify | `frontend-v2/src/components/ThemeDetail.tsx` | Data-derived fallback when insight unavailable |
| Modify | `frontend-v2/src/App.tsx` | Extend `PrevCtx` with country type; save theme context on NarrativeThreads country click |

---

## Task 1: briefingPrefetch library

**Files:**
- Create: `frontend-v2/src/lib/briefingPrefetch.ts`

- [ ] **Step 1.1: Create the file**

```typescript
// frontend-v2/src/lib/briefingPrefetch.ts
const CACHE_KEY = 'atlas_brief_prefetch'
const MAX_AGE_MS = 4 * 60 * 1000 // 4 minutes — stays within Vite HMR and user attention span

interface PrefetchPayload {
  briefing: unknown
  insight: string | null
  fetchedAt: number
  hours: number
}

export function readBriefingCache(hours: number): { briefing: unknown; insight: string | null } | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const payload: PrefetchPayload = JSON.parse(raw)
    if (payload.hours !== hours) return null
    if (Date.now() - payload.fetchedAt > MAX_AGE_MS) return null
    return { briefing: payload.briefing, insight: payload.insight }
  } catch {
    return null
  }
}

export async function prefetchBriefing(hours = 24): Promise<void> {
  // Skip if fresh cache already exists
  if (readBriefingCache(hours)) return
  try {
    const [briefRes, insightRes] = await Promise.all([
      fetch(`/api/v2/briefing?hours=${hours}`),
      fetch(`/api/v2/briefing/insight?hours=${hours}`)
    ])
    if (!briefRes.ok) return
    const briefing = await briefRes.json()
    let insight: string | null = null
    if (insightRes.ok) {
      const insightData = await insightRes.json()
      if (insightData.insight) insight = insightData.insight
    }
    const payload: PrefetchPayload = { briefing, insight, fetchedAt: Date.now(), hours }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
  } catch {
    // Prefetch is best-effort — never block the page
  }
}
```

- [ ] **Step 1.2: Verify TypeScript compiles**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npx tsc --noEmit src/lib/briefingPrefetch.ts 2>&1 | head -20
```

Expected: no output (no errors).

---

## Task 2: Unit tests for briefingPrefetch

**Files:**
- Create: `frontend-v2/src/lib/briefingPrefetch.test.ts`

- [ ] **Step 2.1: Write failing tests first**

```typescript
// frontend-v2/src/lib/briefingPrefetch.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { readBriefingCache } from './briefingPrefetch'

// Vitest runs in Node — stub sessionStorage
const store: Record<string, string> = {}
globalThis.sessionStorage = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
  clear: () => { for (const k in store) delete store[k] },
  length: 0,
  key: () => null,
} as unknown as Storage

const CACHE_KEY = 'atlas_brief_prefetch'

beforeEach(() => sessionStorage.clear())

describe('readBriefingCache', () => {
  it('returns null when sessionStorage is empty', () => {
    expect(readBriefingCache(24)).toBeNull()
  })

  it('returns null when hours mismatch', () => {
    const payload = { briefing: { stats: {} }, insight: null, fetchedAt: Date.now(), hours: 24 }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    expect(readBriefingCache(168)).toBeNull()
  })

  it('returns null when cache is older than 4 minutes', () => {
    const payload = {
      briefing: { stats: {} },
      insight: 'test',
      fetchedAt: Date.now() - 5 * 60 * 1000, // 5 min ago
      hours: 24,
    }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    expect(readBriefingCache(24)).toBeNull()
  })

  it('returns cached data when fresh and hours match', () => {
    const briefing = { stats: { total_signals: 100 } }
    const payload = { briefing, insight: 'some insight', fetchedAt: Date.now(), hours: 24 }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    const result = readBriefingCache(24)
    expect(result).not.toBeNull()
    expect(result!.insight).toBe('some insight')
    expect(result!.briefing).toEqual(briefing)
  })

  it('returns null when sessionStorage contains malformed JSON', () => {
    sessionStorage.setItem(CACHE_KEY, '{bad json}')
    expect(readBriefingCache(24)).toBeNull()
  })
})
```

- [ ] **Step 2.2: Run tests — expect PASS**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npx vitest run src/lib/briefingPrefetch.test.ts
```

Expected output: `5 tests passed`.

- [ ] **Step 2.3: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/lib/briefingPrefetch.ts frontend-v2/src/lib/briefingPrefetch.test.ts
git commit -m "feat(brief): add briefingPrefetch lib with sessionStorage cache (#136)"
```

---

## Task 3: Landing.tsx — prefetch on mount

**Files:**
- Modify: `frontend-v2/src/pages/Landing.tsx`

The file already has a `useEffect` import from React (line 1: `import { useEffect, useRef } from 'react'`).

- [ ] **Step 3.1: Add import at top of Landing.tsx**

Find the last import line (currently `import './Landing.css'`) and add one line after it:

```typescript
import { prefetchBriefing } from '../lib/briefingPrefetch'
```

- [ ] **Step 3.2: Add prefetch call inside the Landing component**

Inside the `Landing` function body, after `const navigate = useNavigate()`, add:

```typescript
// Warm the brief cache so /brief loads instantly after CTA click
useEffect(() => { prefetchBriefing(24) }, [])
```

- [ ] **Step 3.3: Verify build**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -10
```

Expected: build succeeds (exit 0). Known large-chunk warning is acceptable.

- [ ] **Step 3.4: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/pages/Landing.tsx
git commit -m "feat(landing): prefetch briefing on mount to eliminate /brief loading delay (#136)"
```

---

## Task 4: BriefNewspaper.tsx — consume cache + loading copy

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

- [ ] **Step 4.1: Add import**

At the top of `BriefNewspaper.tsx`, find the last import line (currently `import './BriefNewspaper.css'`) and add one line before it:

```typescript
import { readBriefingCache } from '../lib/briefingPrefetch'
```

- [ ] **Step 4.2: Consume the cache in fetchData**

The `fetchData` callback starts at approximately line 101:

```typescript
const fetchData = useCallback(async (h: number) => {
    setLoading(true)
    setData(null)
    setInsight(null)
    setThemeSignals({})
    try {
        const [briefRes, insightRes] = await Promise.all([
            fetch(`/api/v2/briefing?hours=${h}`),
            fetch(`/api/v2/briefing/insight?hours=${h}`)
        ])
        if (!briefRes.ok) throw new Error(`Briefing request failed: ${briefRes.status}`)
        const briefData: BriefingData = await briefRes.json()
        setData(briefData)
        if (insightRes.ok) {
            const insightData = await insightRes.json()
            if (insightData.insight) setInsight(insightData.insight)
        }
```

Replace **only** the block from `setLoading(true)` through the `setInsight` call above the theme-signals section with:

```typescript
const fetchData = useCallback(async (h: number) => {
    setLoading(true)
    setData(null)
    setInsight(null)
    setThemeSignals({})
    try {
        // Use Landing prefetch cache when available — eliminates visible loading delay
        const cached = readBriefingCache(h)
        let briefData: BriefingData
        if (cached) {
            briefData = cached.briefing as BriefingData
            setData(briefData)
            if (cached.insight) setInsight(cached.insight)
        } else {
            const [briefRes, insightRes] = await Promise.all([
                fetch(`/api/v2/briefing?hours=${h}`),
                fetch(`/api/v2/briefing/insight?hours=${h}`)
            ])
            if (!briefRes.ok) throw new Error(`Briefing request failed: ${briefRes.status}`)
            briefData = await briefRes.json()
            setData(briefData)
            if (insightRes.ok) {
                const insightData = await insightRes.json()
                if (insightData.insight) setInsight(insightData.insight)
            }
        }
```

Everything after (theme signal fetches, try/catch/finally) remains unchanged.

- [ ] **Step 4.3: Update loading copy**

Find the loading state JSX (around line 328):

```jsx
{loading ? (
    <div className="brief-loading">
        <div className="brief-loading-lines">
            {[90, 75, 60, 80, 45].map((w, i) => (
                <div key={i} className="brief-loading-line" style={{ width: `${w}%` }} />
            ))}
        </div>
        <p>Composing brief...</p>
    </div>
```

Change only the `<p>` text:

```jsx
        <p>Loading brief…</p>
```

(The ellipsis `…` instead of `...` is intentional — consistent with the rest of the UI copy.)

- [ ] **Step 4.4: Verify build and full test suite**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -10
npx vitest run 2>&1 | tail -5
```

Expected: build passes, all existing tests pass (currently 26).

- [ ] **Step 4.5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/pages/BriefNewspaper.tsx
git commit -m "feat(brief): consume Landing prefetch cache to skip loading state (#136)"
```

---

## Task 5: ThemeDetail.tsx — data-derived insight fallback

**Files:**
- Modify: `frontend-v2/src/components/ThemeDetail.tsx`

When `insightFailed` is true and `data` is available, show a stats-derived summary instead of "Coverage analysis unavailable". This uses `data.countryBreakdown` and `data.avgSentiment` which are guaranteed to exist when `data !== null`.

- [ ] **Step 5.1: Add resolveCountryName import**

In `ThemeDetail.tsx`, after the existing imports, add:

```typescript
import { resolveCountryName } from '../lib/countryNames'
```

(Check first with `grep -n "resolveCountryName" frontend-v2/src/components/ThemeDetail.tsx` — if it's already imported, skip this step.)

- [ ] **Step 5.2: Replace the unavailable block**

Find this block (around lines 381–387):

```jsx
{insightFailed && !insightLoading && !insight && (
    <p className="theme-insight-unavailable">
        {insightError === 'insight_unavailable'
            ? 'Coverage analysis unavailable'
            : insightError === 'insight_no_credits'
                ? 'AI analysis unavailable — Anthropic account has no credits (top up at console.anthropic.com)'
                : 'Coverage analysis unavailable'}
    </p>
)}
```

Replace with:

```jsx
{insightFailed && !insightLoading && !insight && (
    <p className="theme-insight-unavailable">
        {insightError === 'insight_no_credits'
            ? 'AI analysis unavailable — Anthropic account has no credits.'
            : data
                ? (() => {
                    const top = data.countryBreakdown[0]
                    const topName = top ? resolveCountryName(top.code) : null
                    const tone = data.avgSentiment > 0.1 ? 'positive' : data.avgSentiment < -0.1 ? 'negative' : 'neutral'
                    return [
                        topName ? `Top coverage: ${topName} (${top!.count} signals).` : null,
                        `Overall tone: ${tone} (${data.avgSentiment.toFixed(2)}).`,
                        `${data.total.toLocaleString()} total signals. AI summary unavailable.`,
                    ].filter(Boolean).join(' ')
                })()
                : 'AI summary unavailable.'
        }
    </p>
)}
```

- [ ] **Step 5.3: Verify build**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -10
```

Expected: build passes.

- [ ] **Step 5.4: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/components/ThemeDetail.tsx
git commit -m "ux(theme-detail): show data-derived fallback when AI insight unavailable (#137)"
```

---

## Task 6: BriefNewspaper.tsx — methodology tooltips

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

Add `data-tip` attributes to the opaque labels users saw in the video: "global mood", "signal density", and the editor's analysis section tag. The codebase convention is `data-tip="text"` (never native `title=`).

- [ ] **Step 6.1: Tooltip on global mood stat**

Find (around line 357–360):

```jsx
<div className={`brief-stat ${moodClass(displayedStats.avg_sentiment)}`}>
    <span className="brief-stat-value">{moodLabel(displayedStats.avg_sentiment)}</span>
    <span className="brief-stat-label">{countryFilter ? 'country mood' : 'global mood'}</span>
</div>
```

Replace with:

```jsx
<div
    className={`brief-stat ${moodClass(displayedStats.avg_sentiment)}`}
    data-tip="Aggregate sentiment across all signals in this window. Positive = media frames events favourably on balance. Negative = critical or alarming framing dominates. Neutral = mixed or factual coverage."
>
    <span className="brief-stat-value">{moodLabel(displayedStats.avg_sentiment)}</span>
    <span className="brief-stat-label">{countryFilter ? 'country mood' : 'global mood'}</span>
</div>
```

- [ ] **Step 6.2: Tooltip on signal density map label**

Find (around line 365):

```jsx
<div className="brief-minimap-label">Signal density — {TIME_RANGE_LABELS[timeRange]}</div>
```

Replace with:

```jsx
<div
    className="brief-minimap-label"
    data-tip="Signal density: how many media signals Atlas captured per country in this window. Darker = more coverage. Coverage volume reflects media attention, not geopolitical importance."
>
    Signal density — {TIME_RANGE_LABELS[timeRange]}
</div>
```

- [ ] **Step 6.3: Tooltip on EDITOR'S ANALYSIS tag**

Find (around line 409):

```jsx
<div className="brief-section-tag">{countryFilter ? 'COUNTRY ANALYSIS' : "EDITOR'S ANALYSIS"}</div>
```

Replace with:

```jsx
<div
    className="brief-section-tag"
    data-tip={countryFilter
        ? "Country-scoped summary derived from signal clusters and source patterns in this window."
        : "AI-generated pattern reading based on signal volume, sentiment shifts, and narrative spread. Describes observable coverage patterns — does not reflect Atlas editorial opinion."
    }
>
    {countryFilter ? 'COUNTRY ANALYSIS' : "EDITOR'S ANALYSIS"}
</div>
```

- [ ] **Step 6.4: Verify build + tests**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -10
npx vitest run 2>&1 | tail -5
```

Expected: build passes, 26+ tests pass.

- [ ] **Step 6.5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/pages/BriefNewspaper.tsx
git commit -m "ux(brief): add methodology tooltips to mood, signal density, and editor analysis (#137)"
```

---

## Task 7: App.tsx — investigation context preservation

**Files:**
- Modify: `frontend-v2/src/App.tsx`

Two changes:
1. Extend the `PrevCtx` type to include a `country` variant so Source clicks from CountryBrief can restore the country panel on Back.
2. When NarrativeThreads fires `onCountrySelect` while a theme is active in the stream, save the theme as `prevStreamCtx` before switching panels — so the Back button returns to the theme.

### Part A — extend PrevCtx

- [ ] **Step 7.1: Extend the PrevCtx union type**

Find (around line 318):

```typescript
type PrevCtx = { type: 'chokepoint'; cp: Chokepoint } | { type: 'theme'; theme: string; originCountry?: string; originCountryName?: string }
```

Replace with:

```typescript
type PrevCtx =
    | { type: 'chokepoint'; cp: Chokepoint }
    | { type: 'theme'; theme: string; originCountry?: string; originCountryName?: string }
    | { type: 'country'; code: string; name: string }
```

- [ ] **Step 7.2: Handle country type in handleStreamBack**

Find (around line 1149):

```typescript
const handleStreamBack = () => {
    if (prevStreamCtx?.type === 'chokepoint') {
        setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
        setPrevStreamCtx(null)
        // selectedChokepoint still set → ChokepointPanel reappears
    } else if (prevStreamCtx?.type === 'theme') {
        setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
        setSelectedTheme({ theme: prevStreamCtx.theme, originCountry: prevStreamCtx.originCountry, originCountryName: prevStreamCtx.originCountryName })
        setPrevStreamCtx(null)
    } else {
        closeAll()
    }
}
```

Replace with:

```typescript
const handleStreamBack = () => {
    if (prevStreamCtx?.type === 'chokepoint') {
        setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
        setPrevStreamCtx(null)
        // selectedChokepoint still set → ChokepointPanel reappears
    } else if (prevStreamCtx?.type === 'theme') {
        setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
        setSelectedTheme({ theme: prevStreamCtx.theme, originCountry: prevStreamCtx.originCountry, originCountryName: prevStreamCtx.originCountryName })
        setPrevStreamCtx(null)
    } else if (prevStreamCtx?.type === 'country') {
        handleCountryClick(prevStreamCtx.code)
        setMapFlyCountry(prevStreamCtx.code)
        setPrevStreamCtx(null)
    } else {
        closeAll()
    }
}
```

### Part B — save theme context on NarrativeThreads country click

- [ ] **Step 7.3: Save prevStreamCtx in NarrativeThreads onCountrySelect**

Find (around line 1301):

```tsx
<NarrativeThreads onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }} />
```

Replace with:

```tsx
<NarrativeThreads onCountrySelect={(code) => {
    // If a theme is open in the stream, save it so Back can restore the investigation
    if (selectedTheme) {
        setPrevStreamCtx({
            type: 'theme',
            theme: selectedTheme.theme,
            originCountry: selectedTheme.originCountry,
            originCountryName: selectedTheme.originCountryName,
        })
    }
    handleCountryClick(code)
    setMapFlyCountry(code)
}} />
```

### Part C — save country context when SourceProfile opens from CountryBrief

CountryBrief is rendered inline in the stream panel (around line 1244). The source click from CountryBrief does not yet pass through App.tsx — CountryBrief has no `onSourceClick` prop. We wire it now.

- [ ] **Step 7.4: Add onSourceClick to CountryBrief in App.tsx**

Find the CountryBrief inline render (around line 1244):

```tsx
) : isCountry ? (
    <CountryBrief inline
        countryCode={selectedCountryCode!}
        countryName={selectedCountryName}
        timeWindow={timeRangeToHours(timeRange)}
        onClose={handleStreamBack}
        onThemeSelect={(theme) => { handleThemeSelect(theme, selectedCountryCode!, selectedCountryName); setMapFlyCountry(selectedCountryCode!) }}
    />
```

Replace with:

```tsx
) : isCountry ? (
    <CountryBrief inline
        countryCode={selectedCountryCode!}
        countryName={selectedCountryName}
        timeWindow={timeRangeToHours(timeRange)}
        onClose={handleStreamBack}
        onThemeSelect={(theme) => { handleThemeSelect(theme, selectedCountryCode!, selectedCountryName); setMapFlyCountry(selectedCountryCode!) }}
        onSourceClick={(domain) => {
            setPrevStreamCtx({ type: 'country', code: selectedCountryCode!, name: selectedCountryName })
            setSelectedSourceProfile(domain)
        }}
    />
```

- [ ] **Step 7.5: Add onSourceClick prop to CountryBrief component**

File: `frontend-v2/src/components/CountryBrief.tsx`

Find the `CountryBriefProps` interface (around line 122):

```typescript
interface CountryBriefProps {
    ...
    onClose: () => void;
    onThemeSelect?: (theme: string) => void;
```

Add after `onThemeSelect`:

```typescript
    onSourceClick?: (domain: string) => void;
```

Then find where CountryBrief destructures its props (around line 169):

```typescript
    onClose,
    onThemeSelect,
```

Add:

```typescript
    onSourceClick,
```

Then find any place in CountryBrief where sources are rendered as clickable elements. Run:

```bash
grep -n "source\|Source" frontend-v2/src/components/CountryBrief.tsx | grep -i "click\|button\|onClick\|href" | head -10
```

If CountryBrief renders source rows with `onClick`, wire `onSourceClick?.(domain)` there. If there are no source click handlers, `onSourceClick` is passed but unused — that is acceptable; the prop exists for future use and for Back context preservation when it IS called externally.

- [ ] **Step 7.6: Verify build and tests**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -10
npx vitest run 2>&1 | tail -5
```

Expected: build passes, 26+ tests pass.

- [ ] **Step 7.7: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add frontend-v2/src/App.tsx frontend-v2/src/components/CountryBrief.tsx
git commit -m "ux(navigation): preserve investigation context across NarrativeThreads and Source pivots (#138)"
```

---

## Task 8: Final validation

- [ ] **Step 8.1: Run full test suite**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npx vitest run 2>&1 | tail -10
```

Expected: all tests pass. Count should be 31 (26 existing + 5 new briefingPrefetch tests).

- [ ] **Step 8.2: Run production build**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/frontend-v2
npm run build 2>&1 | tail -15
```

Expected: build succeeds. Known large-chunk warning for MapLibre/main is acceptable.

- [ ] **Step 8.3: Update STATUS.md**

In `/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/STATUS.md`, update the "Current handoff" section to reflect:
- Session 19
- Issues closed: #136, #137 (partial — tooltips + fallback), #138 (partial — NarrativeThreads + Source context)
- Next: remaining P0 (#128 Workspace viewport, #69 Spanish search, #104 Trends)

- [ ] **Step 8.4: Push to origin**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git push origin v3-intel-layer
```

---

## Self-Review

### Spec coverage check

| Requirement | Task |
|-------------|------|
| #136: Brief loads without visible delay when coming from Landing | Tasks 1–4 |
| #136: Loading state is not a confusing blank screen | Task 4.3 (copy change) |
| #137: "Coverage Analysis unavailable" shows data instead | Task 5 |
| #137: Mood/Tone/Drift labels have explanations | Task 6 |
| #138: Country click from NarrativeThreads while theme is open → Back returns to theme | Task 7.3 |
| #138: Source click from CountryBrief → Back returns to CountryBrief | Tasks 7.4–7.5 |

### What is NOT covered (deferred)

- #137: ThemeDetail itself — "Analyzing coverage patterns…" label, Drift chart baseline tooltip, Tone/Mood labels within ThemeDetail header. These can be addressed as a follow-up once the no-insight fallback is proven in production.
- #138: Compound URL state when both theme and country are active is already handled by `useUrlSync`; no change needed.
- #138: Source click wired INTO CountryBrief (actually dispatching `onSourceClick` from a rendered row) — deferred to when we audit CountryBrief source rendering.

### Placeholder scan

No TBD, TODO, or placeholder phrases present. All code blocks are complete.

### Type consistency

- `PrevCtx` extended in Task 7.1; all three uses (`chokepoint`, `theme`, `country`) reference the same discriminant field `type`.
- `CountryBrief.onSourceClick?: (domain: string) => void` matches the signature used in App.tsx Task 7.4.
- `readBriefingCache(hours: number)` signature in lib matches calls in BriefNewspaper (Task 4) and test (Task 2).
