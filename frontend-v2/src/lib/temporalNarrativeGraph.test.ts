import { describe, expect, it } from 'vitest'
import { buildTemporalNarrativeGraph } from './temporalNarrativeGraph'

describe('buildTemporalNarrativeGraph', () => {
  it('groups signals into chronological hourly graph buckets', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'WB_696_PUBLIC_SECTOR_MANAGEMENT',
      themeLabel: 'Public Sector',
      signals: [
        {
          timestamp: '2026-05-08T13:10:00Z',
          country: 'US',
          source: 'iheart.com',
          sentiment: -2,
          otherThemes: ['PUBLIC_SAFETY'],
          persons: ['donald trump'],
        },
        {
          timestamp: '2026-05-08T14:20:00Z',
          country: 'GB',
          source: 'bbc.co.uk',
          sentiment: -1,
          otherThemes: ['HEALTH'],
          persons: ['helen mcentegart'],
        },
      ],
    })

    expect(result.buckets).toHaveLength(2)
    expect(result.buckets[0].id).toBe('2026-05-08T13:00:00.000Z')
    expect(result.buckets[1].id).toBe('2026-05-08T14:00:00.000Z')
    expect(result.buckets[0].nodes.some(node => node.id === 'theme-WB_696_PUBLIC_SECTOR_MANAGEMENT')).toBe(true)
    expect(result.buckets[0].nodes.some(node => node.id === 'country-US')).toBe(true)
    expect(result.buckets[0].links.some(link => link.kind === 'country-theme')).toBe(true)
  })

  it('ignores invalid timestamps and keeps empty graph safe', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'HEALTH',
      themeLabel: 'Health',
      signals: [{ timestamp: 'not-a-date', country: 'US' }],
    })

    expect(result.buckets).toEqual([])
  })

  it('caps people and related themes per signal to avoid noisy graphs', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'HEALTH',
      themeLabel: 'Health',
      maxPeople: 2,
      maxRelatedThemes: 2,
      signals: [{
        timestamp: '2026-05-08T13:10:00Z',
        country: 'US',
        source: 'example.com',
        persons: ['a', 'b', 'c'],
        otherThemes: ['T1', 'T2', 'T3'],
      }],
    })

    const ids = result.buckets[0].nodes.map(node => node.id)
    expect(ids).toContain('person-a')
    expect(ids).toContain('person-b')
    expect(ids).not.toContain('person-c')
    expect(ids).toContain('theme-T1')
    expect(ids).toContain('theme-T2')
    expect(ids).not.toContain('theme-T3')
  })

  it('caps sources per bucket by source frequency', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'HEALTH',
      themeLabel: 'Health',
      maxSources: 1,
      signals: [
        { timestamp: '2026-05-08T13:10:00Z', country: 'US', source: 'a.com' },
        { timestamp: '2026-05-08T13:12:00Z', country: 'US', source: 'a.com' },
        { timestamp: '2026-05-08T13:14:00Z', country: 'US', source: 'b.com' },
      ],
    })

    const ids = result.buckets[0].nodes.map(node => node.id)
    expect(ids).toContain('source-a.com')
    expect(ids).not.toContain('source-b.com')
  })

  it('caps countries per bucket by country frequency', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'HEALTH',
      themeLabel: 'Health',
      maxCountries: 1,
      signals: [
        { timestamp: '2026-05-08T13:10:00Z', country: 'US', source: 'a.com' },
        { timestamp: '2026-05-08T13:12:00Z', country: 'US', source: 'b.com' },
        { timestamp: '2026-05-08T13:14:00Z', country: 'GB', source: 'c.com' },
      ],
    })

    const ids = result.buckets[0].nodes.map(node => node.id)
    expect(ids).toContain('country-US')
    expect(ids).not.toContain('country-GB')
  })

  it('applies a final node cap per type after aggregating a busy bucket', () => {
    const result = buildTemporalNarrativeGraph({
      theme: 'HEALTH',
      themeLabel: 'Health',
      maxPeople: 2,
      signals: Array.from({ length: 8 }, (_, index) => ({
        timestamp: '2026-05-08T13:10:00Z',
        country: 'US',
        persons: [`person-${index}`],
      })),
    })

    const people = result.buckets[0].nodes.filter(node => node.type === 'person')
    expect(people).toHaveLength(4)
  })
})
