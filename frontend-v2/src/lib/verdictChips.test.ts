// Verdict-chip flywheel (Inés): every dossier self-critique → an ACTIONABLE chip.
// The resolver (critique kind → action) is the tested core; deriveVerdictChips
// turns the frozen pins/citations into the chips the dossier renders.
import { describe, expect, it } from 'vitest'
import {
  resolveVerdictAction,
  classifyCritique,
  isSingleSourced,
  isMetadataOnly,
  pinEvidenceSources,
  deriveVerdictChips,
  type VerdictCritiqueKind,
} from './verdictChips'
import type { WorkbenchPin } from './workbench'

function pin(over: Partial<WorkbenchPin> = {}): WorkbenchPin {
  return {
    anchorId: 'a1', anchorType: 'thread', label: 'Test thread',
    pinnedAt: '2026-07-15T00:00:00Z', ...over,
  }
}

describe('resolveVerdictAction — the reason→action resolver', () => {
  it('maps label-unreliable → Split / relabel', () => {
    const a = resolveVerdictAction('label-unreliable')
    expect(a.kind).toBe('split-relabel')
    expect(a.label).toBe('Split / relabel')
    expect(a.destructive).toBe(false)
  })
  it('maps unrelated-receipt → Drop receipt (destructive)', () => {
    const a = resolveVerdictAction('unrelated-receipt')
    expect(a.kind).toBe('drop-receipt')
    expect(a.label).toBe('Drop receipt')
    expect(a.destructive).toBe(true)
  })
  it('maps single-sourced → Needs corroboration', () => {
    const a = resolveVerdictAction('single-sourced')
    expect(a.kind).toBe('needs-corroboration')
    expect(a.label).toBe('Needs corroboration')
    expect(a.destructive).toBe(false)
  })
  it('maps stale-snapshot → Request snapshot', () => {
    const a = resolveVerdictAction('stale-snapshot')
    expect(a.kind).toBe('request-snapshot')
    expect(a.label).toBe('Request snapshot')
  })
  it('every critique kind has a distinct, non-empty action label + tip', () => {
    const kinds: VerdictCritiqueKind[] = ['label-unreliable', 'unrelated-receipt', 'single-sourced', 'stale-snapshot']
    const labels = kinds.map(k => resolveVerdictAction(k).label)
    expect(new Set(labels).size).toBe(4)
    for (const k of kinds) {
      expect(resolveVerdictAction(k).tip.length).toBeGreaterThan(10)
    }
  })
})

describe('classifyCritique — free-text critique → kind', () => {
  it('label-court / confidence critiques → label-unreliable', () => {
    expect(classifyCritique('This label did not match its receipts.')).toBe('label-unreliable')
    expect(classifyCritique('LABEL UNDER REVIEW')).toBe('label-unreliable')
    expect(classifyCritique('matched the taxonomy description, not found evidence')).toBe('label-unreliable')
    expect(classifyCritique('connection(s) are keyword-only')).toBe('label-unreliable')
  })
  it('single-source critiques → single-sourced', () => {
    expect(classifyCritique('single-sourced — one outlet')).toBe('single-sourced')
    expect(classifyCritique('This claim is uncorroborated')).toBe('single-sourced')
  })
  it('metadata/stale critiques → stale-snapshot', () => {
    expect(classifyCritique('captured without frozen evidence (metadata only)')).toBe('stale-snapshot')
    expect(classifyCritique('frozen at pin time; live counts may have drifted since')).toBe('stale-snapshot')
  })
  it('isolated / below-gate critiques → unrelated-receipt', () => {
    expect(classifyCritique('every pinned story is isolated')).toBe('unrelated-receipt')
    expect(classifyCritique('Did not clear the quality gate — candidate material, not verified coverage')).toBe('unrelated-receipt')
  })
  it('returns null for an unrecognized critique', () => {
    expect(classifyCritique('the weather is nice today')).toBeNull()
  })
})

describe('pin evidence predicates', () => {
  it('pinEvidenceSources returns distinct non-empty sources', () => {
    const p = pin({ snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'Reuters' },
      { headline: 'b', source: 'reuters' }, // case-fold dup
      { headline: 'c', source: 'AP' },
      { headline: 'd' }, // no source
    ] } })
    expect(pinEvidenceSources(p)).toEqual(['reuters', 'ap'])
  })
  it('isSingleSourced: exactly one distinct source across ≥1 headline', () => {
    expect(isSingleSourced(pin({ snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'Reuters' },
      { headline: 'b', source: 'Reuters' },
    ] } }))).toBe(true)
    // single headline, one source
    expect(isSingleSourced(pin({ snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'Reuters' },
    ] } }))).toBe(true)
  })
  it('isSingleSourced is false for two distinct sources', () => {
    expect(isSingleSourced(pin({ snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'Reuters' },
      { headline: 'b', source: 'AP' },
    ] } }))).toBe(false)
  })
  it('isSingleSourced is false when there is NO frozen evidence (that is metadata-only, not single-sourced)', () => {
    expect(isSingleSourced(pin({ snapshot: { capturedAt: 'x', evidence: [] } }))).toBe(false)
    expect(isSingleSourced(pin())).toBe(false)
  })
  it('isMetadataOnly: no frozen evidence rows', () => {
    expect(isMetadataOnly(pin())).toBe(true)
    expect(isMetadataOnly(pin({ snapshot: { capturedAt: 'x', evidence: [] } }))).toBe(true)
    expect(isMetadataOnly(pin({ snapshot: { capturedAt: 'x', evidence: [{ headline: 'a', source: 'AP' }] } }))).toBe(false)
  })
})

describe('deriveVerdictChips — dossier state → chips', () => {
  it('a single-sourced pin yields a Needs-corroboration chip carrying its receipts as provenance', () => {
    const p = pin({ anchorId: 'flood--ir', label: 'Iran flood', snapshot: { capturedAt: 'x', evidence: [
      { headline: 'Flood hits Tehran', source: 'IRNA', url: 'https://irna/1' },
      { headline: 'More rain forecast', source: 'IRNA', url: 'https://irna/2' },
    ] } })
    const chips = deriveVerdictChips([p], [])
    const chip = chips.find(c => c.kind === 'single-sourced')
    expect(chip).toBeTruthy()
    expect(chip!.targetId).toBe('flood--ir')
    expect(chip!.targetKind).toBe('pin')
    expect(chip!.provenance).toEqual(['https://irna/1', 'https://irna/2'])
  })
  it('a metadata-only pin yields a Request-snapshot chip, NOT a single-sourced one', () => {
    const p = pin({ anchorId: 'meta--us', label: 'US anomaly' })
    const chips = deriveVerdictChips([p], [])
    expect(chips.some(c => c.kind === 'stale-snapshot' && c.targetId === 'meta--us')).toBe(true)
    expect(chips.some(c => c.kind === 'single-sourced')).toBe(false)
  })
  it('a taxonomy-only pin yields a label-unreliable chip', () => {
    const p = pin({ anchorId: 'tax--x', matchBasis: 'topic_description', snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'AP' }, { headline: 'b', source: 'Reuters' },
    ] } })
    const chips = deriveVerdictChips([p], [])
    expect(chips.some(c => c.kind === 'label-unreliable' && c.targetId === 'tax--x')).toBe(true)
  })
  it('an isolated connection node yields an unrelated-receipt chip on that pin', () => {
    const p = pin({ anchorId: 'iso--x', label: 'Lonely thread', snapshot: { capturedAt: 'x', evidence: [
      { headline: 'a', source: 'AP' }, { headline: 'b', source: 'Reuters' },
    ] } })
    const chips = deriveVerdictChips([p], [{ id: 'iso--x', state: 'isolated' }])
    expect(chips.some(c => c.kind === 'unrelated-receipt' && c.targetId === 'iso--x')).toBe(true)
  })
  it('chip ids are stable + unique per (kind,target)', () => {
    const p = pin({ anchorId: 'flood--ir', snapshot: { capturedAt: 'x', evidence: [{ headline: 'a', source: 'IRNA' }] } })
    const a = deriveVerdictChips([p], [])
    const b = deriveVerdictChips([p], [])
    expect(a[0].id).toBe(b[0].id)
    expect(new Set(a.map(c => c.id)).size).toBe(a.length)
  })
})
