import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import {
    describePositiveColumn,
    describeToneBlend,
    formatSentimentPm1,
    formatTone10,
    measuredSentimentChip,
    toneBridgeNote,
    toneLineageNote,
    toneSaturationTip,
    toneScaleFooter,
} from './sentimentScale'

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

// ── C2 (blind judge §4.8/§4.9/§5) ────────────────────────────────────────────
// Three numbers on one screen with no bridge: strip "−0.49 · ±1", panels
// "−10.0 · GDELT tone", Analysis "−0.20". MEASURED 2026-08-13: all three come
// from ONE fused lineage (choose_sentiment_weighted → ±1), so the bridge is a
// single ×10. And the panels' label was false — 100% of rendered rows were
// NLP-weighted under a footer reading "GDELT tone".

describe('signed zero (Jordan "−0.0" listed under MOST POSITIVE)', () => {
    it('a tiny negative that rounds to zero never prints a minus sign', () => {
        expect(formatTone10(-0.004).display).toBe('0.0')
        expect(formatTone10(-0.0).display).toBe('0.0')
    })

    it('the ±1 formatter shares the rule', () => {
        expect(formatSentimentPm1(-0.0004)).toBe('0.00')
    })

    it('values that still round away from zero keep their sign', () => {
        expect(formatTone10(-0.006).display).toBe('-0.1')
        expect(formatSentimentPm1(-0.006)).toBe('-0.01')
    })
})

describe('saturation marker (Yemen/North Korea at exactly −10.0)', () => {
    it('a clamped value carries a visible boundary marker, not a bare number', () => {
        const out = formatTone10(-1.12)
        expect(out.display).toBe('-10.0')
        expect(out.marker).toBe('≤')   // ≤ — "at or beyond the floor"
        expect(out.clamped).toBe(true)
    })

    it('the positive edge marks the ceiling', () => {
        expect(formatTone10(1.27).marker).toBe('≥')
    })

    it('in-legend values carry no marker', () => {
        expect(formatTone10(-0.32).marker).toBe('')
    })

    it('saturation tip names the clamp and the measured value', () => {
        const tip = toneSaturationTip(formatTone10(-1.12))
        expect(tip).toContain('saturated at the scale floor')
        expect(tip).toContain('-11.2')
    })

    it('no tip for an unclamped value', () => {
        expect(toneSaturationTip(formatTone10(-0.32))).toBeNull()
    })
})

describe('describeToneBlend (the chip said NLP, the footer said GDELT)', () => {
    it('all-NLP rows name the NLP lineage', () => {
        const b = describeToneBlend(['nlp_weighted', 'nlp_weighted', 'nlp'])
        expect(b.label).toBe('NLP-weighted tone')
        expect(b.detail).toBe('3 of 3 rows')
    })

    it('all-GDELT rows name GDELT', () => {
        const b = describeToneBlend(['gdelt', 'gdelt'])
        expect(b.label).toBe('GDELT tone')
        expect(b.detail).toBe('2 of 2 rows')
    })

    it('a mixed column never claims a single source', () => {
        const b = describeToneBlend(['nlp_weighted', 'gdelt', 'gdelt'])
        expect(b.label).toBe('Fused tone')
        expect(b.detail).toBe('1 NLP-weighted · 2 GDELT')
    })

    it('missing provenance degrades to GDELT (the serializer fallback), never silence', () => {
        expect(describeToneBlend([undefined, undefined]).label).toBe('GDELT tone')
    })

    it('an empty column states no rows rather than asserting a source', () => {
        expect(describeToneBlend([]).detail).toBe('no rows')
    })

    it('the footer states the blend AND the legend together', () => {
        expect(toneScaleFooter(['nlp_weighted'])).toBe(
            'NLP-weighted tone · −10…+10 · 1 of 1 rows',
        )
    })
})

describe('toneBridgeNote (the missing bridge between strip and panels)', () => {
    it('states the conversion with this window’s own number', () => {
        expect(toneBridgeNote(-0.49)).toBe(
            '±1 scale · ×10 = -4.9 on the tone panels below',
        )
    })

    it('degrades honestly when the aggregate is missing', () => {
        expect(toneBridgeNote(Number.NaN)).toBe('±1 scale · window aggregate')
    })
})

describe('describePositiveColumn ("Jordan −0.0" as a most-positive entry)', () => {
    it('says nothing when the column is genuinely positive', () => {
        expect(describePositiveColumn([0.3, 0.2, 0.1])).toBeNull()
    })

    it('names the ranking when no rendered row is positive', () => {
        expect(describePositiveColumn([-0.01, -0.02, -0.04])).toBe(
            'least negative — no country in this window scored positive',
        )
    })

    it('flags a partially-negative column instead of implying all are positive', () => {
        expect(describePositiveColumn([0.3, -0.01])).toBe(
            'ranked high-to-low — 1 of 2 rows is not positive',
        )
    })

    it('no rows, no claim', () => {
        expect(describePositiveColumn([])).toBeNull()
    })
})

// The descriptor is SERVED (briefing `sentiment_scale`, derived from
// sentiment_fusion's own constants) precisely so tuning
// BRIEFING_NLP_SENTIMENT_SCALE can never leave the client's disclosure stale.
describe('served scale descriptor drives the render (no client-side drift)', () => {
    const wider = {
        panel_multiplier: 10,
        panel_bounds: [-20, 20] as [number, number],
        served_abs_max: 1.185,
        nlp_coverage_threshold: 0.5,
    }

    it('a wider served legend stops clamping a value the default would clip', () => {
        expect(formatTone10(-1.12).clamped).toBe(true)
        const out = formatTone10(-1.12, wider)
        expect(out.display).toBe('-11.2')
        expect(out.clamped).toBe(false)
        expect(out.marker).toBe('')
    })

    it('the saturation tip quotes the SERVED range, not a baked constant', () => {
        const narrow = { ...wider, panel_bounds: [-5, 5] as [number, number] }
        const tip = toneSaturationTip(formatTone10(-1.12, narrow), narrow)
        expect(tip).toContain('−5…+5')
        expect(tip).toContain('±11.9')
    })

    it('the footer legend follows the served bounds', () => {
        expect(toneScaleFooter(['gdelt'], wider)).toBe('GDELT tone · −20…+20 · 1 of 1 rows')
    })

    it('the bridge follows the served multiplier', () => {
        const half = { ...wider, panel_multiplier: 100, panel_bounds: [-100, 100] as [number, number] }
        expect(toneBridgeNote(-0.49, half)).toContain('×100 = -49.0')
    })

    it('lineage note quotes the served coverage threshold', () => {
        expect(toneLineageNote(wider)).toContain('50%')
    })

    it('missing descriptor falls back to the shipped defaults, never to NaN', () => {
        expect(formatTone10(-0.32, undefined).display).toBe('-3.2')
        expect(toneLineageNote(undefined)).toContain('30%')
    })
})

// The desktop bridge lives in the tile's ".sub" caption — which mobile CSS
// hides for vertical space (BriefNewspaper.css, max-width:768px). Without a
// mobile carrier the phone shows "−0.49" over panels reading "−10.0" with no
// conversion anywhere: the exact defect, unfixed on half the surface. Mobile
// therefore folds the bridge into its short label, the same trick the strip
// already uses for the hidden sub (#236).
describe('BriefNewspaper wiring — the bridge survives the mobile label swap', () => {
    const src = readFileSync(
        new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8',
    )

    it('the mobile sentiment label carries the ×10 conversion, not just the scale', () => {
        const label = src.match(/brief-vital-k-mobile">([^<]*Sentiment[^<]*)</)?.[1] ?? ''
        expect(label).toContain('±1')
        expect(label).toContain('×10')
    })

    it('the desktop caption is the served bridge, not a hardcoded string', () => {
        expect(src).toContain('toneBridgeNote(data.stats.avg_sentiment, data.sentiment_scale)')
    })

    it('the tone columns pass the served scale to every formatter', () => {
        expect(src).toContain('formatTone10(c.sentiment, scale)')
        expect(src).toContain('toneSaturationTip(tone, scale)')
        expect(src).toMatch(/toneScaleFooter\(negRows\.map\(c => c\.sentiment_source\), scale\)/)
    })

    it('no column footer asserts a single source as a static string', () => {
        expect(src).not.toMatch(/"GDELT tone · −10…\+10"|>GDELT tone · −10…\+10</)
    })
})
