import { getThemeLabel } from './themeLabels'

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
