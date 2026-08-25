/**
 * briefTodaysNumber — the Brief's HERO: one measured number for the day.
 *
 * Winner of the 2026-08-24 first-15-seconds championship ("Today's Number").
 * The hero states ONE served measurement, with its base IN the copy, chosen by
 * a fixed, documented rule chain. Nothing here is computed from raw data: the
 * inputs are the SAME integers the INK voice-mix strip already serves (tier
 * percentages over the frozen receipts) plus, when served, the lead's measured
 * outlet count. No input → `null` → the hero does not render (honest absence).
 *
 * RULE CHAIN (fixed priority, first match wins):
 *   R1  state == major, both > 0     → "state media matched the major press"
 *   R2  state >  major, state > 0    → "state wrote more than major"
 *   R3  local >  wire+state+major    → "local wrote more than the rest together"
 *   R4  unknown >= 30                → "we cannot identify X percent"
 *   R5  lead served (outlets+label)  → "M outlets covered one story"
 *   —   nothing served               → null (no hero)
 *
 * DOCUMENTED GUARDS:
 *   - R1/R2 require state > 0: a comparison about state media needs state ink
 *     on the sheet. A 0% = 0% "match" is vacuously true and says nothing, so
 *     the chain falls through to the next rule instead.
 *   - All comparisons run on the SERVED integers (the strip's own rounding),
 *     never on re-derived floats — the hero and the strip can never disagree.
 *   - The mix is usable only with a positive receipt base; a base of zero has
 *     no percentages to state.
 *
 * All copy is ASD-STE100 (docs/design/2026-08-24-atlas-ste-style.md): short
 * sentences, active voice, every number with its base.
 */

export type TodaysNumberLang = 'en' | 'es'

export type TodaysNumberRule = 'R1' | 'R2' | 'R3' | 'R4' | 'R5'

/** Integer percentages exactly as the INK strip serves them, plus the base. */
export interface TodaysNumberMix {
  wire: number
  state: number
  major: number
  local: number
  unknown: number
  /** The frozen receipts the percentages were measured over. */
  totalReceipts: number
}

export interface TodaysNumberLead {
  /** The lead's MEASURED outlet count (resolveSourceCount kind 'measured'). */
  outlets?: number | null
  /** The lead's served label, verbatim. */
  label?: string | null
}

export interface TodaysNumberInput {
  mix?: TodaysNumberMix | null
  lead?: TodaysNumberLead | null
}

export interface TodaysNumber {
  rule: TodaysNumberRule
  /** The big-type number ("14% = 14%", "31% to 22%", "48%", "51 outlets"). */
  headline: string
  /** The full sentence(s), base included, verbatim per the winning design. */
  body: string
  /** R3 only: the local comparative sentence the voices caption repeats. */
  voicesNote: string | null
}

const isPct = (n: unknown): n is number =>
  typeof n === 'number' && Number.isFinite(n) && n >= 0

function usableMix(mix?: TodaysNumberMix | null): TodaysNumberMix | null {
  if (!mix) return null
  if (typeof mix.totalReceipts !== 'number' || !Number.isFinite(mix.totalReceipts) || mix.totalReceipts < 1) return null
  if (![mix.wire, mix.state, mix.major, mix.local, mix.unknown].every(isPct)) return null
  return mix
}

/** Build the strip-identical integer mix from the served patches.
 *  Same rounding as the strip labels (Math.round(count/total*100)); an absent
 *  patch is a MEASURED zero of the base, not a missing field. */
export function todaysNumberMixFrom(
  patches: ReadonlyArray<{ tier: string; count: number }>,
  totalReceipts: number,
): TodaysNumberMix | null {
  if (!Number.isFinite(totalReceipts) || totalReceipts < 1) return null
  const pct = (tier: string): number => {
    const patch = patches.find(p => p.tier === tier)
    if (!patch || !Number.isFinite(patch.count) || patch.count <= 0) return 0
    return Math.round((patch.count / totalReceipts) * 100)
  }
  return {
    wire: pct('wire'),
    state: pct('state'),
    major: pct('major'),
    local: pct('local'),
    unknown: pct('unknown'),
    totalReceipts: Math.round(totalReceipts),
  }
}

const COPY = {
  en: {
    r1Body: (state: number, major: number, n: number) =>
      `State outlets wrote ${state} percent of today's ${n.toLocaleString()} receipts. `
      + `Major news outlets also wrote ${major} percent. `
      + 'Today, state media matched the major press.',
    r2Body: (state: number, major: number, n: number) =>
      `State outlets wrote more of today's receipts than major outlets: ${state}% to ${major}%. `
      + `Base: ${n.toLocaleString()} receipts.`,
    r3Note: (local: number, rest: number) =>
      `Local outlets wrote more receipts than wire, state and major outlets together: ${local}% to ${rest}%.`,
    r3Base: (n: number) => ` Base: ${n.toLocaleString()} receipts.`,
    r4Body: (unknown: number, n: number) =>
      `We cannot identify ${unknown} percent of today's ${n.toLocaleString()} voices. `
      + 'We tell you when we do not know.',
    r5Headline: (m: number) => (m === 1 ? '1 outlet' : `${m.toLocaleString()} outlets`),
    r5Body: (m: number, label: string) =>
      `${m === 1 ? '1 outlet' : `${m.toLocaleString()} outlets`} covered one story today: "${label}".`,
  },
  es: {
    r1Body: (state: number, major: number, n: number) =>
      `Los medios estatales escribieron el ${state} por ciento de los ${n.toLocaleString()} recibos de hoy. `
      + `Los grandes medios también escribieron el ${major} por ciento. `
      + 'Hoy, la prensa estatal igualó a la gran prensa.',
    r2Body: (state: number, major: number, n: number) =>
      `Los medios estatales escribieron más recibos de hoy que los grandes medios: ${state}% a ${major}%. `
      + `Base: ${n.toLocaleString()} recibos.`,
    r3Note: (local: number, rest: number) =>
      `Los medios locales escribieron más recibos que los medios de agencia, estatales y grandes juntos: ${local}% a ${rest}%.`,
    r3Base: (n: number) => ` Base: ${n.toLocaleString()} recibos.`,
    r4Body: (unknown: number, n: number) =>
      `No podemos identificar el ${unknown} por ciento de las ${n.toLocaleString()} voces de hoy. `
      + 'Te decimos cuando no sabemos.',
    r5Headline: (m: number) => (m === 1 ? '1 medio' : `${m.toLocaleString()} medios`),
    r5Body: (m: number, label: string) =>
      `${m === 1 ? '1 medio cubrió' : `${m.toLocaleString()} medios cubrieron`} una historia hoy: "${label}".`,
  },
} as const

/** Decide today's number. Fixed priority R1→R5; no data → null (no hero). */
export function buildTodaysNumber(
  input: TodaysNumberInput,
  lang: TodaysNumberLang = 'en',
): TodaysNumber | null {
  const c = COPY[lang]
  const mix = usableMix(input.mix)

  if (mix) {
    const n = mix.totalReceipts
    // R1 — state matched major (both present; see the documented guard).
    if (mix.state > 0 && mix.major > 0 && mix.state === mix.major) {
      return {
        rule: 'R1',
        headline: `${mix.state}% = ${mix.major}%`,
        body: c.r1Body(mix.state, mix.major, n),
        voicesNote: null,
      }
    }
    // R2 — state above major (state > 0 is implied by state > major >= 0
    // only when major > 0; require it explicitly so 0-vs-0 never fires).
    if (mix.state > 0 && mix.state > mix.major) {
      return {
        rule: 'R2',
        headline: `${mix.state}% to ${mix.major}%`,
        body: c.r2Body(mix.state, mix.major, n),
        voicesNote: null,
      }
    }
    // R3 — local beats wire+state+major together (served integers).
    const rest = mix.wire + mix.state + mix.major
    if (mix.local > 0 && mix.local > rest) {
      const note = c.r3Note(mix.local, rest)
      return {
        rule: 'R3',
        headline: `${mix.local}% to ${rest}%`,
        body: note + c.r3Base(n),
        voicesNote: note,
      }
    }
    // R4 — the unknown share is the story.
    if (mix.unknown >= 30) {
      return {
        rule: 'R4',
        headline: `${mix.unknown}%`,
        body: c.r4Body(mix.unknown, n),
        voicesNote: null,
      }
    }
  }

  // R5 — fallback: the lead's measured outlet count, when it is served.
  const outlets = input.lead?.outlets
  const label = (input.lead?.label ?? '').trim()
  if (typeof outlets === 'number' && Number.isFinite(outlets) && outlets >= 1 && label.length > 0) {
    const m = Math.round(outlets)
    return {
      rule: 'R5',
      headline: c.r5Headline(m),
      body: c.r5Body(m, label),
      voicesNote: null,
    }
  }

  // Nothing served → no hero. The absence IS the honest render.
  return null
}

/**
 * Whole hours until the served next-seal moment. `null` when the schedule is
 * absent, unparseable, or already past — the return hook simply does not
 * render (honest absence; a negative countdown would be an invented promise).
 *
 * Rounds like the seal band (staleBanner's `Math.round(minutes/60)`) so the
 * hook and the band can never state two different hour counts for the same
 * served instant; a seal under half an hour away still says 1, never 0.
 */
export function hoursUntilNextSeal(nextAttemptAt: string | null | undefined, now: Date): number | null {
  const raw = (nextAttemptAt ?? '').trim()
  if (!raw) return null
  const next = new Date(raw)
  if (Number.isNaN(next.getTime())) return null
  const ms = next.getTime() - now.getTime()
  if (ms <= 0) return null
  return Math.max(1, Math.round(ms / 3_600_000))
}
