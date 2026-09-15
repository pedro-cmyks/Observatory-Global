// The LinkedIn kit's curation pool — WHICH served receipts the analyst gets
// to pick from, in what order.
//
// Campaign review 2026-09-14: the kit offered the 30 most RECENT receipts.
// On an umbrella / grab-bag identity that slice is the worst possible one —
// Ceuta's pool was 6/30 on-story (7 rows of German women's basketball, 6 of
// Trump in Ireland) while 104/200 on-story receipts sat further down. Recency
// is the wrong first key. Relevance to the story's own LABEL is the honest
// one we have client-side: it uses nothing the payload did not serve, it is
// inspectable (the match is shown), and it never hides a receipt — it only
// orders them. Recency stays as the tiebreak.
//
// Pure: no DOM, no fetch.

export interface PoolSignal {
  id?: number
  headline?: string | null
  source?: string | null
  source_lang?: string | null
  timestamp?: string | null
  country?: string | null
  archived?: boolean
}

export interface RankedReceipt<T extends PoolSignal = PoolSignal> {
  signal: T
  /** Number of label tokens the headline matches (0 = no label overlap). */
  score: number
  /** The label tokens that matched — shown in the row so the order is legible. */
  matched: string[]
}

const STOP = new Set([
  // en
  'the', 'and', 'for', 'with', 'from', 'into', 'over', 'after', 'amid', 'says', 'said', 'new', 'news',
  'crisis', 'updates', 'update', 'live', 'latest', 'tensions', 'plan', 'talks', 'deal',
  // es
  'los', 'las', 'del', 'por', 'para', 'con', 'una', 'uno', 'que', 'sobre', 'tras', 'entre',
  // fr / pt / it / de
  'les', 'des', 'dans', 'pour', 'sur', 'avec', 'dos', 'das', 'com', 'para', 'sobre', 'della', 'delle',
  'degli', 'nel', 'nella', 'und', 'der', 'die', 'das', 'mit', 'von', 'nach',
])

/** Lowercase, diacritics folded, punctuation → space. */
export function foldText(s: string | null | undefined): string {
  return (s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

/** The label's content tokens (≥3 chars, no stopwords), deduped, in order. */
export function labelTokens(label: string): string[] {
  const out: string[] = []
  for (const t of foldText(label).split(/\s+/)) {
    if (t.length < 3 || STOP.has(t)) continue
    if (!out.includes(t)) out.push(t)
  }
  return out
}

/** Prefix match on words (ceuta ~ ceutas, migrant ~ migrants/migrantes/migración)
 *  — a 5-char stem is the cheapest cross-language stem we can defend. */
function wordMatches(word: string, token: string): boolean {
  if (word === token) return true
  const stem = token.slice(0, Math.max(5, Math.min(token.length, 6)))
  return token.length >= 5 && word.startsWith(stem)
}

export function scoreHeadline(headline: string | null | undefined, tokens: string[]): string[] {
  if (!headline || tokens.length === 0) return []
  const words = foldText(headline).split(/\s+/)
  const matched: string[] = []
  for (const tok of tokens) {
    if (words.some(w => wordMatches(w, tok))) matched.push(tok)
  }
  return matched
}

/** Rank the served receipts for the curation list: label relevance desc,
 *  then recency desc. Headline-less rows are dropped (nothing to curate). */
export function rankReceiptPool<T extends PoolSignal>(
  signals: T[],
  label: string,
  limit = 60,
): RankedReceipt<T>[] {
  const tokens = labelTokens(label)
  const ranked = signals
    .filter(s => !!s.headline)
    .map(s => {
      const matched = scoreHeadline(s.headline, tokens)
      return { signal: s, score: matched.length, matched }
    })
  ranked.sort((a, b) =>
    b.score - a.score
    || (b.signal.timestamp ?? '').localeCompare(a.signal.timestamp ?? ''),
  )
  return ranked.slice(0, limit)
}

/** Free-text filter over headline + outlet (folded). Empty query = all. */
export function filterPool<T extends PoolSignal>(pool: RankedReceipt<T>[], query: string): RankedReceipt<T>[] {
  const q = foldText(query)
  if (!q) return pool
  return pool.filter(r =>
    foldText(r.signal.headline).includes(q) || foldText(r.signal.source).includes(q),
  )
}

/** Share of the pool that overlaps the label — the number the dialog prints
 *  so an analyst sees a grab-bag before curating it. */
export function poolLabelCoverage(pool: RankedReceipt[]): { onLabel: number; total: number } {
  return { onLabel: pool.filter(r => r.score > 0).length, total: pool.length }
}
