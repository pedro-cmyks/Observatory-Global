import { describe, it, expect } from 'vitest'
import { receiptBasis, GAP_RECEIPT_TIER_TIP } from './gapReceiptBasis'
import type { GapReceipt } from './coverageGaps'

const r = (over: Partial<GapReceipt> = {}): GapReceipt => ({
  headline: 'How Did the Gold Standard Contribute to the Great Depression?',
  source: 'history.com',
  url: 'https://history.com/x',
  gate_score: 0.99,
  ...over,
})

describe('receiptBasis — the score never reaches the page as a number', () => {
  // The judge's "precision theatre": an evergreen history.com explainer printed
  // "score 0.99" beside today's currency-and-debt-stress gap, reading exactly
  // like calibrated confidence. Measured slice precision of this tier is 29-43%.
  it('prints no decimal, and no digits at all, in the visible chip', () => {
    const b = receiptBasis(r({ method: 'lexicon' }))
    expect(b.chip).not.toContain('0.99')
    expect(b.chip).not.toMatch(/\d/)
    expect(b.chip).not.toMatch(/score/i)
  })

  it('holds the same line for every method and for a missing one', () => {
    for (const method of ['lexicon', 'embedding', undefined, null] as const) {
      expect(receiptBasis(r({ method, gate_score: 0.99 })).chip, String(method)).not.toMatch(/\d/)
    }
  })
})

describe('receiptBasis — the chip names the honest basis instead', () => {
  it('calls a lexicon assignment a lexical match', () => {
    expect(receiptBasis(r({ method: 'lexicon' })).chip).toBe('lexical match · unverified')
  })

  it('calls an embedding assignment a semantic match', () => {
    expect(receiptBasis(r({ method: 'embedding' })).chip).toBe('semantic match · unverified')
  })

  it('falls back to the tier, never to a guessed basis, when the method is unknown', () => {
    const chip = receiptBasis(r({ method: null })).chip
    expect(chip).toMatch(/extended/i)
    expect(chip).toMatch(/unverified/)
    expect(chip).not.toMatch(/lexical|semantic/)
  })

  it('always carries "unverified" — this tier is a lead, never evidence', () => {
    for (const method of ['lexicon', 'embedding', null] as const) {
      expect(receiptBasis(r({ method })).chip).toContain('unverified')
    }
  })
})

describe('receiptBasis — the score survives only in the tip, labelled uncalibrated', () => {
  it('keeps the raw number available for inspection', () => {
    expect(receiptBasis(r({ method: 'lexicon' })).tip).toContain('0.99')
  })

  it('names it uncalibrated so the number cannot be read as confidence', () => {
    const tip = receiptBasis(r({ method: 'lexicon' })).tip
    expect(tip).toMatch(/uncalibrated/i)
    // Every mention of "confidence"/"probability" must be negated — the word may
    // appear only to deny that the number is one.
    for (const word of ['confidence', 'probability']) {
      const mentions = tip.match(new RegExp(`\\S+\\s+\\S+\\s+${word}`, 'gi')) ?? []
      for (const m of mentions) expect(m.toLowerCase(), m).toMatch(/\bnot\b/)
    }
  })

  it('carries the measured precision of the tier rather than implying accuracy', () => {
    expect(receiptBasis(r()).tip).toMatch(/29-43%|29–43%/)
    expect(GAP_RECEIPT_TIER_TIP).toMatch(/29-43%|29–43%/)
  })

  it('omits the score line entirely when no score was served', () => {
    const tip = receiptBasis(r({ gate_score: undefined as unknown as number })).tip
    expect(tip).not.toMatch(/NaN|undefined/)
    expect(tip).not.toMatch(/uncalibrated score/i)
  })
})
