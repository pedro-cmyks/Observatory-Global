import { describe, it, expect } from 'vitest'
import { countQualifier } from './countQualifier'

// Count-qualifier contract (council wish 5 / P1-5): every printed number states
// its base — "N · <window> · <base>" — so 42/347/3,762 for one object stop
// reading as contradictions. The helper never changes the number, it explains it.
describe('countQualifier', () => {
  it('raw base: window + base in the label, tip says pre-gate assignment', () => {
    const q = countQualifier(347, '24h', 'raw')
    expect(q.label).toBe('347 · 24h · raw')
    expect(q.suffix).toBe('24h · raw')
    expect(q.tip).toMatch(/347/)
    expect(q.tip).toMatch(/assigned/i)
    expect(q.tip).toMatch(/before.*gate|not yet.*gate/i)
    expect(q.tip).toMatch(/24h/)
  })

  it('verified base: tip says kept by the relevance gate', () => {
    const q = countQualifier(42, '24h', 'verified')
    expect(q.label).toBe('42 · 24h · verified')
    expect(q.tip).toMatch(/relevance gate/i)
    expect(q.tip).toMatch(/kept|cleared/i)
  })

  it('sourced base: tip explains it is the fetched sample with headline+outlet', () => {
    const q = countQualifier(120, '24h', 'sourced')
    expect(q.tip).toMatch(/fetched|sample/i)
    expect(q.tip).toMatch(/headline/i)
  })

  it('lifetime base ignores the window — the number is not windowed', () => {
    const q = countQualifier(3762, '24h', 'lifetime')
    expect(q.label).toBe('3,762 · lifetime')
    expect(q.suffix).toBe('lifetime')
    expect(q.tip).toMatch(/all-?time|since .*first|lifetime/i)
    expect(q.tip).not.toMatch(/24h/)
  })

  it('frozen base: tip says captured at pin time, never updates', () => {
    const q = countQualifier(9, 'Jul 12', 'frozen')
    expect(q.label).toBe('9 · Jul 12 · frozen')
    expect(q.tip).toMatch(/pin time|when .*pinned|captured/i)
    expect(q.tip).toMatch(/not update|do(es)? not update|frozen/i)
  })

  it('gated base (fix round item 2): tip says curated serving membership, detail raw can be larger', () => {
    // The threads-row number for dynamic threads is the SERVED membership for
    // the window (42), while the detail counts every raw assignment (347).
    // Labeling the row "raw" made identical tooltips claim two numbers were
    // the same thing — the row's true base is "gated".
    const q = countQualifier(42, '24h', 'gated')
    expect(q.label).toBe('42 · 24h · gated')
    expect(q.suffix).toBe('24h · gated')
    expect(q.tip).toMatch(/42/)
    expect(q.tip).toMatch(/serv|curated|membership/i)
    expect(q.tip).toMatch(/raw/i)
    expect(q.tip).toMatch(/larger|bigger|higher/i)
  })

  it('formats thousands with separators, never rescales the value', () => {
    expect(countQualifier(141841, '24h', 'raw').label).toBe('141,841 · 24h · raw')
  })

  it('null window drops the window segment', () => {
    const q = countQualifier(5, null, 'verified')
    expect(q.label).toBe('5 · verified')
    expect(q.suffix).toBe('verified')
  })
})
