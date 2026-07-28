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
  addCitation,
  addPin,
  citationId,
  createInvestigation,
  deleteInvestigation,
  exportInvestigationJSON,
  getActiveInvestigationId,
  getInvestigation,
  groupCitationsByPin,
  investigationQuery,
  isCitationPinned,
  listCitations,
  listInvestigations,
  mergeInvestigations,
  mergePinSnapshot,
  movePin,
  onWorkbenchChange,
  removeCitation,
  removePin,
  renameInvestigation,
  toCitationGateStatus,
  updateCitationNote,
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

  it('persists the research-plan query so the plan re-fetches on reopen', () => {
    const inv = createInvestigation('NATO summit Ankara')
    expect(getInvestigation(inv.id)!.query).toBe('NATO summit Ankara')
    // An explicit query wins over the title (auto first-pin titles differ).
    const inv2 = createInvestigation('Renamed later', 'peru election recount')
    expect(getInvestigation(inv2.id)!.query).toBe('peru election recount')
  })

  it('investigationQuery falls back: query → last pin queryText → title', () => {
    const inv = createInvestigation('NATO summit Ankara')
    expect(investigationQuery(inv)).toBe('NATO summit Ankara')
    // Pre-fix records have no persisted query — the last pin's queryText carries it.
    const legacy = createInvestigation('Auto pin title')
    const store = getInvestigation(legacy.id)!
    delete (store as { query?: string }).query
    addPin(legacy.id, { ...PIN, queryText: 'nato ankara base' })
    const got = getInvestigation(legacy.id)!
    got.query = undefined
    expect(investigationQuery(got)).toBe('nato ankara base')
    got.pins = []
    expect(investigationQuery(got)).toBe('Auto pin title')
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

  it('rename persists a custom title and survives reopen', () => {
    const inv = createInvestigation('Cepeda Concedes to De la Espriella')
    renameInvestigation(inv.id, '  Milei Bridges Peru and Colombia Power Transitions  ')
    const got = getInvestigation(inv.id)!
    expect(got.title).toBe('Milei Bridges Peru and Colombia Power Transitions')
    expect(got.titleCustom).toBe(true)
  })

  it('rename with a blank title clears the custom override', () => {
    const inv = createInvestigation('First pin title')
    renameInvestigation(inv.id, 'Custom')
    renameInvestigation(inv.id, '   ')
    const got = getInvestigation(inv.id)!
    expect(got.titleCustom).toBe(false)
  })

  it('delete clears active pointer when needed', () => {
    const inv = createInvestigation('Iran')
    deleteInvestigation(inv.id)
    expect(getActiveInvestigationId()).toBeNull()
    expect(listInvestigations()).toHaveLength(0)
  })

  it('new investigations start with an empty citations array', () => {
    const inv = createInvestigation('Iran')
    expect(getInvestigation(inv.id)!.citations).toEqual([])
  })

  it('survives corrupted storage', () => {
    localStorage.setItem('atlas.workbench.v1', '{not json')
    expect(listInvestigations()).toEqual([])
    setActiveInvestigation('x')
    expect(getActiveInvestigationId()).toBe('x')
  })
})

// Story Lens Task 9: the panel-snapshot enrichment fetch (WorkspaceContext)
// and the lens's sibling-freeze write can land in either order — whichever
// arrives second must not erase the first. mergePinSnapshot is the
// race-proof primitive: shallow field merge, earliest capturedAt wins.
describe('mergePinSnapshot (race-proof snapshot writes)', () => {
  it('merges fields instead of replacing, and the earliest capturedAt wins', () => {
    const inv = createInvestigation('Lens test')
    addPin(inv.id, {
      anchorId: 'theme-x',
      anchorType: 'theme',
      label: 'X',
      snapshot: { capturedAt: '2026-07-28T00:00:00Z', summary: 'seed' },
    })
    mergePinSnapshot(inv.id, 'theme-x', {
      siblings: [{ id: 'dynamic-topic-2', label: 'Sib', weight: 0.7, reason: 'whitened_cos 0.70' }],
    })
    mergePinSnapshot(inv.id, 'theme-x', {
      summary: 'enriched',
      evidence: [{ headline: 'h' }],
    })
    const pin = getInvestigation(inv.id)!.pins.find(p => p.anchorId === 'theme-x')!
    expect(pin.snapshot?.summary).toBe('enriched')
    expect(pin.snapshot?.siblings?.length).toBe(1) // survived the second write
    expect(pin.snapshot?.capturedAt).toBe('2026-07-28T00:00:00Z') // earliest capture wins
  })

  it('touches nothing when the anchor has no matching pin (investigation still returned)', () => {
    const inv = createInvestigation('No pin here')
    const out = mergePinSnapshot(inv.id, 'missing-anchor', { summary: 'x' })
    expect(out?.id).toBe(inv.id)
    expect(getInvestigation(inv.id)!.pins).toHaveLength(0)
  })

  it('is a no-op (null) when the investigation does not exist', () => {
    expect(mergePinSnapshot('nope', 'theme-x', { summary: 'x' })).toBeNull()
  })

  it('creates the snapshot when the pin had none yet (later capture wins as earliest)', () => {
    const inv = createInvestigation('bare pin')
    addPin(inv.id, { anchorId: 'theme-y', anchorType: 'theme', label: 'Y' })
    mergePinSnapshot(inv.id, 'theme-y', { summary: 'first enrichment' })
    const pin = getInvestigation(inv.id)!.pins.find(p => p.anchorId === 'theme-y')!
    expect(pin.snapshot?.summary).toBe('first enrichment')
    expect(pin.snapshot?.capturedAt).toBeTruthy()
  })
})

const RECEIPT = {
  headline: 'Greek highway shut after landslide',
  source: 'kathimerini',
  url: 'https://kathimerini.gr/a/1',
  sourceCountry: 'GR',
  sourceLang: 'el',
  gateStatus: 'below_gate' as const,
  publishedDate: '2026-07-13',
}

describe('workbench citations (receipt-level pinning)', () => {
  it('toCitationGateStatus maps assigned→below_gate and unknowns→unknown', () => {
    expect(toCitationGateStatus('verified')).toBe('verified')
    expect(toCitationGateStatus('extended')).toBe('extended')
    expect(toCitationGateStatus('below_gate')).toBe('below_gate')
    expect(toCitationGateStatus('assigned')).toBe('below_gate')
    expect(toCitationGateStatus(null)).toBe('unknown')
    expect(toCitationGateStatus(undefined)).toBe('unknown')
    expect(toCitationGateStatus('garbage')).toBe('unknown')
  })

  it('citationId prefers the url, falls back to source+headline', () => {
    expect(citationId(RECEIPT)).toBe('cite:url:https://kathimerini.gr/a/1')
    expect(citationId({ headline: 'H', source: 'AP' })).toBe('cite:txt:ap::H')
    // Same receipt, two renders → same id (idempotent toggle).
    expect(citationId({ ...RECEIPT, id: undefined } as never)).toBe(citationId(RECEIPT))
  })

  it('adds a citation with frozen provenance and derives its id', () => {
    const inv = createInvestigation('Greek traffic')
    addCitation(inv.id, RECEIPT)
    const cits = listCitations(inv.id)
    expect(cits).toHaveLength(1)
    expect(cits[0].id).toBe('cite:url:https://kathimerini.gr/a/1')
    expect(cits[0].sourceCountry).toBe('GR')
    expect(cits[0].gateStatus).toBe('below_gate')
    expect(cits[0].capturedAt).toBeTruthy()
    expect(cits[0].investigationId).toBe(inv.id)
  })

  it('citations are idempotent per id (re-pin ignored)', () => {
    const inv = createInvestigation('Greek traffic')
    addCitation(inv.id, RECEIPT)
    addCitation(inv.id, RECEIPT)
    expect(listCitations(inv.id)).toHaveLength(1)
  })

  it('isCitationPinned reflects add/remove', () => {
    const inv = createInvestigation('Greek traffic')
    const id = citationId(RECEIPT)
    expect(isCitationPinned(inv.id, id)).toBe(false)
    addCitation(inv.id, RECEIPT)
    expect(isCitationPinned(inv.id, id)).toBe(true)
    removeCitation(inv.id, id)
    expect(isCitationPinned(inv.id, id)).toBe(false)
    expect(isCitationPinned(null, id)).toBe(false)
  })

  it('updateCitationNote edits the receipt note', () => {
    const inv = createInvestigation('Greek traffic')
    addCitation(inv.id, RECEIPT)
    updateCitationNote(inv.id, citationId(RECEIPT), 'corroborate with local police feed')
    expect(listCitations(inv.id)[0].note).toBe('corroborate with local police feed')
  })

  it('citations are SEPARATE from thread pins and never mix', () => {
    const inv = createInvestigation('Greek traffic')
    addPin(inv.id, PIN)
    addCitation(inv.id, RECEIPT)
    const got = getInvestigation(inv.id)!
    expect(got.pins).toHaveLength(1)
    expect(got.citations).toHaveLength(1)
    expect(got.pins[0].anchorId).toBe(PIN.anchorId)
  })

  it('migrates a pre-citation record WITHOUT losing pins', () => {
    // Simulate a v1 record persisted before citations existed.
    const legacy = {
      investigations: [{
        id: 'inv-legacy', title: 'Old case', createdAt: 'x', updatedAt: 'x',
        pins: [{ ...PIN, pinnedAt: 'x' }],
        trail: [{ at: 'x', action: 'search', detail: 'Old case' }],
        // NOTE: no `citations` key
      }],
    }
    localStorage.setItem('atlas.workbench.v1', JSON.stringify(legacy))
    const got = getInvestigation('inv-legacy')!
    expect(got.pins).toHaveLength(1) // pin preserved
    expect(got.citations).toEqual([]) // defaulted
    // And a citation can now be added to the migrated record.
    addCitation('inv-legacy', RECEIPT)
    expect(listCitations('inv-legacy')).toHaveLength(1)
    expect(getInvestigation('inv-legacy')!.pins).toHaveLength(1) // still there
  })

  it('citations survive JSON export', () => {
    const inv = createInvestigation('Greek traffic')
    addCitation(inv.id, RECEIPT)
    const parsed = JSON.parse(exportInvestigationJSON(inv.id)!)
    expect(parsed.investigation.citations[0].headline).toBe(RECEIPT.headline)
  })

  it('url-less receipts still toggle by source+headline id', () => {
    const inv = createInvestigation('No-url case')
    const noUrl = { headline: 'Wire report', source: 'Reuters', gateStatus: 'unknown' as const }
    addCitation(inv.id, noUrl)
    addCitation(inv.id, noUrl) // idempotent
    expect(listCitations(inv.id)).toHaveLength(1)
  })

  it('groups citations under their anchor pin, unattached bucket for legacy', () => {
    const inv = createInvestigation('t2-citation-group')
    addPin(inv.id, { anchorId: 'theme-1', anchorType: 'theme', label: 'Gaza' } as any)
    addCitation(inv.id, { headline: 'H1', gateStatus: 'verified', anchorId: 'theme-1' })
    addCitation(inv.id, { headline: 'H-orphan', gateStatus: 'unknown' })
    const fresh = getInvestigation(inv.id)!
    const grouped = groupCitationsByPin(fresh.pins, fresh.citations)
    expect(grouped.byPin.get('theme-1')!.map(c => c.headline)).toEqual(['H1'])
    expect(grouped.unattached.map(c => c.headline)).toEqual(['H-orphan'])
  })
})

describe('investigation ergonomics (dedupe / merge / move)', () => {
  it('createInvestigation reuses an existing SAME-QUERY investigation instead of a silent dup', () => {
    const a = createInvestigation('Iran water', 'iran water drought')
    addPin(a.id, PIN)
    // Same query (case/space-insensitive) → reuse, do not create a second record.
    const b = createInvestigation('Iran Water', '  IRAN WATER DROUGHT ')
    expect(b.id).toBe(a.id)
    expect(listInvestigations()).toHaveLength(1)
    expect(getInvestigation(a.id)!.pins).toHaveLength(1) // pins preserved
    expect(getActiveInvestigationId()).toBe(a.id)
  })

  it('a DIFFERENT query still creates a distinct investigation', () => {
    const a = createInvestigation('Iran water', 'iran water')
    const b = createInvestigation('Colombia mining', 'colombia mining')
    expect(b.id).not.toBe(a.id)
    expect(listInvestigations()).toHaveLength(2)
  })

  it('mergeInvestigations unions pins + citations and concatenates the trail, then deletes the source', () => {
    const a = createInvestigation('A case', 'query a')
    const b = createInvestigation('B case', 'query b')
    addPin(a.id, PIN)
    addPin(b.id, { ...PIN, anchorId: 'other--x', label: 'Other thread' })
    addCitation(a.id, RECEIPT)
    addCitation(b.id, { ...RECEIPT, url: 'https://kathimerini.gr/a/2', headline: 'Second receipt' })
    const merged = mergeInvestigations(a.id, b.id)!
    expect(merged.id).toBe(a.id)
    expect(merged.pins).toHaveLength(2)
    expect(merged.citations).toHaveLength(2)
    // source b is gone; active points at the survivor
    expect(getInvestigation(b.id)).toBeNull()
    expect(getActiveInvestigationId()).toBe(a.id)
    expect(merged.trail.some(t => t.detail.toLowerCase().includes('merge'))).toBe(true)
  })

  it('merge dedupes overlapping pins/citations by id (no double-count)', () => {
    const a = createInvestigation('A', 'qa')
    const b = createInvestigation('B', 'qb')
    addPin(a.id, PIN)
    addPin(b.id, PIN) // same anchorId in both
    addCitation(a.id, RECEIPT)
    addCitation(b.id, RECEIPT) // same receipt id in both
    const merged = mergeInvestigations(a.id, b.id)!
    expect(merged.pins).toHaveLength(1)
    expect(merged.citations).toHaveLength(1)
  })

  it('movePin relocates a pin between investigations and leaves trail steps on both', () => {
    const a = createInvestigation('A', 'qa')
    const b = createInvestigation('B', 'qb')
    addPin(a.id, PIN)
    const ok = movePin(PIN.anchorId, a.id, b.id)
    expect(ok).toBe(true)
    expect(getInvestigation(a.id)!.pins).toHaveLength(0)
    expect(getInvestigation(b.id)!.pins).toHaveLength(1)
    expect(getInvestigation(b.id)!.pins[0].anchorId).toBe(PIN.anchorId)
    expect(getInvestigation(a.id)!.trail.some(t => t.action === 'unpin')).toBe(true)
    expect(getInvestigation(b.id)!.trail.some(t => t.action === 'pin')).toBe(true)
  })

  it('movePin is a no-op (false) when the target already has the pin', () => {
    const a = createInvestigation('A', 'qa')
    const b = createInvestigation('B', 'qb')
    addPin(a.id, PIN)
    addPin(b.id, PIN)
    expect(movePin(PIN.anchorId, a.id, b.id)).toBe(false)
    // source keeps its pin (nothing lost on a conflict)
    expect(getInvestigation(a.id)!.pins).toHaveLength(1)
  })
})

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
