// One sentiment scale per render (council P1-4).
//
// Two user-facing scales exist by design:
//   - ±1  (normalized NLP aggregate) — the Brief instrument strip;
//   - ±10 (raw GDELT tone; the API serves ÷10 values) — per-country tone rows.
// The contract here: every printed value states its scale, is CLAMPED to the
// scale its legend declares (never "Gaza −10.3" under a −10…+10 legend), and
// prose companions ("measured −0.52") derive from the SAME formatter the strip
// uses — one number, one format, everywhere on the page.

const EM_DASH = '—'

function clamp(v: number, lo: number, hi: number): number {
    return Math.min(hi, Math.max(lo, v))
}

function signed(v: number, decimals: number): string {
    const text = Math.abs(v).toFixed(decimals)
    if (v > 0) return `+${text}`
    if (v < 0) return `-${text}`
    return text
}

/** ±1 scale (instrument strip + measured chip). Clamps; NaN degrades to —. */
export function formatSentimentPm1(v: number): string {
    if (!Number.isFinite(v)) return EM_DASH
    return signed(clamp(v, -1, 1), 2)
}

export interface Tone10 {
    /** value printed under the −10…+10 legend (always inside it) */
    display: string
    /** true when the raw value fell outside the legend and was clamped */
    clamped: boolean
    /** the raw ×10 value, for the honest hover when clamped */
    raw: string
}

/** −10…+10 GDELT tone legend. Input is the API's ÷10 value. */
export function formatTone10(pm1: number): Tone10 {
    if (!Number.isFinite(pm1)) return { display: EM_DASH, clamped: false, raw: EM_DASH }
    const raw10 = pm1 * 10
    const clamped10 = clamp(raw10, -10, 10)
    const isClamped = raw10 !== clamped10
    return {
        display: signed(clamped10, 1),
        clamped: isClamped,
        raw: signed(raw10, 1),
    }
}

/** Chip rendered next to generated prose: the strip's number, scale inline. */
export function measuredSentimentChip(v: number): string {
    return `measured ${formatSentimentPm1(v)} (±1 scale)`
}
