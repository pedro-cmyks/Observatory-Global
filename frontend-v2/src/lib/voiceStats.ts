// Voice-mix stat resolution for the Landing page (L0 honesty item).
// The landing voice numbers come live from /api/v2/voice-mix; when that fetch
// fails we fall back to the last MEASURED baseline (voice-mix audit,
// 2026-06-23) — but a degraded fetch must never assert month-old numbers as
// current, so the fallback is flagged and rendered with a dated suffix.

export interface VoiceStats {
    countries: number
    langs: number
    entropy: string
}

export interface ResolvedVoiceStats extends VoiceStats {
    /** true when the numbers are the dated baseline, not a live measurement */
    isBaseline: boolean
}

/** Measured 2026-06-23 (voice-mix audit baseline). */
export const VOICE_BASELINE: VoiceStats = { countries: 126, langs: 31, entropy: '0.71' }

/** Suffix rendered next to baseline numbers so they are never read as current. */
export const VOICE_BASELINE_LABEL = 'as of Jun 2026 baseline'

export function resolveVoiceStats(live: VoiceStats | null): ResolvedVoiceStats {
    if (live) return { ...live, isBaseline: false }
    return { ...VOICE_BASELINE, isBaseline: true }
}
