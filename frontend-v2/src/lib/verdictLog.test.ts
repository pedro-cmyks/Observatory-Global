// Verdict log — the resolution ledger. Each entry is one analyst decision on a
// dossier self-critique, with full provenance. This IS the #204 gold the labeler
// is starved for (the analyst telling us WHICH label/receipt is wrong, and why).
import { beforeEach, describe, expect, it, vi } from 'vitest'

const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

const tracked: Array<{ event: string; props?: Record<string, unknown> }> = []
vi.mock('./telemetry', () => ({
  track: (event: string, props?: Record<string, unknown>) => void tracked.push({ event, props }),
  trackOnce: () => {},
}))

import {
  logVerdict,
  listVerdictLog,
  isTargetResolved,
  undoVerdict,
  exportVerdictLog,
} from './verdictLog'

beforeEach(() => { backing.clear(); tracked.length = 0 })

const ENTRY = {
  investigationId: 'inv-1',
  dossierTargetId: 'flood--ir',
  targetKind: 'pin',
  critique: 'single-sourced',
  action: 'needs-corroboration',
  citations: ['https://irna/1', 'https://irna/2'],
}

describe('verdictLog', () => {
  it('logs a verdict with a stamped id + resolvedAt and full provenance', () => {
    const e = logVerdict(ENTRY)
    expect(e.id).toBeTruthy()
    expect(e.resolvedAt).toBeTruthy()
    expect(e.citations).toEqual(['https://irna/1', 'https://irna/2'])
    const all = listVerdictLog()
    expect(all).toHaveLength(1)
    expect(all[0].critique).toBe('single-sourced')
  })

  it('fires verdict_resolved telemetry with {kind, target, provenance}', () => {
    logVerdict(ENTRY)
    const t = tracked.find(t => t.event === 'verdict_resolved')
    expect(t).toBeTruthy()
    expect(t!.props).toMatchObject({
      kind: 'single-sourced',
      target: 'flood--ir',
      provenance: ['https://irna/1', 'https://irna/2'],
    })
  })

  it('listVerdictLog filters by investigation', () => {
    logVerdict(ENTRY)
    logVerdict({ ...ENTRY, investigationId: 'inv-2', dossierTargetId: 'x' })
    expect(listVerdictLog('inv-1')).toHaveLength(1)
    expect(listVerdictLog('inv-2')).toHaveLength(1)
    expect(listVerdictLog()).toHaveLength(2)
  })

  it('isTargetResolved reflects a logged resolution for the same target+action', () => {
    expect(isTargetResolved('inv-1', 'flood--ir', 'needs-corroboration')).toBe(false)
    logVerdict(ENTRY)
    expect(isTargetResolved('inv-1', 'flood--ir', 'needs-corroboration')).toBe(true)
    // a DIFFERENT action on the same target is not resolved
    expect(isTargetResolved('inv-1', 'flood--ir', 'drop-receipt')).toBe(false)
  })

  it('undoVerdict removes the entry (supports the toast+undo path)', () => {
    const e = logVerdict(ENTRY)
    expect(isTargetResolved('inv-1', 'flood--ir', 'needs-corroboration')).toBe(true)
    undoVerdict(e.id)
    expect(isTargetResolved('inv-1', 'flood--ir', 'needs-corroboration')).toBe(false)
    expect(listVerdictLog()).toHaveLength(0)
  })

  it('survives corrupted storage', () => {
    localStorage.setItem('atlas.verdictlog.v1', '{bad')
    expect(listVerdictLog()).toEqual([])
    // and a fresh log still works
    logVerdict(ENTRY)
    expect(listVerdictLog()).toHaveLength(1)
  })

  it('exportVerdictLog produces the labeled gold shape', () => {
    logVerdict(ENTRY)
    const parsed = JSON.parse(exportVerdictLog('inv-1'))
    expect(parsed.format).toBe('atlas-verdict-log-v1')
    expect(parsed.entries[0].critique).toBe('single-sourced')
  })
})
