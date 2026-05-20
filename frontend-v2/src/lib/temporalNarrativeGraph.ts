import { resolveCountryName } from './countryNames'
import { getThemeLabel } from './themeLabels'

export type TemporalNodeType = 'theme' | 'country' | 'source' | 'person'

export type TemporalLinkKind =
  | 'country-theme'
  | 'source-country'
  | 'person-country'
  | 'related-theme'

export interface TemporalSignalInput {
  timestamp: string
  country?: string | null
  source?: string | null
  sentiment?: number | null
  otherThemes?: string[]
  persons?: string[]
}

export interface TemporalNarrativeNode {
  id: string
  type: TemporalNodeType
  label: string
  count: number
  sentiment: number
}

export interface TemporalNarrativeLink {
  id: string
  source: string
  target: string
  kind: TemporalLinkKind
  count: number
}

export interface TemporalNarrativeBucket {
  id: string
  label: string
  start: string
  end: string
  signalCount: number
  nodes: TemporalNarrativeNode[]
  links: TemporalNarrativeLink[]
}

export interface BuildTemporalNarrativeGraphInput {
  theme: string
  themeLabel: string
  signals: TemporalSignalInput[]
  maxCountries?: number
  maxRelatedThemes?: number
  maxPeople?: number
  maxSources?: number
}

export interface TemporalNarrativeGraph {
  buckets: TemporalNarrativeBucket[]
}

interface MutableNode {
  id: string
  type: TemporalNodeType
  label: string
  count: number
  sentimentTotal: number
}

function hourStart(timestamp: string): Date | null {
  const date = new Date(timestamp)
  if (!Number.isFinite(date.getTime())) return null
  date.setUTCMinutes(0, 0, 0)
  return date
}

function addNode(nodes: Map<string, MutableNode>, id: string, type: TemporalNodeType, label: string, sentiment: number): void {
  const existing = nodes.get(id)
  if (existing) {
    existing.count += 1
    existing.sentimentTotal += sentiment
    return
  }
  nodes.set(id, { id, type, label, count: 1, sentimentTotal: sentiment })
}

function addLink(links: Map<string, TemporalNarrativeLink>, source: string, target: string, kind: TemporalLinkKind): void {
  if (source === target) return
  const id = `${kind}:${source}->${target}`
  const existing = links.get(id)
  if (existing) {
    existing.count += 1
    return
  }
  links.set(id, { id, source, target, kind, count: 1 })
}

function rankNodes(nodes: TemporalNarrativeNode[]): TemporalNarrativeNode[] {
  return [...nodes].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}

export function buildTemporalNarrativeGraph(input: BuildTemporalNarrativeGraphInput): TemporalNarrativeGraph {
  const maxCountries = input.maxCountries ?? 12
  const maxRelatedThemes = input.maxRelatedThemes ?? 5
  const maxPeople = input.maxPeople ?? 5
  const maxSources = input.maxSources ?? 8
  const themeId = `theme-${input.theme}`
  const byHour = new Map<string, TemporalSignalInput[]>()

  for (const signal of input.signals) {
    const start = hourStart(signal.timestamp)
    if (!start) continue
    const id = start.toISOString()
    const bucket = byHour.get(id) ?? []
    bucket.push(signal)
    byHour.set(id, bucket)
  }

  const buckets = Array.from(byHour.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([id, signals]) => {
      const nodes = new Map<string, MutableNode>()
      const links = new Map<string, TemporalNarrativeLink>()

      addNode(nodes, themeId, 'theme', input.themeLabel, 0)

      const countryCounts = new Map<string, number>()
      const sourceCounts = new Map<string, number>()
      for (const signal of signals) {
        const country = signal.country?.trim().toUpperCase()
        if (country) countryCounts.set(country, (countryCounts.get(country) ?? 0) + 1)
        const source = signal.source?.trim()
        if (!source) continue
        sourceCounts.set(source, (sourceCounts.get(source) ?? 0) + 1)
      }
      const allowedCountries = new Set(
        Array.from(countryCounts.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, maxCountries)
          .map(([country]) => country),
      )
      const allowedSources = new Set(
        Array.from(sourceCounts.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, maxSources)
          .map(([source]) => source),
      )

      for (const signal of signals) {
        const sentiment = signal.sentiment ?? 0
        const country = signal.country?.trim().toUpperCase()
        const source = signal.source?.trim()
        const countryId = country && allowedCountries.has(country) ? `country-${country}` : null

        if (countryId && country) {
          addNode(nodes, countryId, 'country', resolveCountryName(country), sentiment)
          addLink(links, countryId, themeId, 'country-theme')
        }

        if (source && countryId && allowedSources.has(source)) {
          const sourceId = `source-${source}`
          addNode(nodes, sourceId, 'source', source, sentiment)
          addLink(links, sourceId, countryId, 'source-country')
        }

        for (const person of (signal.persons ?? []).slice(0, maxPeople)) {
          if (!person || !countryId) continue
          const personId = `person-${person}`
          addNode(nodes, personId, 'person', person, sentiment)
          addLink(links, personId, countryId, 'person-country')
        }

        for (const relatedTheme of (signal.otherThemes ?? []).slice(0, maxRelatedThemes)) {
          if (!relatedTheme) continue
          const relatedThemeId = `theme-${relatedTheme}`
          addNode(nodes, relatedThemeId, 'theme', getThemeLabel(relatedTheme), sentiment)
          addLink(links, themeId, relatedThemeId, 'related-theme')
        }
      }

      const start = new Date(id)
      const end = new Date(start.getTime() + 60 * 60 * 1000)
      const allNodes = Array.from(nodes.values()).map(node => ({
        id: node.id,
        type: node.type,
        label: node.label,
        count: node.count,
        sentiment: node.count > 0 ? node.sentimentTotal / node.count : 0,
      }))
      const retainedIds = new Set<string>([themeId])
      const nodeCaps: Record<TemporalNodeType, number> = {
        theme: maxRelatedThemes + 1,
        country: maxCountries,
        source: maxSources,
        person: maxPeople * 2,
      }

      for (const type of Object.keys(nodeCaps) as TemporalNodeType[]) {
        rankNodes(allNodes.filter(node => node.type === type && node.id !== themeId))
          .slice(0, nodeCaps[type])
          .forEach(node => retainedIds.add(node.id))
      }

      const finalNodes = rankNodes(allNodes.filter(node => retainedIds.has(node.id)))
      const finalLinks = Array.from(links.values())
        .filter(link => retainedIds.has(link.source) && retainedIds.has(link.target))
        .sort((a, b) => b.count - a.count)

      return {
        id,
        label: start.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
        start: start.toISOString(),
        end: end.toISOString(),
        signalCount: signals.length,
        nodes: finalNodes,
        links: finalLinks,
      }
    })

  return { buckets }
}
