import { describe, it, expect } from 'vitest'
import { resolveVoiceStats, VOICE_BASELINE, VOICE_BASELINE_LABEL } from './voiceStats'

describe('resolveVoiceStats', () => {
    it('passes live voice-mix values through and marks them as not baseline', () => {
        const live = { countries: 141, langs: 33, entropy: '0.68' }
        const out = resolveVoiceStats(live)
        expect(out.countries).toBe(141)
        expect(out.langs).toBe(33)
        expect(out.entropy).toBe('0.68')
        expect(out.isBaseline).toBe(false)
    })

    it('falls back to the measured Jun 2026 baseline when the live fetch failed', () => {
        const out = resolveVoiceStats(null)
        expect(out.countries).toBe(VOICE_BASELINE.countries)
        expect(out.langs).toBe(VOICE_BASELINE.langs)
        expect(out.entropy).toBe(VOICE_BASELINE.entropy)
        expect(out.isBaseline).toBe(true)
    })

    it('baseline constants match the 2026-06-23 measured values', () => {
        expect(VOICE_BASELINE).toEqual({ countries: 126, langs: 31, entropy: '0.71' })
    })

    it('baseline label dates the numbers so a degraded fetch never asserts them as current', () => {
        expect(VOICE_BASELINE_LABEL.toLowerCase()).toContain('jun 2026')
        expect(VOICE_BASELINE_LABEL.toLowerCase()).toContain('baseline')
    })
})
