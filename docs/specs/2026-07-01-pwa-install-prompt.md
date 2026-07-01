# Spec: PWA Install Prompt (mobile "download the app" toast)

**Date:** 2026-07-01
**Status:** SHIPPED (code) — browser-verified both platforms; manifest `screenshots` asset deferred

## Execution status (2026-07-01)

- **`lib/installPrompt.ts`** + **`lib/installPrompt.test.ts`** — pure gate + platform
  detection, **16 tests pass** (TDD, red→green). Exports `shouldShowInstallPrompt`,
  `detectPlatform`, `DISMISS_WINDOW_MS`, `INSTALL_PROMPT_KEY`.
- **Already-installed detection** (Pedro Q, 2026-07-01): gate reads `isStandalone`
  (`display-mode: standalone` / iOS `navigator.standalone`). **Android** fully covered —
  installed users get no toast (Chrome suppresses `beforeinstallprompt` when installed,
  and my Android path requires that event). **iOS** has no API to detect an install from
  a Safari tab (Apple limit, partitioned storage), so the iOS ✕ is now **permanent**
  (`INSTALL_PROMPT_KEY = 'never'` sentinel + `permanentlyDismissed` gate field); Android
  ✕ stays a 30-day snooze (timestamp).
- **`components/InstallPrompt.tsx`** + **`.css`** — slide-in toast, Android 1-tap
  (`beforeinstallprompt`) / iOS Share-hint (glyph + bouncing arrow), i18n ES/EN,
  engagement trigger (15s or scroll>400), 30-day dismiss, `appinstalled` success,
  telemetry via `lib/telemetry.ts`.
- **Mounted** global in `main.tsx` (all routes).
- **Browser-verified** (mobile 375, preview): Android toast renders 68px, clears the
  56px tab bar (bottom 744 vs tabbar 755, no overlap), icon loads, correct copy;
  iOS variant renders share glyph + arrow, no install button; **zero console errors**.
- **`npm run build` green**, full vitest 134/135 (the 1 fail = pre-existing #204
  `exportFormatters` taxonomy-label rename, unrelated).
- **DEFERRED — manifest `screenshots`:** needs a real narrow phone PNG in `public/`.
  No headless screenshot tool in the repo (won't add a ~170MB browser dep for one
  asset). Land when Pedro drops a branded shot in `public/screenshot-brief-narrow.png`
  (then add `manifest.screenshots` + `includeAssets` entry) — Android install dialog
  already shows name+icon+description meanwhile.
- **Not committed** (awaiting Pedro's go).

**Wedge tie-in:** PWA is the *entry point to a dedicated app*. This surface makes
Atlas read as a **downloadable app** in the user's mind — not a bookmark — and is
the on-ramp for a future native app. No new product surface; a promotion layer on
the PWA that already ships (`vite-plugin-pwa`, `display: standalone`, full icon set).

## Goal

When a mobile visitor opens Atlas in a normal browser tab, surface a **non-invasive,
eye-catching slide-in toast** ("avioneta") that prompts installing Atlas to the home
screen. On Android it is a real 1-tap install; on iOS it is an animated hint (Apple
blocks programmatic install). Measured, app-framed, never nagging.

## Non-goals (YAGNI)

- No native app store build. PWA only.
- No desktop install prompt (mobile-only for v1).
- No new telemetry table/endpoint — reuse existing `telemetry_events` + `POST /api/v2/telemetry`.
- No backdrop / modal / tap-trap. The toast never blocks the page.
- No A/B experiment framework — just funnel counters for now.

## Platform reality (drives the whole design)

| Platform | Programmatic install? | Our behavior |
|---|---|---|
| Android / Chromium | YES — `beforeinstallprompt` fires | Capture event, show toast with **[Instalar]**, tap → `deferredPrompt.prompt()` → native install dialog |
| iOS Safari | NO — Apple blocks it | Toast with animated arrow → Safari **Share ⎋** → "Añadir a pantalla de inicio" |
| In-app webviews (FB/IG/etc.) | Cannot A2HS | Suppress toast entirely |
| Already installed (standalone) | n/a | Never show |

## Architecture

Pure frontend + one manifest edit. No backend, no migration.

### Components / files

- **`frontend-v2/src/lib/installPrompt.ts`** (new) — pure logic, unit-tested:
  - `type InstallEnv` — the inputs (standalone?, mobile?, iOS?, in-app webview?, dismissedAt, installed).
  - `shouldShowInstallPrompt(env, now): boolean` — the gate (pure).
  - `detectPlatform(nav, mediaMatch): { isIOS, isAndroidChromium, isInAppWebview, isStandalone }` — pure given injected `navigator`/matchMedia results.
  - localStorage key `atlas_install_prompt_v1` = dismissal timestamp (ms). Mirrors the `atlas_*_v1` walkthrough convention.
  - `DISMISS_WINDOW_MS = 30 * 24 * 60 * 60 * 1000` (30 days).
- **`frontend-v2/src/components/InstallPrompt.tsx`** (new) — the toast UI + the
  `beforeinstallprompt`/`appinstalled` event wiring + engagement trigger + telemetry.
  Mirrors `OfflineBanner.tsx` mount style.
- **`frontend-v2/src/components/InstallPrompt.css`** (new) — slide-in toast styling.
- **`frontend-v2/src/App.tsx`** (edit) — mount `<InstallPrompt />` top-level, gated on
  `useIsMobile()` (existing hook, `hooks/useIsMobile.ts`, exports `isMobileWidth`/`MOBILE_MAX`).
- **`frontend-v2/vite.config.ts`** (edit) — add `manifest.screenshots` (+ `description`
  already present) so Android renders the **app-store-style richer install dialog**.
- **Assets** (new) — 1–2 narrow (phone) PNG screenshots under `frontend-v2/public/`
  (e.g. `screenshot-brief-narrow.png`), listed in `includeAssets` + `manifest.screenshots`
  with `form_factor: "narrow"`. Captured from the mobile preview during implementation.

### Gate — `shouldShowInstallPrompt` returns false when ANY:

1. `isStandalone` — already installed (`matchMedia('(display-mode: standalone)').matches` OR iOS `navigator.standalone === true`).
2. not mobile — `!isMobileWidth(window.innerWidth)`.
3. `isInAppWebview` — FB/IG/TikTok/Line UA tokens (`FBAN|FBAV|Instagram|Line|TikTok`).
4. installed this session (`appinstalled` fired) — in-memory flag.
5. dismissed < 30 days ago — `now - dismissedAt < DISMISS_WINDOW_MS`.
6. Android-only extra: no `beforeinstallprompt` captured yet → nothing to install → don't show the Android variant. (iOS variant shows without an event.)

### Engagement trigger (earned, not instant)

On mount (and only if the gate could pass), arm a reveal that fires on **whichever comes first**:
- `setTimeout` ≈ **15s**, or
- first `scroll` past ≈ **400px**.

Then re-check the gate and reveal with a slide-in. Rationale: Google A2HS guidance —
prompting before the user sees value tanks conversion and annoys.

### UI — the "avioneta"

- Compact card, **not** full-width, slides up from the bottom edge, sits **above** the
  mobile tab bar (reuse the walkthrough's tab-bar-clearance fix — do not collide with
  `.mobile` tab bar or the focus chip that floats above it).
- Left **accent bar** + a **one-time gentle pulse** on entrance = "llamativo" without blocking.
- Shows the **Atlas app icon** (`icon-192.png`) + app-framed copy so it reads as an app.
- Non-invasive: no backdrop, page stays tappable. Ignore it → it sits quietly. ✕ or install clears it.
- **Android:** primary button **[Instalar]** (`↓` glyph). Tap → `deferredPrompt.prompt()`, await `userChoice`.
- **iOS:** an animated arrow pointing toward the browser Share control + two-step hint.
- **Success:** on `appinstalled`, swap to a brief success toast (*"Atlas instalado ✓"*), then unmount; set installed flag so it never returns.

### Copy (i18n by `navigator.language`, ES default when `es*`)

- Android title (ES): **"Instala la app de Atlas"** · sub: *"Gratis, sin tienda. Ábrelo desde tu inicio."* · button: **"Instalar"**
- Android (EN): **"Install the Atlas app"** · *"Free, no store. Opens from your home screen."* · **"Install"**
- iOS (ES): **"Añade Atlas a tu inicio"** · *"Toca Compartir ⎋ → 'Añadir a pantalla de inicio'."**
- iOS (EN): **"Add Atlas to your home screen"** · *"Tap Share ⎋ → 'Add to Home Screen'."*
- Success (ES/EN): **"Atlas instalado ✓" / "Atlas installed ✓"**

### Telemetry (reuse `lib/telemetry.ts` → `POST /api/v2/telemetry`)

Fire via existing `track()` / `trackOnce()`; best-effort, never blocks UI:
- `install_prompt_shown` (`trackOnce`) — props `{ platform: 'android'|'ios' }`
- `install_prompt_accepted` — Android, after `.prompt()` resolves — props `{ outcome: 'accepted'|'dismissed' }` (from `userChoice`)
- `install_prompt_dismissed` — user hit ✕ — props `{ platform }`
- `install_prompt_ios_hint_shown` (`trackOnce`)
- `app_installed` — on `appinstalled` event
Funnel readable later via SQL over `telemetry_events` (`event LIKE 'install_prompt_%'`). No dashboard in v1.

### Manifest richer-install (Android app-store-style dialog)

In `vite.config.ts` `manifest`, add:
```ts
screenshots: [
  { src: 'screenshot-brief-narrow.png', sizes: '<WxH>', type: 'image/png', form_factor: 'narrow' },
  // optional 2nd: threads/map narrow shot
],
```
`description` is already set. With `screenshots` + `form_factor: narrow`, Chrome on
Android upgrades the install prompt to a card with preview images — the strongest
"this is a real downloadable app" signal. Screenshots captured from the mobile preview
at implementation time (or Pedro supplies branded ones).

## Error handling / edge cases

- `beforeinstallprompt` may never fire (criteria unmet, already installed, unsupported) → simply no Android toast; iOS path unaffected.
- Telemetry POST failure → swallowed (endpoint already returns 202 best-effort).
- localStorage unavailable (private mode) → treat as "never dismissed"; wrap access in try/catch, fail open to showing once.
- Chromium mobile also supports the native mini-infobar — we `preventDefault()` it so only our toast shows (no double prompt).
- SSR/no-window guard not needed (Vite SPA, client-only), but access `navigator`/`window` inside effects.

## Testing

- **`frontend-v2/src/lib/installPrompt.test.ts`** (vitest) — table tests on `shouldShowInstallPrompt`:
  installed→false, desktop→false, in-app webview→false, dismissed-yesterday→false,
  dismissed-31-days-ago→true, iOS-fresh→true, Android-with-event→true, Android-no-event→false.
- **`detectPlatform`** — UA fixtures: iPhone Safari, Android Chrome, FB in-app, desktop, installed-standalone.
- Component smoke: renders nothing when gate fails; renders toast when it passes (jsdom).
- `npm run build` must pass (Vite `tsc -b` strict). Run full vitest.

## Deploy

Frontend-only → Vercel. No Fly, no migration. Verify on a real phone (Android 1-tap +
iPhone hint) after deploy; eyeball the slide-in above the tab bar on 375px.

## Open implementation detail (not a blocker)

- Exact `sizes` for the screenshot(s) filled once captured.
- Whether to also fire the reveal on "opened a thread" as a third engagement signal —
  start with timeout-or-scroll; add thread-open only if conversion looks low.
