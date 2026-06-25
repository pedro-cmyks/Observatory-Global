# Atlas Level-0 Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the public Landing (and apply the new type system to Docs) so Atlas leads with narrative *movement*, reveals depth via a public→console register gradient, and sheds the generic "AI-made" look.

**Architecture:** Frontend-only. New type system (Fraunces + Geist + Geist Mono) wired through the existing token layers (variables.css, themes.ts, tailwind.config.js, DESIGN.md). A bespoke animated SVG hero ("Follow the thread") driven by a pure data helper fed from the existing `/api/v2/threads` + briefing prefetch. Landing restructured into a 7-section descent. No backend change; ships via Vercel.

**Tech Stack:** React + Vite + TypeScript, Tailwind (Landing only), vanilla CSS (Docs/console), Vitest, @fontsource-variable for self-hosted Geist.

**Spec:** `docs/superpowers/specs/2026-06-24-level0-redesign-design.md`

**Branch:** `feat/level0-redesign` (already created). Merge to `v3-intel-layer` only after preview verification passes.

---

## File Structure

- `frontend-v2/package.json` — add `@fontsource-variable/geist`, `@fontsource-variable/geist-mono`.
- `frontend-v2/src/main.tsx` — import the two font packages.
- `frontend-v2/index.html` — swap the Google Fonts link (Fraunces in; Outfit/Jakarta/Space-Grotesk out).
- `frontend-v2/src/styles/variables.css` — `--font-*` definitions.
- `frontend-v2/src/styles/themes.ts` — default theme `fontSans`/`fontMono`.
- `frontend-v2/tailwind.config.js` — `fontFamily` tokens (Landing consumes these).
- `DESIGN.md` — typography token amendment (source of truth).
- `frontend-v2/src/pages/Docs.css` — replace `JetBrains Mono` refs with `var(--font-mono)`.
- `frontend-v2/src/lib/heroThreads.ts` (new) — pure data helper shaping `/threads` into hero movers.
- `frontend-v2/src/lib/heroThreads.test.ts` (new) — vitest for the helper.
- `frontend-v2/src/components/HeroThread.tsx` (+ `HeroThread.css`) (new) — bespoke animated hero.
- `frontend-v2/src/pages/Landing.tsx` + `Landing.css` — full restructure (register gradient + 7 sections).

---

## Task 1: Type system foundation (fonts + tokens)

**Files:**
- Modify: `frontend-v2/package.json`
- Modify: `frontend-v2/src/main.tsx:4-5`
- Modify: `frontend-v2/index.html:31`
- Modify: `frontend-v2/src/styles/variables.css:34-37`
- Modify: `frontend-v2/src/styles/themes.ts:69-70`
- Modify: `frontend-v2/tailwind.config.js:63-71`
- Modify: `DESIGN.md` (typography families block, ~lines 215-239)
- Modify: `frontend-v2/src/pages/Docs.css` (JetBrains Mono refs)

- [ ] **Step 1: Install the self-hosted Geist font packages**

Run: `cd frontend-v2 && npm install @fontsource-variable/geist @fontsource-variable/geist-mono`
Expected: both added to `package.json` dependencies, no peer warnings that fail install.

- [ ] **Step 2: Import the fonts at app entry**

In `frontend-v2/src/main.tsx`, add after line 3 (before `import './index.css'`):

```ts
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
```

- [ ] **Step 3: Swap the Google Fonts link**

In `frontend-v2/index.html`, replace line 31 (the Outfit/Plus Jakarta Sans/Space Grotesk link) with:

```html
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..900;1,9..144,400..600&display=swap" rel="stylesheet">
```

Keep the Material Symbols link (line 32) and the two preconnects.

- [ ] **Step 4: Update the CSS variable definitions**

In `frontend-v2/src/styles/variables.css`, replace lines 34-37 with:

```css
    --font-display: 'Fraunces', Georgia, serif;
    --font-sans: 'Geist Variable', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-technical: 'Geist Mono Variable', 'Geist Mono', 'SF Mono', monospace;
    --font-mono: 'Geist Mono Variable', 'Geist Mono', 'SF Mono', monospace;
```

- [ ] **Step 5: Update the default theme typography**

In `frontend-v2/src/styles/themes.ts`, replace lines 69-70 with:

```ts
        fontMono: "'Geist Mono Variable', 'Geist Mono', 'SF Mono', monospace",
        fontSans: "'Geist Variable', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif",
```

(Leave the alternate retro theme at lines 108-109 — VT323/Inter — unchanged; it is intentional.)

- [ ] **Step 6: Update the Tailwind fontFamily tokens**

In `frontend-v2/tailwind.config.js`, replace the `fontFamily` block (lines 63-71) with:

```js
      fontFamily: {
        'display-xl':      ['Fraunces', 'Georgia', 'serif'],
        'headline-md':     ['Fraunces', 'Georgia', 'serif'],
        'body-main':       ['"Geist Variable"', 'Geist', 'sans-serif'],
        'body-strong':     ['"Geist Variable"', 'Geist', 'sans-serif'],
        'nav-link':        ['"Geist Variable"', 'Geist', 'sans-serif'],
        'technical-label': ['"Geist Mono Variable"', '"Geist Mono"', 'monospace'],
        'code-snippet':    ['"Geist Mono Variable"', '"Geist Mono"', 'monospace'],
      },
```

- [ ] **Step 7: Amend DESIGN.md typography families (source of truth)**

In `DESIGN.md`, update the `typography.families` token values: `display` → `"Fraunces, Georgia, serif"`; `sans` → `"Geist Variable, Geist, -apple-system, sans-serif"`; `technical` → `"Geist Mono Variable, Geist Mono, monospace"`; `mono` → `"Geist Mono Variable, Geist Mono, SF Mono, monospace"`; `editorial` → `"Fraunces, Georgia, serif"`. Update each `description` line to reflect the new role (Fraunces = editorial/display fingerprint; Geist = console UI; Geist Mono = labels + tabular numbers).

- [ ] **Step 8: Fix Docs.css mono references**

In `frontend-v2/src/pages/Docs.css`, replace any `'JetBrains Mono', monospace` font-family with `var(--font-mono)`. Run `grep -n "JetBrains Mono" src/pages/Docs.css` first; replace each occurrence.

- [ ] **Step 9: Build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds, no TS errors.

- [ ] **Step 10: Preview-verify the font swap (before any restructure)**

Ensure dev server running (preview_start "frontend" if needed). Navigate to `/` and `/docs`.
- `preview_console_logs` level error → none.
- `preview_eval`: confirm `getComputedStyle` on the hero `h1` returns a Fraunces family, and a technical label returns Geist Mono.
- `preview_eval`: confirm no stylesheet/link href contains `Outfit` or `Plus+Jakarta`.
Expected: Landing/Docs render with Fraunces headings + Geist body; no console errors; AI-trio link gone.

- [ ] **Step 11: Commit**

```bash
git add frontend-v2/package.json frontend-v2/package-lock.json frontend-v2/src/main.tsx frontend-v2/index.html frontend-v2/src/styles/variables.css frontend-v2/src/styles/themes.ts frontend-v2/tailwind.config.js DESIGN.md frontend-v2/src/pages/Docs.css
git commit -m "feat(design): type system B — Fraunces + Geist + Geist Mono, retire AI-trio"
```

---

## Task 2: Hero data helper (pure, TDD)

**Files:**
- Create: `frontend-v2/src/lib/heroThreads.ts`
- Test: `frontend-v2/src/lib/heroThreads.test.ts`

The helper turns raw `/api/v2/threads` items into deterministic hero "movers": a center story node plus typed satellite nodes (country/source/actor/attention) and an ordered route. Determinism (no `Math.random`) keeps it testable and avoids layout jitter between renders.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest'
import { buildHeroThreads, type RawThread } from './heroThreads'

const sample: RawThread[] = [
  { thread_id: 't1', label: "Iran's water crisis", trend: 'accelerating', velocity: 9, top_countries: ['IR', 'IQ', 'SA'] },
  { thread_id: 't2', label: 'Sahel coup fallout', trend: 'stable', velocity: 3, top_countries: ['ML', 'NE'] },
]

describe('buildHeroThreads', () => {
  it('returns one mover per thread, capped at max', () => {
    const out = buildHeroThreads(sample, { max: 5 })
    expect(out).toHaveLength(2)
    expect(out[0].id).toBe('t1')
    expect(out[0].title).toBe("Iran's water crisis")
  })

  it('gives each mover a center node and typed satellites with deterministic positions', () => {
    const out = buildHeroThreads(sample, { max: 5 })
    const m = out[0]
    expect(m.center).toMatchObject({ type: 'story' })
    expect(m.satellites.length).toBeGreaterThanOrEqual(3)
    expect(m.satellites.some(s => s.type === 'country')).toBe(true)
    // deterministic: same input → same coordinates
    const again = buildHeroThreads(sample, { max: 5 })
    expect(again[0].center.x).toBe(m.center.x)
    expect(again[0].satellites[0].x).toBe(m.satellites[0].x)
  })

  it('orders the route through the satellites ending at the center (the investigation)', () => {
    const m = buildHeroThreads(sample, { max: 5 })[0]
    expect(m.route.length).toBeGreaterThanOrEqual(2)
    expect(m.route[m.route.length - 1]).toEqual({ x: m.center.x, y: m.center.y })
  })

  it('degrades to empty array on no/garbage input without throwing', () => {
    expect(buildHeroThreads([], { max: 5 })).toEqual([])
    // @ts-expect-error garbage
    expect(buildHeroThreads(null, { max: 5 })).toEqual([])
  })

  it('respects max', () => {
    const many = Array.from({ length: 9 }, (_, i) => ({ ...sample[0], thread_id: `t${i}`, label: `s${i}` }))
    expect(buildHeroThreads(many, { max: 4 })).toHaveLength(4)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/heroThreads.test.ts`
Expected: FAIL — `heroThreads` module not found.

- [ ] **Step 3: Implement the helper**

```ts
// frontend-v2/src/lib/heroThreads.ts
export interface RawThread {
  thread_id: string
  label: string
  trend?: 'accelerating' | 'stable' | 'fading' | string
  velocity?: number
  top_countries?: string[]
}

export type NodeType = 'story' | 'country' | 'source' | 'actor' | 'attention'
export interface HeroNode { type: NodeType; label: string; x: number; y: number }
export interface HeroMover {
  id: string
  title: string
  trend: string
  velocity: number
  center: HeroNode
  satellites: HeroNode[]
  route: { x: number; y: number }[]
}

// viewBox is 0..640 x, 0..240 y (matches HeroThread.tsx)
const W = 640, H = 240

// deterministic hash → [0,1)
function hash01(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return ((h >>> 0) % 100000) / 100000
}

function place(seed: string, xMin: number, xMax: number, yMin: number, yMax: number): { x: number; y: number } {
  const a = hash01(seed), b = hash01(seed + '#y')
  return { x: Math.round(xMin + a * (xMax - xMin)), y: Math.round(yMin + b * (yMax - yMin)) }
}

export function buildHeroThreads(threads: RawThread[], opts: { max: number }): HeroMover[] {
  if (!Array.isArray(threads)) return []
  return threads.slice(0, opts.max).map((t) => {
    const center: HeroNode = { type: 'story', label: t.label, ...place(t.thread_id + 'C', 360, 460, 70, 110) }
    const countries = (t.top_countries ?? []).slice(0, 3).map((cc, i): HeroNode => ({
      type: 'country', label: cc, ...place(t.thread_id + 'cc' + cc + i, 90, 320, 40, 170),
    }))
    // synthesize the fixed evidence-layer satellites (source / actor / attention)
    const fixed: HeroNode[] = [
      { type: 'source', label: 'SOURCES', ...place(t.thread_id + 'src', 460, 560, 30, 70) },
      { type: 'actor', label: 'ACTORS', ...place(t.thread_id + 'act', 360, 440, 130, 175) },
      { type: 'attention', label: 'ATTENTION', ...place(t.thread_id + 'att', 440, 580, 100, 150) },
    ]
    const satellites = [...countries, ...fixed]
    // route: travel the satellites then end at the center (the investigation)
    const route = [...satellites.map(s => ({ x: s.x, y: s.y })), { x: center.x, y: center.y }]
    return {
      id: t.thread_id,
      title: t.label,
      trend: t.trend ?? 'stable',
      velocity: typeof t.velocity === 'number' ? t.velocity : 0,
      center, satellites, route,
    }
  })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/heroThreads.test.ts`
Expected: PASS (all 5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/heroThreads.ts frontend-v2/src/lib/heroThreads.test.ts
git commit -m "feat(landing): pure hero-threads data helper + tests"
```

---

## Task 3: HeroThread component (bespoke animated SVG)

**Files:**
- Create: `frontend-v2/src/components/HeroThread.tsx`
- Create: `frontend-v2/src/components/HeroThread.css`

Renders the faint world graticule, the typed constellation, a comet traveling the route (SMIL), and a pulsing center, cycling through movers from `buildHeroThreads`. Fetches `/api/v2/threads`; degrades to a static single mover if the feed is empty/unavailable. Honors `prefers-reduced-motion`. MUST NOT import `InteractiveWorkspace`/react-force-graph.

- [ ] **Step 1: Implement the component**

Use the validated mock at `.superpowers/brainstorm/75884-1782333334/content/hero-dynamic.html` as the visual reference. Component contract:

```tsx
// frontend-v2/src/components/HeroThread.tsx
import { useEffect, useRef, useState } from 'react'
import { buildHeroThreads, type HeroMover, type RawThread } from '../lib/heroThreads'
import './HeroThread.css'

const FALLBACK: RawThread[] = [
  { thread_id: 'fallback', label: 'Tracking global narratives', trend: 'stable', velocity: 0, top_countries: ['US', 'GB', 'IR'] },
]
const NODE_COLOR: Record<string, string> = {
  story: '#68dbae', country: '#60a5fa', source: '#f59e0b', actor: '#a78bfa', attention: '#2dd4bf',
}

export function HeroThread() {
  const [movers, setMovers] = useState<HeroMover[]>(() => buildHeroThreads(FALLBACK, { max: 1 }))
  const [active, setActive] = useState(0)
  const reduced = useRef(false)

  useEffect(() => {
    reduced.current = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    fetch('/api/v2/threads?hours=24&limit=6')
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        const raw: RawThread[] = (d?.threads ?? d ?? []).map((t: any) => ({
          thread_id: t.thread_id ?? t.id, label: t.label ?? t.title,
          trend: t.trend, velocity: t.velocity, top_countries: t.top_countries,
        })).filter((t: RawThread) => t.thread_id && t.label)
        const built = buildHeroThreads(raw, { max: 5 })
        if (built.length) setMovers(built)
      })
      .catch(() => { /* keep fallback */ })
  }, [])

  useEffect(() => {
    if (reduced.current || movers.length <= 1) return
    const id = setInterval(() => setActive(a => (a + 1) % movers.length), 5200)
    return () => clearInterval(id)
  }, [movers])

  const m = movers[active] ?? movers[0]
  const routeD = 'M' + m.route.map(p => `${p.x},${p.y}`).join(' L')

  return (
    <div className="hero-thread" aria-hidden="true">
      <svg viewBox="0 0 640 240" preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="ht-glow" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="3" /></filter>
        </defs>
        {/* faint world graticule */}
        <g className="ht-grid" fill="none">
          <ellipse cx="320" cy="120" rx="300" ry="110" />
          <line x1="20" y1="120" x2="620" y2="120" /><line x1="20" y1="80" x2="620" y2="80" /><line x1="20" y1="160" x2="620" y2="160" />
          <line x1="170" y1="14" x2="170" y2="226" /><line x1="320" y1="10" x2="320" y2="230" /><line x1="470" y1="14" x2="470" y2="226" />
        </g>
        {/* constellation edges */}
        <g className="ht-edges">
          {m.satellites.map((s, i) => (
            <line key={i} x1={m.center.x} y1={m.center.y} x2={s.x} y2={s.y} />
          ))}
        </g>
        {/* route */}
        <path className="ht-route" d={routeD} />
        {/* comet (skip when reduced motion) */}
        {!reduced.current && (
          <circle r="4" fill="#86f8c9" filter="url(#ht-glow)">
            <animateMotion dur="3.4s" repeatCount="indefinite" path={routeD} />
            <animate attributeName="opacity" values="0;1;1;1;0" dur="3.4s" repeatCount="indefinite" />
          </circle>
        )}
        {/* satellites */}
        {m.satellites.map((s, i) => (
          <g key={i}>
            <circle cx={s.x} cy={s.y} r="8" fill={NODE_COLOR[s.type]} filter="url(#ht-glow)" opacity="0.45" />
            <circle cx={s.x} cy={s.y} r="4.5" fill={NODE_COLOR[s.type]} />
          </g>
        ))}
        {/* center story (pulse) */}
        <circle className={reduced.current ? '' : 'ht-pulse'} cx={m.center.x} cy={m.center.y} r="20" fill="#68dbae" filter="url(#ht-glow)" opacity="0.4" />
        <circle cx={m.center.x} cy={m.center.y} r="12" fill="#0a1220" stroke="#68dbae" strokeWidth="1.5" />
        <text x={m.center.x} y={m.center.y - 18} fill="#68dbae" fontSize="11" textAnchor="middle" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
          {m.title} {m.trend === 'accelerating' ? '▲' : ''}
        </text>
      </svg>
    </div>
  )
}
```

- [ ] **Step 2: Implement the styles**

```css
/* frontend-v2/src/components/HeroThread.css */
.hero-thread { width: 100%; }
.hero-thread svg { width: 100%; height: auto; display: block; }
.ht-grid { stroke: rgba(96,165,250,0.10); stroke-width: 1; }
.ht-edges line { stroke: #1d9e75; stroke-width: 1; opacity: 0.35; }
.ht-route { fill: none; stroke: #68dbae; stroke-width: 1.4; stroke-dasharray: 3 6; opacity: 0.55; }
.ht-pulse { animation: ht-pulse 2.4s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
@keyframes ht-pulse { 0%,100% { opacity: 0.5; r: 16px; } 50% { opacity: 0.2; r: 24px; } }
@media (prefers-reduced-motion: reduce) { .ht-pulse { animation: none; } }
```

- [ ] **Step 3: Build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds, no TS errors, and the main bundle does NOT gain react-force-graph (verify HeroThread imports only `heroThreads`).

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/HeroThread.tsx frontend-v2/src/components/HeroThread.css
git commit -m "feat(landing): bespoke animated HeroThread (live /threads, reduced-motion safe)"
```

---

## Task 4: Landing restructure (register gradient + 7 sections)

**Files:**
- Modify: `frontend-v2/src/pages/Landing.tsx` (full restructure)
- Modify: `frontend-v2/src/pages/Landing.css`

Rebuild Landing per spec §6 as a continuous descent. Keep it Tailwind-styled (Landing is the one Tailwind surface). Replace the old radar hero with `<HeroThread />`. Apply the register gradient: editorial sections use Fraunces (`font-display-xl`/`font-headline-md`) + warm spacing; console sections use Geist body + `font-technical-label` (Geist Mono) uppercase labels + emerald HUD panels. All numbers use `tabular-nums`. Vary card hierarchy (no uniform bento — the "surfaces" lead card is larger).

Exact section order + copy:

1. **Hero** — eyebrow `ATLAS · NARRATIVE INTELLIGENCE · LIVE`; H1 (Fraunces) **"Follow the thread."**; standfirst "Every live story is a web of countries, sources, and people. Watch a narrative move across the world — then pull the thread into an investigation."; `<HeroThread />`; CTAs: **Start with the brief** → `/brief`, **Open the console** → `/app`, **Read the docs** → `/docs`.
2. **Moving right now** (editorial) — section eyebrow "The world tonight"; one lead narrative (largest, Fraunces headline) + 3 movers with movement chips; fed from the briefing prefetch (`prefetchBriefing(24)` is already imported) / `/api/v2/threads`. If unavailable, show a quiet explanatory line, not an empty block.
3. **How narratives move** (transition) — three concepts: **Spread** (a story crosses borders), **Mutation** (framing/sentiment shifts as it travels), **Polarization** (same story, opposite framing). Short instrument-style copy; register begins turning technical.
4. **Soft beat** — a centered Geist Mono line: `FROM READING → INVESTIGATING`.
5. **Research Workflow** (console climax) — section label "RESEARCH · WORKFLOW"; H2 (Fraunces) "From a question to an investigation"; the flow `Ask → Anchors (direct/context/weak chips) → Gaps → Workbench` as bordered emerald HUD steps; one-line CTA into `/app`.
6. **The surfaces** (console) — Globe · Signal Stream · Narrative Threads · Anomaly Alert · Workspace. NON-uniform: a wide lead card (e.g. Globe or Workspace) + smaller supporting cards. Each links to `/app` (or `/brief` for the brief).
7. **Data + voice** (console) — left: source layers (GDELT, RSS/ReliefWeb, news APIs, Reddit, public attention, NLP+embeddings). Right: a "Global without the monoculture" panel — voice entropy + self-coverage line (copy only; static numbers OK, label them as illustrative or wire to `/api/v2/voice-mix` if trivial). Then **Who it's for** (journalists/researchers/readers), **Support** (Ko-fi), **Footer** (sources + the already-fixed GitHub link `https://github.com/pedro-cmyks/Observatory-Global`).

- [ ] **Step 1: Restructure Landing.tsx**

Replace the hero block (current `Landing.tsx:135-197` radar section) with the new eyebrow/H1/standfirst/`<HeroThread />`/CTAs, and reorder/rewrite the sections to the 7 above. Import `HeroThread` from `../components/HeroThread`. Keep the existing `RevealSection`, `BentoCard`, `useReveal`, `prefetchBriefing`, and `/health` live-stats logic; reuse `BentoCard` for the surfaces (but give the lead card a wider span class). Use Tailwind classes already in the file (`font-display-xl`, `font-headline-md`, `font-technical-label`, `bg-bg-surface`, `border-border-subtle`, etc.). Add `tabular-nums` to every numeric span.

- [ ] **Step 2: Register-gradient + anti-AI CSS in Landing.css**

Add classes for: editorial section spacing/serif leads; console section density; the soft-beat divider; HUD step panels (1px emerald border, low-opacity emerald bg); the non-uniform surfaces grid (one `md:col-span-2` lead card). Keep DESIGN.md palette (navy + emerald, amber caution, blue/cyan geo, violet people).

- [ ] **Step 3: Build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds, no TS errors.

- [ ] **Step 4: Preview-verify Landing**

Navigate to `/`:
- `preview_console_logs` error → none.
- `preview_eval`: H1 text is "Follow the thread."; HeroThread `<svg>` present; no `react-force-graph` chunk loaded on `/`.
- `preview_resize` 1440 / 1280 / 375: no horizontal scroll (`maxScrollX === 0`), sections readable, cards reflow.
- `preview_eval` set `prefers-reduced-motion` (or check): comet absent / pulse stopped under reduced motion.
- `preview_screenshot` at 1440 and 375 → share with user.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/pages/Landing.tsx frontend-v2/src/pages/Landing.css
git commit -m "feat(landing): movement-led redesign — register gradient, thread hero, 7-section descent"
```

---

## Task 5: Docs visual consistency check

**Files:**
- Modify (optional): `frontend-v2/src/pages/Docs.css` (heading font only, if needed)

Docs already got the content truth-pass and the font-var swap (Task 1, Step 8). This task verifies it reads coherently with the new system and optionally lifts headings to Fraunces for the editorial signature.

- [ ] **Step 1: Preview-verify Docs**

Navigate to `/docs`:
- `preview_console_logs` error → none.
- `preview_eval`: a Docs `h2` computed font-family includes Fraunces (if not, and you want the editorial signature, set Docs `h1,h2` to `var(--font-display)` in Docs.css); `.docs-section-eyebrow` / `.docs-method` use Geist Mono (`var(--font-mono)`/`var(--font-technical)`).
- `preview_screenshot` of one Docs section → share with user.

- [ ] **Step 2: (If changed) Build + commit**

Run: `cd frontend-v2 && npm run build` (expected pass)
```bash
git add frontend-v2/src/pages/Docs.css
git commit -m "style(docs): align headings to Fraunces editorial register"
```

---

## Task 6: Final verification + deploy to Vercel

**Files:** none (integration + release)

- [ ] **Step 1: Full build + test suite**

Run: `cd frontend-v2 && npm run build && npx vitest run`
Expected: build passes; all tests green (including `heroThreads.test.ts`).

- [ ] **Step 2: Final preview smoke**

`/` and `/docs`: 0 console errors; hero animates and shows a real live thread title (or graceful fallback); fonts loaded (no Outfit/Jakarta link); responsive 1440/1280/375; reduced-motion fallback works.

- [ ] **Step 3: Confirm deploy scope with user**

Confirm: frontend-only → Vercel; Fly/#176 backend NOT included. (Default unless user says otherwise.)

- [ ] **Step 4: Merge to the production branch**

```bash
git checkout v3-intel-layer
git merge --no-ff feat/level0-redesign -m "feat: level-0 narrative + aesthetic redesign (Landing + Docs)"
git push origin v3-intel-layer
```
Expected: Vercel auto-builds `v3-intel-layer` → production.

- [ ] **Step 5: Post-deploy production smoke**

Once Vercel reports the deployment live, verify the production Landing + Docs: hero renders with live threads, Fraunces/Geist fonts loaded, no console errors, GitHub link correct. Report the deployment URL to the user.

---

## Self-Review (completed)

- **Spec coverage:** §3 positioning → Task 4 copy; §4 register gradient → Task 4 steps 1-2; §5 hero → Tasks 2+3; §6 structure → Task 4; §7 type system → Task 1; §8 anti-AI (tabular-nums, non-uniform grid, real data, reduced-motion) → Tasks 1/3/4; §9 file map → all tasks; §10 verification → preview steps + Task 6; §11 deploy → Task 6. All covered.
- **Placeholder scan:** hero helper + test have full code; component has full code; Landing copy is explicit; no TBDs. Landing.tsx/CSS are described as a structured restructure with exact section order/copy rather than a 400-line dump (the engineer rebuilds against the listed contracts) — acceptable for a page rewrite.
- **Type consistency:** `buildHeroThreads`, `HeroMover`, `HeroNode`, `RawThread`, `NODE_COLOR` names match across Tasks 2 and 3; viewBox 640×240 consistent between helper coordinates and component.
