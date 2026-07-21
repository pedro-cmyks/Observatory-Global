import { describe, it, expect } from 'vitest'
import {
  isKnownOriginCountry,
  resolveOriginChip,
  resolveTierChip,
} from './sourceProvenance'

// Council R2 N1: provenance chips must ENTAIL source_origin_country.
// Exact council cases: globalmedia.mx / excelsior.com wearing "LOCAL IR"
// (Mexican outlets, Iran SUBJECT); an Iowa radio station "COVERED FROM: Iran".
// The resolver takes NO subject-country input by construction — an origin
// assertion can only ever derive from the outlet's own origin country.

describe('isKnownOriginCountry', () => {
  it('accepts a plain ISO2 code, case-insensitive', () => {
    expect(isKnownOriginCountry('MX')).toBe(true)
    expect(isKnownOriginCountry('us')).toBe(true)
  })
  it('rejects absence and placeholders — absence over guess', () => {
    expect(isKnownOriginCountry(undefined)).toBe(false)
    expect(isKnownOriginCountry(null)).toBe(false)
    expect(isKnownOriginCountry('')).toBe(false)
    expect(isKnownOriginCountry('  ')).toBe(false)
    expect(isKnownOriginCountry('XX')).toBe(false) // unknown-country placeholder
    expect(isKnownOriginCountry('UNK')).toBe(false)
    expect(isKnownOriginCountry('USA')).toBe(false) // ISO3 is not the contract
  })
})

describe('resolveOriginChip — the "covered from" assertion', () => {
  it('council case: a Mexican outlet covering Iran gets an MX chip, never IR', () => {
    // The subject country (IR) is not even an input — entailment by construction.
    const chip = resolveOriginChip('MX')
    expect(chip).not.toBeNull()
    expect(chip!.countryCode).toBe('MX')
    expect(chip!.tip).toMatch(/origin|based/i)
    expect(chip!.tip).not.toMatch(/\bIran\b/)
  })
  it('council case: unknown origin (Iowa radio row without origin) → NO origin chip', () => {
    expect(resolveOriginChip(undefined)).toBeNull()
    expect(resolveOriginChip(null)).toBeNull()
    expect(resolveOriginChip('')).toBeNull()
    expect(resolveOriginChip('XX')).toBeNull()
  })
  it('normalizes case and names the country in the tip', () => {
    const chip = resolveOriginChip('us')
    expect(chip!.countryCode).toBe('US')
    expect(chip!.tip).toContain('United States')
  })
  it('tip never claims subject-hood — it says outlet origin, not story subject', () => {
    const chip = resolveOriginChip('DE')
    expect(chip!.tip).toMatch(/not .*subject/i)
  })
})

describe('resolveTierChip — LOCAL requires a known origin', () => {
  it('council case: globalmedia.mx with NO known origin never renders LOCAL', () => {
    const chip = resolveTierChip('globalmedia.mx', undefined)
    expect(chip.tier).not.toBe('local')
    expect(chip.tier).toBe('unknown')
    expect(chip.tip).toMatch(/origin/i)
  })
  it('a local-classified outlet WITH known origin renders LOCAL, tied to that origin', () => {
    const chip = resolveTierChip('globalmedia.mx', 'MX')
    expect(chip.tier).toBe('local')
    expect(chip.label).toBe('LOCAL')
    expect(chip.tip).toContain('Mexico')
  })
  it('wire is origin-independent — Reuters stays WIRE with no origin', () => {
    const chip = resolveTierChip('Reuters', undefined)
    expect(chip.tier).toBe('wire')
    expect(chip.label).toBe('WIRE')
  })
  it('major is origin-independent — BBC stays MAJOR with no origin', () => {
    expect(resolveTierChip('bbc.com', null).tier).toBe('major')
  })
  it('state is origin-independent', () => {
    expect(resolveTierChip('rt.com', undefined).tier).toBe('state')
  })
  it('an unclassifiable bare name stays unknown either way', () => {
    expect(resolveTierChip('zzqq', undefined).tier).toBe('unknown')
    expect(resolveTierChip('zzqq', 'US').tier).toBe('unknown')
  })
  it('empty source is unknown', () => {
    expect(resolveTierChip(undefined, 'US').tier).toBe('unknown')
  })

  // Council R3 P0: the authoritative ingest flag forces STATE even when the
  // name classifier would miss the outlet — a state source is never neutral.
  it('authoritative is_state_media forces STATE tier over the name classifier', () => {
    // A bare/unlisted outlet the name classifier would call unknown/local:
    const flagged = resolveTierChip('some-regional-outlet', 'RU', true)
    expect(flagged.tier).toBe('state')
    expect(flagged.label).toBe('STATE')
    expect(flagged.tip).toMatch(/state/i)
  })
  it('is_state_media false/undefined leaves the name classifier untouched', () => {
    expect(resolveTierChip('Reuters', undefined, false).tier).toBe('wire')
    expect(resolveTierChip('bbc.com', null, undefined).tier).toBe('major')
    // rt.com still resolves STATE via the domain list even without the flag.
    expect(resolveTierChip('rt.com', undefined).tier).toBe('state')
  })
})
