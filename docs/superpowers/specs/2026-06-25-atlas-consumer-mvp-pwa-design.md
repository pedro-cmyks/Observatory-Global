# Atlas Consumer MVP (PWA, web + mobile) — design spec

Date: 2026-06-25. Status: approved (design), pending implementation plan.
Derived from `docs/product/2026-06-25-what-atlas-lacks-to-be-a-product.md`.
This is **Phase 1** of a sequenced-hybrid product: a free/viral consumer
narrative-read front door. Phase 2 (accounts, follow, alerts, dossier — the
pro analyst loop) is explicitly out of scope here and gets its own spec.

## 1. The one job
"Give me the global narrative weather, let me tap a story and actually read
it — down to the original source." Anonymous, no login. The loop:

open → scan the Brief → tap a story → read the thread (evidence + original
article + translation) → share.

Success: a commuter opens Atlas on their phone, understands what's happening
in the world in 30 seconds, taps one narrative, reads it with real evidence
and reaches the original article, and can share it — and never sees an
obviously-wrong front page.

## 2. Scope

**In (MVP surfaces, mobile + web):**
- **L0 Landing** — already responsive; light polish only.
- **L1 Brief** (`/brief`) — the consumer feed. Already largely responsive.
- **Thread-detail read** — full-screen readable article view on mobile,
  reachable from the Brief (lead "Open thread" + watchlist rows). Reuses the
  existing `ThemeDetail` (headlines, source→coverage expand, original link,
  translation — all shipped 2026-06-25).
- **PWA shell** — installable, offline-last-Brief.
- **Share** — a thread share-card (image) for the viral loop.

**Out (Phase 2+, YAGNI for MVP):**
accounts · follow/save · alerts/push · dossier/report · the L2 console
(map/cockpit) on mobile · native apps · comments/community · personalization.
The L2 console stays **desktop-web only** for MVP.

## 3. Architecture — PWA on the existing React/Vite frontend

One codebase. No backend changes except a frontend-only chip relabel (§5).

- **Tooling:** `vite-plugin-pwa` (Workbox under the hood) — the modern,
  maintained path; generates the service worker + injects the manifest.
- **Manifest** (`manifest.webmanifest`): `name` "Atlas — Narrative
  Intelligence", `short_name` "Atlas", `display: standalone`,
  `theme_color`/`background_color` from the dark theme, `start_url: /brief`,
  icons (192/512 + maskable). MVP icon = a simple Atlas wordmark/glyph; the
  kraken mascot (#106) is a later brand pass, NOT a blocker.
- **Service worker / caching (Workbox):**
  - Precache the app shell (JS/CSS/fonts/icons).
  - Runtime cache the briefing API (`/api/v2/briefing*`,
    `/api/v2/threads*`) **network-first with a cache fallback + short
    expiration** → the last Brief reads offline; fresh when online.
  - Theme detail (`/api/v2/theme/*`) network-first, cache fallback.
  - Never cache `/api/v2/translate` aggressively (already memoized client +
    server-cached).
- **Installability:** manifest + SW + HTTPS (Vercel) → "Add to Home Screen".
  A subtle in-app "Install" hint on mobile when `beforeinstallprompt` fires
  (dismissable, remembered in localStorage).
- **Push scaffold (no push yet):** register the SW so Phase-2 Web Push can be
  added without re-architecting. Do NOT request notification permission in
  the MVP.

## 4. Mobile UX shape (per 2026 news-UX research: clean, fewer decisions per
screen, readable article view)

- **Brief = single-column vertical feed** on narrow viewports: lead story →
  watchlist (movement + country chips) → heating strip → "by theme"
  back-matter. Large tap targets; the demoted desktop choropleth is hidden or
  collapsed on mobile (a map is not a mobile-consumer surface). Time-range
  control becomes a compact control.
- **Thread-detail = full-screen readable article view** on mobile: when opened
  from the Brief on a small viewport, render `ThemeDetail` full-screen (console
  chrome hidden), lead with the why-now + evidence headlines (translatable) +
  Top-Sources→coverage expand → "open original ↗". Back button returns to the
  Brief. The dense desktop sections (evolution graph, framing matrix) are
  collapsed/secondary on mobile.
- **Share = thread share-card:** a "Share" affordance on a thread generates a
  clean card image (reuse the existing `html-to-image` dependency, as
  `ExportMenu` already does) — thread label + why-now + a couple of evidence
  headlines + "Atlas" wordmark + the thread URL. Web Share API on mobile
  (`navigator.share`) with a copy-link/download fallback.

## 5. Trust = the MVP gate (no trust → not a product)

The read must be right. Already fixed this session: lead-story selection,
geo mistag (title-only + backfill), same-event dedup guard, count semantics.
Remaining MVP trust work:
- **Honest country chips (frontend-only interim):** today chips show coverage
  countries as if they were the subject (Venezuela earthquake → BR/MX/RU, VE
  absent). For the MVP, **relabel** them honestly — they represent "where it's
  being covered," not "what it's about" — via a small label/affordance, so the
  surface stops implying a false subject. The deep fix (subject geography) is
  **#238**, post-MVP.
- **Honest empty states** everywhere (already the pattern: gated=0 fallbacks,
  UNVERIFIED badges, hide-empty-drift). Audit the mobile surfaces for any
  remaining ugly empty placeholders.

## 6. Data flow
No new endpoints. The Brief uses `/api/v2/briefing`; thread-detail uses
`/api/v2/theme/{id}` (now carrying `id` + `source_lang` for translation);
share-card is built client-side from data already on screen. The SW caches
these responses for offline.

## 7. Error / empty / offline states
- Offline + no cached Brief → a clear "You're offline — last Brief unavailable"
  state, not a spinner.
- Offline + cached Brief → show it with an "Offline · last updated <time>"
  banner.
- Failed thread fetch → reuse the existing below-gate / UNVERIFIED honest
  fallbacks.
- Translation failure → silently render the original (already the behavior).

## 8. Testing / verification
- `npm run build` (strict) green; existing vitest green.
- Lighthouse **PWA category passes** (installable, SW, manifest, offline).
- Preview verification (mobile viewport 375px): Brief feed reads as one column;
  tap a story → full-screen readable thread; source expand + original link;
  share-card generates; offline (SW) serves the last Brief.
- Real-device sanity (Pedro): install to home screen, open offline.

## 9. Definition of Done ("listo")
Installable PWA (Lighthouse PWA pass) · Brief + thread read well on mobile +
web · last Brief readable offline · shareable thread cards · country chips
honest · trustworthy surface (no obviously-wrong front page) · deployed to
Vercel · existing tests green.

## 10. Papers linkage (keep updating as we build)
Mobile read surfaces + share loop = **Paper 7** (analyst/consumer workflow &
visualization). Trust/geo/identity = **Paper 3 + 4**. Voice/diversity surfacing
in the read = the diversity papers. Each shipped slice updates its paper's
evidence/method section in `docs/research/atlas-paper/`.

## 11. Implementation order (phased)
1. **PWA scaffold** — `vite-plugin-pwa`, manifest, icons, SW with the caching
   strategy; verify installable + Lighthouse PWA pass. (Smallest, unblocks
   "web + mobile" claim.)
2. **Mobile Brief feed** — responsive single-column reshape; hide/collapse the
   map; compact controls. Verify at 375px.
3. **Mobile thread-read** — full-screen `ThemeDetail` on mobile reachable from
   the Brief; collapse dense sections. Verify the read loop end-to-end.
4. **Honest chips (trust)** — frontend relabel of country chips.
5. **Share-card** — `html-to-image` thread card + Web Share API.
6. **Offline polish + empty-state audit** — banners, offline-no-cache state.
7. **Verify + deploy** — Lighthouse, mobile preview, ship to Vercel; update
   the papers.

Each step is independently shippable and verifiable; ship + verify before the
next. Steps 1–3 are the core "web + mobile read"; 4–6 are the trust + growth
polish that make it a *product*, not just a responsive site.
