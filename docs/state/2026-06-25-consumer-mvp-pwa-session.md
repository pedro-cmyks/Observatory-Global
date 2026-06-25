# Session handoff — 2026-06-25 (Consumer MVP, PWA web+mobile)

Goal: "listo MVP de Atlas para web y móvil." Followed the full process:
product-gap assessment → brainstorm (hybrid-sequenced: consumer read front
door first) → spec → plan → implementation. Spec:
`docs/superpowers/specs/2026-06-25-atlas-consumer-mvp-pwa-design.md`. Plan:
`docs/superpowers/plans/2026-06-25-atlas-consumer-mvp-pwa.md`.

## Decision (brainstorm)
Phase 1 = a free/viral **consumer narrative-read** front door (anonymous, no
login). Phase 2 (accounts, follow, alerts, dossier — the pro analyst loop) is
a separate later spec. Delivery: **PWA on the existing React/Vite app**
(research-backed PWA-first-2026), one codebase, sets up Phase-2 push.

## Shipped + deployed (Vercel, frontend-only) — Tasks 1–5, 7 of 8
1. **PWA scaffold** (`d8330c9`) — `vite-plugin-pwa` (Workbox): manifest
   (Atlas, standalone, start_url /brief), generated icons
   (`scripts/gen-pwa-icons.mjs`, dep-free PNG, replaceable brand), service
   worker network-first caching `/briefing` `/threads` `/theme` so the last
   Brief reads offline. SW build-only (dev preview unaffected). Build emits
   sw.js + manifest + workbox + 35-entry precache.
2. **`useIsMobile`** (`382341c`) — hook + pure `isMobileWidth` (3 tests),
   MOBILE_MAX 768. Repo tests are node/pure (no jsdom) — tested the pure fn.
3. **Mobile Brief feed** (`594396e`) — `@media(max-width:768px)`: hide the
   choropleth (keep "Most Active"), single column, compact masthead/body,
   56px tap targets, wrapped range selector. Verified at 375px: lead renders,
   no map, no horizontal scroll.
4. **Mobile full-screen thread read** (`20d9a95`) — `.theme-detail-overlay`
   fixed full-screen (z-index 9000) over the console on phones + body-scroll
   lock; Evolution Graph (force-graph) skipped on mobile via useIsMobile.
   Verified at 375px: overlay full-width, graph hidden, top-sources read
   intact.
5. **Honest chips** (`64fbd19`) — chips are coverage volume, not subject;
   "Covered from:" caption + "where it's covered from — not its subject"
   tooltip (`lib/countryChips.ts`, 2 tests). Deep fix = #238.
7. **Offline banner** (`e7eb50f`) — sticky "Offline — showing the last Brief"
   when navigator offline.

Tests: 84 vitest green (28 files). Builds green throughout.

6. **Shareable thread** (`64f6be0`) — Share button on the thread read uses the
   Web Share API (native sheet on mobile) with a timeout-guarded clipboard
   fallback (never hangs). The IMAGE share-card was prototyped but
   html-to-image stalls embedding cross-origin Google Fonts even with
   `skipFonts` → **deferred** (self-host the card fonts or pre-rasterize);
   text+link ships now. The offscreen `.share-card` CSS/markup is retained for
   that follow-up. 86 vitest green.

All 8 plan tasks implemented; the consumer read MVP is deployed.

## Remaining (close-out)
- **Lighthouse PWA pass** on the live Vercel build (the SW only runs on the
  production build, not the dev preview) + real-device install/offline sanity
  (Pedro).
- **Image share-card** follow-up (self-host card fonts to unblock
  html-to-image).
- **Papers:** grow Paper 7 (mobile read + share loop) + Paper 3/4 (honest-chips
  interim). Phase 2 (accounts/alerts/dossier) + #238 (subject geography) next.

## Pending Pedro eyeball (Vercel, once deployed)
- Install Atlas to home screen (Add to Home Screen) on a phone.
- `/brief` reads as one column; tap a story → full-screen readable thread →
  source expand → original article. Offline: last Brief still readable.

## Notes
- Map heat VISUAL caveat from prior sessions is unrelated (the consumer MVP
  hides the map on mobile).
- The SW is now live for ALL users (incl. desktop) — network-first for the
  API, autoUpdate on each deploy; safe, but watch for any stale-asset reports.
- Phase 2 (accounts/alerts/dossier) and #238 (subject geography — the deep
  fix behind honest chips) are the next big tracks.
