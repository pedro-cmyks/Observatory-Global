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

export function getTrendingSearchesUrl(limit: number, hours: number, countryCode?: string): string {
  const params = new URLSearchParams({
    hours: String(hours),
    limit: String(limit),
  })
  if (countryCode) params.set('country_code', countryCode.toUpperCase())
  return `/api/v2/trends/search?${params.toString()}`
}

export function buildCountryPublicAttentionNarrative({
  countryName,
  signalCount,
  hours,
  topThemes,
  topSearches = [],
  topWikiArticles = [],
}: CountryNarrativeInput): string {
  const readableThemes = topThemes
    .filter(theme => theme.name && !theme.name.startsWith('WORLDLANGUAGES_') && !theme.name.startsWith('TAX_WORLDLANGUAGES_'))
    .slice(0, 3)
    .map(theme => getThemeLabel(theme.name))

  const mediaClause = readableThemes.length > 0
    ? `led by ${compactJoin(readableThemes)}`
    : 'without a dominant media theme yet'

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
