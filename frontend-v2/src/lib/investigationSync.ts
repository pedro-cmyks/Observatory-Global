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
  /** F2: ids whose REMOTE tombstone we adopted — their pushed-markers must be
   *  dropped, or a later resurrection from another device would be read as
   *  "deleted locally" and re-tombstoned by this device. */
  toForget: string[]
}

const SYNC_KEY = 'atlas.sync.v1'

type PushedMap = Record<string, string> // investigationId -> updatedAt last pushed

export function readPushedMap(): PushedMap {
  try {
    // n2: anything but a plain object (corrupt/hand-edited key) reads as empty.
    const parsed: unknown = JSON.parse(localStorage.getItem(SYNC_KEY) || '{}')
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return {}
    return parsed as PushedMap
  } catch { return {} }
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
  const toForget: string[] = []

  // Walk the union of ids.
  const ids = new Set([...byIdLocal.keys(), ...byIdRemote.keys()])
  for (const id of ids) {
    const l = byIdLocal.get(id)
    const r = byIdRemote.get(id)
    if (l && !r) { merged.push(l); toPush.push(l); continue }          // local-only
    if (!l && r) {
      if (r.deleted) { toForget.push(id); continue }                   // deleted everywhere
      if (pushed[id]) { toTombstone.push(id); continue }               // we deleted it locally
      merged.push(r.payload); continue                                 // other-device investigation
    }
    // both exist. F1: compare INSTANTS, not strings — Postgres re-serializes
    // timestamps ('…Z' written locally comes back '…+00:00' via PostgREST), so
    // a lexicographic compare reads local as forever-newer → perpetual re-push
    // churn. Ties → remote wins (no push).
    const lNewer = Date.parse(l!.updatedAt) > Date.parse(r!.updated_at)
    if (r!.deleted) {
      if (lNewer) { merged.push(l!); toPush.push(l!) }                 // resurrect
      else toForget.push(id)                                           // tombstone wins → adopted
      continue
    }
    if (lNewer) { merged.push(l!); toPush.push(l!) }
    else merged.push(r!.payload)                                       // remote newer or equal
  }
  return { merged, toPush, toTombstone, toForget }
}

// ── engine (thin I/O over the pure merge) ────────────────────────────────

let debounceTimer: ReturnType<typeof setTimeout> | null = null
let engineOff: (() => void) | null = null
// n1: in-flight guard — a syncNow that lands mid-run is coalesced into ONE
// follow-up run after the current one finishes (never two overlapping pulls
// racing the same marker map).
let syncing = false
let pendingUserId: string | null = null

/** Full bidirectional sync. Called on sign-in and after local mutations. */
export async function syncNow(userId: string): Promise<{ pushed: number; pulled: boolean } | null> {
  const sb = supabaseClient()
  if (!sb) return null
  if (syncing) { pendingUserId = userId; return null }
  syncing = true
  try {
    const { data, error } = await sb.from('user_investigations')
      .select('investigation_id, payload, updated_at, deleted')
    if (error) { track('sync_error', { stage: 'pull', message: error.message }); return null }

    const local = listInvestigations()
    const pushedMap = readPushedMap()
    const { merged, toPush, toTombstone, toForget } =
      mergeInvestigationSets(local, (data ?? []) as RemoteRow[], pushedMap)

    // F2: we adopted these remote tombstones — drop their markers so a later
    // resurrection from another device is pulled, not re-tombstoned.
    for (const id of toForget) delete pushedMap[id]

    // Adopt the merged set locally. NOTE: this deliberately BYPASSES the store
    // API (raw localStorage write) — see adoptMerged for why that bypass is the
    // sync loop guard.
    adoptMerged(merged)

    let pushFailed = false
    if (toPush.length > 0) {
      const rows = toPush.map(i => ({
        user_id: userId, investigation_id: i.id, payload: i,
        updated_at: i.updatedAt, deleted: false,
      }))
      const { error: pushErr } = await sb.from('user_investigations').upsert(rows)
      if (pushErr) { pushFailed = true; track('sync_error', { stage: 'push', message: pushErr.message }) }
      else for (const i of toPush) pushedMap[i.id] = i.updatedAt
    }

    // n3: an EMPTY local store alongside several pushed-markers looks like
    // localStorage corruption/eviction, not N deliberate deletions — skip the
    // mass tombstone (the account copy survives for a human look) and flag it.
    const massDeleteSuspect = local.length === 0 && Object.keys(pushedMap).length > 2
    let tombstoned = 0
    if (massDeleteSuspect && toTombstone.length > 0) {
      track('sync_error', { stage: 'guard', message: 'local empty, markers present — tombstone skipped' })
    } else {
      for (const id of toTombstone) {
        // F3: a failed tombstone must KEEP the marker — deleting it would make
        // the next sync pull the row back, silently resurrecting the user's
        // deletion.
        const { error: tombErr } = await sb.from('user_investigations')
          .update({ deleted: true, updated_at: new Date().toISOString() })
          .eq('investigation_id', id)
        if (tombErr) { track('sync_error', { stage: 'tombstone', message: tombErr.message }); continue }
        delete pushedMap[id]
        tombstoned += 1
      }
    }
    writePushedMap(pushedMap)
    // Success-shaped event only when the push actually succeeded (F3); the
    // tombstoned count reports what was WRITTEN, not what was attempted.
    if (!pushFailed) track('sync_done', { pushed: toPush.length, tombstoned, user_id: userId })
    return { pushed: toPush.length, pulled: true }
  } finally {
    syncing = false
    if (pendingUserId) {
      const uid = pendingUserId
      pendingUserId = null
      void syncNow(uid)   // the coalesced follow-up run
    }
  }
}

/** Replace the local store with the merged set — only when it differs.
 *
 * DELIBERATE raw-localStorage write, NOT the workbench store API: bypassing
 * `onWorkbenchChange` IS the loop guard. Routing this through `writeStore`
 * would notify the sync engine's own subscriber → 3s debounce → syncNow →
 * adoptMerged → … a permanent sync loop. The UI learns about pulled data via
 * the `atlas-workbench-pulled` DOM event instead (a pure re-render tick that
 * cannot re-enter sync). Seam: this must track workbench.ts STORE_KEY
 * ('atlas.workbench.v1') — grep for it if the key ever changes. */
function adoptMerged(merged: Investigation[]): void {
  const current = JSON.stringify(listInvestigations())
  const next = JSON.stringify(merged)
  if (current === next) return
  try {
    localStorage.setItem('atlas.workbench.v1', JSON.stringify({ investigations: merged }))
  } catch { return /* quota: UI keeps the in-memory copy; nothing changed */ }
  try {
    window.dispatchEvent(new CustomEvent('atlas-workbench-pulled'))
  } catch { /* non-DOM environment (tests) */ }
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
  // Sign-out mid-sync: a coalesced re-run queued during the in-flight run must
  // not fire after disarm with the dying session.
  pendingUserId = null
}
