import { describe, it, expect } from 'vitest'
import { labelTokens, scoreHeadline, rankReceiptPool, filterPool, poolLabelCoverage, foldText, latinShare } from './storyReceiptPool'

const S = (headline: string, ts: string, source = 'x', extra: Record<string, unknown> = {}) =>
  ({ headline, timestamp: ts, source, ...extra })

describe('labelTokens', () => {
  it('drops stopwords and short tokens, folds diacritics, dedupes', () => {
    expect(labelTokens('Ceuta Migrant Crisis')).toEqual(['ceuta', 'migrant'])
    expect(labelTokens('Crisis migratoria de Ceuta y Melilla')).toEqual(['migratoria', 'ceuta', 'melilla'])
    expect(labelTokens('US Iran Tensions')).toEqual(['iran'])
    expect(labelTokens('Netanyahu Rejects Trump Gaza Plan')).toEqual(['netanyahu', 'rejects', 'trump', 'gaza'])
  })
})

describe('scoreHeadline', () => {
  it('matches exact words and 5-char stems across languages', () => {
    const t = labelTokens('Ceuta Migrant Crisis')
    expect(scoreHeadline('Al menos 40 chabolas de migrantes en Ceuta', t)).toEqual(['ceuta', 'migrant'])
    expect(scoreHeadline('Morocco denies involvement in migrant surge into Ceuta', t)).toEqual(['ceuta', 'migrant'])
    expect(scoreHeadline('Basketball-WM: Deutschland verliert gegen Spanien', t)).toEqual([])
  })
  it('never stems short tokens into false matches', () => {
    // 'iran' (4 chars) must not match 'irani...' loosely via stem; exact or nothing
    expect(scoreHeadline('Iranian strikes damage jets', labelTokens('Iran'))).toEqual([])
    expect(scoreHeadline('Iran talks postponed', labelTokens('Iran'))).toEqual(['iran'])
  })
})

describe('rankReceiptPool', () => {
  it('puts label-matching receipts first, recency as tiebreak, drops headline-less rows', () => {
    const pool = rankReceiptPool([
      S('Basketball-WM: Deutschland verliert', '2026-09-13T21:00'),
      S('Marchan miles por la paz en Culiacán', '2026-09-14T08:14'),
      S('Morocco denies involvement in migrant surge into Ceuta', '2026-09-10T20:45', 'aljazeera.com'),
      S('El PP responde a Rabat por la crisis de Ceuta', '2026-09-11T10:24', 'elpais.com'),
      { headline: null, timestamp: '2026-09-14T09:00', source: 'ghost' },
    ], 'Ceuta Migrant Crisis')
    expect(pool.map(r => r.signal.source)).toEqual(['aljazeera.com', 'elpais.com', 'x', 'x'])
    expect(pool[0].score).toBe(2)          // ceuta + migrant
    expect(pool[1].matched).toEqual(['ceuta'])
    // among zero-score rows the newer one comes first
    expect(pool[2].signal.headline).toContain('Culiacán')
    expect(pool).toHaveLength(4)
  })
  it('respects the limit after ranking (relevance is never cut by recency first)', () => {
    const many = Array.from({ length: 80 }, (_, i) => S(`junk ${i}`, `2026-09-14T${String(i % 24).padStart(2, '0')}:00`))
    many.push(S('Ceuta migrant camp fire', '2026-09-01T00:00'))
    const pool = rankReceiptPool(many, 'Ceuta Migrant Crisis', 60)
    expect(pool).toHaveLength(60)
    expect(pool[0].signal.headline).toBe('Ceuta migrant camp fire')
  })
})

describe('non-Latin receipts', () => {
  it('rank between matched and unmatched-Latin rows instead of falling off the pool', () => {
    const pool = rankReceiptPool([
      S('Basketball-WM: Deutschland verliert', '2026-09-13T21:00'),
      S('مصدر إيراني يكشف تفاصيل التفاهم مع عُمان', '2026-09-12T17:45', 'arabic.rt.com'),
      S('Bahrain says it will not participate in Iran meeting', '2026-09-12T20:45', 'aljazeera.com'),
    ], 'US Iran Tensions')
    expect(pool.map(r => r.signal.source)).toEqual(['aljazeera.com', 'arabic.rt.com', 'x'])
    expect(pool[1].uncomparable).toBe(true)
    expect(pool[2].uncomparable).toBe(false)
    expect(latinShare('İran ile görüşme')).toBeGreaterThan(0.4)
    expect(latinShare('اليوم الـ198 للحرب')).toBeLessThan(0.4)
  })
})

describe('reserved seats for other scripts', () => {
  it('keeps up to 10 non-Latin receipts when the matched tier overflows the limit', () => {
    const many = Array.from({ length: 80 }, (_, i) => S(`Iran headline ${i}`, `2026-09-1${i % 5}T00:00`))
    const arabic = Array.from({ length: 12 }, (_, i) => S(`إيران ${i} خبر`, '2026-09-12T00:00', `ar${i}`))
    const pool = rankReceiptPool([...many, ...arabic], 'US Iran Tensions', 60)
    expect(pool).toHaveLength(60)
    expect(pool.filter(r => r.uncomparable)).toHaveLength(10)
    expect(pool.slice(0, 50).every(r => r.score > 0)).toBe(true)
  })
})

describe('filterPool / coverage', () => {
  it('filters on headline or outlet, folded; empty query passes all', () => {
    const pool = rankReceiptPool([
      S('El País: Marruecos rechaza', '2026-09-10', 'elpais.com'),
      S('Bahrain refuses meeting', '2026-09-12', 'aljazeera.com'),
    ], 'Ceuta')
    expect(filterPool(pool, 'marruecos').map(r => r.signal.source)).toEqual(['elpais.com'])
    expect(filterPool(pool, 'JAZEERA')).toHaveLength(1)
    expect(filterPool(pool, '')).toHaveLength(2)
    expect(poolLabelCoverage(pool)).toEqual({ onLabel: 0, total: 2 })
  })
  it('foldText strips accents and punctuation', () => {
    expect(foldText('Sánchez: “desastre” — Ceuta')).toBe('sanchez desastre ceuta')
  })
})
