import { getThemeLabel } from './themeLabels'

const PUBLIC_ATTENTION_WIKI_DAYS = 7

interface CountryNarrativeInput {
  countryName: string
  signalCount: number
  hours: number
  topThemes: Array<{ name: string; count: number }>
  topSearches?: Array<{ keyword: string; rank?: number | null }>
  topWikiArticles?: Array<{ title: string; views?: number | null }>
}

export interface PublicAttentionOrigin {
  title: string
  views?: number
  country_count?: number
  query?: string
  country?: string
  countryName?: string
  /** When the origin is a single signal (e.g. a forum post), its id — lets the
   *  panel mount the "Where this fits" ConnectionsSection (truncated thread). */
  signalId?: number
}

function compactJoin(items: string[]): string {
  if (items.length <= 1) return items[0] ?? ''
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`
}

export function getPublicAttentionTopUrl(limit: number, countryCode?: string): string {
  const params = new URLSearchParams({
    days: String(PUBLIC_ATTENTION_WIKI_DAYS),
    limit: String(limit),
  })
  if (countryCode) params.set('country_code', countryCode.toUpperCase())
  return `/api/v2/wiki/top?${params.toString()}`
}

// Use 72h window — Google Trends RSS is rate-limited from cloud IPs for high-volume
// countries (US/BR/MX), so data can be 24-48h stale. Better to show stale than empty.
export function getTrendingSearchesUrl(limit: number, hours: number, countryCode?: string): string {
  const params = new URLSearchParams({
    hours: String(Math.max(hours, 72)),
    limit: String(limit),
  })
  if (countryCode) params.set('country_code', countryCode.toUpperCase())
  return `/api/v2/trends/search?${params.toString()}`
}

// Forum discussion lane (Reddit). Country-scoped uses a wider 14-day window
// because forum volume is thin; global uses 7 days.
export function getForumAttentionUrl(limit: number, countryCode?: string): string {
  const params = new URLSearchParams({
    limit: String(limit),
    hours: countryCode ? '336' : '168',
  })
  if (countryCode) params.set('country', countryCode.toUpperCase())
  return `/api/v2/public-attention?${params.toString()}`
}

export function buildCountryPublicAttentionNarrative({
  countryName,
  signalCount,
  hours,
  topThemes,
  topSearches = [],
  topWikiArticles = [],
  topThread,
}: CountryNarrativeInput & { topThread?: { label: string; count: number; trend?: string | null } }): string {
  const readableThemes = topThemes
    .filter(theme => theme.name && !theme.name.startsWith('WORLDLANGUAGES_') && !theme.name.startsWith('TAX_WORLDLANGUAGES_'))
    .slice(0, 3)
    .map(theme => getThemeLabel(theme.name))

  const mediaClause = readableThemes.length > 0
    ? `led by ${compactJoin(readableThemes)}`
    : 'without a dominant media theme yet'

  // D9 (Pedro's review): the reader wants the STORY first — "Sudán shows 138
  // signals led by conflict… people include Agnes" says nothing. Lead with the
  // country's top narrative thread when one exists.
  if (topThread?.label) {
    const trendBit = topThread.trend === 'surging' ? ' and accelerating'
      : topThread.trend === 'fading' ? ' but fading' : ''
    const attentionBits2: string[] = []
    if (topSearches.length > 0) attentionBits2.push(`searches around ${compactJoin(topSearches.slice(0, 2).map(i => i.keyword))}`)
    if (topWikiArticles.length > 0) attentionBits2.push(`Wikipedia reads on ${compactJoin(topWikiArticles.slice(0, 1).map(i => i.title))}`)
    const attn = attentionBits2.length > 0 ? ` Public attention: ${attentionBits2.join('; ')}.` : ''
    return `“${topThread.label}” leads ${countryName}'s coverage — ${topThread.count.toLocaleString()} signals${trendBit}, within ${signalCount.toLocaleString()} total this ${hours}h window.${attn}`
  }

  const attentionBits: string[] = []
  if (topSearches.length > 0) {
    attentionBits.push(`public attention is visible around ${compactJoin(topSearches.slice(0, 2).map(item => item.keyword))}`)
  }
  if (topWikiArticles.length > 0) {
    attentionBits.push(`Wikipedia attention is concentrated on ${compactJoin(topWikiArticles.slice(0, 2).map(item => item.title))}`)
  }

  const attentionClause = attentionBits.length > 0
    ? ` On the people-side layer, ${attentionBits.join('; ')}.`
    : ' Public-attention proxies are quiet or unavailable for this country in the current window.'

  return `${countryName} shows ${signalCount.toLocaleString()} signals in this ${hours}h window, ${mediaClause}.${attentionClause}`
}
