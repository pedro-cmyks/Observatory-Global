# Accounts + Investigation Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Free user accounts (Supabase Auth magic-link) that sync Workbench investigations off device-bound localStorage — the missing market primitive: cross-device retention + a measurable L3 funnel. Nothing gets paywalled.

**Architecture:** Local-first. Anonymous users keep pure localStorage (preserves the W0-D5 privacy decision: the server never sees an anonymous user's pins). Signing in is the explicit opt-in to sync: the frontend talks DIRECTLY to Supabase (`@supabase/supabase-js` + RLS on a `user_investigations` table storing each Investigation as a jsonb blob, last-write-wins by `updatedAt`). The Fly backend is untouched — auth, storage and isolation all ride on Supabase primitives we already pay for. Telemetry gains a pseudonymous `user_id` via existing `props` (zero backend change).

**Tech Stack:** Supabase Auth (email OTP/magic link) · `@supabase/supabase-js@^2` · RLS · React context · vitest.

**Deliberate non-goals (YAGNI):** no paywall/billing, no OAuth providers, no per-pin CRDT merging (whole-investigation LWW), no backend JWT middleware (nothing server-side is gated yet), no profile page.

---

## Context for an engineer with zero repo knowledge

- Frontend: `frontend-v2/` (React 18 + Vite + vanilla CSS; **no Tailwind in dashboard components**). Tests: `npx vitest run`. Build gate: `npm run build` (tsc -b, stricter than tsc --noEmit).
- The Workbench store is `frontend-v2/src/lib/workbench.ts` — localStorage key `atlas.workbench.v1`, shape `{ investigations: Investigation[] }`. `Investigation` carries `id, title, query?, createdAt, updatedAt, pins[], citations[], claims[], trail[]`. Every mutation funnels through the module-private `writeStore(store)`.
- Telemetry: `frontend-v2/src/lib/telemetry.ts` — `track(event, props)` fire-and-forget POST to `/api/v2/telemetry`; `props` is an open jsonb on the backend.
- DB: Supabase Postgres. Migrations are **raw SQL files** in `backend/migrations/` applied via psql/SQL editor (NOT alembic). Next free number: **081** (verify with `ls backend/migrations/ | tail -1` before applying).
- Env: Vite exposes `import.meta.env.VITE_*`. There is no `.env` in `frontend-v2/` today — local dev uses `frontend-v2/.env.local` (gitignored by Vite's defaults; verify `.gitignore`), prod uses Vercel project env vars.
- CSS: theme via CSS custom properties (ThemeContext). Use existing var names (`--panel-bg`, `--text-primary` style tokens — copy from a neighboring component's CSS).

## Manual prerequisites (Pedro, Supabase dashboard — before Task 5 can be end-to-end verified)

1. Supabase → Authentication → Providers → **Email**: enable, with "magic link / OTP" (no password).
2. Authentication → URL Configuration: add site URLs `http://localhost:3000` (dev) and the Vercel prod origin (`https://observatory-global.vercel.app`).
3. Project Settings → API: copy **Project URL** and **anon public key** →
   - `frontend-v2/.env.local`: `VITE_SUPABASE_URL=...` and `VITE_SUPABASE_ANON_KEY=...`
   - Vercel project env: same two vars.
   The anon key is safe to expose (RLS is the guard).

Until these exist, the UI degrades honestly: `supabaseClient()` returns null and the Account section renders "Sync unavailable — not configured".

---

### Task 1: Migration 081 — `user_investigations` with RLS

**Files:**
- Create: `backend/migrations/081_user_investigations.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 081_user_investigations.sql
-- Accounts v1 (2026-07-18 plan): server-side store for a SIGNED-IN user's
-- Workbench investigations. Local-first: anonymous users never write here
-- (preserves the W0-D5 decision — the server only ever sees anonymous
-- telemetry for them). One row per investigation, whole Investigation JSON
-- as payload, last-write-wins by updated_at. Access is DIRECT from the
-- frontend via supabase-js + RLS — the Fly API is not in this path.
--
-- Reversible: DROP TABLE user_investigations;

CREATE TABLE IF NOT EXISTS user_investigations (
    user_id          UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    investigation_id TEXT        NOT NULL,
    payload          JSONB       NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,   -- the Investigation's own updatedAt (LWW key)
    deleted          BOOLEAN     NOT NULL DEFAULT FALSE,  -- tombstone, never hard-delete
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, investigation_id)
);

ALTER TABLE user_investigations ENABLE ROW LEVEL SECURITY;

-- Owner-only, all verbs. auth.uid() comes from the Supabase JWT.
CREATE POLICY user_investigations_select ON user_investigations
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY user_investigations_insert ON user_investigations
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY user_investigations_update ON user_investigations
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON user_investigations TO authenticated;
-- (no DELETE grant: tombstones only; no anon grant: signed-in only)
```

- [ ] **Step 2: Verify 081 is the next free number**

Run: `ls backend/migrations/ | tail -2`
Expected: `080_label_court.sql` is the last entry. If 081 exists, renumber this file to the next free.

- [ ] **Step 3: Apply to Supabase**

Run (env from `/Users/pedro/AtlasLocalWorker/.env`):
```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/081_user_investigations.sql
```
Expected: `CREATE TABLE`, `ALTER TABLE`, `CREATE POLICY` ×3, `GRANT`.

- [ ] **Step 4: Verify RLS is on**

```bash
psql "$DATABASE_URL" -t -c "SELECT relrowsecurity FROM pg_class WHERE relname='user_investigations'"
```
Expected: `t`

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/081_user_investigations.sql
git commit -m "feat(accounts): mig 081 user_investigations (RLS, tombstones, LWW)"
```

---

### Task 2: Supabase client singleton (graceful when unconfigured)

**Files:**
- Create: `frontend-v2/src/lib/supabaseClient.ts`

- [ ] **Step 1: Install the dependency**

Run (in `frontend-v2/`): `npm install @supabase/supabase-js@^2`
Expected: package.json gains the dep; lockfile updates.

- [ ] **Step 2: Write the module**

```ts
// Supabase client for ACCOUNTS + investigation sync only (accounts-v1 plan,
// docs/superpowers/plans/2026-07-18-accounts-sync.md). All product data
// still flows through the Fly API — this client exists solely for Auth and
// the RLS-guarded user_investigations table.
//
// Graceful degradation: when the env vars are absent (local dev without
// keys, forks), supabaseClient() returns null and every accounts surface
// renders its honest "not configured" state. Never throw at import time.

import { createClient, type SupabaseClient } from '@supabase/supabase-js'

let cached: SupabaseClient | null | undefined

export function supabaseClient(): SupabaseClient | null {
  if (cached !== undefined) return cached
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
  const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined
  cached = url && anon ? createClient(url, anon) : null
  return cached
}

/** Test seam: reset the memoized client (vitest re-imports don't). */
export function _resetSupabaseClient(): void {
  cached = undefined
}
```

- [ ] **Step 3: Build gate**

Run: `npm run build`
Expected: green (proves the dep + module typecheck).

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json src/lib/supabaseClient.ts
git commit -m "feat(accounts): supabase-js client singleton, null when unconfigured"
```

---

### Task 3: Workbench change hook (the sync trigger)

**Files:**
- Modify: `frontend-v2/src/lib/workbench.ts` (the `writeStore` function, ~line 165)
- Test: `frontend-v2/src/lib/workbench.test.ts` (append)

- [ ] **Step 1: Write the failing test** (append to `workbench.test.ts`)

```ts
describe('onWorkbenchChange (accounts-v1 sync hook)', () => {
  it('fires subscribers after any store mutation, with the fresh list', () => {
    localStorage.clear()
    const seen: number[] = []
    const off = onWorkbenchChange((invs) => seen.push(invs.length))
    createInvestigation('sync hook test')
    expect(seen.length).toBeGreaterThan(0)
    expect(seen[seen.length - 1]).toBe(1)
    off()
    createInvestigation('after unsubscribe')
    expect(seen[seen.length - 1]).toBe(1) // did not fire again
  })

  it('a throwing subscriber never breaks the store write', () => {
    localStorage.clear()
    const off = onWorkbenchChange(() => { throw new Error('boom') })
    expect(() => createInvestigation('still works')).not.toThrow()
    expect(listInvestigations()).toHaveLength(1)
    off()
  })
})
```

Add `onWorkbenchChange` to the existing import list at the top of the test file.

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/lib/workbench.test.ts`
Expected: FAIL — `onWorkbenchChange is not a function` (not exported).

- [ ] **Step 3: Implement** — in `workbench.ts`, above `writeStore`:

```ts
// ── accounts-v1 sync hook ────────────────────────────────────────────────
// Every mutation funnels through writeStore; subscribers (the sync engine)
// get the fresh investigation list after each write. Subscribers must never
// break the store — errors are swallowed (sync is best-effort by design).
type WorkbenchListener = (investigations: Investigation[]) => void
const changeListeners = new Set<WorkbenchListener>()

export function onWorkbenchChange(cb: WorkbenchListener): () => void {
  changeListeners.add(cb)
  return () => changeListeners.delete(cb)
}
```

And at the END of `writeStore` (inside the function, after `localStorage.setItem`, still inside the try or after it — after the try/catch block so quota failures still notify the in-memory state):

```ts
  for (const cb of changeListeners) {
    try { cb(store.investigations) } catch { /* sync must never break the store */ }
  }
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/lib/workbench.test.ts`
Expected: PASS (all existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/lib/workbench.ts src/lib/workbench.test.ts
git commit -m "feat(accounts): onWorkbenchChange store hook for the sync engine"
```

---

### Task 4: Merge logic + sync engine (TDD the merge; engine is thin I/O)

**Files:**
- Create: `frontend-v2/src/lib/investigationSync.ts`
- Test: `frontend-v2/src/lib/investigationSync.test.ts`

- [ ] **Step 1: Write the failing merge tests**

```ts
import { describe, it, expect } from 'vitest'
import { mergeInvestigationSets, type RemoteRow } from './investigationSync'
import type { Investigation } from './workbench'

function inv(id: string, updatedAt: string, title = id): Investigation {
  return { id, title, createdAt: '2026-07-01T00:00:00Z', updatedAt,
           pins: [], citations: [], claims: [], trail: [] } as unknown as Investigation
}
function row(id: string, updatedAt: string, deleted = false): RemoteRow {
  return { investigation_id: id, payload: inv(id, updatedAt), updated_at: updatedAt, deleted }
}

describe('mergeInvestigationSets (LWW by updatedAt, tombstones win over stale)', () => {
  it('local-only investigations are pushed', () => {
    const r = mergeInvestigationSets([inv('a', '2026-07-18T10:00:00Z')], [], {})
    expect(r.toPush.map(i => i.id)).toEqual(['a'])
    expect(r.merged.map(i => i.id)).toEqual(['a'])
  })

  it('remote-only investigations are pulled into merged', () => {
    const r = mergeInvestigationSets([], [row('b', '2026-07-18T09:00:00Z')], {})
    expect(r.merged.map(i => i.id)).toEqual(['b'])
    expect(r.toPush).toHaveLength(0)
  })

  it('newer local wins and is pushed; newer remote wins and replaces local', () => {
    const local = [inv('a', '2026-07-18T12:00:00Z'), inv('b', '2026-07-18T08:00:00Z')]
    const remote = [row('a', '2026-07-18T11:00:00Z'), row('b', '2026-07-18T09:00:00Z')]
    const r = mergeInvestigationSets(local, remote, {})
    expect(r.toPush.map(i => i.id)).toEqual(['a'])          // local a newer
    expect(r.merged.find(i => i.id === 'b')!.updatedAt).toBe('2026-07-18T09:00:00Z') // remote b newer
  })

  it('a remote tombstone removes the stale local copy', () => {
    const r = mergeInvestigationSets([inv('a', '2026-07-18T08:00:00Z')],
                                     [row('a', '2026-07-18T09:00:00Z', true)], {})
    expect(r.merged).toHaveLength(0)
    expect(r.toPush).toHaveLength(0)
  })

  it('a local edit NEWER than the tombstone resurrects (pushes) it', () => {
    const r = mergeInvestigationSets([inv('a', '2026-07-18T10:00:00Z')],
                                     [row('a', '2026-07-18T09:00:00Z', true)], {})
    expect(r.merged.map(i => i.id)).toEqual(['a'])
    expect(r.toPush.map(i => i.id)).toEqual(['a'])
  })

  it('previously-pushed id now missing locally → tombstone it remotely', () => {
    const pushed = { a: '2026-07-18T08:00:00Z' }
    const r = mergeInvestigationSets([], [row('a', '2026-07-18T08:00:00Z')], pushed)
    expect(r.toTombstone).toEqual(['a'])
    expect(r.merged).toHaveLength(0)
  })

  it('remote id never seen locally and never pushed is NOT tombstoned (other device)', () => {
    const r = mergeInvestigationSets([], [row('c', '2026-07-18T08:00:00Z')], {})
    expect(r.toTombstone).toHaveLength(0)
    expect(r.merged.map(i => i.id)).toEqual(['c'])
  })

  it('equal timestamps: no push, no pull churn', () => {
    const t = '2026-07-18T08:00:00Z'
    const r = mergeInvestigationSets([inv('a', t)], [row('a', t)], {})
    expect(r.toPush).toHaveLength(0)
    expect(r.merged.map(i => i.id)).toEqual(['a'])
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run src/lib/investigationSync.test.ts`
Expected: FAIL — module has no exports.

- [ ] **Step 3: Implement**

```ts
// Investigation sync (accounts-v1). LOCAL-FIRST: localStorage stays the
// source the UI reads; the server copy is backup + cross-device transport.
// Whole-investigation last-write-wins by updatedAt (per-pin merging is a
// deliberate non-goal). Tombstones (deleted=true) instead of hard deletes;
// a local edit NEWER than the tombstone resurrects the investigation.
//
// The engine keeps a pushed-marker map in localStorage (atlas.sync.v1)
// recording {investigationId: updatedAt-last-pushed} — how we distinguish
// "deleted locally" (tombstone remotely) from "created on another device"
// (pull it).

import type { Investigation } from './workbench'
import { listInvestigations, onWorkbenchChange } from './workbench'
import { supabaseClient } from './supabaseClient'
import { track } from './telemetry'

export interface RemoteRow {
  investigation_id: string
  payload: Investigation
  updated_at: string
  deleted: boolean
}

export interface MergeResult {
  merged: Investigation[]     // what localStorage should now hold
  toPush: Investigation[]     // local copies newer than remote (or new)
  toTombstone: string[]       // ids to mark deleted=true remotely
}

const SYNC_KEY = 'atlas.sync.v1'

type PushedMap = Record<string, string> // investigationId -> updatedAt last pushed

export function readPushedMap(): PushedMap {
  try { return JSON.parse(localStorage.getItem(SYNC_KEY) || '{}') } catch { return {} }
}
function writePushedMap(m: PushedMap): void {
  try { localStorage.setItem(SYNC_KEY, JSON.stringify(m)) } catch { /* best-effort */ }
}

export function mergeInvestigationSets(
  local: Investigation[],
  remote: RemoteRow[],
  pushed: PushedMap,
): MergeResult {
  const byIdLocal = new Map(local.map(i => [i.id, i]))
  const byIdRemote = new Map(remote.map(r => [r.investigation_id, r]))
  const merged: Investigation[] = []
  const toPush: Investigation[] = []
  const toTombstone: string[] = []

  // Walk the union of ids.
  const ids = new Set([...byIdLocal.keys(), ...byIdRemote.keys()])
  for (const id of ids) {
    const l = byIdLocal.get(id)
    const r = byIdRemote.get(id)
    if (l && !r) { merged.push(l); toPush.push(l); continue }          // local-only
    if (!l && r) {
      if (r.deleted) continue                                          // deleted everywhere
      if (pushed[id]) { toTombstone.push(id); continue }               // we deleted it locally
      merged.push(r.payload); continue                                 // other-device investigation
    }
    // both exist
    const lNewer = l!.updatedAt > r!.updated_at
    if (r!.deleted) {
      if (lNewer) { merged.push(l!); toPush.push(l!) }                 // resurrect
      continue                                                         // tombstone wins
    }
    if (lNewer) { merged.push(l!); toPush.push(l!) }
    else merged.push(r!.payload)                                       // remote newer or equal
  }
  return { merged, toPush, toTombstone }
}

// ── engine (thin I/O over the pure merge) ────────────────────────────────

let debounceTimer: ReturnType<typeof setTimeout> | null = null
let engineOff: (() => void) | null = null

/** Full bidirectional sync. Called on sign-in and after local mutations. */
export async function syncNow(userId: string): Promise<{ pushed: number; pulled: boolean } | null> {
  const sb = supabaseClient()
  if (!sb) return null
  const { data, error } = await sb.from('user_investigations')
    .select('investigation_id, payload, updated_at, deleted')
  if (error) { track('sync_error', { stage: 'pull', message: error.message }); return null }

  const local = listInvestigations()
  const pushedMap = readPushedMap()
  const { merged, toPush, toTombstone } = mergeInvestigationSets(local, (data ?? []) as RemoteRow[], pushedMap)

  // Adopt the merged set locally (import path writes through the store so the
  // UI and the change-hook both see it; loop-guard: identical JSON = no write).
  adoptMerged(merged)

  if (toPush.length > 0) {
    const rows = toPush.map(i => ({
      user_id: userId, investigation_id: i.id, payload: i,
      updated_at: i.updatedAt, deleted: false,
    }))
    const { error: pushErr } = await sb.from('user_investigations').upsert(rows)
    if (pushErr) track('sync_error', { stage: 'push', message: pushErr.message })
    else for (const i of toPush) pushedMap[i.id] = i.updatedAt
  }
  for (const id of toTombstone) {
    await sb.from('user_investigations')
      .update({ deleted: true, updated_at: new Date().toISOString() })
      .eq('investigation_id', id)
    delete pushedMap[id]
  }
  writePushedMap(pushedMap)
  track('sync_done', { pushed: toPush.length, tombstoned: toTombstone.length, user_id: userId })
  return { pushed: toPush.length, pulled: true }
}

/** Replace the local store with the merged set — only when it differs. */
function adoptMerged(merged: Investigation[]): void {
  const current = JSON.stringify(listInvestigations())
  const next = JSON.stringify(merged)
  if (current === next) return
  try {
    localStorage.setItem('atlas.workbench.v1', JSON.stringify({ investigations: merged }))
  } catch { /* quota: UI keeps the in-memory copy */ }
}

/** Arm continuous sync for a signed-in session; returns a disarm fn. */
export function startSyncEngine(userId: string): () => void {
  stopSyncEngine()
  void syncNow(userId)                        // initial pull+merge+push
  engineOff = onWorkbenchChange(() => {       // debounce local mutations
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => { void syncNow(userId) }, 3000)
  })
  return stopSyncEngine
}

export function stopSyncEngine(): void {
  if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  if (engineOff) { engineOff(); engineOff = null }
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/lib/investigationSync.test.ts`
Expected: PASS (8/8).

- [ ] **Step 5: Full suite + build**

Run: `npx vitest run && npm run build`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/lib/investigationSync.ts src/lib/investigationSync.test.ts
git commit -m "feat(accounts): LWW merge + sync engine (TDD, tombstones, pushed-markers)"
```

---

### Task 5: AuthContext (session state + magic link + telemetry identity)

**Files:**
- Create: `frontend-v2/src/contexts/AuthContext.tsx`
- Modify: `frontend-v2/src/lib/telemetry.ts` (add `setTelemetryUser`)

- [ ] **Step 1: Extend telemetry** — in `telemetry.ts`, below `sessionId()`:

```ts
// accounts-v1: pseudonymous identity. When a user signs in, every event
// carries their Supabase user id in props (an opaque uuid — no email/PII).
// This is the funnel/retention apparatus the monetization gate requires.
let telemetryUserId: string | null = null
export function setTelemetryUser(id: string | null): void { telemetryUserId = id }
```

And in `track()`, change the body line to merge it in:

```ts
      body: JSON.stringify({ events: [{ event, session_id: sessionId(),
        props: telemetryUserId ? { ...props, user_id: telemetryUserId } : props }] }),
```

- [ ] **Step 2: Write AuthContext**

```tsx
// AuthContext (accounts-v1). Session state + magic-link sign-in + the sync
// engine lifecycle. Anonymous = no session = pure localStorage (W0-D5
// privacy stance unchanged); signing in is the explicit opt-in to sync.
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabaseClient } from '../lib/supabaseClient'
import { startSyncEngine, stopSyncEngine } from '../lib/investigationSync'
import { setTelemetryUser, track } from '../lib/telemetry'

interface AuthState {
  configured: boolean          // env present — accounts UI renders at all
  session: Session | null
  email: string | null
  sendMagicLink: (email: string) => Promise<{ ok: boolean; message: string }>
  signOut: () => Promise<void>
}

const AuthCtx = createContext<AuthState>({
  configured: false, session: null, email: null,
  sendMagicLink: async () => ({ ok: false, message: 'not configured' }),
  signOut: async () => {},
})

export function useAuth(): AuthState { return useContext(AuthCtx) }

export function AuthProvider({ children }: { children: ReactNode }) {
  const sb = supabaseClient()
  const [session, setSession] = useState<Session | null>(null)

  useEffect(() => {
    if (!sb) return
    void sb.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: sub } = sb.auth.onAuthStateChange((_evt, s) => setSession(s))
    return () => sub.subscription.unsubscribe()
  }, [sb])

  // Identity + sync lifecycle follow the session.
  useEffect(() => {
    const uid = session?.user?.id ?? null
    setTelemetryUser(uid)
    if (uid) { track('sign_in'); const off = startSyncEngine(uid); return off }
    stopSyncEngine()
  }, [session?.user?.id])

  const sendMagicLink = async (email: string) => {
    if (!sb) return { ok: false, message: 'not configured' }
    const { error } = await sb.auth.signInWithOtp({
      email, options: { emailRedirectTo: window.location.origin },
    })
    return error ? { ok: false, message: error.message }
                 : { ok: true, message: 'Check your email for the sign-in link.' }
  }

  const signOut = async () => {
    if (!sb) return
    stopSyncEngine()
    await sb.auth.signOut()
    // localStorage investigations REMAIN — local-first; sync just stops.
  }

  return (
    <AuthCtx.Provider value={{
      configured: !!sb, session, email: session?.user?.email ?? null,
      sendMagicLink, signOut,
    }}>{children}</AuthCtx.Provider>
  )
}
```

- [ ] **Step 3: Build gate**

Run: `npm run build`
Expected: green.

- [ ] **Step 4: Commit**

```bash
git add src/contexts/AuthContext.tsx src/lib/telemetry.ts
git commit -m "feat(accounts): AuthContext (magic link, sync lifecycle, telemetry identity)"
```

---

### Task 6: Account UI in the Workbench (sign-in form + synced state)

**Files:**
- Create: `frontend-v2/src/components/AccountSection.tsx`
- Create: `frontend-v2/src/components/AccountSection.css`
- Modify: `frontend-v2/src/components/WorkbenchPanel.tsx` (render it in the sidebar, above the investigations list)
- Modify: `frontend-v2/src/main.tsx` (wrap with `<AuthProvider>`)

- [ ] **Step 1: Write the component**

```tsx
// AccountSection (accounts-v1): lives INSIDE the Workbench — contextually
// where sync matters ("your investigations, on any device"). Three states:
// not-configured (honest, hidden behind nothing), signed-out (email form),
// signed-in (email + sync badge + sign out). No product data is gated.
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './AccountSection.css'

export function AccountSection() {
  const { configured, session, email, sendMagicLink, signOut } = useAuth()
  const [draft, setDraft] = useState('')
  const [note, setNote] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!configured) return null   // env absent: accounts simply don't exist

  if (session) {
    return (
      <div className="account-section" data-signed-in>
        <span className="account-dot" aria-hidden />
        <span className="account-email" title={email ?? ''}>{email}</span>
        <span className="account-sync" data-tip="Investigations sync to your account — local copy stays on this device">synced</span>
        <button className="account-btn" onClick={() => void signOut()}>Sign out</button>
      </div>
    )
  }

  return (
    <div className="account-section">
      <p className="account-pitch">Sign in to keep investigations on every device. Free.</p>
      <form onSubmit={async (e) => {
        e.preventDefault()
        if (!draft.trim() || busy) return
        setBusy(true)
        const res = await sendMagicLink(draft.trim())
        setNote(res.message)
        setBusy(false)
      }}>
        <input className="account-input" type="email" required placeholder="you@example.com"
               value={draft} onChange={e => setDraft(e.target.value)} />
        <button className="account-btn" type="submit" disabled={busy}>
          {busy ? 'Sending…' : 'Send sign-in link'}
        </button>
      </form>
      {note && <p className="account-note">{note}</p>}
    </div>
  )
}
```

- [ ] **Step 2: Write the CSS** (`AccountSection.css` — copy the exact var names used by `WorkbenchPanel.css` for backgrounds/borders; the classes below assume the standard tokens)

```css
.account-section {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  font-size: 12px;
}
.account-pitch { margin: 0 0 6px; opacity: 0.75; width: 100%; }
.account-input {
  flex: 1; min-width: 0; padding: 5px 8px; font-size: 12px;
  background: var(--input-bg, rgba(255,255,255,0.05));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.12));
  color: inherit; border-radius: 4px;
}
.account-btn {
  padding: 5px 10px; font-size: 11px; cursor: pointer; border-radius: 4px;
  background: var(--accent-subtle, rgba(64,255,170,0.12));
  border: 1px solid var(--accent, #2ecc8f); color: inherit;
}
.account-note { margin: 4px 0 0; width: 100%; opacity: 0.8; }
.account-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent, #2ecc8f); }
.account-email { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.account-sync { font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.7; cursor: help; }
```

- [ ] **Step 3: Wire the provider** — in `main.tsx`, wrap the existing root component tree:

```tsx
import { AuthProvider } from './contexts/AuthContext'
// … inside the render, OUTSIDE Routes but inside any existing top providers:
<AuthProvider>
  {/* existing AppBriefKeepAlive / Routes tree unchanged */}
</AuthProvider>
```

(Locate the current top-level composition in `main.tsx` and wrap the outermost custom element; do not reorder anything else — the keep-alive shell must stay exactly where it is.)

- [ ] **Step 4: Mount in the Workbench sidebar** — in `WorkbenchPanel.tsx`, find the investigations sidebar header (the `LEFT investigations` column) and render `<AccountSection />` as its first child. Import at top:

```tsx
import { AccountSection } from './AccountSection'
```

- [ ] **Step 5: Build + full tests**

Run: `npx vitest run && npm run build`
Expected: green.

- [ ] **Step 6: Browser-verify all three states**

Run the dev server; open the Workbench:
1. WITHOUT env vars: no account section at all (configured=false).
2. Add `frontend-v2/.env.local` with the Supabase URL/anon key (manual prerequisite); restart dev; the email form renders.
3. Submit your email → "Check your email…"; click the magic link → signed-in chip + `synced` badge; `localStorage['atlas.sync.v1']` populates after a pin.

- [ ] **Step 7: Commit**

```bash
git add src/components/AccountSection.tsx src/components/AccountSection.css \
        src/components/WorkbenchPanel.tsx src/main.tsx
git commit -m "feat(accounts): sign-in UI in the Workbench + provider wiring"
```

---

### Task 7: End-to-end sync verification (two “devices”)

**Files:** none (verification task)

- [ ] **Step 1: Device A** — normal browser profile: sign in, create an investigation "Sync E2E", pin a receipt, wait >3s (debounce). Verify in Supabase:

```bash
psql "$DATABASE_URL" -t -c "SELECT investigation_id, updated_at, deleted FROM user_investigations ORDER BY synced_at DESC LIMIT 3"
```
Expected: a row whose payload is the "Sync E2E" investigation.

- [ ] **Step 2: Device B** — incognito window, same email magic link: after sign-in the Workbench lists "Sync E2E" WITH its pin (pulled+merged).

- [ ] **Step 3: Conflict** — edit the title on B; wait 3s; reload A → A shows B's title (remote newer wins).

- [ ] **Step 4: Tombstone** — delete the investigation on A (if a delete affordance exists; otherwise skip — deletion UI is out of scope); B after reload no longer lists it.

- [ ] **Step 5: Anonymous unchanged** — a THIRD incognito window, never signed in: Workbench works purely local; `user_investigations` gains no rows; no `sign_in` telemetry.

- [ ] **Step 6: Funnel check** — telemetry rows now carry `user_id` in props for the signed-in session:

```bash
psql "$DATABASE_URL" -t -c "SELECT props->>'user_id', event FROM research_pin_events WHERE props ? 'user_id' ORDER BY created_at DESC LIMIT 3" 2>/dev/null || echo "check the telemetry table name in app/routers/telemetry.py"
```

- [ ] **Step 7: Commit any doc-only notes + push**

```bash
git push origin v3-intel-layer
```

---

### Task 8: Weekly-read + docs

**Files:**
- Modify: `docs/superpowers/plans/2026-07-17-council-workplan.md` (add an "Accounts shipped" line under In-flight)
- Modify: `CLAUDE.md` (session block: accounts-v1 shipped, W0-D5 stance preserved, monetization still gated on score ≥70 + 4 weeks retention)

- [ ] **Step 1: Update both docs** with: what shipped, the local-first/tombstone design, the manual Supabase prerequisites, and the explicit note that NOTHING is paywalled — accounts are the measurement apparatus; the monetization gate (score ≥70, reliability ≥70, 4 clean weeks of retention) still stands.

- [ ] **Step 2: Commit + push**

```bash
git add docs/superpowers/plans/2026-07-17-council-workplan.md CLAUDE.md
git commit -m "docs(accounts): accounts-v1 shipped — measurement apparatus, monetization still gated"
git push origin v3-intel-layer
```

---

## Self-review notes

- **Spec coverage:** free accounts ✓ (Task 5-6) · off-localStorage sync ✓ (Task 1, 4) · retention/funnel measurement ✓ (Task 5 telemetry + Task 7 step 6) · nothing paywalled ✓ (explicit non-goal) · anonymous privacy preserved ✓ (Task 4 engine only runs with a session; Task 7 step 5 verifies).
- **Type consistency:** `RemoteRow`/`MergeResult`/`PushedMap` defined in Task 4 and only used there; `onWorkbenchChange` defined Task 3, consumed Task 4; `setTelemetryUser` defined Task 5 step 1, consumed Task 5 step 2.
- **Known seam:** `adoptMerged` writes `atlas.workbench.v1` directly (matching `STORE_KEY`) instead of a store API — acceptable v1; if `workbench.ts` ever changes its key, the sync module must follow (grep `atlas.workbench.v1`).
- **Deletion UI:** tombstone logic is implemented and tested, but if the Workbench has no delete-investigation affordance yet, Task 7 step 4 is skippable — the merge handles it whenever deletion ships.
