import { describe, it, expect } from 'vitest'
import { newestTimestamp, streamLiveness, type StreamLivenessInput } from './streamLiveness'

const NOW = Date.UTC(2026, 7, 13, 12, 0, 0)

const base = (over: Partial<StreamLivenessInput> = {}): StreamLivenessInput => ({
  lane: 'served',
  visibleCount: 12,
  fetchedCount: 40,
  lastSignalAt: NOW - 30_000,
  now: NOW,
  hovered: false,
  velocityPerMinute: 7,
  ...over,
})

/** The whole point of X6: these two sentences can never co-occur. */
const claimsTheWordLive = (text: string) => /live/i.test(text)

describe('streamLiveness — the LIVE claim', () => {
  it('claims LIVE only when the lane answered and rows are on screen', () => {
    const s = streamLiveness(base())
    expect(s.tone).toBe('live')
    expect(s.claimsLive).toBe(true)
    expect(s.statusText).toContain('LIVE')
    expect(s.emptyCopy).toBeNull()
  })

  it('never claims LIVE when the lane has not answered yet', () => {
    const s = streamLiveness(base({ lane: 'pending', visibleCount: 0, fetchedCount: 0, lastSignalAt: null }))
    expect(s.tone).toBe('pending')
    expect(s.claimsLive).toBe(false)
    expect(claimsTheWordLive(s.statusText)).toBe(false)
    expect(s.showVelocity).toBe(false)
  })

  it('never claims LIVE when the lane failed — and says so, not "no signals"', () => {
    const s = streamLiveness(base({ lane: 'unanswered', visibleCount: 0, fetchedCount: 0 }))
    expect(s.tone).toBe('unanswered')
    expect(s.claimsLive).toBe(false)
    expect(claimsTheWordLive(s.statusText)).toBe(false)
    expect(s.statusText).toMatch(/did not answer|reconnect/i)
    expect(s.emptyCopy).not.toMatch(/no signals found/i)
    expect(s.emptyNote).toMatch(/unknown/i)
  })

  it('keeps the last-good rows visible while the lane is down, but stops claiming LIVE over them', () => {
    const s = streamLiveness(base({ lane: 'unanswered', visibleCount: 9 }))
    expect(s.claimsLive).toBe(false)
    expect(s.showVelocity).toBe(false)
    expect(s.emptyCopy).toBeNull() // rows are rendering; the header carries the truth
  })

  it('C9: LIVE and an empty list are unrepresentable together', () => {
    const cases: StreamLivenessInput[] = [
      base({ lane: 'served', visibleCount: 0, fetchedCount: 0 }),
      base({ lane: 'served', visibleCount: 0, fetchedCount: 0, lastSignalAt: null }),
      base({ lane: 'served', visibleCount: 0, fetchedCount: 31 }),
      base({ lane: 'unanswered', visibleCount: 0, fetchedCount: 0 }),
      base({ lane: 'pending', visibleCount: 0, fetchedCount: 0 }),
    ]
    for (const input of cases) {
      const s = streamLiveness(input)
      expect(s.claimsLive).toBe(false)
      expect(claimsTheWordLive(s.statusText)).toBe(false)
    }
  })
})

describe('streamLiveness — the measured quiet', () => {
  it('names the last signal it saw instead of "No signals found"', () => {
    const s = streamLiveness(base({ visibleCount: 0, fetchedCount: 0, lastSignalAt: NOW - 14 * 60_000 }))
    expect(s.tone).toBe('quiet')
    expect(s.statusText).toContain('14m')
    expect(s.emptyCopy).toMatch(/quiet right now/i)
    expect(s.emptyCopy).toContain('14m')
    expect(s.emptyCopy).not.toMatch(/no signals found/i)
  })

  it('rounds the age the way the stream rows do (s → m → h)', () => {
    const at = (ms: number) =>
      streamLiveness(base({ visibleCount: 0, fetchedCount: 0, lastSignalAt: NOW - ms })).statusText
    expect(at(20_000)).toContain('20s')
    expect(at(5 * 60_000)).toContain('5m')
    expect(at(3 * 3_600_000)).toContain('3h')
  })

  it('refuses to invent a last-seen time it never measured', () => {
    const s = streamLiveness(base({ visibleCount: 0, fetchedCount: 0, lastSignalAt: null }))
    expect(s.tone).toBe('quiet')
    expect(s.statusText).toMatch(/quiet/i)
    expect(s.emptyCopy).toMatch(/no signals in the last 24 h/i)
    // A measured zero must not read as a broken lane, and vice versa.
    expect(s.emptyNote).toMatch(/answered/i)
    expect(s.emptyNote).not.toMatch(/unknown/i)
  })

  it('a measured zero and an unanswered lane never share a sentence', () => {
    const quiet = streamLiveness(base({ visibleCount: 0, fetchedCount: 0, lastSignalAt: null }))
    const down = streamLiveness(base({ lane: 'unanswered', visibleCount: 0, fetchedCount: 0, lastSignalAt: null }))
    expect(quiet.emptyCopy).not.toBe(down.emptyCopy)
    expect(quiet.tone).not.toBe(down.tone)
  })

  it('says the view is filtered when the lane DID answer but this tab shows none', () => {
    const s = streamLiveness(base({ visibleCount: 0, fetchedCount: 31 }))
    expect(s.tone).toBe('filtered')
    expect(s.claimsLive).toBe(false)
    expect(s.emptyCopy).toContain('31')
    expect(s.emptyCopy).not.toMatch(/no signals found/i)
  })

  it('scoped (lens/eclipse) empties keep their own honest sentence', () => {
    const s = streamLiveness(base({ visibleCount: 0, fetchedCount: 0, scoped: true, lastSignalAt: null }))
    expect(s.tone).toBe('quiet')
    expect(s.emptyCopy).toMatch(/scope/i)
  })
})

describe('streamLiveness — the velocity chip', () => {
  it('prints a rate only where a rate is meaningful', () => {
    expect(streamLiveness(base()).showVelocity).toBe(true)
    expect(streamLiveness(base({ velocityPerMinute: '--' })).showVelocity).toBe(false)
    expect(streamLiveness(base({ velocityPerMinute: null })).showVelocity).toBe(false)
    expect(streamLiveness(base({ velocityPerMinute: undefined })).showVelocity).toBe(false)
    expect(streamLiveness(base({ hovered: true })).showVelocity).toBe(false)
  })

  it('accepts the loosely-typed rate the API actually serves', () => {
    // /api/v2/signals emits numbers as numbers but '--' as a literal string.
    expect(streamLiveness(base({ velocityPerMinute: '12' })).showVelocity).toBe(true)
    expect(streamLiveness(base({ velocityPerMinute: 'n/a' })).showVelocity).toBe(false)
  })

  it('never prints "0 sig/min" beside an empty list — the C9 pairing itself', () => {
    const s = streamLiveness(base({ visibleCount: 0, fetchedCount: 0, velocityPerMinute: 0 }))
    expect(s.showVelocity).toBe(false)
  })

  it('allows a real 0 sig/min while rows are on screen (slow, not dead)', () => {
    const s = streamLiveness(base({ visibleCount: 8, velocityPerMinute: 0 }))
    expect(s.showVelocity).toBe(true)
    expect(s.claimsLive).toBe(true)
  })
})

describe('streamLiveness — the deliberate pause', () => {
  it('keeps the hover pause exactly as it was, and it is not a LIVE claim', () => {
    const s = streamLiveness(base({ hovered: true }))
    expect(s.tone).toBe('paused')
    expect(s.claimsLive).toBe(false)
    expect(s.statusText).toMatch(/paused/i)
  })

  it('does not dress an empty list as "paused" — quiet outranks a meaningless hover', () => {
    const s = streamLiveness(base({ hovered: true, visibleCount: 0, fetchedCount: 0 }))
    expect(s.tone).toBe('quiet')
  })

  it('a failed lane outranks the hover pause', () => {
    const s = streamLiveness(base({ hovered: true, lane: 'unanswered' }))
    expect(s.tone).toBe('unanswered')
  })
})

describe('newestTimestamp — dating a quiet window', () => {
  const iso = (ms: number) => new Date(ms).toISOString()

  it('reads the newest row, not the first', () => {
    const rows = [
      { timestamp: iso(NOW - 60_000) },
      { timestamp: iso(NOW - 10_000) },
      { timestamp: iso(NOW - 3_600_000) },
    ]
    expect(newestTimestamp(rows)).toBe(NOW - 10_000)
  })

  it('dates a window whose every row is junk the stream will never render', () => {
    // The exact case that makes the dated quiet reachable: the lane answered
    // with rows, all of which `isValidHeadline` drops.
    const rows = [{ headline: '26061264.Doc', timestamp: iso(NOW - 14 * 60_000) }]
    expect(newestTimestamp(rows)).toBe(NOW - 14 * 60_000)
  })

  it('returns null rather than dating a quiet it cannot date', () => {
    expect(newestTimestamp([])).toBeNull()
    expect(newestTimestamp(null)).toBeNull()
    expect(newestTimestamp(undefined)).toBeNull()
    expect(newestTimestamp('nope')).toBeNull()
    expect(newestTimestamp([{ headline: 'no clock' }])).toBeNull()
  })

  it('skips unparseable stamps instead of dating the window to 1970', () => {
    const rows = [{ timestamp: 'not-a-date' }, { timestamp: iso(NOW - 5_000) }]
    expect(newestTimestamp(rows)).toBe(NOW - 5_000)
    expect(newestTimestamp([{ timestamp: 'not-a-date' }])).toBeNull()
  })
})

describe('streamLiveness — the dot', () => {
  it('gives each state its own dot so the chrome cannot lie by colour either', () => {
    expect(streamLiveness(base()).dotModifier).toBe('')
    expect(streamLiveness(base({ hovered: true })).dotModifier).toBe('paused')
    expect(streamLiveness(base({ lane: 'unanswered' })).dotModifier).toBe('feed-error')
    expect(streamLiveness(base({ lane: 'pending', visibleCount: 0, fetchedCount: 0 })).dotModifier).toBe('pending')
    expect(streamLiveness(base({ visibleCount: 0, fetchedCount: 0 })).dotModifier).toBe('quiet')
  })
})
