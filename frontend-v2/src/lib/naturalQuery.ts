// X5 · natural-language search bridge (colegio ciego 2026-08-13, persona
// USUARIO-PERDIDO).
//
// The finding, verbatim: "I typed 'what is happening in israel,' pressed Enter
// — nothing, no message, no 'try a country name.' … Three tries, gave up."
//
// Atlas HAS a lane for that question (the cross-thread story / research-plan
// anchors, reachable from the console search's "Open the story" CTA and from
// `/app?q=`). The reader never found it because the surface he typed into — a
// lexical country filter — answers a non-match with an empty dropdown and no
// words. This predicate decides when a zero-hit lexical box should stop being
// silent and NAME that lane instead.
//
// It is deliberately loose: it only ever runs where the lexical answer is
// already nothing, so a false positive costs one honest extra row, while a
// false negative costs the reader the session.

/** Question words that mark a query as a spoken question rather than analyst
 *  vocabulary. Accent-folded, so `qué`/`que` and `cómo`/`como` both match. */
const QUESTION_WORDS = new Set([
  // English
  'what', 'whats', 'why', 'how', 'who', 'whom', 'whose', 'when', 'where',
  'which', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'happening',
  'happened', 'going', 'tell', 'explain',
  // Spanish (accent-folded)
  'que', 'porque', 'porq', 'como', 'quien', 'quienes', 'cuando', 'donde',
  'cual', 'cuales', 'cuanto', 'cuantos', 'pasa', 'pasando', 'paso', 'sucede',
  'sucediendo', 'ocurre', 'ocurriendo', 'esta', 'estan', 'hay', 'explica',
])

function foldTokens(raw: string): string[] {
  return raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .split(/[^a-z0-9']+/)
    .filter(Boolean)
}

/**
 * True when a query reads like a person asking a question rather than naming an
 * entity: it ends in "?", carries a question word, or runs to four-plus words.
 */
export function looksLikeNaturalQuestion(raw: string): boolean {
  const trimmed = (raw ?? '').trim()
  if (!trimmed) return false
  if (trimmed.endsWith('?')) return true
  const tokens = foldTokens(trimmed)
  if (tokens.length === 0) return false
  if (tokens.length >= 4) return true
  return tokens.some(t => QUESTION_WORDS.has(t))
}

/** Cap so the bridge row never blows out a narrow dropdown. */
const MAX_ECHO = 56

/** The bridge's label. It echoes the query the reader ACTUALLY typed — not the
 *  token-stripped form the lexical lane searched on — because the whole point
 *  is that the reader recognizes his own question coming back. */
export function askAtlasLabel(raw: string): string {
  const q = (raw ?? '').trim().replace(/\s+/g, ' ')
  const echo = q.length > MAX_ECHO ? `${q.slice(0, MAX_ECHO - 1).trimEnd()}…` : q
  return `Ask Atlas: “${echo}”`
}
