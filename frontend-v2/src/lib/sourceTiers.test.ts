// Coarse source-credibility tiers (#217) — the FRONTEND classifier for
// analyst-pinned receipts (Citations) and rollups, where the rich backend
// credibility payload is absent (a Citation carries only a source string).
//
// Coarse ladder, HONEST by construction: wire | state | major | local |
// unknown. `unknown` is a real tier — never guessed into something better.
import { describe, it, expect } from 'vitest'
import {
  classifyOutlet,
  coarseTierLabel,
  isOfficialishTier,
  sourceMix,
  formatSourceMix,
  type CoarseTier,
} from './sourceTiers'

const tierOf = (s: string | null | undefined): CoarseTier => classifyOutlet(s).tier

describe('classifyOutlet — wire', () => {
  it('classifies international wire agencies by name', () => {
    expect(tierOf('Reuters')).toBe('wire')
    expect(tierOf('Associated Press')).toBe('wire')
    expect(tierOf('AP')).toBe('wire')
    expect(tierOf('AFP')).toBe('wire')
    expect(tierOf('Agence France-Presse')).toBe('wire')
    expect(tierOf('Bloomberg')).toBe('wire')
    expect(tierOf('EFE')).toBe('wire')
    expect(tierOf('Kyodo News')).toBe('wire')
  })
  it('classifies wire agencies by domain', () => {
    expect(tierOf('reuters.com')).toBe('wire')
    expect(tierOf('https://www.apnews.com/article/x')).toBe('wire')
    expect(tierOf('feeds.reuters.com')).toBe('wire')
  })
  it('every classification carries provenance', () => {
    expect(classifyOutlet('Reuters').provenance).toMatch(/wire|agency/i)
  })
})

describe('classifyOutlet — state', () => {
  it('classifies state broadcasters by name', () => {
    expect(tierOf('RT')).toBe('state')
    expect(tierOf('Russia Today')).toBe('state')
    expect(tierOf('Sputnik')).toBe('state')
    expect(tierOf('Xinhua')).toBe('state')
    expect(tierOf('CGTN')).toBe('state')
    expect(tierOf('Global Times')).toBe('state')
    expect(tierOf('Press TV')).toBe('state')
    expect(tierOf('TASS')).toBe('state')
  })
  it('classifies state broadcasters by domain', () => {
    expect(tierOf('rt.com')).toBe('state')
    expect(tierOf('globaltimes.cn')).toBe('state')
    expect(tierOf('presstv.ir')).toBe('state')
  })
})

describe('classifyOutlet — major', () => {
  it('classifies established national/international press by name', () => {
    expect(tierOf('BBC')).toBe('major')
    expect(tierOf('The Guardian')).toBe('major')
    expect(tierOf('New York Times')).toBe('major')
    expect(tierOf('CNN')).toBe('major')
    expect(tierOf('Al Jazeera')).toBe('major')
    expect(tierOf('Le Monde')).toBe('major')
  })
  it('classifies majors by domain', () => {
    expect(tierOf('bbc.co.uk')).toBe('major')
    expect(tierOf('nytimes.com')).toBe('major')
    expect(tierOf('theguardian.com')).toBe('major')
  })
})

describe('classifyOutlet — local', () => {
  it('classifies an unrecognized registered outlet (has a domain) as local', () => {
    expect(tierOf('elnacional.com.ve')).toBe('local')
    expect(tierOf('kathimerini.gr')).toBe('local')
    expect(tierOf('theexaminer.com.au')).toBe('local')
  })
  it('classifies an unrecognized name with a press marker as local', () => {
    expect(tierOf('Riverside Herald')).toBe('local')
    expect(tierOf('Bendigo Advertiser')).toBe('local')
    expect(tierOf('Daily Gazette')).toBe('local')
  })
})

describe('classifyOutlet — unknown (never guessed)', () => {
  it('is the honest fallback for no-signal names', () => {
    expect(tierOf('Anonymous')).toBe('unknown')
    expect(tierOf('user1234')).toBe('unknown')
    expect(tierOf('random blog')).toBe('unknown')
  })
  it('is unknown for empty / missing source', () => {
    expect(tierOf(undefined)).toBe('unknown')
    expect(tierOf(null)).toBe('unknown')
    expect(tierOf('')).toBe('unknown')
    expect(tierOf('   ')).toBe('unknown')
  })
})

describe('coarseTierLabel + isOfficialishTier', () => {
  it('exposes uppercase display labels', () => {
    expect(coarseTierLabel('wire')).toBe('WIRE')
    expect(coarseTierLabel('unknown')).toBe('UNKNOWN')
  })
  it('treats wire and state as official-ish, others not', () => {
    expect(isOfficialishTier('wire')).toBe(true)
    expect(isOfficialishTier('state')).toBe(true)
    expect(isOfficialishTier('major')).toBe(false)
    expect(isOfficialishTier('local')).toBe(false)
    expect(isOfficialishTier('unknown')).toBe(false)
  })
})

describe('sourceMix + formatSourceMix — dossier rollup', () => {
  it('counts sources into coarse tiers', () => {
    const mix = sourceMix([
      'Reuters', 'AP',                       // 2 wire
      'BBC', 'CNN', 'The Guardian', 'Le Monde', 'Al Jazeera', // 5 major
      'Riverside Herald', 'kathimerini.gr',  // 2 local
      'Anonymous',                           // 1 unknown
    ])
    expect(mix.wire).toBe(2)
    expect(mix.major).toBe(5)
    expect(mix.local).toBe(2)
    expect(mix.unknown).toBe(1)
    expect(mix.state).toBe(0)
  })
  it('formats the rollup in ladder order, omitting empty tiers', () => {
    const mix = sourceMix(['Reuters', 'AP', 'BBC', 'CNN', 'Riverside Herald', 'Anonymous'])
    expect(formatSourceMix(mix)).toBe('2 wire · 2 major · 1 local · 1 unknown')
  })
  it('returns empty string for no sources', () => {
    expect(formatSourceMix(sourceMix([]))).toBe('')
  })
  it('is single-source honest (one local outlet)', () => {
    expect(formatSourceMix(sourceMix(['Bendigo Advertiser']))).toBe('1 local')
  })
})
