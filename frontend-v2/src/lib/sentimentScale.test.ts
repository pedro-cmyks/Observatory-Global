import { describe, it, expect } from 'vitest'
import { formatSentimentPm1, formatTone10, measuredSentimentChip } from './sentimentScale'

// Council P1-4: one sentiment scale per render. Every printed sentiment states
// its scale, values never print outside the scale their legend declares
// ("Gaza −10.3" on a −10…+10 legend), and the Editor's-Analysis chip derives
// from the SAME ±1 number the instrument strip shows.

describe('formatSentimentPm1 (±1 scale — instrument strip + measured chip)', () => {
    it('formats a negative value with sign and two decimals', () => {
        expect(formatSentimentPm1(-0.52)).toBe('-0.52')
    })

    it('prefixes positive values with +', () => {
        expect(formatSentimentPm1(0.132)).toBe('+0.13')
    })

    it('zero renders unsigned', () => {
        expect(formatSentimentPm1(0)).toBe('0.00')
    })

    it('clamps values outside ±1 so the print never exceeds the stated scale', () => {
        expect(formatSentimentPm1(-1.4)).toBe('-1.00')
        expect(formatSentimentPm1(2.3)).toBe('+1.00')
    })

    it('non-finite input degrades to an em-dash, never NaN text', () => {
        expect(formatSentimentPm1(Number.NaN)).toBe('—')
    })
})

describe('formatTone10 (GDELT −10…+10 legend, API serves ÷10 values)', () => {
    it('multiplies the ÷10 API value back to the display scale', () => {
        const out = formatTone10(-0.32)
        expect(out.display).toBe('-3.2')
        expect(out.clamped).toBe(false)
    })

    it('positive values carry an explicit +', () => {
        expect(formatTone10(0.21).display).toBe('+2.1')
    })

    it('clamps beyond-scale values to the printed legend and flags the clamp', () => {
        const out = formatTone10(-1.03) // the "Gaza −10.3" reproduction
        expect(out.display).toBe('-10.0')
        expect(out.clamped).toBe(true)
        expect(out.raw).toBe('-10.3')
    })

    it('clamps the positive edge too', () => {
        const out = formatTone10(1.27)
        expect(out.display).toBe('+10.0')
        expect(out.clamped).toBe(true)
        expect(out.raw).toBe('+12.7')
    })

    it('non-finite input degrades to an em-dash', () => {
        const out = formatTone10(Number.NaN)
        expect(out.display).toBe('—')
        expect(out.clamped).toBe(false)
    })
})

describe('measuredSentimentChip (prose companion, same number as the strip)', () => {
    it('states the value and the scale inline', () => {
        expect(measuredSentimentChip(-0.52)).toBe('measured -0.52 (±1 scale)')
    })

    it('uses the identical formatter as the strip (sign + clamp semantics)', () => {
        expect(measuredSentimentChip(0.7)).toBe('measured +0.70 (±1 scale)')
        expect(measuredSentimentChip(-1.6)).toBe('measured -1.00 (±1 scale)')
    })
})
