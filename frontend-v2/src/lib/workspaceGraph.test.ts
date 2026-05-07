import { describe, expect, it } from 'vitest'
import { buildWorkspaceGraph, filterWorkspaceGraph, type WorkspaceGraphInput } from './workspaceGraph'

const baseInput: WorkspaceGraphInput = {
  items: [
    {
      id: 'theme-ARMEDCONFLICT',
      type: 'theme',
      title: 'Armed conflict',
      urlParams: '?theme=ARMEDCONFLICT',
      notes: '',
      timestamp: 1,
    },
    {
      id: 'country-CO',
      type: 'country',
      title: 'Colombia',
      urlParams: '?country=CO',
      notes: '',
      timestamp: 2,
    },
  ],
  details: {
    'theme-ARMEDCONFLICT': {
      relatedThemes: [{ theme: 'TAX_FNCACT_INSURGENT', count: 11 }],
      countryBreakdown: [{ country_code: 'CO', country_name: 'Colombia', count: 22 }],
      topSources: [{ name: 'reuters.com', count: 7 }],
      topPersons: [{ name: 'Example Person', count: 3 }],
    },
    'country-CO': {
      themes: [{ name: 'ARMEDCONFLICT', count: 19 }],
      sources: [{ name: 'reuters.com', count: 4 }],
      keyPersons: [{ name: 'Example Person', count: 2 }],
    },
  },
}

describe('workspaceGraph', () => {
  it('builds pinned and derived nodes with typed relationship links', () => {
    const graph = buildWorkspaceGraph(baseInput)

    expect(graph.nodes.map(n => n.id)).toEqual(expect.arrayContaining([
      'theme-ARMEDCONFLICT',
      'country-CO',
      'theme-TAX_FNCACT_INSURGENT',
      'source-reuters.com',
      'person-Example Person',
    ]))

    expect(graph.links).toEqual(expect.arrayContaining([
      expect.objectContaining({
        source: 'theme-ARMEDCONFLICT',
        target: 'country-CO',
        kind: 'country-framing',
      }),
      expect.objectContaining({
        source: 'country-CO',
        target: 'theme-ARMEDCONFLICT',
        kind: 'shared-theme',
      }),
      expect.objectContaining({
        source: 'theme-ARMEDCONFLICT',
        target: 'source-reuters.com',
        kind: 'shared-source',
      }),
      expect.objectContaining({
        source: 'country-CO',
        target: 'person-Example Person',
        kind: 'co-mentioned-person',
      }),
    ]))
  })

  it('filters nodes and keeps only links whose endpoints remain visible', () => {
    const graph = buildWorkspaceGraph(baseInput)
    const filtered = filterWorkspaceGraph(graph, {
      query: 'colombia',
      nodeTypes: new Set(['country', 'theme', 'source', 'person', 'signal', 'chokepoint', 'public_attention']),
      linkKinds: new Set(['country-framing', 'shared-theme', 'shared-source', 'co-mentioned-person', 'related-theme']),
    })

    expect(filtered.nodes).toHaveLength(1)
    expect(filtered.nodes[0]?.id).toBe('country-CO')
    expect(filtered.links).toHaveLength(0)
  })

  it('builds relationships for public attention pins from unified search data', () => {
    const graph = buildWorkspaceGraph({
      items: [{
        id: 'public-attention-ted-turner',
        type: 'public_attention',
        title: 'Ted Turner',
        urlParams: '?attention=Ted%20Turner',
        notes: '',
        timestamp: 3,
      }],
      details: {
        'public-attention-ted-turner': {
          signal_matches: [
            { country: 'US', source: 'forbes.com', themes: ['MEDIA_MSM'], headline: 'Ted Turner story' },
            { country: 'CA', source: 'edmontonsun.com', themes: ['MEDIA_MSM'], headline: 'Jane Fonda tribute' },
          ],
          themes: [{ theme: 'TAX_FNCACT_BROADCASTER', total_signals: 5 }],
          persons: [{ person: 'Jane Fonda', signal_count: 2 }],
        },
      },
    })

    expect(graph.nodes.map(n => n.id)).toEqual(expect.arrayContaining([
      'public-attention-ted-turner',
      'country-US',
      'country-CA',
      'source-forbes.com',
      'source-edmontonsun.com',
      'theme-MEDIA_MSM',
      'theme-TAX_FNCACT_BROADCASTER',
      'person-Jane Fonda',
    ]))
    expect(graph.links).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'public-attention-ted-turner', target: 'country-US', kind: 'country-framing' }),
      expect.objectContaining({ source: 'public-attention-ted-turner', target: 'theme-MEDIA_MSM', kind: 'shared-theme' }),
      expect.objectContaining({ source: 'public-attention-ted-turner', target: 'source-forbes.com', kind: 'shared-source' }),
      expect.objectContaining({ source: 'public-attention-ted-turner', target: 'person-Jane Fonda', kind: 'co-mentioned-person' }),
    ]))
  })
})
