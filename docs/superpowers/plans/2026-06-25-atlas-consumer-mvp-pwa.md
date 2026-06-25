# Atlas Consumer MVP (PWA web+mobile) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Atlas web app into an installable, offline-capable, mobile-readable consumer narrative-read PWA (Phase 1 front door), without backend changes.

**Architecture:** PWA on the existing `frontend-v2` React 19 + Vite app via `vite-plugin-pwa` (Workbox). Reuse the existing Brief (`/brief`) and thread-detail (`ThemeDetail`) surfaces; add mobile responsive layouts, an install hint, a `useIsMobile` hook, honest country-chip labeling, a shareable thread card (`html-to-image`), and an offline banner. The L2 console stays desktop-only. Spec: `docs/superpowers/specs/2026-06-25-atlas-consumer-mvp-pwa-design.md`.

**Tech Stack:** React 19, Vite, TypeScript, vanilla CSS, vite-plugin-pwa (Workbox), html-to-image (already a dep), vitest. Backend untouched.

---

## File structure (decomposition)

| File | Create/Modify | Responsibility |
|---|---|---|
| `frontend-v2/package.json` | Modify | add `vite-plugin-pwa` devDep |
| `frontend-v2/vite.config.ts` | Modify | register `VitePWA` plugin + manifest + Workbox runtime caching |
| `frontend-v2/public/icon-192.png`, `icon-512.png`, `icon-maskable-512.png` | Create | PWA icons (simple Atlas glyph) |
| `frontend-v2/index.html` | Modify | `theme-color`, `apple-touch-icon`, viewport-fit |
| `frontend-v2/src/hooks/useIsMobile.ts` | Create | viewport breakpoint hook (pure-ish, testable) |
| `frontend-v2/src/hooks/useIsMobile.test.ts` | Create | unit test for the breakpoint logic |
| `frontend-v2/src/components/InstallPrompt.tsx` (+`.css`) | Create | dismissable "Add to Home Screen" hint |
| `frontend-v2/src/components/OfflineBanner.tsx` (+`.css`) | Create | online/offline + "offline · last updated" banner |
| `frontend-v2/src/lib/countryChips.ts` | Create | honest chip label helper (pure, testable) |
| `frontend-v2/src/lib/countryChips.test.ts` | Create | unit test |
| `frontend-v2/src/lib/shareCard.ts` | Create | build share text + render card to PNG + Web Share (logic testable) |
| `frontend-v2/src/lib/shareCard.test.ts` | Create | unit test for the share-text builder |
| `frontend-v2/src/components/ShareCard.tsx` (+`.css`) | Create | offscreen card markup + Share button |
| `frontend-v2/src/pages/BriefNewspaper.tsx` / `.css` | Modify | mobile single-column feed; hide map on mobile; share button; honest chips |
| `frontend-v2/src/components/ThemeDetail.tsx` / `.css` | Modify | full-screen mobile read; honest chips; share button |
| `frontend-v2/src/App.css` / console chrome | Modify | hide L2 console chrome on mobile where it leaks into the read |

---

## Task 1: PWA scaffold (installable + offline)

**Files:**
- Modify: `frontend-v2/package.json`
- Modify: `frontend-v2/vite.config.ts`
- Create: `frontend-v2/public/icon-192.png`, `icon-512.png`, `icon-maskable-512.png`
- Modify: `frontend-v2/index.html`

- [ ] **Step 1: Install the plugin**

Run: `cd frontend-v2 && npm install -D vite-plugin-pwa`
Expected: added to devDependencies, no peer-dep errors (React 19 ok).

- [ ] **Step 2: Generate icons**

Create three PNGs from a simple dark-bg "A" / Atlas glyph (ImageMagick if available, else a minimal script). Example:
```bash
cd frontend-v2/public
# Solid dark square with a light "A"; replace with real brand later (#106 kraken)
for s in 192 512; do
  magick -size ${s}x${s} xc:'#0b0e13' -gravity center -fill '#1D9E75' \
    -font Helvetica -pointsize $((s*55/100)) -annotate +0+0 'A' icon-${s}.png
done
magick -size 512x512 xc:'#0b0e13' -gravity center -fill '#1D9E75' \
  -font Helvetica -pointsize 250 -annotate +0+0 'A' icon-maskable-512.png
```
Expected: three PNGs exist. (If `magick` unavailable, create with a tiny node `canvas`/sharp script or a checked-in placeholder — icons are replaceable.)

- [ ] **Step 3: Register VitePWA in vite.config.ts**

Add to the plugins array (keep existing react()/etc.):
```ts
import { VitePWA } from 'vite-plugin-pwa'

// inside defineConfig({ plugins: [ ... ] })
VitePWA({
  registerType: 'autoUpdate',
  includeAssets: ['icon-192.png', 'icon-512.png', 'icon-maskable-512.png'],
  manifest: {
    name: 'Atlas — Narrative Intelligence',
    short_name: 'Atlas',
    description: 'The global narrative weather — what is happening, who is saying what, where it is heading.',
    start_url: '/brief',
    display: 'standalone',
    background_color: '#0b0e13',
    theme_color: '#0b0e13',
    icons: [
      { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: 'icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  },
  workbox: {
    globPatterns: ['**/*.{js,css,html,woff2,png,svg}'],
    navigateFallbackDenylist: [/^\/api\//],
    runtimeCaching: [
      {
        urlPattern: ({ url }) => url.pathname.startsWith('/api/v2/briefing') || url.pathname.startsWith('/api/v2/threads'),
        handler: 'NetworkFirst',
        options: { cacheName: 'atlas-brief', networkTimeoutSeconds: 5, expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 } },
      },
      {
        urlPattern: ({ url }) => url.pathname.startsWith('/api/v2/theme/'),
        handler: 'NetworkFirst',
        options: { cacheName: 'atlas-theme', networkTimeoutSeconds: 5, expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 12 } },
      },
    ],
  },
})
```

- [ ] **Step 4: index.html meta**

In `frontend-v2/index.html` `<head>`, ensure:
```html
<meta name="theme-color" content="#0b0e13" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<link rel="apple-touch-icon" href="/icon-192.png" />
```

- [ ] **Step 5: Build + verify PWA artifacts**

Run: `cd frontend-v2 && npm run build`
Expected: build green; `dist/` contains `sw.js`, `manifest.webmanifest`, `registerSW.js`.

- [ ] **Step 6: Lighthouse PWA check (manual, preview)**

Start preview, open DevTools → Lighthouse → PWA. Expected: installable; SW registered; manifest valid. (In the agent loop: `preview_start`, then verify `navigator.serviceWorker.getRegistrations()` is non-empty via preview_eval, and the manifest link resolves.)

- [ ] **Step 7: Commit**
```bash
git add frontend-v2/package.json frontend-v2/package-lock.json frontend-v2/vite.config.ts frontend-v2/index.html frontend-v2/public/icon-*.png
git commit -m "feat(pwa): vite-plugin-pwa scaffold — installable + offline brief/theme caching"
```

---

## Task 2: `useIsMobile` hook (foundation for mobile layouts)

**Files:**
- Create: `frontend-v2/src/hooks/useIsMobile.ts`
- Test: `frontend-v2/src/hooks/useIsMobile.test.ts`

- [ ] **Step 1: Write the failing test**
```ts
import { renderHook } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { useIsMobile, MOBILE_MAX } from './useIsMobile'

function setWidth(w: number) {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: w })
  window.dispatchEvent(new Event('resize'))
}

describe('useIsMobile', () => {
  beforeEach(() => setWidth(1280))
  it('is false on desktop width', () => {
    setWidth(1280)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })
  it('is true at/below the mobile breakpoint', () => {
    setWidth(MOBILE_MAX)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })
})
```

- [ ] **Step 2: Run test, verify it fails**

Run: `cd frontend-v2 && npx vitest run src/hooks/useIsMobile.test.ts`
Expected: FAIL ("Cannot find module './useIsMobile'").

- [ ] **Step 3: Implement**
```ts
import { useEffect, useState } from 'react'

export const MOBILE_MAX = 768

export function useIsMobile(max: number = MOBILE_MAX): boolean {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth <= max : false,
  )
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= max)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [max])
  return isMobile
}
```

- [ ] **Step 4: Run test, verify pass**

Run: `cd frontend-v2 && npx vitest run src/hooks/useIsMobile.test.ts`
Expected: PASS (2 tests). If `@testing-library/react` is missing, add `-D @testing-library/react` or rewrite the test to drive the hook through a tiny wrapper component already used in the repo's test setup.

- [ ] **Step 5: Commit**
```bash
git add frontend-v2/src/hooks/useIsMobile.ts frontend-v2/src/hooks/useIsMobile.test.ts
git commit -m "feat(mobile): useIsMobile viewport hook"
```

---

## Task 3: Mobile Brief feed (single column, no map)

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.css`
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

- [ ] **Step 1: Hide the choropleth on mobile**

In `BriefNewspaper.tsx`, import `useIsMobile`; gate the map/`SignalDensity` block: `{!isMobile && (<the map block/>)}`. (Locate the demoted half-width map added in the L1 rebuild; wrap it.)

- [ ] **Step 2: Mobile CSS — single column + tap targets**

Append to `BriefNewspaper.css`:
```css
@media (max-width: 768px) {
  .brief-grid, .brief-columns { display: block; }       /* whatever the 2-col container is — verify class */
  .brief-lead-story { padding: 16px; }
  .brief-lead-headline { font-size: 1.5rem; line-height: 1.2; }
  .brief-watchlist button { padding: 12px; min-height: 48px; }  /* tap target */
  .brief-time-range { flex-wrap: wrap; gap: 6px; }
  .brief-heating-strip { overflow-x: auto; }
}
```
(Verify the real container class names in the JSX before writing; replace the placeholders above with the actual classes — do NOT ship guessed selectors.)

- [ ] **Step 3: Build + preview at 375px**

Run: `cd frontend-v2 && npm run build` (green), then in preview: `preview_resize` to 375px, navigate `/brief`, `preview_screenshot`. Expected: one column, no map, lead + watchlist + heating + by-theme stacked, large tap targets, `maxScrollX === 0` (no horizontal scroll — verify via preview_eval `document.documentElement.scrollWidth <= window.innerWidth`).

- [ ] **Step 4: Commit**
```bash
git add frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/pages/BriefNewspaper.css
git commit -m "feat(mobile): single-column Brief feed, map hidden on phones"
```

---

## Task 4: Mobile full-screen thread read

**Files:**
- Modify: `frontend-v2/src/components/ThemeDetail.css`
- Modify: `frontend-v2/src/components/ThemeDetail.tsx` (only if routing/visibility needs it)

- [ ] **Step 1: Verify how the Brief opens a thread on mobile**

Read `BriefNewspaper.tsx` `openThread` + how the app renders `ThemeDetail` (panel inside `/app`, or an overlay). Document the actual path. The read must be reachable from `/brief` on mobile and render full-screen.

- [ ] **Step 2: Full-screen mobile CSS for the read**

Append to `ThemeDetail.css`:
```css
@media (max-width: 768px) {
  .theme-detail { position: fixed; inset: 0; width: 100vw; height: 100dvh; z-index: 60; overflow-y: auto; border-radius: 0; }
  .theme-detail-close { position: sticky; top: 0; }
  /* collapse dense desktop sections on phones */
  .evolution-graph, .narrative-drift, .framing-matrix { display: none; }
  .coverage-article-headline { font-size: 15px; }
  .source-item { min-height: 44px; }
}
```
(Verify the real class names — `.theme-detail`, the evolution-graph/framing containers — and replace; ship only real selectors.)

- [ ] **Step 3: Ensure console chrome doesn't bleed through on mobile**

If `ThemeDetail` renders inside the `/app` console, hide the map/legend/command-bar behind the full-screen read on mobile (CSS `.app-console > *:not(.theme-detail) { ... }` or a body class). Verify nothing of the cockpit is visible behind the read on a phone.

- [ ] **Step 4: Build + preview the read loop at 375px**

Build green. Preview at 375px: `/brief` → tap the lead "Open thread" → full-screen readable thread; tap a Top Source → coverage articles with headlines + "open original ↗"; back returns to Brief. Screenshot. 0 console errors.

- [ ] **Step 5: Commit**
```bash
git add frontend-v2/src/components/ThemeDetail.css frontend-v2/src/components/ThemeDetail.tsx
git commit -m "feat(mobile): full-screen readable thread view on phones"
```

---

## Task 5: Honest country chips (trust)

**Files:**
- Create: `frontend-v2/src/lib/countryChips.ts`
- Test: `frontend-v2/src/lib/countryChips.test.ts`
- Modify: `BriefNewspaper.tsx` (watchlist chips), `ThemeDetail.tsx` (chips)

- [ ] **Step 1: Failing test**
```ts
import { describe, it, expect } from 'vitest'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from './countryChips'

describe('countryChips honesty', () => {
  it('labels chips as coverage geography, not subject', () => {
    expect(COVERAGE_CHIP_LABEL).toMatch(/cover/i)
  })
  it('tip explains these are where it is reported from', () => {
    expect(coverageChipTip('United States')).toMatch(/covered|reported/i)
    expect(coverageChipTip('United States')).toContain('United States')
  })
})
```

- [ ] **Step 2: Run, verify fail**

Run: `cd frontend-v2 && npx vitest run src/lib/countryChips.test.ts` → FAIL.

- [ ] **Step 3: Implement**
```ts
// Country chips on threads reflect COVERAGE volume (where a story is being
// reported), NOT the story's subject country — the subject-geography fix is
// #238. Until then, label them honestly so the surface never implies a false
// subject (e.g. a Venezuela earthquake whose chips read US/BR/RU).
export const COVERAGE_CHIP_LABEL = 'Covered from'

export function coverageChipTip(country: string): string {
  return `Where this story is being covered from — not necessarily its subject. (${country})`
}
```

- [ ] **Step 4: Run, verify pass**

Run: `cd frontend-v2 && npx vitest run src/lib/countryChips.test.ts` → PASS.

- [ ] **Step 5: Apply in the UI**

In `BriefNewspaper.tsx` watchlist + lead chip rows and `ThemeDetail.tsx` country chips, add a small "Covered from" caption above/with the chip group and set `data-tip={coverageChipTip(name)}` on each chip. Keep it subtle (one caption per group, not per chip).

- [ ] **Step 6: Build + preview + commit**

Build green; preview shows the honest caption on the Venezuela-type case. Then:
```bash
git add frontend-v2/src/lib/countryChips.ts frontend-v2/src/lib/countryChips.test.ts frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/components/ThemeDetail.tsx
git commit -m "feat(trust): honest 'covered from' country-chip labeling (interim, #238 deep fix pending)"
```

---

## Task 6: Shareable thread card

**Files:**
- Create: `frontend-v2/src/lib/shareCard.ts`
- Test: `frontend-v2/src/lib/shareCard.test.ts`
- Create: `frontend-v2/src/components/ShareCard.tsx` (+ `.css`)
- Modify: `ThemeDetail.tsx` (Share button)

- [ ] **Step 1: Failing test for the share-text builder**
```ts
import { describe, it, expect } from 'vitest'
import { buildShareText } from './shareCard'

describe('buildShareText', () => {
  it('includes label, why-now, and url', () => {
    const t = buildShareText({ label: 'Ukraine War Updates', whyNow: 'Up 147 vs prior 10h', url: 'https://atlas.app/app?theme=x' })
    expect(t).toContain('Ukraine War Updates')
    expect(t).toContain('Up 147')
    expect(t).toContain('https://atlas.app/app?theme=x')
    expect(t).toContain('Atlas')
  })
})
```

- [ ] **Step 2: Run, verify fail** → `npx vitest run src/lib/shareCard.test.ts` FAIL.

- [ ] **Step 3: Implement shareCard.ts**
```ts
import { toPng } from 'html-to-image'

export interface ShareInput { label: string; whyNow?: string | null; url: string }

export function buildShareText({ label, whyNow, url }: ShareInput): string {
  const lines = [`📡 ${label}`]
  if (whyNow) lines.push(whyNow)
  lines.push(`via Atlas — ${url}`)
  return lines.join('\n')
}

export async function shareThread(input: ShareInput, cardEl: HTMLElement | null): Promise<void> {
  const text = buildShareText(input)
  let file: File | undefined
  if (cardEl) {
    try {
      const dataUrl = await toPng(cardEl, { pixelRatio: 2, cacheBust: true })
      const blob = await (await fetch(dataUrl)).blob()
      file = new File([blob], 'atlas-thread.png', { type: 'image/png' })
    } catch { /* fall back to text-only */ }
  }
  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean }
  if (file && nav.canShare?.({ files: [file] })) {
    await navigator.share({ files: [file], text, title: input.label })
  } else if (nav.share) {
    await navigator.share({ text, title: input.label, url: input.url })
  } else {
    await navigator.clipboard.writeText(text)
  }
}
```

- [ ] **Step 4: Run, verify pass** → PASS.

- [ ] **Step 5: ShareCard.tsx (offscreen render target)**

Create a visually-styled card (dark bg, label, why-now, up to 2 evidence headlines, "ATLAS" wordmark) positioned offscreen (`position:fixed; left:-9999px`) and a Share button that calls `shareThread(input, ref.current)`. Vanilla CSS in `ShareCard.css`.

- [ ] **Step 6: Wire into ThemeDetail**

Add a Share button in the thread header that mounts `ShareCard` (hidden) and triggers `shareThread`. `url` = `window.location.origin + '/app?theme=' + thread id` (the existing thread route).

- [ ] **Step 7: Build + preview (desktop fallback copies text; mobile uses Web Share) + commit**
```bash
git add frontend-v2/src/lib/shareCard.ts frontend-v2/src/lib/shareCard.test.ts frontend-v2/src/components/ShareCard.tsx frontend-v2/src/components/ShareCard.css frontend-v2/src/components/ThemeDetail.tsx
git commit -m "feat(share): shareable thread card (html-to-image + Web Share API)"
```

---

## Task 7: Offline banner + empty-state audit

**Files:**
- Create: `frontend-v2/src/components/OfflineBanner.tsx` (+ `.css`)
- Modify: `BriefNewspaper.tsx` (mount banner)

- [ ] **Step 1: OfflineBanner component**
```tsx
import { useEffect, useState } from 'react'
import './OfflineBanner.css'

export function OfflineBanner() {
  const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)
  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false)
    window.addEventListener('online', on); window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])
  if (online) return null
  return <div className="offline-banner" role="status">Offline — showing the last Brief you loaded.</div>
}
```

- [ ] **Step 2: Mount it at the top of the Brief**

In `BriefNewspaper.tsx`, render `<OfflineBanner />` above the feed.

- [ ] **Step 3: Empty-state audit**

On mobile preview, walk Brief + thread read offline (DevTools offline) and with a thin thread; confirm no ugly empty placeholders (drift already hides; check watchlist/heating/coverage). Fix any with honest copy.

- [ ] **Step 4: Build + preview (toggle offline) + commit**
```bash
git add frontend-v2/src/components/OfflineBanner.tsx frontend-v2/src/components/OfflineBanner.css frontend-v2/src/pages/BriefNewspaper.tsx
git commit -m "feat(pwa): offline banner + mobile empty-state audit"
```

---

## Task 8: Verify, deploy, update papers

- [ ] **Step 1: Full build + test sweep**

Run: `cd frontend-v2 && npm run build && npx vitest run`
Expected: build green; all vitest pass (incl. the new useIsMobile/countryChips/shareCard tests).

- [ ] **Step 2: Lighthouse PWA + mobile pass**

Preview at 375px: PWA installable, offline serves last Brief, the read loop works, share works. Record a screenshot of the mobile Brief + the mobile thread read.

- [ ] **Step 3: Deploy**

Push to `v3-intel-layer` (Vercel auto-deploy). No Fly deploy (frontend-only).
```bash
git push origin v3-intel-layer
```

- [ ] **Step 4: Update papers + handoff**

Add the mobile read + share loop to Paper 7's evidence; note the honest-chips interim under Paper 3/4 (the #238 down-payment). Append a session handoff block + update the CLAUDE.md pointer. Commit.

---

## Self-Review

- **Spec coverage:** §2 surfaces → Tasks 3,4; §3 PWA → Task 1; §4 mobile UX → Tasks 3,4,6; §5 trust/chips → Task 5; §7 offline/empty → Task 7; §8 testing → every task + Task 8; §9 DoD → Task 8; §10 papers → Task 8. All covered.
- **Placeholders:** the only "verify the real class names" notes (Tasks 3,4) are deliberate guards — the executor MUST read the actual JSX and replace guessed selectors before shipping; they are instructions, not shipped placeholders.
- **Type consistency:** `useIsMobile`/`MOBILE_MAX`, `coverageChipTip`/`COVERAGE_CHIP_LABEL`, `buildShareText`/`shareThread`/`ShareInput` are used consistently across tasks.
- **Scope:** single Phase-1 PWA; Phase 2 (accounts/alerts/dossier) excluded.

## Execution note
Tasks 1–4 are the core "web + mobile read" (ship-and-verify each). Tasks 5–7 are the trust + growth polish that make it a product. Task 8 closes it out. Each task ends green + committed and is independently verifiable in the 375px preview.
