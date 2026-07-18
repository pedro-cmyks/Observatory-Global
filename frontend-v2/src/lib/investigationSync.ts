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
