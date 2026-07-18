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
