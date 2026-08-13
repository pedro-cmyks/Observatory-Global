import { describe, it, expect } from 'vitest'
import { buildGeoNarrative } from './geoNarrative'

/**
 * X1 (2026-08-13). This one-liner sits under the entity panel and reads as a
 * verdict on where a story is being covered. It is computed entirely from
 * `signal_count` over Atlas's ingest, so "Limited elsewhere" and "Global
 * coverage" were claims about the world drawn from the shape of a feed set —
 * the same defect that told a blind panel the US press had not picked up the
 * Hormuz story while CNN ran live coverage.
 */
const node = (cc: string, n: number) => ({ country_code: cc, signal_count: n })

describe('geo narrative — the ingest is not the world', () => {
  it('never claims coverage is limited somewhere, only that the ingest is', () => {
    // Two dominant regions, combined >= 70% — the old "Limited elsewhere" arm.
    const line = buildGeoNarrative([node('US', 50), node('CA', 30), node('FR', 15)])
    expect(line).not.toContain('Limited elsewhere')
    expect(line?.toLowerCase()).toContain('atlas')
  })

  it('never calls the coverage global', () => {
    // Wide spread across >= 4 regions with no dominant one.
    const line = buildGeoNarrative([
      node('US', 10), node('FR', 10), node('CN', 10), node('NG', 10), node('BR', 10),
    ])
    expect(line).not.toContain('Global coverage')
    expect(line?.toLowerCase()).toContain('atlas')
  })

  it('names the base on the concentrated arm', () => {
    // >= 3 nodes: the panel refuses to narrate a thinner field at all.
    const line = buildGeoNarrative([node('US', 90), node('CA', 5), node('FR', 5)])
    expect(line).toContain('Atlas')
    expect(line).toContain('concentrated')
    expect(line).toContain('95%')
  })

  it('says countries PRESENT rather than countries reporting', () => {
    // "Reporting" attributes an act to newsrooms; presence is what is measured.
    const line = buildGeoNarrative([node('US', 40), node('FR', 30), node('DE', 25)])
    expect(line).not.toContain('reporting')
  })

  it('still returns null on an empty field rather than inventing a shape', () => {
    expect(buildGeoNarrative([])).toBeNull()
    expect(buildGeoNarrative([node('US', 0)])).toBeNull()
  })
})
