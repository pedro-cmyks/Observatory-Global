import { describe, expect, it } from 'vitest'
import { buildRegMarkData, buildVoiceMix } from './PrintersMarks'
import type { DailyPublicationArtifact, EditionServing } from '../lib/dailyPublication'

// Pure-builder contract for the printer's marks: every mark's numbers come
// from the payload the page already serves, never invented.

const sealedServing: EditionServing = {
  serve: 'sealed', ageHours: 4, fresh: true, reasonCodes: [], degradation: [],
}
const liveServing: EditionServing = {
  serve: 'live', ageHours: 30, fresh: false, reasonCodes: ['seal_stale'], degradation: [],
}

function artifact(status: string, readinessStatuses: string[]): DailyPublicationArtifact {
  const keys = ['who', 'what', 'when', 'where', 'how', 'why']
  const readiness = Object.fromEntries(
    readinessStatuses.map((s, i) => [keys[i], { status: s, values: [], reason_codes: [] }]),
  )
  return {
    contract: 'atlas-daily-publication-v1',
    edition_date: '2026-08-13',
    sealed_at: '2026-08-13T02:31:00',
    status,
    graph: { contract: 'atlas-investigation-graph-v1', nodes: [], edges: [], completion: {} },
    package: { readiness } as unknown as DailyPublicationArtifact['package'],
    completion: {},
  } as DailyPublicationArtifact
}

describe('buildRegMarkData', () => {
  it('ready seal registers FULL with the readiness count and 24h seal time', () => {
    const d = buildRegMarkData(
      artifact('ready', ['ready', 'ready', 'ready', 'ready', 'ready', 'ready']),
      sealedServing,
      { ageLabel: 'sealed 4 h ago' },
    )
    expect(d.state).toBe('full')
    expect(d.answered).toBe(6)
    expect(d.total).toBe(6)
    expect(d.sealTime).toMatch(/^\d{2}:\d{2}$/) // 24h clock, no AM/PM
  })

  it('degraded seal is PARTIAL and counts only ready cells as answered', () => {
    const d = buildRegMarkData(
      artifact('degraded', ['ready', 'partial', 'missing', 'ready', 'missing', 'missing']),
      sealedServing,
      {},
    )
    expect(d.state).toBe('partial')
    expect(d.answered).toBe(2) // partial is NOT answered
    expect(d.total).toBe(6)
  })

  it('live serve is unregistered and carries the reason + next seal verbatim', () => {
    const d = buildRegMarkData(artifact('ready', []), liveServing, {
      liveReason: 'no edition has sealed within the last day',
      nextSeal: 'next seal attempt 02:30',
    })
    expect(d.state).toBe('live')
    expect(d.reason).toBe('no edition has sealed within the last day')
    expect(d.nextSeal).toBe('next seal attempt 02:30')
  })

  it('no artifact at all is the live state with null seal facts, never fabricated', () => {
    const d = buildRegMarkData(null, liveServing, {})
    expect(d.state).toBe('live')
    expect(d.sealTime).toBeNull()
    expect(d.answered).toBeNull()
  })
})

describe('buildVoiceMix', () => {
  it('classifies receipts with the receipt-chip classifier and sums to the total', () => {
    const mix = buildVoiceMix(
      [
        { source: 'reuters.com' },                       // wire
        { source: 'nightly-gazette.example', is_state_media: true }, // state (ingest flag wins)
        { source: 'no-such-outlet.example' },            // unknown (no origin on record)
      ],
      'sealed',
    )
    expect(mix).not.toBeNull()
    expect(mix!.totalReceipts).toBe(3)
    expect(mix!.basis).toBe('sealed')
    const byTier = Object.fromEntries(mix!.patches.map(p => [p.tier, p.count]))
    expect(byTier.wire).toBe(1)
    expect(byTier.state).toBe(1)
    expect(mix!.patches.reduce((n, p) => n + p.count, 0)).toBe(3)
  })

  it('returns null on zero receipts — the strip never renders an empty claim', () => {
    expect(buildVoiceMix([], 'live')).toBeNull()
  })

  it('omits absent tiers and keeps ladder order for the present ones', () => {
    const mix = buildVoiceMix([{ source: 'reuters.com' }, { source: 'afp.com' }], 'live')
    expect(mix!.patches.map(p => p.tier)).toEqual(['wire'])
  })
})
