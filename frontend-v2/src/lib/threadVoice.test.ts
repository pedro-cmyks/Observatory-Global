// Thread-scoped Voice Mix panel model (council wish 18) — pure shaping of the
// thread-voice-v0 payload. Honesty: unavailable carries the backend reason;
// unknown/unattributed are always stated; thin attributable bases are flagged.
import { describe, expect, it } from 'vitest'
import { buildThreadVoiceModel, canHaveThreadVoice } from './threadVoice'

const base = {
    available: true,
    voices_total: 40,
    languages: [{ lang: 'en', n: 20 }, { lang: 'fa', n: 12 }],
    language_unknown: 8,
    origins: [{ cc: 'IR', n: 10 }, { cc: 'GB', n: 8 }],
    origin_unattributed: 22,
    subject_country: 'IR',
    subject_share: 0.8,
    relation: {
        self_voice: 10, self_voice_ratio: 0.5556, attributable_voices: 18,
        unattributed: 22, soft_power_local_language: 4, soft_power_ratio: 0.2222,
        dominant_outsider: { origin: 'GB', n: 8 },
    },
}

describe('buildThreadVoiceModel', () => {
    it('carries the backend reason when unavailable', () => {
        const m = buildThreadVoiceModel({ available: false, reason: 'projection lags' })
        expect(m).toEqual({ kind: 'unavailable', reason: 'projection lags' })
    })

    it('shapes languages with an explicit unknown count', () => {
        const m = buildThreadVoiceModel(base)
        if (m.kind !== 'mix') throw new Error('expected mix')
        expect(m.languages).toEqual([{ lang: 'EN', n: 20 }, { lang: 'FA', n: 12 }])
        expect(m.languageUnknown).toBe(8)
        expect(m.voicesTotal).toBe(40)
    })

    it('computes the self-voice block from the relation', () => {
        const m = buildThreadVoiceModel(base)
        if (m.kind !== 'mix') throw new Error('expected mix')
        expect(m.selfVoice).toEqual({
            subject: 'IR', pct: 56, selfN: 10, attributable: 18,
            unattributed: 22, softPct: 22,
            dominantOutsider: { origin: 'GB', n: 8 }, thin: false,
        })
    })

    it('flags a thin attributable base instead of hiding it', () => {
        const m = buildThreadVoiceModel({
            ...base,
            relation: { ...base.relation, attributable_voices: 6, self_voice: 2, self_voice_ratio: 0.3333 },
        })
        if (m.kind !== 'mix') throw new Error('expected mix')
        expect(m.selfVoice?.thin).toBe(true)
    })

    it('serves the mix without a self-voice block when there is no relation', () => {
        const { relation: _r, ...noRel } = base
        const m = buildThreadVoiceModel({ ...noRel, subject_country: null })
        if (m.kind !== 'mix') throw new Error('expected mix')
        expect(m.selfVoice).toBeNull()
    })

    it('never renders a self-voice ratio over zero attributable voices', () => {
        const m = buildThreadVoiceModel({
            ...base,
            relation: { ...base.relation, attributable_voices: 0, self_voice: 0, self_voice_ratio: 0 },
        })
        if (m.kind !== 'mix') throw new Error('expected mix')
        expect(m.selfVoice).toBeNull()
    })
})

describe('canHaveThreadVoice', () => {
    it('accepts topic-backed threads (dynamic + atlas slugs)', () => {
        expect(canHaveThreadVoice('dynamic-topic-3435')).toBe(true)
        expect(canHaveThreadVoice('disease-outbreak')).toBe(true)
        expect(canHaveThreadVoice('disease-outbreak--co')).toBe(true)
    })
    it('rejects tokens the member table cannot hold', () => {
        expect(canHaveThreadVoice('query-thread::iran water')).toBe(false)
        expect(canHaveThreadVoice('emergent-cluster-9')).toBe(false)
        expect(canHaveThreadVoice('ARMEDCONFLICT')).toBe(false)
        expect(canHaveThreadVoice('')).toBe(false)
    })
})
