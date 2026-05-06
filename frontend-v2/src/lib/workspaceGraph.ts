import { resolveCountryName } from './countryNames'
import { getThemeLabel } from './themeLabels'
import type { PinnedItem, PinnedItemType } from '../contexts/WorkspaceContext'

export type WorkspaceLinkKind =
  | 'shared-theme'
  | 'shared-source'
  | 'country-framing'
  | 'co-mentioned-person'
  | 'related-theme'

export interface WorkspaceGraphNode {
  id: string
  type: PinnedItemType
  title: string
  subtitle?: string
  pinned: boolean
  weight: number
  urlParams?: string
  sourceItemId?: string
}

export interface WorkspaceGraphLink {
  id: string
  source: string
  target: string
  kind: WorkspaceLinkKind
  label: string
  weight: number
}

export interface WorkspaceGraph {
  nodes: WorkspaceGraphNode[]
  links: WorkspaceGraphLink[]
}

export interface WorkspaceGraphFilters {
  query: string
  nodeTypes: Set<PinnedItemType>
  linkKinds: Set<WorkspaceLinkKind>
}

interface ThemeDetailGraphData {
  relatedThemes?: Array<{ theme: string; count: number }>
  countryBreakdown?: Array<{ country_code: string; country_name?: string; count: number }>
  topSources?: Array<{ name: string; count: number }>
  topPersons?: Array<{ name: string; count: number }>
}

interface CountryDetailGraphData {
  themes?: Array<{ name: string; count: number }>
  sources?: Array<{ name: string; count: number }>
  keyPersons?: Array<{ name: string; count: number }>
}

interface FocusGraphData {
  nodes?: Array<{ country_code: string; signal_count: number }>
  related_topics?: Array<{ topic: string; count: number }>
  top_sources?: Array<{ source: string; count: number }>
}

interface SourceProfileGraphData {
  top_themes?: Array<{ theme: string; count: number }>
  top_countries?: Array<{ country_code: string; count: number }>
}

export interface WorkspaceGraphInput {
  items: PinnedItem[]
  details: Record<string, unknown | undefined>
}

export const WORKSPACE_NODE_TYPES: PinnedItemType[] = ['theme', 'country', 'source', 'person', 'signal', 'chokepoint']

export const WORKSPACE_LINK_KINDS: WorkspaceLinkKind[] = [
  'shared-theme',
  'shared-source',
  'country-framing',
  'co-mentioned-person',
  'related-theme',
]

const MAX_DERIVED_PER_GROUP = 8

function themeId(theme: string): string {
  return `theme-${theme}`
}

function countryId(code: string): string {
  return `country-${code.toUpperCase()}`
}

function sourceId(source: string): string {
  return `source-${source}`
}

function personId(person: string): string {
  return `person-${person}`
}

function addNode(nodes: Map<string, WorkspaceGraphNode>, node: WorkspaceGraphNode): void {
  const existing = nodes.get(node.id)
  if (!existing) {
    nodes.set(node.id, node)
    return
  }

  nodes.set(node.id, {
    ...existing,
    ...node,
    pinned: existing.pinned || node.pinned,
    weight: Math.max(existing.weight, node.weight),
    urlParams: existing.urlParams ?? node.urlParams,
  })
}

function addLink(links: Map<string, WorkspaceGraphLink>, source: string, target: string, kind: WorkspaceLinkKind, weight: number): void {
  if (source === target) return
  const id = `${kind}:${source}->${target}`
  const existing = links.get(id)
  if (existing) {
    links.set(id, { ...existing, weight: Math.max(existing.weight, weight) })
    return
  }

  links.set(id, {
    id,
    source,
    target,
    kind,
    label: kind.replace(/-/g, ' '),
    weight,
  })
}

function parseThemeFromItem(item: PinnedItem): string {
  const params = new URLSearchParams(item.urlParams.replace(/^\?/, ''))
  return params.get('theme') || item.id.replace(/^theme-/, '').split('-')[0] || item.title
}


function addThemeRelationships(
  item: PinnedItem,
  detail: ThemeDetailGraphData,
  nodes: Map<string, WorkspaceGraphNode>,
  links: Map<string, WorkspaceGraphLink>,
): void {
  const rootTheme = parseThemeFromItem(item)
  const rootId = item.id

  for (const related of (detail.relatedThemes ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = themeId(related.theme)
    addNode(nodes, {
      id,
      type: 'theme',
      title: getThemeLabel(related.theme),
      subtitle: `${related.count.toLocaleString()} co-signals`,
      pinned: false,
      weight: related.count,
      sourceItemId: item.id,
      urlParams: `?theme=${encodeURIComponent(related.theme)}`,
    })
    addLink(links, rootId, id, 'related-theme', related.count)
  }

  for (const country of (detail.countryBreakdown ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = countryId(country.country_code)
    addNode(nodes, {
      id,
      type: 'country',
      title: resolveCountryName(country.country_code, country.country_name),
      subtitle: `${country.count.toLocaleString()} signals`,
      pinned: false,
      weight: country.count,
      sourceItemId: item.id,
      urlParams: `?country=${encodeURIComponent(country.country_code)}&theme=${encodeURIComponent(rootTheme)}`,
    })
    addLink(links, rootId, id, 'country-framing', country.count)
  }

  for (const source of (detail.topSources ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = sourceId(source.name)
    addNode(nodes, {
      id,
      type: 'source',
      title: source.name,
      subtitle: `${source.count.toLocaleString()} signals`,
      pinned: false,
      weight: source.count,
      sourceItemId: item.id,
    })
    addLink(links, rootId, id, 'shared-source', source.count)
  }

  for (const person of (detail.topPersons ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = personId(person.name)
    addNode(nodes, {
      id,
      type: 'person',
      title: person.name,
      subtitle: `${person.count.toLocaleString()} mentions`,
      pinned: false,
      weight: person.count,
      sourceItemId: item.id,
      urlParams: `?person=${encodeURIComponent(person.name)}`,
    })
    addLink(links, rootId, id, 'co-mentioned-person', person.count)
  }
}

function addCountryRelationships(
  item: PinnedItem,
  detail: CountryDetailGraphData,
  nodes: Map<string, WorkspaceGraphNode>,
  links: Map<string, WorkspaceGraphLink>,
): void {
  const rootId = item.id

  for (const theme of (detail.themes ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = themeId(theme.name)
    addNode(nodes, {
      id,
      type: 'theme',
      title: getThemeLabel(theme.name),
      subtitle: `${theme.count.toLocaleString()} signals`,
      pinned: false,
      weight: theme.count,
      sourceItemId: item.id,
      urlParams: `?theme=${encodeURIComponent(theme.name)}`,
    })
    addLink(links, rootId, id, 'shared-theme', theme.count)
  }

  for (const source of (detail.sources ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = sourceId(source.name)
    addNode(nodes, {
      id,
      type: 'source',
      title: source.name,
      subtitle: `${source.count.toLocaleString()} signals`,
      pinned: false,
      weight: source.count,
      sourceItemId: item.id,
    })
    addLink(links, rootId, id, 'shared-source', source.count)
  }

  for (const person of (detail.keyPersons ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = personId(person.name)
    addNode(nodes, {
      id,
      type: 'person',
      title: person.name,
      subtitle: `${person.count.toLocaleString()} mentions`,
      pinned: false,
      weight: person.count,
      sourceItemId: item.id,
      urlParams: `?person=${encodeURIComponent(person.name)}`,
    })
    addLink(links, rootId, id, 'co-mentioned-person', person.count)
  }
}

function addFocusRelationships(
  item: PinnedItem,
  detail: FocusGraphData,
  nodes: Map<string, WorkspaceGraphNode>,
  links: Map<string, WorkspaceGraphLink>,
): void {
  const rootId = item.id

  for (const node of (detail.nodes ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = countryId(node.country_code)
    addNode(nodes, {
      id,
      type: 'country',
      title: resolveCountryName(node.country_code),
      subtitle: `${node.signal_count.toLocaleString()} signals`,
      pinned: false,
      weight: node.signal_count,
      sourceItemId: item.id,
      urlParams: `?country=${encodeURIComponent(node.country_code)}`,
    })
    addLink(links, rootId, id, 'country-framing', node.signal_count)
  }

  for (const topic of (detail.related_topics ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = themeId(topic.topic)
    addNode(nodes, {
      id,
      type: 'theme',
      title: getThemeLabel(topic.topic),
      subtitle: `${topic.count.toLocaleString()} signals`,
      pinned: false,
      weight: topic.count,
      sourceItemId: item.id,
      urlParams: `?theme=${encodeURIComponent(topic.topic)}`,
    })
    addLink(links, rootId, id, 'shared-theme', topic.count)
  }

  for (const source of (detail.top_sources ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = sourceId(source.source)
    addNode(nodes, {
      id,
      type: 'source',
      title: source.source,
      subtitle: `${source.count.toLocaleString()} signals`,
      pinned: false,
      weight: source.count,
      sourceItemId: item.id,
    })
    addLink(links, rootId, id, 'shared-source', source.count)
  }
}

function addSourceRelationships(
  item: PinnedItem,
  detail: SourceProfileGraphData,
  nodes: Map<string, WorkspaceGraphNode>,
  links: Map<string, WorkspaceGraphLink>,
): void {
  const rootId = item.id

  for (const theme of (detail.top_themes ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = themeId(theme.theme)
    addNode(nodes, {
      id,
      type: 'theme',
      title: getThemeLabel(theme.theme),
      subtitle: `${theme.count.toLocaleString()} signals`,
      pinned: false,
      weight: theme.count,
      sourceItemId: item.id,
      urlParams: `?theme=${encodeURIComponent(theme.theme)}`,
    })
    addLink(links, rootId, id, 'shared-theme', theme.count)
  }

  for (const country of (detail.top_countries ?? []).slice(0, MAX_DERIVED_PER_GROUP)) {
    const id = countryId(country.country_code)
    addNode(nodes, {
      id,
      type: 'country',
      title: resolveCountryName(country.country_code),
      subtitle: `${country.count.toLocaleString()} signals`,
      pinned: false,
      weight: country.count,
      sourceItemId: item.id,
      urlParams: `?country=${encodeURIComponent(country.country_code)}`,
    })
    addLink(links, rootId, id, 'country-framing', country.count)
  }
}

export function buildWorkspaceGraph({ items, details }: WorkspaceGraphInput): WorkspaceGraph {
  const nodes = new Map<string, WorkspaceGraphNode>()
  const links = new Map<string, WorkspaceGraphLink>()

  for (const item of items) {
    addNode(nodes, {
      id: item.id,
      type: item.type,
      title: item.title,
      subtitle: item.notes.trim() ? 'Pinned with notes' : undefined,
      pinned: true,
      weight: 100,
      urlParams: item.urlParams,
    })
  }

  for (const item of items) {
    const detail = details[item.id]
    if (!detail) continue

    if (item.type === 'theme') {
      addThemeRelationships(item, detail as ThemeDetailGraphData, nodes, links)
    } else if (item.type === 'country') {
      addCountryRelationships(item, detail as CountryDetailGraphData, nodes, links)
    } else if (item.type === 'person') {
      addFocusRelationships(item, detail as FocusGraphData, nodes, links)
    } else if (item.type === 'source') {
      addSourceRelationships(item, detail as SourceProfileGraphData, nodes, links)
    }
  }

  return {
    nodes: [...nodes.values()],
    links: [...links.values()],
  }
}

export function filterWorkspaceGraph(graph: WorkspaceGraph, filters: WorkspaceGraphFilters): WorkspaceGraph {
  const query = filters.query.trim().toLowerCase()
  const nodes = graph.nodes.filter(node => {
    if (!filters.nodeTypes.has(node.type)) return false
    if (!query) return true
    return `${node.title} ${node.subtitle ?? ''} ${node.type}`.toLowerCase().includes(query)
  })
  const visibleIds = new Set(nodes.map(node => node.id))
  const links = graph.links.filter(link => {
    return filters.linkKinds.has(link.kind)
      && visibleIds.has(String(link.source))
      && visibleIds.has(String(link.target))
  })

  return { nodes, links }
}
