import type { PinnedItem } from '../contexts/WorkspaceContext'
import { getThemeLabel } from './themeLabels'
import { resolveCountryName } from './countryNames'

export interface DossierSignal {
  id: string
  timestamp: string
  country: string
  source: string
  url: string
  headline: string
  sentiment: number
  themes: string[]
  persons: string[]
}

export interface DossierSection {
  item: PinnedItem
  signals: DossierSignal[]
}

export async function fetchItemSignals(item: PinnedItem, hours = 168, limit = 30): Promise<DossierSignal[]> {
  const params = new URLSearchParams({ hours: String(hours), limit: String(limit) })
  if (item.type === 'theme') {
    const theme = new URLSearchParams(item.urlParams.replace(/^\?/, '')).get('theme') || item.id.replace(/^theme-/, '')
    params.set('theme', theme)
  } else if (item.type === 'country') {
    const country = new URLSearchParams(item.urlParams.replace(/^\?/, '')).get('country') || item.id.replace(/^country-/, '')
    params.set('country_code', country)
  } else if (item.type === 'person') {
    const person = new URLSearchParams(item.urlParams.replace(/^\?/, '')).get('person') || item.id.replace(/^person-/, '')
    params.set('person', person)
  } else {
    return []
  }
  try {
    const res = await fetch(`/api/v2/signals?${params}`)
    if (!res.ok) return []
    const data = await res.json() as { signals?: DossierSignal[] }
    return data.signals ?? []
  } catch {
    return []
  }
}

export interface ThemeSignalExport {
  timestamp: string
  source?: string
  title?: string
  sentiment?: number
  url?: string
}

export interface ThemeExportData {
  theme?: string
  total?: number
  avgSentiment?: number
  signals?: ThemeSignalExport[]
  topSources?: Array<{ name: string; count: number; sentiment?: number; family?: string | null }>
  countryBreakdown?: Array<{ code?: string; country_code?: string; country_name?: string; count: number; sentiment?: number }>
  relatedThemes?: Array<{ theme: string; count: number }>
}

export interface CountryBriefExportData {
  country_code: string
  hours: number
  signal_count: number
  top_themes: Array<{ name: string; count: number }>
  top_sources: Array<{ name: string; count: number }>
  keyPersons: Array<{ name: string; count: number }>
  avg_sentiment: number
  sentiment_trend: 'improving' | 'declining' | 'stable'
  top_stories?: Array<{
    source: string
    url: string
    timestamp: string
    sentiment: number
    themeCode: string
  }>
}

interface WorkspaceThemeDetail {
  topSources?: Array<{ name: string; count: number }>
  countryBreakdown?: Array<{ code?: string; country_code?: string; country_name?: string; count: number }>
  relatedThemes?: Array<{ theme: string; count: number }>
}

interface WorkspaceCountryDetail {
  themes?: Array<{ name: string; count: number }>
  sources?: Array<{ name: string; count: number }>
  keyPersons?: Array<{ name: string; count: number }>
}

export function sanitizeFilenamePart(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'atlas'
}

function formatGeneratedAt(date: Date): string {
  return date.toUTCString()
}

function csvEscape(value: unknown): string {
  const text = String(value ?? '')
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`
  return text
}

export function rowsToCsv(headers: string[], rows: unknown[][]): string {
  return [
    headers.map(csvEscape).join(','),
    ...rows.map(row => row.map(csvEscape).join(',')),
  ].join('\n')
}

export function buildThemeSignalsCsv(signals: ThemeSignalExport[] = []): string {
  return rowsToCsv(
    ['date', 'source', 'title', 'sentiment', 'url'],
    signals.map(signal => [
      signal.timestamp,
      signal.source || 'Unknown',
      signal.title || '',
      signal.sentiment ?? 0,
      signal.url || '',
    ]),
  )
}

export function buildThemeBriefingMarkdown({
  themeName,
  data,
  insight,
  generatedAt = new Date(),
}: {
  themeName: string
  data: ThemeExportData
  insight: string | null
  generatedAt?: Date
}): string {
  let md = `# Atlas Intelligence Briefing: ${themeName}\n\n`
  md += `**Generated:** ${formatGeneratedAt(generatedAt)}\n\n`

  if (insight?.trim()) {
    md += `## AI Insight\n${insight.trim()}\n\n`
  }

  md += `## Metrics\n`
  md += `- **Total Signals:** ${data.total ?? 0}\n`
  md += `- **Average Sentiment:** ${(data.avgSentiment ?? 0).toFixed(2)}\n\n`

  if (data.topSources?.length) {
    md += `## Top Sources\n`
    data.topSources.slice(0, 10).forEach(source => {
      const family = source.family ? ` (${source.family})` : ''
      md += `- ${source.name}: ${source.count} signals${family}\n`
    })
    md += '\n'
  }

  if (data.countryBreakdown?.length) {
    md += `## Top Countries\n`
    data.countryBreakdown.slice(0, 10).forEach(country => {
      const code = country.country_code || country.code || country.country_name || 'Unknown'
      md += `- ${code}: ${country.count} signals\n`
    })
    md += '\n'
  }

  if (data.relatedThemes?.length) {
    md += `## Related Topics\n`
    data.relatedThemes.slice(0, 10).forEach(theme => {
      md += `- ${getThemeLabel(theme.theme)}: ${theme.count} co-occurrences\n`
    })
    md += '\n'
  }

  return md
}

export function buildCountryBriefMarkdown({
  countryName,
  data,
  generatedAt = new Date(),
}: {
  countryName: string
  data: CountryBriefExportData
  generatedAt?: Date
}): string {
  let md = `# Atlas Country Brief: ${countryName}\n\n`
  md += `**Generated:** ${formatGeneratedAt(generatedAt)}\n`
  md += `**Window:** Last ${data.hours}h\n\n`

  md += `## Metrics\n`
  md += `- **Signals:** ${data.signal_count}\n`
  md += `- **Average Sentiment:** ${data.avg_sentiment.toFixed(2)}\n`
  md += `- **Trend:** ${data.sentiment_trend}\n\n`

  if (data.top_themes.length) {
    md += `## Top Themes\n`
    data.top_themes.slice(0, 10).forEach(theme => {
      md += `- ${getThemeLabel(theme.name)}: ${theme.count} signals\n`
    })
    md += '\n'
  }

  if (data.top_sources.length) {
    md += `## Top Sources\n`
    data.top_sources.slice(0, 10).forEach(source => {
      md += `- ${source.name}: ${source.count} signals\n`
    })
    md += '\n'
  }

  if (data.keyPersons.length) {
    md += `## Key People\n`
    data.keyPersons.slice(0, 10).forEach(person => {
      md += `- ${person.name}: ${person.count} mentions\n`
    })
    md += '\n'
  }

  if (data.top_stories?.length) {
    md += `## Recent Signals\n`
    data.top_stories.slice(0, 10).forEach(story => {
      md += `- ${story.source} — ${getThemeLabel(story.themeCode)} — ${story.url}\n`
    })
    md += '\n'
  }

  return md
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function asThemeDetail(detail: unknown): WorkspaceThemeDetail {
  return isRecord(detail) ? detail as WorkspaceThemeDetail : {}
}

function asCountryDetail(detail: unknown): WorkspaceCountryDetail {
  return isRecord(detail) ? detail as WorkspaceCountryDetail : {}
}

export function buildWorkspaceMarkdown({
  items,
  details,
  generatedAt = new Date(),
}: {
  items: PinnedItem[]
  details: Record<string, unknown | undefined>
  generatedAt?: Date
}): string {
  let md = `# Atlas Investigation Workspace\n\n`
  md += `*Exported: ${formatGeneratedAt(generatedAt)}*\n\n---\n\n`

  if (items.length === 0) {
    return `${md}*Workspace is empty.*\n`
  }

  items.forEach(item => {
    md += `## [${item.type.toUpperCase()}] ${item.title}\n`
    md += `- **Pinned on:** ${new Date(item.timestamp).toLocaleString()}\n`
    md += `- **URL Context:** \`${item.urlParams}\`\n\n`

    if (item.notes.trim()) {
      md += `### Notes\n${item.notes}\n\n`
    }

    const detail = details[item.id]
    if (item.type === 'theme') {
      const theme = asThemeDetail(detail)
      if (theme.topSources?.length) {
        md += `### Top Sources\n`
        theme.topSources.slice(0, 8).forEach(source => {
          md += `- ${source.name}: ${source.count} signals\n`
        })
        md += '\n'
      }
      if (theme.countryBreakdown?.length) {
        md += `### Top Countries\n`
        theme.countryBreakdown.slice(0, 8).forEach(country => {
          const code = country.country_code || country.code || country.country_name || 'Unknown'
          md += `- ${code}: ${country.count} signals\n`
        })
        md += '\n'
      }
      if (theme.relatedThemes?.length) {
        md += `### Related Topics\n`
        theme.relatedThemes.slice(0, 8).forEach(themeItem => {
          md += `- ${getThemeLabel(themeItem.theme)}: ${themeItem.count} co-occurrences\n`
        })
        md += '\n'
      }
    }

    if (item.type === 'country') {
      const country = asCountryDetail(detail)
      if (country.themes?.length) {
        md += `### Top Themes\n`
        country.themes.slice(0, 8).forEach(theme => {
          md += `- ${getThemeLabel(theme.name)}: ${theme.count} signals\n`
        })
        md += '\n'
      }
      if (country.sources?.length) {
        md += `### Top Sources\n`
        country.sources.slice(0, 8).forEach(source => {
          md += `- ${source.name}: ${source.count} signals\n`
        })
        md += '\n'
      }
      if (country.keyPersons?.length) {
        md += `### Key People\n`
        country.keyPersons.slice(0, 8).forEach(person => {
          md += `- ${person.name}: ${person.count} mentions\n`
        })
        md += '\n'
      }
    }

    md += `---\n\n`
  })

  return md
}

function sentimentLabel(s: number): string {
  if (s > 0.1) return '+'
  if (s < -0.1) return '−'
  return '·'
}

export function buildDossierMarkdown(sections: DossierSection[], generatedAt = new Date()): string {
  let md = `# Atlas Signal Dossier\n\n`
  md += `*Generated: ${formatGeneratedAt(generatedAt)}*\n`
  md += `*Window: last 7 days · ${sections.reduce((n, s) => n + s.signals.length, 0)} signals across ${sections.length} pinned items*\n\n---\n\n`

  if (sections.length === 0) return `${md}*No pinned items with signals.*\n`

  sections.forEach(({ item, signals }) => {
    md += `## ${item.title}\n`
    md += `*Type: ${item.type}*`
    if (item.notes.trim()) md += ` · *Note: ${item.notes.trim()}*`
    md += '\n\n'

    if (signals.length === 0) {
      md += `*No signals found in window.*\n\n---\n\n`
      return
    }

    signals.forEach(sig => {
      const date = new Date(sig.timestamp).toUTCString().replace(/ GMT$/, ' UTC')
      const country = resolveCountryName(sig.country)
      const sentiment = sentimentLabel(sig.sentiment)
      md += `### ${sentiment} ${sig.headline || '(no headline)'}\n`
      md += `- **Source:** ${sig.source || 'unknown'} · **Country:** ${country}\n`
      md += `- **Date:** ${date}\n`
      if (sig.url) md += `- **URL:** ${sig.url}\n`
      if (sig.persons?.length) md += `- **People:** ${sig.persons.slice(0, 5).join(', ')}\n`
      md += '\n'
    })

    md += `---\n\n`
  })

  return md
}
