import { beforeEach, describe, expect, it, vi } from 'vitest'

// vitest runs in node: back localStorage with a Map (same seam as workbench.test.ts).
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

// F4b: adoptMerged announces pulled changes on window — capture the events.
const dispatched: string[] = []
vi.stubGlobal('window', {
  dispatchEvent: (e: Event) => { dispatched.push(e.type); return true },
})

// The engine's I/O seam: swap the Supabase client per test (null = unconfigured).
const holder = vi.hoisted(() => ({ sb: null as unknown }))
vi.mock('./supabaseClient', () => ({
  supabaseClient: () => holder.sb,
  _resetSupabaseClient: () => { holder.sb = null },
}))

// Telemetry is asserted on (sync_error stages) — mock it (workbench imports
// trackOnce from the same module, so the factory must provide both).
vi.mock('./telemetry', () => ({ track: vi.fn(), trackOnce: vi.fn() }))

import { mergeInvestigationSets, readPushedMap, stopSyncEngine, syncNow, type RemoteRow } from './investigationSync'
import { track } from './telemetry'
import type { Investigation } from './workbench'

beforeEach(() => {
  backing.clear()
  dispatched.length = 0
  holder.sb = null
  vi.mocked(track).mockClear()
})

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

describe('F1: LWW compares instants, not strings', () => {
  it('postgres-format timestamp of the same instant is not "newer" (no re-push churn)', () => {
    const r = mergeInvestigationSets(
      [inv('a', '2026-07-18T10:00:00.000Z')],
      [row('a', '2026-07-18T10:00:00+00:00')], {})
    expect(r.toPush).toHaveLength(0)               // tie → remote wins, nothing to push
    expect(r.merged.map(i => i.id)).toEqual(['a']) // no churn: the copy survives
  })
})

describe('F2: adopting a remote tombstone forgets the pushed-marker', () => {
  it('reports toForget for both tombstone-adoption paths', () => {
    const pushed = { a: '2026-07-18T08:00:00Z' }
    // no local copy left, remote tombstone (deleted-everywhere path)
    const r1 = mergeInvestigationSets([], [row('a', '2026-07-18T09:00:00Z', true)], pushed)
    expect(r1.toForget).toEqual(['a'])
    expect(r1.toTombstone).toHaveLength(0)
    // stale local copy, remote tombstone wins (both-exist path)
    const r2 = mergeInvestigationSets([inv('a', '2026-07-18T08:00:00Z')],
                                      [row('a', '2026-07-18T09:00:00Z', true)], pushed)
    expect(r2.toForget).toEqual(['a'])
    expect(r2.merged).toHaveLength(0)
  })

  it("after forgetting, another device's resurrection is pulled, NOT tombstoned", () => {
    // marker was forgotten in the previous sync → resurrected remote row pulls
    const r = mergeInvestigationSets([], [row('a', '2026-07-18T10:00:00Z')], {})
    expect(r.toTombstone).toHaveLength(0)
    expect(r.merged.map(i => i.id)).toEqual(['a'])
  })

  it('syncNow drops the marker when the tombstone is adopted (engine consumption)', async () => {
    localStorage.setItem('atlas.sync.v1', JSON.stringify({ a: '2026-07-18T08:00:00Z' }))
    holder.sb = {
      from: () => ({
        select: async () => ({ data: [row('a', '2026-07-18T09:00:00Z', true)], error: null }),
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => ({ error: null }) }),
      }),
    }
    await syncNow('user-1')
    expect(readPushedMap()).toEqual({})   // marker forgotten → no future false tombstone
  })
})

describe('F3: tombstone write failures are honest', () => {
  it('a failed tombstone update keeps the pushed-marker (own deletion not resurrected)', async () => {
    localStorage.setItem('atlas.sync.v1', JSON.stringify({ a: '2026-07-18T08:00:00Z' }))
    holder.sb = {
      from: () => ({
        select: async () => ({ data: [row('a', '2026-07-18T08:00:00Z')], error: null }),
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => ({ error: { message: 'boom' } }) }),
      }),
    }
    await syncNow('user-1')
    // marker retained → next sync retries the tombstone instead of pulling the row back
    expect(readPushedMap()).toEqual({ a: '2026-07-18T08:00:00Z' })
    expect(vi.mocked(track)).toHaveBeenCalledWith('sync_error',
      expect.objectContaining({ stage: 'tombstone', message: 'boom' }))
  })
})

describe('F4: adopted pull notifies the UI (and only on real change)', () => {
  it('dispatches atlas-workbench-pulled exactly when the local data changed', async () => {
    holder.sb = {
      from: () => ({
        select: async () => ({ data: [row('b', '2026-07-18T09:00:00Z')], error: null }),
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => ({ error: null }) }),
      }),
    }
    await syncNow('user-1')                            // pulls b → store changes
    expect(dispatched).toEqual(['atlas-workbench-pulled'])
    await syncNow('user-1')                            // same remote → no change
    expect(dispatched).toEqual(['atlas-workbench-pulled'])  // no second event
  })
})

describe('reviewer nits', () => {
  it('n1: overlapping syncNow calls coalesce — no concurrent I/O, one re-run after', async () => {
    let release!: (v: { data: RemoteRow[]; error: null }) => void
    let selects = 0
    holder.sb = {
      from: () => ({
        select: () => {
          selects += 1
          if (selects === 1) return new Promise(res => { release = res })
          return Promise.resolve({ data: [], error: null })
        },
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => ({ error: null }) }),
      }),
    }
    const p1 = syncNow('user-1')
    const second = await syncNow('user-1')     // while the first awaits its pull
    expect(second).toBeNull()                  // did not run concurrently
    expect(selects).toBe(1)                    // no overlapping I/O
    release({ data: [], error: null })
    await p1
    await vi.waitFor(() => expect(selects).toBe(2))  // coalesced re-run fired once
    await new Promise(res => setTimeout(res, 0))     // let the re-run settle
  })

  it('n2: readPushedMap yields {} for non-object JSON in the sync key', () => {
    for (const bad of ['"str"', '[1,2]', 'null', '42']) {
      localStorage.setItem('atlas.sync.v1', bad)
      expect(readPushedMap()).toEqual({})
    }
  })

  it('n3: empty local store + several markers = corruption suspect, tombstoning skipped', async () => {
    const t = '2026-07-18T08:00:00Z'
    localStorage.setItem('atlas.sync.v1', JSON.stringify({ a: t, b: t, c: t }))
    const updates: number[] = []
    holder.sb = {
      from: () => ({
        select: async () => ({ data: [row('a', t), row('b', t), row('c', t)], error: null }),
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => { updates.push(1); return { error: null } } }),
      }),
    }
    await syncNow('user-1')
    expect(updates).toHaveLength(0)                       // nothing tombstoned
    expect(readPushedMap()).toEqual({ a: t, b: t, c: t }) // markers retained for a human look
    expect(vi.mocked(track)).toHaveBeenCalledWith('sync_error',
      expect.objectContaining({ stage: 'guard' }))
  })
})

describe('re-review: disarm clears the coalesced queue', () => {
  it('stopSyncEngine while a run is in flight cancels the queued re-run', async () => {
    let release!: (v: { data: RemoteRow[]; error: null }) => void
    let selects = 0
    holder.sb = {
      from: () => ({
        select: () => {
          selects += 1
          if (selects === 1) return new Promise(res => { release = res })
          return Promise.resolve({ data: [], error: null })
        },
        upsert: async () => ({ error: null }),
        update: () => ({ eq: async () => ({ error: null }) }),
      }),
    }
    const p1 = syncNow('user-1')
    await syncNow('user-1')                       // lands mid-run → queues a re-run
    stopSyncEngine()                              // sign-out mid-sync
    release({ data: [], error: null })
    await p1
    await new Promise(res => setTimeout(res, 0))  // a would-be re-run gets its chance
    expect(selects).toBe(1)                       // no re-run with the dying session
  })
})
