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
  /** True when the headline's script cannot be compared with the label's
   *  (Arabic/Cyrillic/CJK/Hebrew vs a Latin label): NOT off-label — unknown.
   *  Ranked between matched and unmatched rows so a Latin label never pushes
   *  the non-Latin voices out of the pool (the exact voices Atlas exists for). */
  uncomparable: boolean
}

/** Share of letters in the headline that are Latin — under 0.4 the label's
 *  Latin tokens cannot be expected to appear even when the story is the same. */
export function latinShare(text: string | null | undefined): number {
  const letters = (text ?? '').match(/\p{L}/gu) ?? []
  if (letters.length === 0) return 1
  const latin = letters.filter(ch => /\p{Script=Latin}/u.test(ch)).length
  return latin / letters.length
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
  const labelLatin = latinShare(label) >= 0.4
  const ranked = signals
    .filter(s => !!s.headline)
    .map(s => {
      const matched = scoreHeadline(s.headline, tokens)
      const uncomparable = matched.length === 0 && labelLatin && latinShare(s.headline) < 0.4
      return { signal: s, score: matched.length, matched, uncomparable }
    })
  // tier: matched (2) > uncomparable script (1) > unmatched Latin (0)
  const tier = (r: { score: number; uncomparable: boolean }) => (r.score > 0 ? 2 : r.uncomparable ? 1 : 0)
  ranked.sort((a, b) =>
    tier(b) - tier(a)
    || b.score - a.score
    || (b.signal.timestamp ?? '').localeCompare(a.signal.timestamp ?? ''),
  )
  if (ranked.length <= limit) return ranked
  // Reserved seats: when the matched tier alone overflows the limit (an
  // English-heavy story), the non-Latin voices would still be cut. Keep up
  // to UNCOMPARABLE_RESERVE of them by giving back the matched tail.
  const head = ranked.slice(0, limit)
  const reserve = ranked.slice(limit).filter(r => r.uncomparable).slice(0, UNCOMPARABLE_RESERVE)
  if (reserve.length === 0) return head
  const kept = head.slice(0, limit - reserve.length)
  return [...kept, ...reserve]
}

const UNCOMPARABLE_RESERVE = 10

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
