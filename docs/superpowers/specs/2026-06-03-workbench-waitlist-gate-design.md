# Workbench Early-Access Waitlist Gate — Design

**Date:** 2026-06-03
**Status:** Approved design, ready for implementation plan
**Branch:** `v3-intel-layer`
**Track:** Product (public MVP launch)

## Context

The Atlas Workbench (interactive investigation workspace) is the surface chosen
to lead the public MVP launch next week. It is currently gated in production
behind a static blurred "Coming soon" overlay with a `mailto:` early-access link
and a `Support Atlas` (ko-fi) link.

`mailto:` is a weak launch signal: it depends on the visitor having a configured
mail client, captures nothing measurable, and cannot count interest. This design
replaces it with a real, measurable early-access waitlist while keeping the
Workbench itself gated (Option A — the gate becomes interactive; the Workbench is
not yet opened hands-on).

This is consistent with the Atlas pivot documented in
[[2026-06-03-research-model-product-roadmap]]: Atlas exists to expose how
information moves, where it comes from, and how it changes over time — not to
classify true/false. The waitlist copy reflects that stance, and the counter
shows **real data only** (no inflated/random numbers) because faking interest on
an anti-disinformation product contradicts its own thesis.

Related context:
- [[2026-06-03-frontend-surface-data-map]] — current surface/data ownership.
- [[Frontend Product Surfaces]] — MOC this spec is linked from.
- [[PROJECT_INVENTORY]] — generated endpoint/frontend map (regenerate after).

## Scope

In scope:
- A `workbench_waitlist` table (Supabase/Postgres, RLS-locked).
- A backend `POST /api/v2/waitlist` + `GET /api/v2/waitlist/count`.
- An interactive overlay replacing the static gate in
  `InteractiveWorkspace.tsx`, with inline email capture, optional use-case, real
  waitlist count, success/error states, and a separate support CTA.

Out of scope (explicitly deferred):
- Opening the Workbench hands-on (Option B).
- Platform-wide language/positioning coherence pass (landing + walkthrough +
  microcopy) — its own dedicated brainstorm/spec after this ships.
- Email delivery / automated follow-up. The waitlist only captures contacts; any
  outreach is manual for the MVP.
- Captcha. MVP uses a honeypot + soft IP rate limit only.

## Data model

Migration `backend/migrations/051_workbench_waitlist.sql` (latest applied is
`050`):

```sql
CREATE TABLE IF NOT EXISTS workbench_waitlist (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    use_case    TEXT NULL,
    referrer    TEXT NULL,            -- server-derived (Referer/origin), not user field
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT workbench_waitlist_email_unique UNIQUE (email)
);

ALTER TABLE workbench_waitlist ENABLE ROW LEVEL SECURITY;
-- No public policies: only the backend service role reads/writes.
```

Notes:
- User-facing fields are minimal: `email` + `use_case`. `referrer` is captured
  server-side only (best-effort) and is never required.
- `email` is normalized to trimmed lowercase before insert.
- `UNIQUE(email)` makes re-submission idempotent (no duplicate rows).
- RLS locked like `dynamic_topics`; emails are never exposed by any public GET.

## Backend

New router (or addition to an existing `app/routers/` module), following the
existing FastAPI + asyncpg patterns:

### `POST /api/v2/waitlist`

Request:
```json
{ "email": "a@b.com", "use_case": "track how a story spreads", "company": "" }
```

- `company` is a **honeypot**: a hidden field the real UI leaves empty. If it is
  non-empty, respond `200 { "ok": true }` without writing (silently drop bots).
- Validate `email` with a conservative regex and length bound (<= 320 chars).
  Invalid → `422`.
- `use_case` optional, trimmed, length-capped (e.g. <= 500 chars).
- Insert `ON CONFLICT (email) DO NOTHING`.
- Soft per-IP rate limit using the existing Redis cache pattern (e.g. max ~5
  submits / 10 min / IP); on exceed respond `429`.
- Response: `200 { "ok": true }`. Do **not** leak whether the email already
  existed.

### `GET /api/v2/waitlist/count`

- Returns `{ "count": <int> }` — aggregate row count only, never emails.
- Cacheable (short TTL, e.g. 60s) via the existing Redis pattern.
- Public.

## Frontend

Replace the static overlay block at `InteractiveWorkspace.tsx` (currently the
`lockedForPublicPreview` overlay) with an interactive panel. The
`shouldLockWorkspacePreview()` gate logic in `InvestigationWorkspace.tsx` is
unchanged.

States:

1. **Form (default).**
   - Kicker: `Workbench · beta privada`.
   - Headline: `Sé de los primeros en usarlo`.
   - Body copy aligned to the pivot: Atlas does not tell you what to believe — it
     shows how information moves, where it comes from, and how it changes. The
     Workbench is where you assemble that investigation.
   - Real waitlist count: fetched from `GET /api/v2/waitlist/count`. Shown as
     `Ya van N en la lista` only when `N >= 25`; below that, show qualitative copy
     (`Beta privada · primeros accesos`) instead of a small number. Honest — no
     inflation, just not leading with a weak count.
   - Inputs: `email` (required) + `use_case` (optional textarea, "¿para qué lo
     usarías?") + hidden honeypot `company`.
   - Primary button: `Pedir acceso` → `POST /api/v2/waitlist`.
2. **Success.** `Estás dentro · te escribimos pronto.` No `mailto:`.
3. **Error.** Inline, retryable message; does not lose typed input.

Below the form, visually separated:
- `Apoyar Atlas` (ko-fi, existing link) — for people who care about the project
  /information directly, distinct from requesting access.
- `Keep exploring` ghost button (existing) — closes the overlay, lets the visitor
  continue using the rest of the product.

`mailto:` is removed entirely.

Frontend talks to the backend through relative `fetch('/api/v2/...')` exactly
like the existing surfaces — **no `supabase-js` dependency, no anon key in the
frontend.**

## Error handling

- Invalid email → inline form error, no network noise.
- Network failure on submit → error state, input preserved, retry allowed.
- `GET count` failure → fall back to qualitative copy (never block the form).
- Honeypot hit → silent success, no write.
- Rate-limited (`429`) → friendly "demasiados intentos, intenta en un momento".

## Testing

Backend:
- valid insert writes one row;
- invalid email → `422`;
- duplicate email → idempotent (one row, `200`);
- honeypot non-empty → `200`, zero rows written;
- `count` returns aggregate and never returns emails.

Frontend:
- `npm run build` (Vite `tsc -b`, stricter than `tsc --noEmit`) must pass before
  push;
- focused test for the submit happy path and error path if the local Vitest
  environment is stable (it has hung previously — see [[STATUS]]); otherwise rely
  on the production browser smoke.

Production smoke after deploy:
- submit a real email → confirm one new row in `workbench_waitlist`;
- confirm `GET /api/v2/waitlist/count` increments;
- confirm overlay success state and that the Workbench stays gated.

## Deployment order

1. Apply migration via Supabase MCP.
2. Deploy backend (`scripts/deploy-fly-api.sh`, API process group).
3. Verify Fly `/health` + the two new endpoints.
4. Build + deploy frontend (Vercel) once `npm run build` passes.
5. Browser smoke in production.
6. Regenerate `PROJECT_INVENTORY.md` and update [[Frontend Product Surfaces]].

## Obsidian connections

- Linked from [[Frontend Product Surfaces]] (Primary surfaces / launch section).
- Linked from [[000-INDEX]].
- Upstream rationale: [[2026-06-03-research-model-product-roadmap]].
- Surface map: [[2026-06-03-frontend-surface-data-map]].
- Follow-up track: platform language/positioning coherence pass (to be specced).
