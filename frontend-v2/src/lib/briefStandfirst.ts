/**
 * briefStandfirst — weaves the sealed edition's 5W+H readiness payload into a
 * readable standfirst paragraph (Pedro 2026-08-24: "las preguntas … deberían de
 * salir EN EL TEXTO").
 *
 * Hard honesty rules, enforced here and frozen by tests:
 *  - Only a field served `ready` is woven into prose. A `partial` field is
 *    NEVER woven — it is declared, by name, in one short line at the end
 *    ("Below the full bar today: WHO, WHERE."). A missing/absent field simply
 *    produces no sentence and no mention (the six tiles remain the inspectable
 *    record).
 *  - Values are never invented, extended, or reworded — only PRESENTED. The
 *    single presentation cleanup allowed is stripping the typed-subject
 *    annotation suffix ("Canada (place)" → "Canada"); the underlying datum is
 *    untouched (this module never mutates its input).
 *  - An outlet woven from HOW carries its measured credibility: a domain
 *    classified `state` by sourceTiers is flagged so the render can mark it —
 *    state media is never presented as neutral.
 *  - WHY is capped at `partial` by the backend by construction (movement is
 *    never causality), so it can only ever appear in the below-bar line.
 */
import { classifyOutlet, TIER_TIP } from './sourceTiers'

export type StandfirstLang = 'en' | 'es'

export const QUESTION_KEYS = ['who', 'what', 'when', 'where', 'how', 'why'] as const
export type QuestionKey = (typeof QUESTION_KEYS)[number]

export interface StandfirstReadinessItem {
  status: string
  values?: string[] | null
  reason_codes?: string[] | null
}

/** Loose on purpose: the payload is a network artifact — any field may be
 *  absent, and an absent field must yield an absent sentence, never a throw. */
export type StandfirstReadiness = Partial<
  Record<QuestionKey, StandfirstReadinessItem | null | undefined>
> | null | undefined

export type StandfirstPart =
  | { kind: 'text'; text: string }
  | { kind: 'outlet'; name: string; state: boolean }

export interface EditionStandfirst {
  /** In-order prose runs. Outlet runs carry the measured STATE flag. */
  parts: StandfirstPart[]
  /** Question keys served but graded `partial` — declared, never woven. */
  belowBar: QuestionKey[]
  /** The one honest closing line for `belowBar`, or null when nothing is partial. */
  belowBarLine: string | null
  /** true when at least one ready field produced prose. */
  hasProse: boolean
}

// ── localized connectors (chrome copy lives here so the lib stays the single
//    testable source of the paragraph — uiCopy is untouched) ────────────────
const COPY = {
  en: {
    todaysLead: 'Today’s lead: ',
    coverageOpen: 'Today’s coverage',
    measuredAcross: (codes: string) => `measured across ${codes} coverage`,
    ledBy: 'led by ',
    and: ' and ',
    listComma: ', ',
    moreOutlets: (n: number) => (n === 1 ? ' and 1 more outlet' : ` and ${n} more outlets`),
    atCenter: 'At the center: ',
    moreStories: (n: number) =>
      n === 1 ? '1 more story met today’s measured bar.' : `${n} more stories met today’s measured bar.`,
    belowBar: 'Below the full bar today: ',
    months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    monthFirst: true,
  },
  es: {
    todaysLead: 'La nota del día: ',
    coverageOpen: 'La cobertura de hoy',
    measuredAcross: (codes: string) => `medida en cobertura ${codes}`,
    ledBy: 'encabezada por ',
    and: ' y ',
    listComma: ', ',
    moreOutlets: (n: number) => (n === 1 ? ' y 1 medio más' : ` y ${n} medios más`),
    atCenter: 'Al centro: ',
    moreStories: (n: number) =>
      n === 1 ? '1 historia más pasó la barra medida de hoy.' : `${n} historias más pasaron la barra medida de hoy.`,
    belowBar: 'Hoy bajo la barra completa: ',
    months: ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'],
    monthFirst: false,
  },
} as const

/** Chrome strings for the render around the paragraph (aria, the details
 *  summary, the STATE chip). Kept beside the prose so en/es stay in one file. */
export function standfirstChrome(lang: StandfirstLang) {
  return lang === 'es'
    ? {
        aria: 'Entradilla de la edición',
        seeQuestions: 'Ver las seis preguntas medidas',
        stateChip: 'STATE',
        stateTip: TIER_TIP.state,
      }
    : {
        aria: 'Edition standfirst',
        seeQuestions: 'See the six measured questions',
        stateChip: 'STATE',
        stateTip: TIER_TIP.state,
      }
}

// ── presentation cleanup (render-only; the datum is never mutated) ──────────
const SUBJECT_ANNOTATION = /\s*\((?:place|person|org|organization|group|event)\)\s*$/i

/** "Canada (place)" → "Canada". Presentation only. */
export function cleanSubjectValue(value: string): string {
  return value.replace(SUBJECT_ANNOTATION, '').trim()
}

// ── date range ──────────────────────────────────────────────────────────────
const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/

interface IsoDay { y: number; m: number; d: number }

function parseIsoDay(value: string): IsoDay | null {
  const m = ISO_DAY.exec(value.trim())
  if (!m) return null
  const [, y, mo, d] = m
  const month = Number(mo)
  const day = Number(d)
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  return { y: Number(y), m: month, d: day }
}

function formatDay(day: IsoDay, lang: StandfirstLang, withYear: boolean): string {
  const c = COPY[lang]
  const mon = c.months[day.m - 1]
  const core = c.monthFirst ? `${mon} ${day.d}` : `${day.d} ${mon}`
  return withYear ? `${core}, ${day.y}` : core
}

/**
 * "2026-08-23","2026-08-24" → "Aug 23–24" (en) / "23–24 ago" (es).
 * Only well-formed ISO days participate; none valid → null (no invention).
 */
export function formatDateRange(values: string[], lang: StandfirstLang): string | null {
  const days = values.map(parseIsoDay).filter((d): d is IsoDay => d !== null)
  if (days.length === 0) return null
  const sorted = [...days].sort((a, b) => a.y - b.y || a.m - b.m || a.d - b.d)
  const lo = sorted[0]
  const hi = sorted[sorted.length - 1]
  const c = COPY[lang]
  if (lo.y === hi.y && lo.m === hi.m && lo.d === hi.d) return formatDay(lo, lang, false)
  if (lo.y === hi.y && lo.m === hi.m) {
    const mon = c.months[lo.m - 1]
    return c.monthFirst ? `${mon} ${lo.d}–${hi.d}` : `${lo.d}–${hi.d} ${mon}`
  }
  if (lo.y === hi.y) return `${formatDay(lo, lang, false)} – ${formatDay(hi, lang, false)}`
  return `${formatDay(lo, lang, true)} – ${formatDay(hi, lang, true)}`
}

// ── weaving ─────────────────────────────────────────────────────────────────
const WHERE_CAP = 6
const WHO_CAP = 3
const OUTLET_CAP = 2

function readyValues(item: StandfirstReadinessItem | null | undefined): string[] {
  if (!item || item.status !== 'ready' || !Array.isArray(item.values)) return []
  return item.values.filter((v): v is string => typeof v === 'string' && v.trim().length > 0)
}

function text(t: string): StandfirstPart {
  return { kind: 'text', text: t }
}

function outletPart(name: string): StandfirstPart {
  return { kind: 'outlet', name, state: classifyOutlet(name).tier === 'state' }
}

/** Merge adjacent text runs so the render (and the tests) see minimal parts. */
function mergeParts(parts: StandfirstPart[]): StandfirstPart[] {
  const out: StandfirstPart[] = []
  for (const p of parts) {
    const last = out[out.length - 1]
    if (p.kind === 'text' && last?.kind === 'text') {
      out[out.length - 1] = text(last.text + p.text)
    } else {
      out.push(p)
    }
  }
  return out
}

/** Human list: [a] · [a, b] → "a and b" · [a, b, c] → "a, b and c". */
function joinList(items: string[], lang: StandfirstLang): string {
  const c = COPY[lang]
  if (items.length <= 1) return items[0] ?? ''
  return `${items.slice(0, -1).join(c.listComma)}${c.and}${items[items.length - 1]}`
}

export function composeEditionStandfirst(
  readiness: StandfirstReadiness,
  lang: StandfirstLang = 'en',
): EditionStandfirst {
  const c = COPY[lang]
  const empty: EditionStandfirst = { parts: [], belowBar: [], belowBarLine: null, hasProse: false }
  if (!readiness || typeof readiness !== 'object') return empty

  const belowBar = QUESTION_KEYS.filter(k => readiness[k]?.status === 'partial')
  const belowBarLine = belowBar.length > 0
    ? `${c.belowBar}${belowBar.map(k => k.toUpperCase()).join(', ')}.`
    : null

  const whatValues = readyValues(readiness.what)
  const whoValues = readyValues(readiness.who).map(cleanSubjectValue).filter(v => v.length > 0)
  const whereValues = readyValues(readiness.where)
  const whenRange = readiness.when?.status === 'ready'
    ? formatDateRange(readyValues(readiness.when), lang)
    : null
  const howOutlets = readyValues(readiness.how)
  // WHY is never woven: capped at partial by construction backend-side, and
  // even a hypothetical ready WHY carries machine tokens, not prose.

  const parts: StandfirstPart[] = []

  // ---- sentence 1: lead + measured coverage clauses -----------------------
  const clauses: StandfirstPart[][] = []
  if (whereValues.length > 0) {
    const shown = whereValues.slice(0, WHERE_CAP)
    const rem = whereValues.length - shown.length
    const codes = shown.join(' · ') + (rem > 0 ? ` +${rem}` : '')
    clauses.push([text(c.measuredAcross(codes))])
  }
  if (whenRange) clauses.push([text(whenRange)])
  if (howOutlets.length > 0) {
    const shown = howOutlets.slice(0, OUTLET_CAP)
    const rem = howOutlets.length - shown.length
    const how: StandfirstPart[] = [text(c.ledBy)]
    shown.forEach((name, i) => {
      if (i > 0) how.push(text(rem > 0 ? c.listComma : c.and))
      how.push(outletPart(name))
    })
    if (rem > 0) how.push(text(c.moreOutlets(rem)))
    clauses.push(how)
  }

  if (whatValues.length > 0 || clauses.length > 0) {
    parts.push(text(whatValues.length > 0 ? `${c.todaysLead}${whatValues[0]}` : c.coverageOpen))
    clauses.forEach((clause, i) => {
      parts.push(text(i === 0 ? ' — ' : ', '))
      parts.push(...clause)
    })
    parts.push(text('.'))
  }

  // ---- sentence 2: the measured subjects ----------------------------------
  if (whoValues.length > 0) {
    if (parts.length > 0) parts.push(text(' '))
    parts.push(text(`${c.atCenter}${joinList(whoValues.slice(0, WHO_CAP), lang)}.`))
  }

  // ---- sentence 3: the rest of the measured page --------------------------
  if (whatValues.length > 1) {
    if (parts.length > 0) parts.push(text(' '))
    parts.push(text(c.moreStories(whatValues.length - 1)))
  }

  const merged = mergeParts(parts)
  return {
    parts: merged,
    belowBar,
    belowBarLine,
    hasProse: merged.length > 0,
  }
}
