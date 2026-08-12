// Thread-scoped Voice Mix (council wish 18): pure shaping of the
// `thread-voice-v0` payload (GET /api/v2/topic/{id}/voice) into the panel
// model. Who SPEAKS inside a thread — languages, outlet origins, and the
// self-voice relation vs the thread's dominant subject country (ownership,
// not language — same definition as the country Voice Mix panel).
//
// Honesty rules mirrored from the backend:
//  * unavailable -> the backend's reason travels to the UI, never silence;
//  * unknown-language / unattributed-origin counts are always stated;
//  * a thin attributable base (<10) is flagged, not hidden;
//  * zero attributable voices -> no self-voice block (a ratio over nothing
//    is not a measurement).

export interface ThreadVoiceRelation {
    self_voice: number
    self_voice_ratio: number
    attributable_voices: number
    unattributed: number
    soft_power_local_language: number
    soft_power_ratio: number
    dominant_outsider: { origin: string; n: number } | null
}

export interface ThreadVoicePayload {
    available: boolean
    reason?: string
    voices_total?: number
    languages?: Array<{ lang: string; n: number }>
    language_unknown?: number
    origins?: Array<{ cc: string; n: number }>
    origin_unattributed?: number
    subject_country?: string | null
    subject_share?: number
    relation?: ThreadVoiceRelation
}

export interface ThreadVoiceSelf {
    subject: string
    pct: number
    selfN: number
    attributable: number
    unattributed: number
    softPct: number
    dominantOutsider: { origin: string; n: number } | null
    thin: boolean
}

export type ThreadVoiceModel =
    | { kind: 'unavailable'; reason: string }
    | {
        kind: 'mix'
        voicesTotal: number
        languages: Array<{ lang: string; n: number }>
        languageUnknown: number
        origins: Array<{ cc: string; n: number }>
        originUnattributed: number
        selfVoice: ThreadVoiceSelf | null
    }

const THIN_ATTRIBUTABLE = 10

export function buildThreadVoiceModel(p: ThreadVoicePayload): ThreadVoiceModel {
    if (!p.available) {
        return { kind: 'unavailable', reason: p.reason || 'voice mix unavailable for this story' }
    }
    const rel = p.relation
    let selfVoice: ThreadVoiceSelf | null = null
    if (rel && p.subject_country && rel.attributable_voices > 0) {
        selfVoice = {
            subject: p.subject_country,
            pct: Math.round(rel.self_voice_ratio * 100),
            selfN: rel.self_voice,
            attributable: rel.attributable_voices,
            unattributed: rel.unattributed,
            softPct: Math.round(rel.soft_power_ratio * 100),
            dominantOutsider: rel.dominant_outsider ?? null,
            thin: rel.attributable_voices < THIN_ATTRIBUTABLE,
        }
    }
    return {
        kind: 'mix',
        voicesTotal: p.voices_total ?? 0,
        languages: (p.languages ?? []).map(l => ({ lang: l.lang.toUpperCase(), n: l.n })),
        languageUnknown: p.language_unknown ?? 0,
        origins: p.origins ?? [],
        originUnattributed: p.origin_unattributed ?? 0,
        selfVoice,
    }
}

// topic_members.topic_id holds atlas slugs ('disease-outbreak') and
// 'dynamic-topic-<n>' only — query threads, emergent clusters, and raw GDELT
// theme codes can never have a voice row, so we don't fetch (an absent
// section for a thread type the substrate cannot cover is honest).
const ATLAS_SLUG_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)+$/

export function canHaveThreadVoice(theme: string): boolean {
    if (!theme) return false
    const base = theme.split('--', 1)[0]
    if (base.startsWith('dynamic-topic-')) return true
    if (base.startsWith('emergent-cluster-') || base.startsWith('cluster-')) return false
    if (theme.startsWith('query-thread::')) return false
    return ATLAS_SLUG_RE.test(base)
}
