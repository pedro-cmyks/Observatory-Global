// Claim ledger (Carolina's spec / council Phase 2). A Claim links two receipts
// (Citations) — or a receipt + a typed value — with a relation, so the dossier
// can put contested figures (e.g. two death tolls) side by side and flag when
// NO official/wire source backs a contested number.
//
// Everything here is PURE — no localStorage. The store wrappers live in
// workbench.ts (the Citation precedent). These tests exercise the logic:
// figure extraction, official-source detection, claim construction, the table
// builder (incl. the death-toll fixture + official-source-missing), and markdown.
import { describe, expect, it } from 'vitest'
import type { Citation } from './workbench'
import {
  buildClaimTable,
  claimId,
  claimTableMarkdown,
  extractFigure,
  formatFigure,
  isOfficialSource,
  makeClaim,
  type Claim,
} from './claimLedger'

function cite(partial: Partial<Citation> & { headline: string }): Citation {
  return {
    id: partial.id ?? `cite:txt:${(partial.source ?? '').toLowerCase()}::${partial.headline}`,
    headline: partial.headline,
    source: partial.source,
    url: partial.url,
    originCountry: partial.originCountry,
    sourceLang: partial.sourceLang,
    gateStatus: partial.gateStatus ?? 'unknown',
    publishedDate: partial.publishedDate,
    capturedAt: partial.capturedAt ?? '2026-07-17T00:00:00Z',
    investigationId: partial.investigationId ?? 'inv-1',
    note: partial.note,
  }
}

describe('extractFigure', () => {
  it('pulls a thousands-separated number from a headline', () => {
    expect(extractFigure('Venezuela quake toll rises to 4,734 dead')).toBe(4734)
  })
  it('pulls a plain integer', () => {
    expect(extractFigure('At least 312 killed in the floods')).toBe(312)
  })
  it('handles "over N,NNN"', () => {
    expect(extractFigure('Over 4,930 confirmed dead, officials say')).toBe(4930)
  })
  it('returns the first figure when several appear', () => {
    expect(extractFigure('4,734 dead and 12,000 displaced')).toBe(4734)
  })
  it('returns null when there is no number', () => {
    expect(extractFigure('Rescue operations continue in the capital')).toBeNull()
    expect(extractFigure('')).toBeNull()
  })

  // corroborate-v2 F1 — the locale mirror of the backend's _parse_figure_token
  // (corroboration.py). Council C-N17: Indonesian "1.700" read as 1.7 made the
  // best match the top contradiction. Both ends must parse a toll identically.
  it('parses dot-grouped thousands under a comma-decimal source language', () => {
    expect(extractFigure('1.700 orang tewas', 'id')).toBe(1700)
    expect(extractFigure('1.700 muertos', 'es')).toBe(1700)
    expect(extractFigure('magnitud 7,6', 'es')).toBeCloseTo(7.6)
  })

  it('keeps en-default behavior without a lang', () => {
    expect(extractFigure('1,700 dead')).toBe(1700)
    expect(extractFigure('magnitude 7.6')).toBeCloseTo(7.6)
    expect(extractFigure('1.700 dead')).toBeCloseTo(1.7) // unknown lang: conservative
  })

  it('parses unambiguous multi-group numbers in any lang', () => {
    expect(extractFigure('1.234.567 affected')).toBe(1234567)
    expect(extractFigure('1.234.567,89', 'de')).toBeCloseTo(1234567.89)
    expect(extractFigure('1,234,567.89 total')).toBeCloseTo(1234567.89)
    expect(extractFigure('1,234,567 affected')).toBe(1234567)
  })

  it('normalizes the lang tag (case + region subtag) like the backend', () => {
    expect(extractFigure('1.700 mortos', 'PT-BR')).toBe(1700)
    expect(extractFigure('1.700 dead', 'EN-GB')).toBeCloseTo(1.7)
  })

  it('is unchanged for a 1-arg call — every existing call site keeps its result', () => {
    expect(extractFigure('Venezuela quake toll rises to 4,734 dead')).toBe(4734)
    expect(extractFigure('At least 312 killed in the floods')).toBe(312)
    expect(extractFigure('4,734 dead and 12,000 displaced')).toBe(4734)
  })
})

describe('formatFigure', () => {
  it('groups thousands', () => {
    expect(formatFigure(4734)).toBe('4,734')
    expect(formatFigure(312)).toBe('312')
  })
  it('renders null as a dash', () => {
    expect(formatFigure(null)).toBe('—')
  })
})

describe('isOfficialSource', () => {
  it('recognizes international wire agencies by name', () => {
    expect(isOfficialSource('Reuters')).toBe(true)
    expect(isOfficialSource('Associated Press')).toBe(true)
    expect(isOfficialSource('AP')).toBe(true)
    expect(isOfficialSource('Agence France-Presse')).toBe(true)
    expect(isOfficialSource('AFP')).toBe(true)
  })
  it('does not treat an ordinary outlet as official', () => {
    expect(isOfficialSource('El Nacional')).toBe(false)
    expect(isOfficialSource('kathimerini')).toBe(false)
    expect(isOfficialSource(undefined)).toBe(false)
    expect(isOfficialSource('')).toBe(false)
  })
})

describe('claimId / makeClaim', () => {
  it('derives a stable pair id independent of selection order', () => {
    expect(claimId('cite:a', 'cite:b')).toBe(claimId('cite:b', 'cite:a'))
  })
  it('derives a distinct id for a citation + typed value', () => {
    expect(claimId('cite:a', null)).not.toBe(claimId('cite:a', 'cite:b'))
  })
  it('stamps id + createdAt and carries the relation', () => {
    const c = makeClaim(
      { investigationId: 'inv-1', citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' },
      '2026-07-17T12:00:00Z',
    )
    expect(c.id).toBe(claimId('cite:a', 'cite:b'))
    expect(c.relation).toBe('CONTRADICTS')
    expect(c.createdAt).toBe('2026-07-17T12:00:00Z')
  })
})

// ── The death-toll fixture (the demo Carolina's spec must handle) ──────────────
const TOLL_A = cite({
  id: 'cite:a', headline: 'Venezuela quake toll rises to 4,734 dead',
  source: 'El Nacional', originCountry: 'VE', publishedDate: '2026-07-14',
})
const TOLL_B = cite({
  id: 'cite:b', headline: 'Officials put earthquake dead at 4,930',
  source: 'Últimas Noticias', originCountry: 'VE', publishedDate: '2026-07-15',
})
const TOLL_WIRE = cite({
  id: 'cite:w', headline: 'Reuters: Venezuela quake toll reaches 4,800',
  source: 'Reuters', originCountry: 'GB', publishedDate: '2026-07-15',
})

describe('buildClaimTable', () => {
  it('puts two death-toll figures side by side and flags official source missing', () => {
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' }, 'x'),
    ]
    const rows = buildClaimTable([TOLL_A, TOLL_B], claims)
    expect(rows).toHaveLength(2)
    const figures = rows.map(r => r.figure)
    expect(figures).toContain(4734)
    expect(figures).toContain(4930)
    // Each row carries its own outlet / country / date.
    const a = rows.find(r => r.figure === 4734)!
    expect(a.outlet).toBe('El Nacional')
    expect(a.country).toBe('VE')
    expect(a.date).toBe('2026-07-14')
    expect(a.relation).toBe('CONTRADICTS')
    // No wire/official outlet backs either contested figure.
    expect(rows.every(r => r.officialSourcePresent === false)).toBe(true)
    expect(rows.every(r => r.official === false)).toBe(true)
  })

  it("reads each receipt's figure in ITS OWN source language (corroborate-v2 F1)", () => {
    // Same toll, two locales. Before the mirror, the Indonesian receipt read
    // 1.7 and the pair looked like a contradiction of three orders of magnitude.
    const idCite = cite({
      id: 'cite:id', headline: '1.700 orang tewas akibat gempa',
      source: 'Kompas', sourceLang: 'id',
    })
    const enCite = cite({
      id: 'cite:en', headline: '1,700 dead in Sulawesi quake',
      source: 'Reuters', sourceLang: 'en',
    })
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:id', citationIdB: 'cite:en', relation: 'CORROBORATES' }, 'x'),
    ]
    const rows = buildClaimTable([idCite, enCite], claims)
    expect(rows.map(r => r.figure)).toEqual([1700, 1700])
  })

  it('falls back to the conservative parse when a receipt carries no source language', () => {
    const noLang = cite({ id: 'cite:nl', headline: '1.700 dead', source: 'Unknown Outlet' })
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:nl', citationIdB: null, relation: 'CONTEXT', typedValue: { figure: 1700, label: 'official' } }, 'x'),
    ]
    const rows = buildClaimTable([noLang], claims)
    expect(rows.find(r => r.outlet === 'Unknown Outlet')!.figure).toBeCloseTo(1.7)
  })

  it('marks official source present once a wire outlet is in the claim', () => {
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:a', citationIdB: 'cite:w', relation: 'CONTRADICTS' }, 'x'),
    ]
    const rows = buildClaimTable([TOLL_A, TOLL_WIRE], claims)
    expect(rows).toHaveLength(2)
    expect(rows.every(r => r.officialSourcePresent === true)).toBe(true)
    const wire = rows.find(r => r.outlet === 'Reuters')!
    expect(wire.official).toBe(true)
    const outlet = rows.find(r => r.outlet === 'El Nacional')!
    expect(outlet.official).toBe(false)
  })

  it('supports a citation vs a typed official value (analyst-keyed figure)', () => {
    const claims: Claim[] = [
      makeClaim({
        investigationId: 'inv-1', citationIdA: 'cite:a', citationIdB: null,
        relation: 'CONTRADICTS',
        typedValue: { figure: 4800, label: 'UN OCHA official toll', official: true },
      }, 'x'),
    ]
    const rows = buildClaimTable([TOLL_A], claims)
    expect(rows).toHaveLength(2)
    const typed = rows.find(r => r.figure === 4800)!
    expect(typed.outlet).toBe('UN OCHA official toll')
    expect(typed.official).toBe(true)
    expect(rows.every(r => r.officialSourcePresent === true)).toBe(true)
  })

  it('uses the claim-level figure override when the headline has no number', () => {
    const noNum = cite({ id: 'cite:n', headline: 'Death toll keeps climbing, ministry warns', source: 'VTV' })
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:n', citationIdB: 'cite:a', relation: 'CORROBORATES', figure: 5000 }, 'x'),
    ]
    const rows = buildClaimTable([noNum, TOLL_A], claims)
    const overridden = rows.find(r => r.outlet === 'VTV')!
    expect(overridden.figure).toBe(5000)
    expect(rows.every(r => r.relation === 'CORROBORATES')).toBe(true)
  })

  it('skips claims whose citations are missing from the list', () => {
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:gone', citationIdB: 'cite:also-gone', relation: 'CONTEXT' }, 'x'),
    ]
    expect(buildClaimTable([TOLL_A], claims)).toEqual([])
  })

  it('returns no rows when there are no claims', () => {
    expect(buildClaimTable([TOLL_A, TOLL_B], [])).toEqual([])
  })
})

describe('claimTableMarkdown', () => {
  it('renders a markdown table with the figures and a no-official caveat', () => {
    const claims: Claim[] = [
      makeClaim({ investigationId: 'inv-1', citationIdA: 'cite:a', citationIdB: 'cite:b', relation: 'CONTRADICTS' }, 'x'),
    ]
    const rows = buildClaimTable([TOLL_A, TOLL_B], claims)
    const md = claimTableMarkdown(rows).join('\n')
    expect(md).toContain('## Contested figures')
    expect(md).toContain('| Figure |')
    expect(md).toContain('4,734')
    expect(md).toContain('4,930')
    expect(md).toContain('CONTRADICTS')
    expect(md.toLowerCase()).toContain('no official')
  })

  it('is empty when there are no rows', () => {
    expect(claimTableMarkdown([])).toEqual([])
  })
})
