// Coarse source-credibility tiers (#217, spec capability G — product face of P2).
//
// The rich, domain-precise ladder lives on the BACKEND
// (backend/app/services/source_tiers.py: reference|wire|mainstream|unknown|
// state|flagged) and reaches ThemeDetail via each evidence row's `credibility`
// payload. But an analyst-pinned receipt (Citation, workbench.ts) carries only a
// bare `source` STRING — no credibility payload. This module is the FRONTEND,
// name-or-domain classifier for exactly those places: the Phase-2 Citations, the
// Brief top-source tags, and the dossier source-mix rollup.
//
// COARSE by design (five buckets an analyst reads at a glance) and HONEST:
//   wire    — international news agencies (syndication roots): AP/Reuters/AFP…
//   state   — state-controlled/affiliated broadcasters (perspective, not falsity)
//   major   — established national/international press (BBC/NYT/Guardian…)
//   local   — a registered/regional outlet with no wire/state/major signal
//   unknown — no signal either way. A REAL tier, never guessed into something
//             better (No Silent Filtering: label the absence, don't invent).
//
// Every classification returns a `provenance` string that says WHY the tier
// holds. wire+state read as "official-ish" for the claim ledger's
// official-source detection (isOfficialishTier).

export type CoarseTier = 'wire' | 'state' | 'major' | 'local' | 'unknown'

/** Ladder order used by rollups + display. */
export const COARSE_TIERS: CoarseTier[] = ['wire', 'state', 'major', 'local', 'unknown']

const TIER_LABEL: Record<CoarseTier, string> = {
  wire: 'WIRE', state: 'STATE', major: 'MAJOR', local: 'LOCAL', unknown: 'UNKNOWN',
}

/** Uppercase display label for a tier chip. */
export function coarseTierLabel(tier: CoarseTier): string {
  return TIER_LABEL[tier]
}

/** Short tooltip copy for a tier chip — the honesty label the analyst reads. */
export const TIER_TIP: Record<CoarseTier, string> = {
  wire: 'International wire agency (syndication root) — an official-ish source.',
  state: 'State-controlled or state-affiliated outlet — a perspective label, weigh accordingly.',
  major: 'Established national / international press.',
  local: 'A registered / regional outlet with no wire, state, or major-press signal.',
  unknown: 'No credibility signal either way — the honest default, not a downgrade.',
}

export interface SourceTierResult {
  tier: CoarseTier
  provenance: string
}

/** wire + state count as "official-ish" (government / wire / state channel) —
 *  feeds the claim ledger's official-source detection. major/local/unknown do not. */
export function isOfficialishTier(tier: CoarseTier): boolean {
  return tier === 'wire' || tier === 'state'
}

// ── curated coarse lists (name substrings + domain suffixes) ────────────────
// `token` entries match the outlet name as a whole-word; `domain` entries match
// the registrable domain on suffix (endsWith). Short/ambiguous tokens (ap, rt,
// efe, dw) are handled with explicit word-boundary regexes below.

const WIRE_DOMAINS = [
  'reuters.com', 'apnews.com', 'ap.org', 'afp.com', 'bloomberg.com', 'efe.com',
  'dpa.com', 'ansa.it', 'kyodonews.net', 'yna.co.kr', 'upi.com', 'ptinews.com',
  'ianslive.in', 'notimex.com',
]
const WIRE_TOKENS = [
  'reuters', 'associated press', 'agence france', 'bloomberg',
  'kyodo', 'yonhap', 'pa media', 'press association',
  'united press international', 'press trust of india', 'notimex',
]

const STATE_DOMAINS = [
  'rt.com', 'sputniknews.com', 'sputnikglobe.com', 'tass.com', 'tass.ru',
  'ria.ru', 'xinhuanet.com', 'news.cn', 'cgtn.com', 'globaltimes.cn',
  'people.com.cn', 'chinadaily.com.cn', 'presstv.ir', 'irna.ir',
  'tasnimnews.com', 'mehrnews.com', 'trtworld.com', 'aa.com.tr', 'cctv.com',
  'kcna.kp', 'granma.cu', 'telesurtv.net', 'sana.sy', 'prensa-latina.cu',
]
const STATE_TOKENS = [
  'russia today', 'sputnik', 'tass', 'ria novosti', 'xinhua', 'cgtn',
  'global times', "people's daily", 'china daily', 'press tv', 'presstv',
  'irna', 'tasnim', 'mehr news', 'trt world', 'anadolu', 'cctv', 'kcna',
  'granma', 'telesur', 'prensa latina',
]

const MAJOR_DOMAINS = [
  'bbc.co.uk', 'bbc.com', 'cnn.com', 'nytimes.com', 'washingtonpost.com',
  'wsj.com', 'theguardian.com', 'ft.com', 'economist.com', 'latimes.com',
  'nbcnews.com', 'abcnews.go.com', 'cbsnews.com', 'foxnews.com', 'npr.org',
  'pbs.org', 'politico.com', 'axios.com', 'theatlantic.com', 'time.com',
  'newsweek.com', 'usatoday.com', 'lemonde.fr', 'lefigaro.fr', 'spiegel.de',
  'zeit.de', 'faz.net', 'elpais.com', 'elmundo.es', 'corriere.it',
  'repubblica.it', 'aljazeera.com', 'aljazeera.net', 'dw.com', 'france24.com',
  'euronews.com', 'thetimes.co.uk', 'telegraph.co.uk', 'independent.co.uk',
]
const MAJOR_TOKENS = [
  'bbc', 'cnn', 'new york times', 'nytimes', 'washington post',
  'wall street journal', 'the guardian', 'financial times', 'the economist',
  'los angeles times', 'nbc news', 'abc news', 'cbs news', 'fox news',
  'the atlantic', 'usa today', 'le monde', 'le figaro', 'der spiegel',
  'die zeit', 'el pais', 'el mundo', 'corriere', 'la repubblica',
  'al jazeera', 'deutsche welle', 'france 24', 'france24', 'euronews',
  'the telegraph', 'the independent', 'newsweek', 'politico', 'axios',
]

// Whole-word regexes for short/ambiguous acronyms (avoid "Apple" matching "AP").
const WIRE_WORDS = /\b(ap|afp|efe|upi|pti|ians|dpa)\b/
const STATE_WORDS = /\b(rt)\b/
const MAJOR_WORDS = /\b(wsj|npr|pbs|dw)\b/

// Positive markers that a bare name is a real (if unrecognized) press outlet →
// local, not unknown. Conservative: only established masthead words.
const PRESS_MARKERS = [
  'times', 'post', 'herald', 'gazette', 'tribune', 'journal', 'observer',
  'chronicle', 'dispatch', 'register', 'bulletin', 'sentinel', 'courier',
  'ledger', 'advertiser', 'advocate', 'mercury', 'telegraph', 'express',
  'standard', 'daily', 'weekly', 'news', 'press', 'record', 'star',
  'globe', 'mirror', 'sun', 'wire',
]

function normalize(source: string | null | undefined): string {
  return (source ?? '').trim().toLowerCase()
}

/** Registrable domain if the source looks like a URL/host, else ''. */
function domainOf(s: string): string {
  let d = s
  if (d.includes('://')) d = d.split('://', 2)[1]
  d = d.split('/', 1)[0]
  d = d.replace(/^www\./, '')
  // Only treat as a domain when it has a dot AND a plausible 2+ char TLD.
  if (/^[a-z0-9.-]+\.[a-z]{2,}$/.test(d)) return d
  return ''
}

function matchDomain(dom: string, list: string[]): boolean {
  if (!dom) return false
  return list.some(d => dom === d || dom.endsWith('.' + d))
}

function matchToken(name: string, tokens: string[]): boolean {
  return tokens.some(t => name.includes(t))
}

/** Classify one outlet name-or-domain into a coarse credibility tier with
 *  provenance. Order: wire > state > major (recognized) > local (registered/
 *  masthead signal) > unknown (honest default). */
export function classifyOutlet(source: string | null | undefined): SourceTierResult {
  const name = normalize(source)
  if (!name) return { tier: 'unknown', provenance: TIER_TIP.unknown }
  const dom = domainOf(name)

  if (matchDomain(dom, WIRE_DOMAINS) || matchToken(name, WIRE_TOKENS) || WIRE_WORDS.test(name)) {
    return { tier: 'wire', provenance: 'International wire agency (syndication root).' }
  }
  if (matchDomain(dom, STATE_DOMAINS) || matchToken(name, STATE_TOKENS) || STATE_WORDS.test(name)) {
    return { tier: 'state', provenance: 'State-controlled or state-affiliated broadcaster.' }
  }
  if (matchDomain(dom, MAJOR_DOMAINS) || matchToken(name, MAJOR_TOKENS) || MAJOR_WORDS.test(name)) {
    return { tier: 'major', provenance: 'Established national / international press.' }
  }
  if (dom) {
    return {
      tier: 'local',
      provenance: 'Registered outlet, not among recognized wire / state / major sources — treated as local/regional.',
    }
  }
  if (matchToken(name, PRESS_MARKERS)) {
    return {
      tier: 'local',
      provenance: 'Name carries an established press masthead marker — treated as local/regional.',
    }
  }
  return { tier: 'unknown', provenance: TIER_TIP.unknown }
}

/** Count a list of source names into the coarse tiers (dossier source mix). */
export function sourceMix(sources: Array<string | null | undefined>): Record<CoarseTier, number> {
  const mix: Record<CoarseTier, number> = { wire: 0, state: 0, major: 0, local: 0, unknown: 0 }
  for (const s of sources) mix[classifyOutlet(s).tier] += 1
  return mix
}

/** "2 wire · 5 major · 11 local · 3 unknown" — ladder order, empty tiers
 *  omitted. Empty string when there are no sources. */
export function formatSourceMix(mix: Record<CoarseTier, number>): string {
  return COARSE_TIERS
    .filter(t => mix[t] > 0)
    .map(t => `${mix[t]} ${t}`)
    .join(' · ')
}
