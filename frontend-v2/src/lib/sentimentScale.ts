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

/**
 * The scale the briefing payload declares (`sentiment_scale`, derived in
 * `app/services/sentiment_fusion.sentiment_scale_descriptor`). The client
 * never re-derives these: tuning BRIEFING_NLP_SENTIMENT_SCALE server-side
 * must move the printed disclosure with it, or the disclosure is a claim we
 * stopped measuring.
 */
export interface SentimentScale {
    /** ±1 unit → panel scale */
    panel_multiplier: number
    /** the legend the panels print */
    panel_bounds: [number, number]
    /** |max| the fusion can SERVE on the ±1 unit (wider than the legend) */
    served_abs_max: number
    /** bucket NLP coverage above which the fused value is NLP-weighted */
    nlp_coverage_threshold: number
}

/** Mirrors sentiment_fusion.py's shipped constants — the payload wins. */
export const DEFAULT_SENTIMENT_SCALE: SentimentScale = {
    panel_multiplier: 10,
    panel_bounds: [-10, 10],
    served_abs_max: 1.185,
    nlp_coverage_threshold: 0.3,
}

function resolveScale(s?: SentimentScale): SentimentScale {
    return s ?? DEFAULT_SENTIMENT_SCALE
}

function legend(s: SentimentScale): string {
    const [lo, hi] = s.panel_bounds
    return `−${Math.abs(lo)}…+${hi}`
}

function clamp(v: number, lo: number, hi: number): number {
    return Math.min(hi, Math.max(lo, v))
}

function signed(v: number, decimals: number): string {
    const text = Math.abs(v).toFixed(decimals)
    // C2: a value that ROUNDS to zero is not negative news. "Jordan −0.0"
    // rendered as a most-positive entry because the sign came from the raw
    // float, not from the number actually printed. Sign the print, not the
    // input: if every printed digit is zero, print zero unsigned.
    if (Number(text) === 0) return text
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
    /** '≤' / '≥' when the print sits at a legend edge it was clamped to */
    marker: '' | '≤' | '≥'
}

/**
 * −10…+10 tone legend. Input is the API's ±1 value (see PANEL_MULTIPLIER in
 * `sentiment_fusion.py` — the payload's `sentiment_scale` serves the bridge).
 *
 * The legend is NARROWER than what the fusion can serve: the NLP model maps to
 * [-5, +5] and is rescaled ×2.37, so a country can reach ±11.85 here. Measured
 * over 14 days of prod: 1.29% of eligible country-days exceed the legend — but
 * clipping happens exactly at the extreme these columns RANK for, so 6 of 9
 * days rendered a clamped value. An exact "−10.0" is therefore the clamp, not
 * a measurement floor, and it must say so on the face of the number.
 */
export function formatTone10(pm1: number, scale?: SentimentScale): Tone10 {
    const s = resolveScale(scale)
    if (!Number.isFinite(pm1)) {
        return { display: EM_DASH, clamped: false, raw: EM_DASH, marker: '' }
    }
    const raw10 = pm1 * s.panel_multiplier
    const clamped10 = clamp(raw10, s.panel_bounds[0], s.panel_bounds[1])
    const isClamped = raw10 !== clamped10
    return {
        display: signed(clamped10, 1),
        clamped: isClamped,
        raw: signed(raw10, 1),
        marker: isClamped ? (raw10 < 0 ? '≤' : '≥') : '',
    }
}

/** Hover copy for a clamped tone — names the clamp AND the measured value. */
export function toneSaturationTip(t: Tone10, scale?: SentimentScale): string | null {
    if (!t.clamped) return null
    const s = resolveScale(scale)
    const edge = t.marker === '≤' ? 'floor' : 'ceiling'
    const served = (s.served_abs_max * s.panel_multiplier).toFixed(1)
    return `Printed at the legend ${edge}: this country measured ${t.raw} on the same scale, `
        + `saturated at the scale ${edge} because the ${legend(s)} legend is narrower than the fused range (±${served}).`
}

/** One line naming what the fusion actually does, at the served threshold. */
export function toneLineageNote(scale?: SentimentScale): string {
    const s = resolveScale(scale)
    return `NLP-weighted where signal coverage clears ${Math.round(s.nlp_coverage_threshold * 100)}%, GDELT V2Tone otherwise`
}

export interface ToneBlend {
    /** what actually produced these numbers */
    label: string
    /** the per-row mix, because COALESCE means it varies row to row */
    detail: string
}

/**
 * Name the lineage of a rendered tone column.
 *
 * The defect this closes: every row carried a green "NLP nn%" provenance chip
 * under a column footer reading "GDELT tone". The chip was right — the footer
 * asserted one source for a column whose source is chosen PER ROW (NLP-weighted
 * where bucket coverage ≥ 30%, GDELT V2Tone otherwise). So the footer names the
 * measured mix instead of a single source it cannot claim.
 */
export function describeToneBlend(sources: (string | undefined)[]): ToneBlend {
    const total = sources.length
    if (total === 0) return { label: 'Fused tone', detail: 'no rows' }
    const nlp = sources.filter(s => (s ?? 'gdelt').startsWith('nlp')).length
    const gdelt = total - nlp
    if (nlp === total) return { label: 'NLP-weighted tone', detail: `${total} of ${total} rows` }
    if (gdelt === total) return { label: 'GDELT tone', detail: `${total} of ${total} rows` }
    return { label: 'Fused tone', detail: `${nlp} NLP-weighted · ${gdelt} GDELT` }
}

/** The column footer: blend + legend in one line, neither asserted alone. */
export function toneScaleFooter(sources: (string | undefined)[], scale?: SentimentScale): string {
    const blend = describeToneBlend(sources)
    return `${blend.label} · ${legend(resolveScale(scale))} · ${blend.detail}`
}

/**
 * The bridge the page was missing. The instrument strip and the tone panels
 * print the SAME fused aggregate; only the scale differs, by exactly ×10.
 */
export function toneBridgeNote(avgPm1: number, scale?: SentimentScale): string {
    if (!Number.isFinite(avgPm1)) return '±1 scale · window aggregate'
    const s = resolveScale(scale)
    return `±1 scale · ×${s.panel_multiplier} = ${formatTone10(avgPm1, s).display} on the tone panels below`
}

/**
 * "Most Positive" ranks the top of the tone distribution — it does not promise
 * the rows are positive. On a negative-skewed day the column legitimately fills
 * with near-zero negatives ("Jordan −0.0"), which reads absurd only because the
 * heading over-claims. Say what the ranking is instead.
 */
export function describePositiveColumn(values: number[]): string | null {
    if (values.length === 0) return null
    const nonPositive = values.filter(v => !(v > 0)).length
    if (nonPositive === 0) return null
    if (nonPositive === values.length) {
        return 'least negative — no country in this window scored positive'
    }
    return `ranked high-to-low — ${nonPositive} of ${values.length} rows is not positive`
}

/** Chip rendered next to generated prose: the strip's number, scale inline. */
export function measuredSentimentChip(v: number): string {
    return `measured ${formatSentimentPm1(v)} (±1 scale)`
}
