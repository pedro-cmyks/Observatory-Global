# Atlas First-User Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Atlas's blank-state dashboard from a raw-data terminal into a navigable discovery surface for a first-time user with zero context.

**Architecture:** All changes are frontend-only. The stream panel slot (`terminal-panel.stream`) gains a new default state — `DiscoveryPanel` — rendered when no country/theme/person/chokepoint is focused. Two CSS-only changes restructure the grid and surface the Anomaly Alert. Three copy tweaks in `App.tsx` complete the onboarding layer.

**Tech Stack:** React 18, TypeScript, Vanilla CSS (no Tailwind in dashboard components), MapLibre GL, existing `/api/v2/narratives` endpoint.

---

## Pre-flight: Two Spec Items Already Implemented

Before starting, verify these are live — if so, skip their tasks:

1. **SearchBar placeholder** — `frontend-v2/src/components/SearchBar.tsx:275` already renders `placeholder="Search topics, countries, people... try 'elections Colombia'"`. No action needed.
2. **NarrativeThreads display names** — `NarrativeThreads.tsx:192` already calls `getThemeLabel(n.theme_code)` which converts GDELT codes to human-readable labels. No action needed.

---

## File Map

| Action | File | Purpose |
| --- | --- | --- |
| Modify | `frontend-v2/src/App.tsx` | Welcome Card copy, stats text, map hint state/JSX, DiscoveryPanel import + wiring |
| Modify | `frontend-v2/src/App.css` | Grid-template-areas, Anomaly border/layout, map hint styles |
| Create | `frontend-v2/src/components/DiscoveryPanel.tsx` | New default center panel — top topics in natural language |
| Create | `frontend-v2/src/components/DiscoveryPanel.css` | Styles for DiscoveryPanel |

---

## Task 1: Welcome Card copy + stats humanization

**Files:**
- Modify: `frontend-v2/src/App.tsx:720` (stats display)
- Modify: `frontend-v2/src/App.tsx:954-955` (welcome card copy)

- [ ] **Step 1: Update the stats display**

In `App.tsx` find line 720:
```tsx
{loading ? '...' : `${nodes.length} ctry • ${totalSignals.toLocaleString()} sig`}
```
Replace with:
```tsx
{loading ? '...' : `${nodes.length} countries · ${totalSignals.toLocaleString()} signals`}
```

- [ ] **Step 2: Rewrite the Welcome Card copy**

In `App.tsx` find lines 953–956 (inside the `.welcome-card` div):
```tsx
<span className="welcome-label">Last 24 hours</span>
<span className="welcome-action">See what's happening →</span>
```
Replace with:
```tsx
<span className="welcome-label">Atlas tracks how the world covers the news</span>
<span className="welcome-action">Click a country or search a topic →</span>
```

- [ ] **Step 3: Verify visually**

Run the dev server:
```bash
cd frontend-v2 && npm run dev
```
Open `http://localhost:5173`. Confirm:
- Top-right shows "36 countries · 1,234,567 signals" (no abbreviations)
- The welcome card in the bottom-left of the map shows the new copy
- Clicking the card still opens the Briefing modal (existing behavior unchanged)

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "ux: rewrite welcome card copy and humanize stats display"
```

---

## Task 2: Map click affordance hint

**Files:**
- Modify: `frontend-v2/src/App.tsx` (state + JSX)
- Modify: `frontend-v2/src/App.css` (hint styles)

- [ ] **Step 1: Add hint state to App.tsx**

In `AppContent()`, after the existing `const [showWelcome, setShowWelcome] = useState(...)` at line 324, add:

```tsx
// Starts false — shown only after mapReady + 2s delay, once per session
const [showMapHint, setShowMapHint] = useState(false)
```

- [ ] **Step 2: Show the hint 2 seconds after map is ready**

After the existing `useEffect` that toggles the heatmap layer (around line 640 in App.tsx), add:

```tsx
// Show map hint 2s after first load — only if user hasn't seen it this session
useEffect(() => {
  if (!mapReady || sessionStorage.getItem('atlas-map-hinted') === 'true') return
  const t = setTimeout(() => setShowMapHint(true), 2000)
  return () => clearTimeout(t)
}, [mapReady])
```

- [ ] **Step 3: Dismiss hint on first country click**

In `handleCountryClick` (around line 468), add one line at the top of the function:

```tsx
const handleCountryClick = (countryCode: string) => {
  if (showMapHint) {
    setShowMapHint(false)
    sessionStorage.setItem('atlas-map-hinted', 'true')
  }
  setSelectedCountryCode(countryCode)
  setShowFlows(true)
  fetchCountryDetail(countryCode)
}
```

- [ ] **Step 4: Add the hint JSX inside the map panel**

In App.tsx, inside the `.panel-content` div of the radar panel, after the `<div className="globe-vignette" />` line (around line 944), add:

```tsx
{showMapHint && !showWelcome && (
  <div className="map-hint" onClick={() => {
    setShowMapHint(false)
    sessionStorage.setItem('atlas-map-hinted', 'true')
  }}>
    Click any country to explore
  </div>
)}
```

- [ ] **Step 5: Add hint CSS to App.css**

At the end of `App.css`, add:

```css
/* Map click affordance — fades in 2s after load, dismisses on first click */
.map-hint {
  position: absolute;
  bottom: 48px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(10, 15, 26, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  font-family: var(--font-sans, system-ui);
  letter-spacing: 0.3px;
  pointer-events: auto;
  cursor: pointer;
  z-index: 10;
  animation: fadeInCard 0.4s ease;
  white-space: nowrap;
}
.map-hint:hover {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 255, 255, 0.2);
}
```

- [ ] **Step 6: Verify visually**

Reload the page in a private/incognito window (clears sessionStorage). Confirm:
- After ~2 seconds the hint "Click any country to explore" appears centered at the bottom of the map
- Clicking any country dismisses the hint
- Refreshing the page does NOT show the hint again (sessionStorage persists within the session)
- The welcome card and the hint don't overlap (hint appears above the welcome card)

- [ ] **Step 7: Commit**

```bash
git add frontend-v2/src/App.tsx frontend-v2/src/App.css
git commit -m "ux: add map click affordance hint that auto-dismisses on first interaction"
```

---

## Task 3: Grid restructure + Anomaly Alert visual weight

**Files:**
- Modify: `frontend-v2/src/App.css` (grid layout, Anomaly border, Matrix hide)

This is a CSS-only change. The Correlation Matrix panel stays in the DOM but is hidden from the default layout. The Anomaly Alert gets 2/3 of the bottom row. Narrative Threads expands to fill both right-column rows.

- [ ] **Step 1: Update the main grid template**

In `App.css`, find the `.terminal-layout` rule (around line 527). Replace the `grid-template-areas` and `grid-template-rows` values:

```css
/* BEFORE */
.terminal-layout {
  display: grid;
  grid-template-areas:
    "radar stream threads"
    "radar stream matrix"
    "integrity anomaly anomaly";
  grid-template-columns: minmax(280px, 35%) minmax(280px, 1fr) minmax(240px, 30%);
  grid-template-rows: minmax(220px, 40%) minmax(180px, 1fr) minmax(140px, 20%);
  /* ... rest unchanged */
}
```

```css
/* AFTER */
.terminal-layout {
  display: grid;
  grid-template-areas:
    "radar stream threads"
    "radar stream threads"
    "anomaly anomaly integrity";
  grid-template-columns: minmax(280px, 35%) minmax(280px, 1fr) minmax(240px, 30%);
  grid-template-rows: minmax(220px, 40%) minmax(180px, 1fr) minmax(140px, 20%);
  /* ... rest unchanged */
}
```

- [ ] **Step 2: Hide the Correlation Matrix panel**

The `.terminal-panel.matrix` element is always rendered in the DOM. Since it's no longer in `grid-template-areas`, add an explicit hide rule. Find the `.terminal-panel.matrix` rule in `App.css` (around line 605) and update it:

```css
/* BEFORE */
.terminal-panel.matrix { grid-area: matrix; }

/* AFTER */
.terminal-panel.matrix {
  grid-area: matrix;
  display: none; /* Removed from default layout — accessible via ThemeDetail */
}
```

- [ ] **Step 3: Give Anomaly Alert a visible border**

Find the `.terminal-panel.anomaly` rule (around line 608) and update its border:

```css
/* BEFORE */
.terminal-panel.anomaly {
  grid-area: anomaly;
  border: 1px solid rgba(255, 255, 255, 0.03);
  background: rgba(10, 12, 16, 0.95);
}

/* AFTER */
.terminal-panel.anomaly {
  grid-area: anomaly;
  border: 1px solid rgba(239, 68, 68, 0.15);
  background: rgba(10, 12, 16, 0.95);
}
```

- [ ] **Step 4: Update the 1100px responsive breakpoint**

Find the `@media (max-width: 1100px)` block (around line 545) and update it to not reference `matrix`:

```css
/* BEFORE */
@media (max-width: 1100px) {
  .terminal-layout {
    grid-template-areas:
      "radar stream"
      "radar stream"
      "integrity anomaly";
    grid-template-columns: minmax(260px, 40%) 1fr;
    grid-template-rows: minmax(200px, 42%) minmax(160px, 1fr) minmax(130px, 18%);
  }
  .terminal-panel.threads,
  .terminal-panel.matrix {
    display: none;
  }
}
```

```css
/* AFTER */
@media (max-width: 1100px) {
  .terminal-layout {
    grid-template-areas:
      "radar stream"
      "radar stream"
      "anomaly integrity";
    grid-template-columns: minmax(260px, 40%) 1fr;
    grid-template-rows: minmax(200px, 42%) minmax(160px, 1fr) minmax(130px, 18%);
  }
  .terminal-panel.threads,
  .terminal-panel.matrix {
    display: none;
  }
}
```

- [ ] **Step 5: Verify visually**

In the browser:
- Narrative Threads now spans both right-column rows (no matrix below it)
- Anomaly Alert spans 2/3 of the bottom row and has a faint red border
- Source Integrity occupies the right 1/3 of the bottom row
- Correlation Matrix is hidden
- No layout overflow or broken panels

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/App.css
git commit -m "ux: restructure grid — anomaly elevated, matrix hidden from default state, threads expanded"
```

---

## Task 4: DiscoveryPanel component

**Files:**
- Create: `frontend-v2/src/components/DiscoveryPanel.tsx`
- Create: `frontend-v2/src/components/DiscoveryPanel.css`

This panel is the new default content for the center slot when no context is active. It fetches from `/api/v2/narratives` (same endpoint as NarrativeThreads) and displays top topics as cards with natural-language names, trend direction, signal volume, and country spread.

- [ ] **Step 1: Create DiscoveryPanel.css**

```css
/* frontend-v2/src/components/DiscoveryPanel.css */

.discovery-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.discovery-intro {
  padding: 10px 14px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.discovery-intro-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary, #94a3b8);
  letter-spacing: 0.3px;
  margin-bottom: 2px;
}

.discovery-intro-sub {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.25);
  font-family: var(--font-mono, monospace);
}

.discovery-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.discovery-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.discovery-card:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.12);
}

.discovery-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.discovery-card-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary, #e2e8f0);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.discovery-trend {
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.discovery-trend.accelerating { color: #ef4444; }
.discovery-trend.stable { color: #60a5fa; }
.discovery-trend.fading { color: #64748b; }

.discovery-card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--color-text-muted, #64748b);
}

.discovery-spread {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.discovery-spread-track {
  height: 2px;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 1px;
  width: 48px;
  overflow: hidden;
  flex-shrink: 0;
}

.discovery-spread-fill {
  height: 100%;
  background: rgba(99, 102, 241, 0.6);
  border-radius: 1px;
}

.discovery-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted, #64748b);
  font-size: 12px;
  font-family: var(--font-mono, monospace);
}

.discovery-skeleton {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  height: 64px;
  animation: discovery-pulse 1.5s ease-in-out infinite;
}

@keyframes discovery-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
```

- [ ] **Step 2: Create DiscoveryPanel.tsx**

```tsx
// frontend-v2/src/components/DiscoveryPanel.tsx
import React, { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { getThemeLabel } from '../lib/themeLabels'
import './DiscoveryPanel.css'

interface DiscoveryTopic {
  theme_code: string
  label: string
  signal_count: number
  country_count: number
  trend: 'accelerating' | 'stable' | 'fading'
  spread_pct: number
  top_countries: string[]
}

export const DiscoveryPanel: React.FC = () => {
  const [topics, setTopics] = useState<DiscoveryTopic[]>([])
  const [loading, setLoading] = useState(true)
  const { setFocus, setMapFlyCountry } = useFocus()
  const { timeRange } = useFocusData()

  const hours = Math.min(timeRangeToHours(timeRange), 24)

  const fetchTopics = useCallback(async () => {
    try {
      const res = await fetch(`/api/v2/narratives?hours=${hours}&limit=5`)
      if (!res.ok) return
      const data = await res.json()
      setTopics(data.narratives || [])
    } catch (e) {
      console.error('[DiscoveryPanel] Fetch error', e)
    } finally {
      setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    setLoading(true)
    fetchTopics()
    const interval = setInterval(fetchTopics, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchTopics])

  const handleTopicClick = (topic: DiscoveryTopic) => {
    const label = getThemeLabel(topic.theme_code)
    setFocus('theme', topic.theme_code, label)
    if (topic.top_countries.length > 0) {
      setMapFlyCountry(topic.top_countries[0])
    }
  }

  const trendSymbol = (trend: string) => {
    if (trend === 'accelerating') return '▲'
    if (trend === 'fading') return '▼'
    return '→'
  }

  if (loading) {
    return (
      <div className="discovery-panel">
        <div className="discovery-intro">
          <div className="discovery-intro-title">Most active right now</div>
          <div className="discovery-intro-sub">global narrative momentum · last 24h</div>
        </div>
        <div className="discovery-list">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="discovery-skeleton" />
          ))}
        </div>
      </div>
    )
  }

  if (topics.length === 0) {
    return (
      <div className="discovery-panel">
        <div className="discovery-intro">
          <div className="discovery-intro-title">Most active right now</div>
          <div className="discovery-intro-sub">global narrative momentum · last 24h</div>
        </div>
        <div className="discovery-empty">No active topics found</div>
      </div>
    )
  }

  return (
    <div className="discovery-panel">
      <div className="discovery-intro">
        <div className="discovery-intro-title">Most active right now</div>
        <div className="discovery-intro-sub">global narrative momentum · last 24h · click any topic to explore</div>
      </div>
      <div className="discovery-list">
        {topics.map(topic => {
          const label = getThemeLabel(topic.theme_code)
          return (
            <div
              key={topic.theme_code}
              className="discovery-card"
              onClick={() => handleTopicClick(topic)}
              data-tip={`${label} — ${topic.signal_count.toLocaleString()} signals across ${topic.country_count} countries. Click to open the full topic breakdown.`}
            >
              <div className="discovery-card-header">
                <span className="discovery-card-name">{label}</span>
                <span className={`discovery-trend ${topic.trend}`}>
                  {trendSymbol(topic.trend)}
                </span>
              </div>
              <div className="discovery-card-meta">
                <span>{topic.signal_count.toLocaleString()} signals</span>
                <span>·</span>
                <span>{topic.country_count} countries</span>
                <div className="discovery-spread">
                  <div className="discovery-spread-track">
                    <div
                      className="discovery-spread-fill"
                      style={{ width: `${Math.min(topic.spread_pct, 100)}%` }}
                    />
                  </div>
                  <span>{topic.spread_pct}% spread</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify the component compiles**

```bash
cd frontend-v2 && npx tsc --noEmit
```

Expected: no errors related to `DiscoveryPanel.tsx`.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/DiscoveryPanel.tsx frontend-v2/src/components/DiscoveryPanel.css
git commit -m "feat: add DiscoveryPanel — natural-language topic cards for blank-state center panel"
```

---

## Task 5: Wire DiscoveryPanel into App.tsx

**Files:**
- Modify: `frontend-v2/src/App.tsx`

The stream slot in `App.tsx` already conditionally renders different panels based on active context. `DiscoveryPanel` becomes the new else-branch, replacing the raw `SignalStream` as the blank-state default.

- [ ] **Step 1: Import DiscoveryPanel**

At the top of `App.tsx`, near the other panel imports (around line 30–36), add:

```tsx
import { DiscoveryPanel } from './components/DiscoveryPanel'
```

- [ ] **Step 2: Replace the SignalStream default with DiscoveryPanel**

In the stream slot IIFE (the `{(() => { ... })()}` block starting around line 964), find the final else branch — the `SignalStream` fallback. It currently looks like:

```tsx
) : (
  <PanelErrorBoundary panelName="SIGNAL STREAM">
    <SignalStream />
  </PanelErrorBoundary>
)}
```

Replace it with:

```tsx
) : (
  <PanelErrorBoundary panelName="DISCOVERY">
    <DiscoveryPanel />
  </PanelErrorBoundary>
)}
```

> **Note:** `SignalStream` was only ever rendered in the blank-state else branch. After this change it is unused. Remove the import from `App.tsx` to avoid lint errors:
> ```tsx
> // Remove this line from App.tsx imports:
> import { SignalStream } from './components/SignalStream'
> ```
> The existing `isPerson / isCountry / isTheme / isChokepoint` branches are unchanged — they render EntityPanel, CountryBrief, ThemeDetail, and ChokepointPanel respectively.

- [ ] **Step 3: Update the panel title for the blank state**

In the same IIFE, the `panelTitle` variable defaults to the "SIGNAL STREAM" label. Update it to show "EXPLORE" when in the blank state. Find:

```tsx
let panelTitle = <>
  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
    SIGNAL STREAM
    <InfoBadge text="Live feed of individual media signals from GDELT. Each row is a news article mentioning a geopolitical event. Click a country code or theme tag to filter the stream. Geopolitical signals appear first." />
  </span>
  <span className="panel-subtitle">live signals, last 15 min</span>
</>
```

Replace with:

```tsx
let panelTitle = <>
  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
    EXPLORE
    <InfoBadge text="Top narratives driving global media coverage right now. Click any topic to open a full breakdown: framing by country, source intelligence, sentiment timeline, and key people." />
  </span>
  <span className="panel-subtitle">most active topics globally</span>
</>
```

- [ ] **Step 4: Verify end-to-end**

Start the dev server:
```bash
cd frontend-v2 && npm run dev
```

Open `http://localhost:5173` in a fresh incognito window. Verify:

1. **Blank state:** Center panel shows "EXPLORE" header and 4–5 topic cards with human-readable names, trend arrows, signal counts, and country counts
2. **Topic click:** Clicking a card sets the theme focus, flies the map to the top country, and transitions the center panel to `ThemeDetail` (back button appears)
3. **Back to blank state:** Pressing Escape or clicking the back button returns the center panel to DiscoveryPanel (not SignalStream)
4. **Country click:** Clicking a country on the map transitions center panel to `CountryBrief` — DiscoveryPanel is gone until context is cleared
5. **Clear focus:** Clearing all filters (close button on CountryBrief, Escape key) brings back DiscoveryPanel
6. **Loading state:** On slow connections, the skeleton placeholder shows 5 pulsing rectangles
7. **Auto-refresh:** Every 5 minutes the topics silently re-fetch (no visible flicker)

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend-v2 && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "feat: wire DiscoveryPanel as default stream slot — replaces raw SignalStream on blank state"
```

---

## Self-Review

### Spec coverage

| Spec item | Task | Status |
| --- | --- | --- |
| R1 — SearchBar placeholder | Pre-flight | Already implemented at SearchBar.tsx:275 |
| R2 — Welcome Card rewrite | Task 1 | ✓ |
| R3 — Map affordance hint | Task 2 | ✓ |
| R4 — Discovery Panel | Tasks 4 + 5 | ✓ |
| R5 — Display names | Pre-flight | Already implemented via getThemeLabel() |
| R6 — Anomaly visual weight | Task 3 | ✓ |
| R7 — Human-readable stats | Task 1 | ✓ |
| R8 — Grid reorder (Matrix hidden) | Task 3 | ✓ |

### Risk mitigations in plan

| Risk | Mitigation in plan |
| --- | --- |
| Stale Discovery Panel content | 5-minute interval in useEffect (same as app refresh cycle) |
| Map hint that doesn't disappear | sessionStorage flag + dismissal in handleCountryClick |
| Discovery Panel replacing Stream for power users | Condition strictly guards blank state; all existing context branches unchanged |
| DiscoveryPanel back-navigation | Task 5 Step 4 verifies Escape key restores DiscoveryPanel |

### Notes for implementer

- **Tailwind is banned in dashboard components.** All CSS goes in `DiscoveryPanel.css` using vanilla CSS and `var(--color-*)` tokens from ThemeContext.
- **The `matrix` panel is hidden via CSS (`display: none`), not removed from JSX.** This is intentional — a future PR can add it as a tab inside ThemeDetail. Do not delete the panel JSX.
- **No new backend endpoints.** DiscoveryPanel uses `/api/v2/narratives` which is already live.
- **Test framework is not configured for the frontend.** All verification is manual via the dev server.
