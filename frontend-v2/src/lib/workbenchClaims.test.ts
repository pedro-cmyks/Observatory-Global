// Claim-ledger STORE wrappers on the workbench (Carolina's spec). The pure
// logic (buildClaimTable, figure extraction) is covered in claimLedger.test.ts;
// this file covers persistence: add/remove/relabel, idempotency per receipt
// pair, migration onto pre-claim records, and JSON-export survival.
//
// In its own file (not workbench.test.ts) to stay isolated from a concurrent
// workbench lane — the claim ledger is self-contained.
import { beforeEach, describe, expect, it, vi } from 'vitest'

const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

import {
  addCitation,
  addClaim,
  addPin,
  createInvestigation,
  exportInvestigationJSON,
  getInvestigation,
  listClaims,
  relabelClaim,
  removeClaim,
} from './workbench'
import { claimId } from './claimLedger'

const RECEIPT_A = {
  id: 'cite:a', headline: 'Toll rises to 4,734 dead', source: 'El Nacional',
  sourceCountry: 'VE', gateStatus: 'below_gate' as const, publishedDate: '2026-07-14',
}
const RECEIPT_B = {
  id: 'cite:b', headline: 'Officials put dead at 4,930', source: 'Últimas Noticias',
  sourceCountry: 'VE', gateStatus: 'below_gate' as const, publishedDate: '2026-07-15',
}

const PIN = {
  anchorId: 'water-stress-drought--ir', anchorType: 'thread',
  label: 'Water stress and drought in Iran',
}

beforeEach(() => localStorage.clear())

describe('workbench claim ledger (store)', () => {
  it('new investigations start with an empty claims array', () => {
    const inv = createInvestigation('Venezuela quake')
    expect(getInvestigation(inv.id)!.claims).toEqual([])
  })

  it('adds a claim linking two citations and records the relation', () => {
    const inv = createInvestigation('Venezuela quake')
    addCitation(inv.id, RECEIPT_A)
    addCitation(inv.id, RECEIPT_B)
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    const claims = listClaims(inv.id)
    expect(claims).toHaveLength(1)
    expect(claims[0].relation).toBe('CONTRADICTS')
    expect(claims[0].id).toBe(claimId('cite:a', 'cite:b'))
    expect(claims[0].createdAt).toBeTruthy()
  })

  it('is idempotent per receipt pair — a second mark relabels in place', () => {
    const inv = createInvestigation('Venezuela quake')
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    // Same pair, opposite order + new relation → still one claim, relabelled.
    addClaim(inv.id, { citationIdA: 'cite:b', citationIdB: 'cite:a', relation: 'CORROBORATES' })
    const claims = listClaims(inv.id)
    expect(claims).toHaveLength(1)
    expect(claims[0].relation).toBe('CORROBORATES')
  })

  it('relabelClaim changes the relation', () => {
    const inv = createInvestigation('Venezuela quake')
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    relabelClaim(inv.id, claimId('cite:a', 'cite:b'), 'CONTEXT')
    expect(listClaims(inv.id)[0].relation).toBe('CONTEXT')
  })

  it('removeClaim drops it', () => {
    const inv = createInvestigation('Venezuela quake')
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    removeClaim(inv.id, claimId('cite:a', 'cite:b'))
    expect(listClaims(inv.id)).toEqual([])
  })

  it('supports a citation-vs-typed-value claim', () => {
    const inv = createInvestigation('Venezuela quake')
    addClaim(inv.id, {
      citationIdA: 'cite:a', citationIdB: null, relation: 'CONTRADICTS',
      typedValue: { figure: 4800, label: 'UN OCHA official', official: true },
    })
    const claims = listClaims(inv.id)
    expect(claims).toHaveLength(1)
    expect(claims[0].citationIdB).toBeNull()
    expect(claims[0].typedValue?.official).toBe(true)
  })

  it('claims are SEPARATE from pins and citations', () => {
    const inv = createInvestigation('Venezuela quake')
    addPin(inv.id, PIN)
    addCitation(inv.id, RECEIPT_A)
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTEXT' })
    const got = getInvestigation(inv.id)!
    expect(got.pins).toHaveLength(1)
    expect(got.citations).toHaveLength(1)
    expect(got.claims).toHaveLength(1)
  })

  it('migrates a pre-claim record WITHOUT losing pins or citations', () => {
    const legacy = {
      investigations: [{
        id: 'inv-legacy', title: 'Old case', createdAt: 'x', updatedAt: 'x',
        pins: [{ ...PIN, pinnedAt: 'x' }],
        citations: [{ ...RECEIPT_A, capturedAt: 'x', investigationId: 'inv-legacy' }],
        trail: [{ at: 'x', action: 'search', detail: 'Old case' }],
        // NOTE: no `claims` key
      }],
    }
    localStorage.setItem('atlas.workbench.v1', JSON.stringify(legacy))
    const got = getInvestigation('inv-legacy')!
    expect(got.pins).toHaveLength(1)
    expect(got.citations).toHaveLength(1)
    expect(got.claims).toEqual([])
    addClaim('inv-legacy', { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    expect(listClaims('inv-legacy')).toHaveLength(1)
    expect(getInvestigation('inv-legacy')!.pins).toHaveLength(1)
  })

  it('claims survive JSON export', () => {
    const inv = createInvestigation('Venezuela quake')
    addClaim(inv.id, { citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' })
    const parsed = JSON.parse(exportInvestigationJSON(inv.id)!)
    expect(parsed.investigation.claims[0].relation).toBe('CONTRADICTS')
  })
})
