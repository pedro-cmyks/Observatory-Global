// Workbench localStorage store (Phase 2). Spec rules under test:
// - multiple investigations, pins never silently mix;
// - pin is idempotent per anchor;
// - trail preserves the route;
// - JSON export is the v1 durability mechanism.
import { beforeEach, describe, expect, it, vi } from 'vitest'

// vitest runs in node: back localStorage with a Map.
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

import {
  addPin,
  createInvestigation,
  deleteInvestigation,
  exportInvestigationJSON,
  getActiveInvestigationId,
  getInvestigation,
  listInvestigations,
  removePin,
  updatePinNote,
  setActiveInvestigation,
} from './workbench'

const PIN = {
  anchorId: 'water-stress-drought--ir',
  anchorType: 'thread',
  label: 'Water stress and drought in Iran',
  evidenceLabel: 'direct_evidence',
  investigativeScore: 0.64,
}

beforeEach(() => localStorage.clear())

describe('workbench store', () => {
  it('creates an investigation and makes it active', () => {
    const inv = createInvestigation('Iran climate water')
    expect(getActiveInvestigationId()).toBe(inv.id)
    expect(listInvestigations()[0].title).toBe('Iran climate water')
    expect(inv.trail[0].action).toBe('search')
  })

  it('pins are idempotent and recorded in the trail', () => {
    const inv = createInvestigation('Iran')
    addPin(inv.id, PIN)
    addPin(inv.id, PIN) // duplicate ignored
    const got = getInvestigation(inv.id)!
    expect(got.pins).toHaveLength(1)
    expect(got.trail.some(t => t.action === 'pin' && t.detail === PIN.label)).toBe(true)
  })

  it('#227: a pin carries a frozen evidence snapshot', () => {
    const inv = createInvestigation('Iran')
    addPin(inv.id, {
      ...PIN,
      snapshot: {
        capturedAt: '2026-06-26T00:00:00Z',
        summary: 'Water stress · direct evidence · score 0.64',
        metrics: { score: 0.64, lane: 'semantic' },
        evidence: [{ headline: 'Tehran water crisis deepens', source: 'irna' }],
      },
    })
    const pin = getInvestigation(inv.id)!.pins[0]
    expect(pin.snapshot?.summary).toContain('Water stress')
    expect(pin.snapshot?.evidence?.[0].headline).toBe('Tehran water crisis deepens')
  })

  it('#227: updatePinNote edits the analyst note', () => {
    const inv = createInvestigation('Iran')
    addPin(inv.id, PIN)
    updatePinNote(inv.id, PIN.anchorId, 'corroborate with satellite imagery')
    expect(getInvestigation(inv.id)!.pins[0].note).toBe('corroborate with satellite imagery')
  })

  it('pins from different investigations never mix', () => {
    const a = createInvestigation('Iran water')
    const b = createInvestigation('Colombia mining')
    addPin(a.id, PIN)
    expect(getInvestigation(b.id)!.pins).toHaveLength(0)
    expect(getInvestigation(a.id)!.pins).toHaveLength(1)
  })

  it('unpin removes and leaves a trail step', () => {
    const inv = createInvestigation('Iran')
    addPin(inv.id, PIN)
    removePin(inv.id, PIN.anchorId)
    const got = getInvestigation(inv.id)!
    expect(got.pins).toHaveLength(0)
    expect(got.trail.some(t => t.action === 'unpin')).toBe(true)
  })

  it('export produces versioned JSON with the full route', () => {
    const inv = createInvestigation('Iran')
    addPin(inv.id, PIN)
    const json = exportInvestigationJSON(inv.id)!
    const parsed = JSON.parse(json)
    expect(parsed.format).toBe('atlas-investigation-v1')
    expect(parsed.investigation.pins[0].anchorId).toBe(PIN.anchorId)
    expect(parsed.investigation.trail.length).toBeGreaterThanOrEqual(2)
  })

  it('delete clears active pointer when needed', () => {
    const inv = createInvestigation('Iran')
    deleteInvestigation(inv.id)
    expect(getActiveInvestigationId()).toBeNull()
    expect(listInvestigations()).toHaveLength(0)
  })

  it('survives corrupted storage', () => {
    localStorage.setItem('atlas.workbench.v1', '{not json')
    expect(listInvestigations()).toEqual([])
    setActiveInvestigation('x')
    expect(getActiveInvestigationId()).toBe('x')
  })
})
