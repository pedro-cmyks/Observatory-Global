# Temporal Narrative Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a temporal graph view inside Atlas topic detail so a user can see how a narrative connects countries, sources, people, and related themes over time.

**Architecture:** Build the first version as a frontend-derived graph from the existing `ThemeDetail` payload. The graph is temporal from day one: `signals[]` are bucketed by time, converted into graph snapshots, and controlled by a scrubber. This avoids a backend endpoint for MVP while keeping a clean adapter boundary for a future `/api/v2/theme/{theme}/graph-timeline` endpoint.

**Tech Stack:** React + TypeScript + Vite, vanilla CSS, `react-force-graph-2d`, existing FastAPI `/api/v2/theme/{theme}` response, Vitest, Playwright/local browser QA.

---

## GitHub Issue Alignment

| Issue | Relationship | Decision |
|---|---|---|
| [#82 Temporal narrative graph](https://github.com/pedro-cmyks/Observatory-Global/issues/82) | Parent issue for this implementation | Implement here first. |
| [#79 AEIL + Workspace graph](https://github.com/pedro-cmyks/Observatory-Global/issues/79) | Shared product grammar | Temporal graph lives inside AEIL/ThemeDetail first, with pin/promote hooks later. |
| [#80 Session graph](https://github.com/pedro-cmyks/Observatory-Global/issues/80) | Related but distinct | Do not mix. Session graph tracks user navigation; Temporal Narrative Graph tracks one narrative's evolution. |
| [#63 Session Trail graph](https://github.com/pedro-cmyks/Observatory-Global/issues/63) | Older version of #80 | Close as duplicate/superseded by #80 or explicitly mark superseded. Not part of this PR. |
| [#61 Comparative engine](https://github.com/pedro-cmyks/Observatory-Global/issues/61) | Shares temporal thinking | Do not implement compare UI here. Temporal graph may later expose graph selection affordances that launch a comparison pane. MVP does not compare selected nodes or buckets. |
| [#70 Theme hierarchy](https://github.com/pedro-cmyks/Observatory-Global/issues/70) | Improves related theme grouping | Not required for MVP. Graph should use `getThemeLabel()` now and accept future cluster labels. |
| [#73 168h aggregates](https://github.com/pedro-cmyks/Observatory-Global/issues/73) | Future backend scale path | Not required for MVP. Full-window graph endpoint should wait until aggregate strategy is clear. |
| [#77 Source framing visualization](https://github.com/pedro-cmyks/Observatory-Global/issues/77) | Related source-analysis view | Not part of this PR. Source sentiment can color source nodes later. |
| [#81 Responsive/AEIL readability](https://github.com/pedro-cmyks/Observatory-Global/issues/81) | Layout constraint | Graph must not crush the readable AEIL summary. It should be collapsible or placed after summary/metrics. |
| [#78 Public Attention panel](https://github.com/pedro-cmyks/Observatory-Global/issues/78) | Similar AEIL pattern | Temporal graph should reuse the “why these signals connect” mental model, not duplicate Public Attention work. |
| [#83 Signal Intelligence Panel](https://github.com/pedro-cmyks/Observatory-Global/issues/83) | Signal click behavior raised during planning | Separate follow-up. Do not bundle with #82. |

## Product Boundaries

The first implementation must answer:

- What countries are active in this narrative at this point in time?
- Which sources and people connect those countries?
- Which related themes co-occur with the selected thread?
- How did those connections appear, strengthen, fade, or disappear across the selected window?

The first implementation must not:

- Replace the current pinned Workspace Board.
- Auto-pin graph nodes.
- Track user clicks as a session trail.
- Add a backend endpoint.
- Open external news links as the primary click action.
- Hide the existing AEIL explanation, country framing cards, activity timeline, related topics, sources, and recent coverage.

## UX Model

Add a new **Evolution Graph** section inside `ThemeDetail`, immediately after the summary metrics and before `NarrativeDrift`.

Recommended reading order:

1. Identity and AI narrative summary.
2. Metrics.
3. **Evolution Graph**.
4. Narrative Drift.
5. How It's Covered.
6. Activity Timeline.
7. Related Topics, People, Sources, Recent Coverage.

The graph section contains:

- Header: `Evolution Graph`.
- Small subtitle: `Connections from the recent coverage sample, bucketed over time`.
- Graph canvas with central theme node.
- Timeline scrubber underneath.
- Current bucket label: `May 8, 13:00`.
- Snapshot stats: `countries`, `sources`, `people`, `links`.
- No autoplay or `Play` button in MVP. Use a scrubber only.

Node types:

- `theme`: central selected theme and related themes. Emerald.
- `country`: countries in signals. Blue.
- `source`: source domains. Amber.
- `person`: people mentioned. Violet.
- `signal`: not shown as regular nodes in MVP to avoid clutter. Signals are evidence behind links.

Link kinds:

- `country-theme`: country covered selected theme in bucket.
- `source-country`: source produced signal associated with country in bucket.
- `person-country`: person mentioned in country signal in bucket.
- `related-theme`: co-occurring theme in bucket.

Visual behavior:

- The graph is not a decorative card inside another card. It is a compact AEIL section.
- Nodes present in the selected bucket are bright.
- Nodes from previous buckets can appear dimmed only if this does not cause clutter. MVP can show selected bucket only.
- Link width scales by count.
- Node size scales by count with min/max caps.
- Tooltips use `data-tip` where DOM-based. Canvas hover text must be rendered through graph hover state, not native `title=`.
- Node clicks are navigation/drilldown only. They do not track session history, auto-pin, open Signal Intelligence panels, or compare selected entities in the MVP.

## Data Strategy

MVP uses the existing `ThemeDetail` response:

```ts
interface ThemeData {
  theme: string
  total: number
  signals: Array<{
    timestamp: string
    country: string
    source: string
    sentiment: number
    otherThemes: string[]
    persons: string[]
  }>
  timeline: Array<{ hour: string; count: number; sentiment: number }>
  countryBreakdown: Array<{ code: string; count: number; sentiment: number }>
  relatedThemes: Array<{ theme: string; count: number }>
  topSources: Array<{ name: string; count: number; sentiment: number }>
  topPersons: Array<{ name: string; count: number }>
}
```

Important limitation:

- `signals[]` is currently a fetched sample, not a full aggregate of every signal in the theme. The graph must label itself as a **recent coverage graph** or **sample graph** until a backend aggregate endpoint exists.
- The existing numeric summary (`total`, `countryBreakdown`, `topSources`) still communicates the full query results. The graph communicates connection shape from fetched evidence.

Future backend endpoint:

```txt
GET /api/v2/theme/{theme_code}/graph-timeline?hours=24&bucket=hour
```

Do not build this endpoint in the first PR. Keep the frontend adapter named so it can switch from local `ThemeData` to endpoint response later.

## File Structure

Create:

- `frontend-v2/src/lib/temporalNarrativeGraph.ts`
  - Pure TypeScript adapter from `ThemeData`-like input to graph timeline snapshots.
  - No React imports.
  - Unit tested.

- `frontend-v2/src/lib/temporalNarrativeGraph.test.ts`
  - Tests bucket creation, node/link aggregation, filtering, and empty-state behavior.

- `frontend-v2/src/components/TemporalNarrativeGraph.tsx`
  - React component using `react-force-graph-2d`.
  - Receives prepared `theme`, `themeLabel`, `signals`, `timeline`, and callbacks.
  - Owns scrubber state and graph hover state.

- `frontend-v2/src/components/TemporalNarrativeGraph.css`
  - Vanilla CSS for section shell, graph canvas, scrubber, legend, empty state.

Modify:

- `frontend-v2/src/components/ThemeDetail.tsx`
  - Lazy-load `TemporalNarrativeGraph` with `React.lazy()` + `Suspense`.
  - Render it only when `data` is loaded.
  - Pass callbacks for selecting country/person/source/theme.
  - Keep existing sections.
  - Replace any touched `title=` with `data-tip`.

- `frontend-v2/src/lib/workspaceGraph.ts`
  - Do not change in MVP.

- `docs/demos/`
  - Add one screenshot after manual QA.

## Types

Use these exact types in `frontend-v2/src/lib/temporalNarrativeGraph.ts`:

```ts
export type TemporalNodeType = 'theme' | 'country' | 'source' | 'person'

export type TemporalLinkKind =
  | 'country-theme'
  | 'source-country'
  | 'person-country'
  | 'related-theme'

export interface TemporalSignalInput {
  timestamp: string
  country?: string | null
  source?: string | null
  sentiment?: number | null
  otherThemes?: string[]
  persons?: string[]
}

export interface TemporalNarrativeNode {
  id: string
  type: TemporalNodeType
  label: string
  count: number
  sentiment: number
}

export interface TemporalNarrativeLink {
  id: string
  source: string
  target: string
  kind: TemporalLinkKind
  count: number
}

export interface TemporalNarrativeBucket {
  id: string
  label: string
  start: string
  end: string
  signalCount: number
  nodes: TemporalNarrativeNode[]
  links: TemporalNarrativeLink[]
}

export interface BuildTemporalNarrativeGraphInput {
  theme: string
  themeLabel: string
  signals: TemporalSignalInput[]
  maxCountries?: number
  maxRelatedThemes?: number
  maxPeople?: number
  maxSources?: number
}
```

## Task 1: Build Pure Graph Timeline Adapter

**Files:**

- Create: `frontend-v2/src/lib/temporalNarrativeGraph.ts`
- Create: `frontend-v2/src/lib/temporalNarrativeGraph.test.ts`

- [ ] **Step 1: Write failing test for hourly buckets**

Create `frontend-v2/src/lib/temporalNarrativeGraph.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildTemporalNarrativeGraph } from './temporalNarrativeGraph'

describe('buildTemporalNarrativeGraph', () => {
  it('groups signals into chronological hourly graph buckets', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'WB_696_PUBLIC_SECTOR_MANAGEMENT',
      themeLabel: 'Public Sector',
      signals: [
        {
          timestamp: '2026-05-08T13:10:00Z',
          country: 'US',
          source: 'iheart.com',
          sentiment: -2,
          otherThemes: ['PUBLIC_SAFETY'],
          persons: ['donald trump'],
        },
        {
          timestamp: '2026-05-08T14:20:00Z',
          country: 'GB',
          source: 'bbc.co.uk',
          sentiment: -1,
          otherThemes: ['HEALTH'],
          persons: ['helen mcentegart'],
        },
      ],
    })

    expect(result.buckets).toHaveLength(2)
    expect(result.buckets[0].id).toBe('2026-05-08T13:00:00.000Z')
    expect(result.buckets[1].id).toBe('2026-05-08T14:00:00.000Z')
    expect(result.buckets[0].nodes.some(node => node.id === 'theme-WB_696_PUBLIC_SECTOR_MANAGEMENT')).toBe(true)
    expect(result.buckets[0].nodes.some(node => node.id === 'country-US')).toBe(true)
    expect(result.buckets[0].links.some(link => link.kind === 'country-theme')).toBe(true)
  })
})
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
cd frontend-v2 && npm run test -- src/lib/temporalNarrativeGraph.test.ts
```

Expected: fail because `./temporalNarrativeGraph` does not exist.

- [ ] **Step 3: Implement minimal adapter**

Create `frontend-v2/src/lib/temporalNarrativeGraph.ts`:

```ts
import { getThemeLabel } from './themeLabels'
import { resolveCountryName } from './countryNames'

export type TemporalNodeType = 'theme' | 'country' | 'source' | 'person'

export type TemporalLinkKind =
  | 'country-theme'
  | 'source-country'
  | 'person-country'
  | 'related-theme'

export interface TemporalSignalInput {
  timestamp: string
  country?: string | null
  source?: string | null
  sentiment?: number | null
  otherThemes?: string[]
  persons?: string[]
}

export interface TemporalNarrativeNode {
  id: string
  type: TemporalNodeType
  label: string
  count: number
  sentiment: number
}

export interface TemporalNarrativeLink {
  id: string
  source: string
  target: string
  kind: TemporalLinkKind
  count: number
}

export interface TemporalNarrativeBucket {
  id: string
  label: string
  start: string
  end: string
  signalCount: number
  nodes: TemporalNarrativeNode[]
  links: TemporalNarrativeLink[]
}

export interface BuildTemporalNarrativeGraphInput {
  theme: string
  themeLabel: string
  signals: TemporalSignalInput[]
  maxCountries?: number
  maxRelatedThemes?: number
  maxPeople?: number
  maxSources?: number
}

export interface TemporalNarrativeGraph {
  buckets: TemporalNarrativeBucket[]
}

interface MutableNode {
  id: string
  type: TemporalNodeType
  label: string
  count: number
  sentimentTotal: number
}

function hourStart(timestamp: string): Date | null {
  const date = new Date(timestamp)
  if (!Number.isFinite(date.getTime())) return null
  date.setUTCMinutes(0, 0, 0)
  return date
}

function addNode(nodes: Map<string, MutableNode>, id: string, type: TemporalNodeType, label: string, sentiment: number): void {
  const existing = nodes.get(id)
  if (existing) {
    existing.count += 1
    existing.sentimentTotal += sentiment
    return
  }
  nodes.set(id, { id, type, label, count: 1, sentimentTotal: sentiment })
}

function addLink(links: Map<string, TemporalNarrativeLink>, source: string, target: string, kind: TemporalLinkKind): void {
  if (source === target) return
  const id = `${kind}:${source}->${target}`
  const existing = links.get(id)
  if (existing) {
    existing.count += 1
    return
  }
  links.set(id, { id, source, target, kind, count: 1 })
}

export function buildTemporalNarrativeGraph(input: BuildTemporalNarrativeGraphInput): TemporalNarrativeGraph {
  const maxRelatedThemes = input.maxRelatedThemes ?? 5
  const maxPeople = input.maxPeople ?? 5
  const maxSources = input.maxSources ?? 8
  const themeId = `theme-${input.theme}`
  const byHour = new Map<string, TemporalSignalInput[]>()

  for (const signal of input.signals) {
    const start = hourStart(signal.timestamp)
    if (!start) continue
    const id = start.toISOString()
    const bucket = byHour.get(id) ?? []
    bucket.push(signal)
    byHour.set(id, bucket)
  }

  const buckets = Array.from(byHour.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([id, signals]) => {
      const nodes = new Map<string, MutableNode>()
      const links = new Map<string, TemporalNarrativeLink>()

      addNode(nodes, themeId, 'theme', input.themeLabel, 0)

      for (const signal of signals) {
        const sentiment = signal.sentiment ?? 0
        const country = signal.country?.trim().toUpperCase()
        const source = signal.source?.trim()
        const countryId = country ? `country-${country}` : null

        if (country && countryId) {
          addNode(nodes, countryId, 'country', resolveCountryName(country), sentiment)
          addLink(links, countryId, themeId, 'country-theme')
        }

        if (source && countryId) {
          const sourceId = `source-${source}`
          addNode(nodes, sourceId, 'source', source, sentiment)
          addLink(links, sourceId, countryId, 'source-country')
        }

        for (const person of (signal.persons ?? []).slice(0, maxPeople)) {
          if (!person || !countryId) continue
          const personId = `person-${person}`
          addNode(nodes, personId, 'person', person, sentiment)
          addLink(links, personId, countryId, 'person-country')
        }

        for (const relatedTheme of (signal.otherThemes ?? []).slice(0, maxRelatedThemes)) {
          if (!relatedTheme) continue
          const relatedThemeId = `theme-${relatedTheme}`
          addNode(nodes, relatedThemeId, 'theme', getThemeLabel(relatedTheme), sentiment)
          addLink(links, themeId, relatedThemeId, 'related-theme')
        }
      }

      const start = new Date(id)
      const end = new Date(start.getTime() + 60 * 60 * 1000)
      return {
        id,
        label: start.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
        start: start.toISOString(),
        end: end.toISOString(),
        signalCount: signals.length,
        nodes: Array.from(nodes.values())
          .map(node => ({
            id: node.id,
            type: node.type,
            label: node.label,
            count: node.count,
            sentiment: node.count > 0 ? node.sentimentTotal / node.count : 0,
          }))
          .sort((a, b) => b.count - a.count),
        links: Array.from(links.values()).sort((a, b) => b.count - a.count),
      }
    })

  return { buckets }
}
```

- [ ] **Step 4: Run test and verify it passes**

Run:

```bash
cd frontend-v2 && npm run test -- src/lib/temporalNarrativeGraph.test.ts
```

Expected: pass.

- [ ] **Step 5: Add tests for caps and bad data**

Append these tests:

```ts
it('ignores invalid timestamps and keeps empty graph safe', () => {
  const result = buildTemporalNarrativeGraph({
    theme: 'HEALTH',
    themeLabel: 'Health',
    signals: [{ timestamp: 'not-a-date', country: 'US' }],
  })

  expect(result.buckets).toEqual([])
})

it('caps people and related themes per signal to avoid noisy graphs', () => {
  const result = buildTemporalNarrativeGraph({
    theme: 'HEALTH',
    themeLabel: 'Health',
    maxPeople: 2,
    maxRelatedThemes: 2,
    signals: [{
      timestamp: '2026-05-08T13:10:00Z',
      country: 'US',
      source: 'example.com',
      persons: ['a', 'b', 'c'],
      otherThemes: ['T1', 'T2', 'T3'],
    }],
  })

  const ids = result.buckets[0].nodes.map(node => node.id)
  expect(ids).toContain('person-a')
  expect(ids).toContain('person-b')
  expect(ids).not.toContain('person-c')
  expect(ids).toContain('theme-T1')
  expect(ids).toContain('theme-T2')
  expect(ids).not.toContain('theme-T3')
})
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd frontend-v2 && npm run test -- src/lib/temporalNarrativeGraph.test.ts
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend-v2/src/lib/temporalNarrativeGraph.ts frontend-v2/src/lib/temporalNarrativeGraph.test.ts
git commit -m "feat(graph): add temporal narrative graph adapter"
```

## Task 2: Build TemporalNarrativeGraph Component

**Files:**

- Create: `frontend-v2/src/components/TemporalNarrativeGraph.tsx`
- Create: `frontend-v2/src/components/TemporalNarrativeGraph.css`

- [ ] **Step 1: Create component skeleton**

Create `frontend-v2/src/components/TemporalNarrativeGraph.tsx`:

```tsx
import { useMemo, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import {
  buildTemporalNarrativeGraph,
  type TemporalNarrativeBucket,
  type TemporalNarrativeNode,
} from '../lib/temporalNarrativeGraph'
import './TemporalNarrativeGraph.css'

interface TemporalNarrativeGraphProps {
  theme: string
  themeLabel: string
  signals: Array<{
    timestamp: string
    country?: string | null
    source?: string | null
    sentiment?: number | null
    otherThemes?: string[]
    persons?: string[]
  }>
  onThemeSelect?: (theme: string) => void
  onCountrySelect?: (code: string) => void
  onPersonSelect?: (name: string) => void
  onSourceSelect?: (domain: string) => void
}

const NODE_COLORS = {
  theme: '#10b981',
  country: '#60a5fa',
  source: '#f59e0b',
  person: '#a78bfa',
}

export function TemporalNarrativeGraph({
  theme,
  themeLabel,
  signals,
  onThemeSelect,
  onCountrySelect,
  onPersonSelect,
  onSourceSelect,
}: TemporalNarrativeGraphProps) {
  const graph = useMemo(() => buildTemporalNarrativeGraph({ theme, themeLabel, signals }), [theme, themeLabel, signals])
  const [bucketIndex, setBucketIndex] = useState(() => Math.max(0, graph.buckets.length - 1))
  const bucket = graph.buckets[Math.min(bucketIndex, Math.max(0, graph.buckets.length - 1))]

  if (!bucket) {
    return (
      <section className="temporal-graph-section">
        <div className="temporal-graph-header">
          <div>
            <h3>Evolution Graph</h3>
            <p>No recent coverage sample available for graphing.</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="temporal-graph-section">
      <div className="temporal-graph-header">
        <div>
          <h3>Evolution Graph</h3>
          <p>How countries, sources, people, and related themes connect over time.</p>
        </div>
        <div className="temporal-graph-stats">
          <span>{bucket.signalCount} signals</span>
          <span>{bucket.nodes.length} nodes</span>
          <span>{bucket.links.length} links</span>
        </div>
      </div>

      <div className="temporal-graph-canvas">
        <ForceGraph2D
          graphData={{ nodes: bucket.nodes, links: bucket.links }}
          nodeId="id"
          nodeLabel={(node) => (node as TemporalNarrativeNode).label}
          nodeColor={(node) => NODE_COLORS[(node as TemporalNarrativeNode).type]}
          nodeVal={(node) => Math.max(3, Math.min(18, (node as TemporalNarrativeNode).count * 2))}
          linkWidth={(link) => Math.max(1, Math.min(5, Number((link as { count?: number }).count ?? 1)))}
          linkColor={() => 'rgba(16, 185, 129, 0.35)'}
          backgroundColor="rgba(0,0,0,0)"
          cooldownTicks={80}
          onNodeClick={(node) => handleNodeClick(node as TemporalNarrativeNode, { onThemeSelect, onCountrySelect, onPersonSelect, onSourceSelect })}
        />
      </div>

      <TemporalScrubber bucket={bucket} buckets={graph.buckets} bucketIndex={bucketIndex} onChange={setBucketIndex} />
    </section>
  )
}

function TemporalScrubber({
  bucket,
  buckets,
  bucketIndex,
  onChange,
}: {
  bucket: TemporalNarrativeBucket
  buckets: TemporalNarrativeBucket[]
  bucketIndex: number
  onChange: (index: number) => void
}) {
  return (
    <div className="temporal-graph-scrubber">
      <span>{bucket.label}</span>
      <input
        type="range"
        min={0}
        max={Math.max(0, buckets.length - 1)}
        value={bucketIndex}
        onChange={event => onChange(Number(event.target.value))}
        aria-label="Narrative graph time bucket"
      />
      <span>{bucket.signalCount} in bucket</span>
    </div>
  )
}

function handleNodeClick(
  node: TemporalNarrativeNode,
  callbacks: Pick<TemporalNarrativeGraphProps, 'onThemeSelect' | 'onCountrySelect' | 'onPersonSelect' | 'onSourceSelect'>,
) {
  if (node.type === 'country') callbacks.onCountrySelect?.(node.id.replace(/^country-/, ''))
  if (node.type === 'person') callbacks.onPersonSelect?.(node.label)
  if (node.type === 'source') callbacks.onSourceSelect?.(node.label)
  if (node.type === 'theme') callbacks.onThemeSelect?.(node.id.replace(/^theme-/, ''))
}
```

- [ ] **Step 2: Add CSS**

Create `frontend-v2/src/components/TemporalNarrativeGraph.css`:

```css
.temporal-graph-section {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 0;
}

.temporal-graph-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.temporal-graph-header h3 {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #cbd5e1;
}

.temporal-graph-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 11px;
}

.temporal-graph-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  color: #94a3b8;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
}

.temporal-graph-stats span {
  padding: 3px 6px;
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.05);
}

.temporal-graph-canvas {
  height: 320px;
  border: 1px solid rgba(16, 185, 129, 0.14);
  border-radius: 6px;
  background:
    linear-gradient(rgba(16, 185, 129, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(16, 185, 129, 0.04) 1px, transparent 1px),
    rgba(2, 6, 14, 0.72);
  background-size: 28px 28px;
  overflow: hidden;
}

.temporal-graph-scrubber {
  display: grid;
  grid-template-columns: minmax(90px, auto) 1fr minmax(80px, auto);
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  color: #94a3b8;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
}

.temporal-graph-scrubber input {
  width: 100%;
  accent-color: #10b981;
}
```

- [ ] **Step 3: Run build**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: build passes. If TypeScript reports `ForceGraph2D` typing issues, add a small local type cast in the component rather than weakening project-wide types.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/TemporalNarrativeGraph.tsx frontend-v2/src/components/TemporalNarrativeGraph.css
git commit -m "feat(graph): add temporal narrative graph component"
```

## Task 3: Lazy-Integrate Graph Into ThemeDetail AEIL

**Files:**

- Modify: `frontend-v2/src/components/ThemeDetail.tsx`

- [ ] **Step 1: Add lazy component import**

Update the React import at the top of `ThemeDetail.tsx`:

```ts
import { lazy, Suspense, useState, useEffect, useRef } from 'react'
```

Add the lazy component near the imports:

```ts
const TemporalNarrativeGraph = lazy(() =>
  import('./TemporalNarrativeGraph').then(module => ({ default: module.TemporalNarrativeGraph }))
)
```

- [ ] **Step 2: Render graph after metrics and before Narrative Drift**

Find the existing metrics block in `ThemeDetail.tsx`, then insert:

```tsx
{data.signals.length > 0 && (
  <Suspense fallback={<div className="temporal-graph-loading">Loading evolution graph...</div>}>
    <TemporalNarrativeGraph
      theme={theme}
      themeLabel={getThemeLabel(theme)}
      signals={data.signals}
      onThemeSelect={onThemeSelect}
      onCountrySelect={(code) => {
        setDrillCountry(code)
        setDrillCountryName(code)
        onCountryCardClick?.(code, code)
      }}
      onPersonSelect={onPersonClick}
      onSourceSelect={onSourceClick}
    />
  </Suspense>
)}
```

Do not remove `NarrativeDrift` or `Activity Timeline`. The graph explains relationships over time; Drift explains tone trajectory; Activity Timeline explains volume by bucket.

- [ ] **Step 3: Replace touched native title attributes**

If editing nearby buttons, replace native `title=` with `data-tip=`.

Example:

```tsx
<button
  onClick={handlePin}
  data-tip={pinned ? 'Unpin Theme' : 'Pin Theme to Workspace'}
>
```

- [ ] **Step 4: Run focused lint**

Run:

```bash
cd frontend-v2 && npx eslint src/components/ThemeDetail.tsx src/components/TemporalNarrativeGraph.tsx src/lib/temporalNarrativeGraph.ts src/lib/temporalNarrativeGraph.test.ts
```

Expected: pass for touched files. Do not attempt repo-wide `npm run lint` in this PR because #62 tracks existing lint debt.

- [ ] **Step 5: Run build**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/components/ThemeDetail.tsx
git commit -m "feat(theme): show temporal graph in topic detail"
```

## Task 4: Signal Stream Click Behavior Plan Stub

**Files:**

- Do not implement in this PR.
- Add a note to issue #82 or create a follow-up issue if not already tracked.

Context:

The user also wants Signal Stream article clicks to open an internal intelligence panel instead of immediately opening the source URL. This is product-aligned with Atlas, but it is a separate workstream.

Follow-up issue should specify:

- Signal click opens `SignalIntelligencePanel`.
- Panel shows headline, source, country, detected themes, people, related countries/sources, and similar signals.
- External source link becomes secondary action: `Open source`.
- Signal nodes can be promoted to Workspace.

Do not bundle this with Temporal Narrative Graph. It touches `SignalStream.tsx`, routing/focus state, and likely Workspace signal behavior. Track this in [#83](https://github.com/pedro-cmyks/Observatory-Global/issues/83).

## Task 5: Manual QA and Demo Capture

**Files:**

- Create: `docs/demos/YYYY-MM-DD-temporal-narrative-graph.png`

- [ ] **Step 1: Start local backend proxy if needed**

If local backend is not running, proxy `/api` to Fly:

```bash
node -e "const http=require('http'); const target='https://atlas-api-pedro.fly.dev'; const drop=new Set(['content-encoding','content-length','transfer-encoding','connection']); http.createServer((req,res)=>{ fetch(target+req.url,{method:req.method,headers:{accept:req.headers.accept||'application/json'}}).then(async r=>{ const headers={}; r.headers.forEach((v,k)=>{ if(!drop.has(k.toLowerCase())) headers[k]=v; }); res.writeHead(r.status,headers); res.end(Buffer.from(await r.arrayBuffer())); }).catch(e=>{ res.writeHead(502,{'content-type':'text/plain'}); res.end(String(e)); }); }).listen(8000,'127.0.0.1',()=>console.log('proxy clean http://127.0.0.1:8000 -> '+target));"
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend-v2 && npm run dev -- --host 127.0.0.1 --port 5173
```

- [ ] **Step 3: Browser QA**

Open:

```txt
http://127.0.0.1:5173/app
```

Manual checks:

- Click a Narrative Thread.
- Confirm ThemeDetail opens.
- Confirm `Evolution Graph` appears after the summary/metrics.
- Move the scrubber.
- Confirm graph changes bucket labels and nodes/links.
- Click a country node.
- Confirm it drills into country framing or triggers the existing country callback.
- Click a related theme node.
- Confirm ThemeDetail switches to that theme.
- Confirm existing sections still work: Narrative Drift, How It's Covered, Activity Timeline, Related Topics, People, Top Sources, Recent Coverage.
- Confirm the graph does not overlap or crush text at 1600x900 and 1600x700.

- [ ] **Step 4: Capture screenshot**

Save:

```txt
docs/demos/YYYY-MM-DD-temporal-narrative-graph.png
```

- [ ] **Step 5: Stop local servers**

```bash
(lsof -ti :5173; lsof -ti :8000) 2>/dev/null | xargs -r kill
```

- [ ] **Step 6: Commit QA evidence**

```bash
git add docs/demos/YYYY-MM-DD-temporal-narrative-graph.png
git commit -m "docs: add temporal graph QA screenshot"
```

## Task 6: Final Verification and Push

- [ ] **Step 1: Run tests**

```bash
cd frontend-v2 && npm run test -- src/lib/temporalNarrativeGraph.test.ts
```

Expected: pass.

- [ ] **Step 2: Run focused lint**

```bash
cd frontend-v2 && npx eslint src/components/ThemeDetail.tsx src/components/TemporalNarrativeGraph.tsx src/lib/temporalNarrativeGraph.ts src/lib/temporalNarrativeGraph.test.ts
```

Expected: pass.

- [ ] **Step 3: Run build**

```bash
cd frontend-v2 && npm run build
```

Expected: pass.

- [ ] **Step 4: Check git status**

```bash
git status --short
```

Expected: only intended files changed or clean after commits.

- [ ] **Step 5: Push**

```bash
git push origin v3-intel-layer
```

- [ ] **Step 6: Update GitHub**

Comment on #82 with:

```md
Implemented first Temporal Narrative Graph MVP.

- Added frontend graph adapter from ThemeDetail signals to hourly graph buckets.
- Added Evolution Graph section inside ThemeDetail.
- Added scrubber for time bucket navigation.
- Kept Workspace and Session Trail separate.
- Added QA screenshot under docs/demos/.

Verification:
- npm run test -- src/lib/temporalNarrativeGraph.test.ts
- focused eslint on touched files
- npm run build
```

## Risks and Follow-Ups

Risk: `ThemeDetail.signals` is a sample.

- Mitigation: label graph as recent coverage/evidence graph.
- Follow-up: backend aggregate endpoint after #73/#70 decisions.

Risk: Force graph in ThemeDetail increases bundle size.

- Mitigation: if build chunk grows too much or interaction is slow, lazy-load `TemporalNarrativeGraph` the same way Workspace lazy-loads `InteractiveWorkspace`.

Risk: Graph becomes visually noisy.

- Mitigation: cap per-signal related themes/people/sources and keep signal nodes hidden in MVP.

Risk: User confuses Drift vs Activity Timeline vs Evolution Graph.

- Mitigation: section labels:
  - `Evolution Graph`: relationship structure over time.
  - `Narrative Drift`: tone/sentiment trajectory over time.
  - `Activity Timeline`: volume by time bucket.

## Self-Review

- Scope is limited to #82 and ThemeDetail integration.
- #79 informs layout but is not fully implemented.
- #80/#63 are explicitly excluded.
- #61 is explicitly excluded.
- No backend endpoint is added.
- No native `title=` attributes should be introduced.
- Plan includes tests before implementation.
- Plan includes build, focused lint, manual QA, screenshot, commit, push, and GitHub update.
