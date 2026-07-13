import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildInvestigationPublication,
  buildResolveNodeInput,
  buildPublicationReadinessMarkdown,
  type PublicationPackage,
} from './investigationPublication'
import type { WorkbenchPin } from './workbench'

const PINNED_AT = '2026-07-12T12:00:00.000Z'

afterEach(() => vi.unstubAllGlobals())

function pin(overrides: Partial<WorkbenchPin> = {}): WorkbenchPin {
  return {
    anchorId: 'dynamic-topic-42',
    anchorType: 'thread',
    label: 'Water stress in Iran',
    pinnedAt: PINNED_AT,
    snapshot: {
      summary: 'A living narrative thread.',
      evidence: [
        {
          headline: 'Reservoir pressure deepens',
          source: 'Example Wire',
          url: 'https://example.test/receipt',
          date: '2026-07-10',
        },
      ],
    },
    ...overrides,
  }
}

describe('Workbench pin → Investigation Graph node input', () => {
  it('maps a thread to the canonical story adapter and preserves every frozen receipt', () => {
    const p = pin({
      snapshot: {
        evidence: Array.from({ length: 9 }, (_, i) => ({
          headline: `Receipt ${i + 1}`,
          source: 'Example Wire',
          date: `2026-07-${String(i + 1).padStart(2, '0')}`,
        })),
      },
    })

    const input = buildResolveNodeInput(p)

    expect(input.node_type).toBe('story')
    expect(input.subtype).toBe('thread')
    expect(input.ref_id).toBe('dynamic-topic-42')
    expect(input.snapshot.evidence).toHaveLength(9)
    expect(input.observation_window.range_start).toBe('2026-07-01T00:00:00.000Z')
    expect(input.observation_window.range_end).toBe(PINNED_AT)
  })

  it('maps country and event pins without pretending they are narrative threads', () => {
    const country = buildResolveNodeInput(pin({
      anchorId: 'country-ir', anchorType: 'country', label: 'Iran',
      open: { surface: 'country_brief', params: { country_code: 'IR' } },
    }))
    const hazard = buildResolveNodeInput(pin({
      anchorId: 'gdacs-eq-123', anchorType: 'natural_hazard', label: 'Earthquake',
    }))

    expect(country).toMatchObject({ node_type: 'country', subtype: 'country', ref_id: 'IR' })
    expect(hazard).toMatchObject({ node_type: 'event', subtype: 'natural_hazard' })
  })

  it('keeps unknown research anchors as explicit context instead of guessing entity identity', () => {
    const input = buildResolveNodeInput(pin({
      anchorId: 'gap-1', anchorType: 'coverage_gap', label: 'Satellite evidence gap',
    }))

    expect(input).toMatchObject({
      node_type: 'attention',
      subtype: 'coverage_gap',
      quality: { mapping_status: 'explicit_context' },
    })
  })
})

describe('publication readiness export', () => {
  it('renders all six editorial questions and their reason codes', () => {
    const pkg = {
      contract: 'atlas-publication-package-v1',
      title: 'Test',
      authorship: 'analyst',
      generated_at: PINNED_AT,
      readiness: {
        who: { status: 'missing', values: [], reason_codes: ['no_verified_subjects'] },
        what: { status: 'ready', values: ['Water stress in Iran'], reason_codes: [] },
        when: { status: 'ready', values: ['2026-07-10'], reason_codes: [] },
        where: { status: 'partial', values: ['IR'], reason_codes: ['coverage_geography_only_not_subject'] },
        how: { status: 'ready', values: ['Example Wire'], reason_codes: [] },
        why: { status: 'partial', values: ['velocity=+0.12'], reason_codes: ['causal_explanation_not_measured'] },
      },
      narrative_spine: [], who_says_what: {}, gaps: ['semantic_inputs_missing'], receipts: [], method: {}, reproducibility: {},
      prose_status: 'not_requested', article: null,
    } as PublicationPackage

    const markdown = buildPublicationReadinessMarkdown(pkg)

    expect(markdown).toContain('## Editorial readiness (5W+H)')
    expect(markdown).toContain('**Who — missing**')
    expect(markdown).toContain('no verified subjects')
    expect(markdown).toContain('**Why — partial**')
    expect(markdown.match(/^- \*\*/gm)).toHaveLength(6)
    expect(markdown).toContain('**Graph/package gaps:** semantic inputs missing')
  })
})

describe('complete Workbench resolution', () => {
  it('sends every pin through one operational batch without a semantic top-N', async () => {
    const calls: Array<{ url: string; body: Record<string, unknown> }> = []
    const graph = {
      contract: 'atlas-investigation-graph-v1', nodes: [], edges: [], suggestions: [],
      relation_context: {}, unresolved_ledger: [], measured_at: PINNED_AT,
      completion: { requested_nodes: 0, resolved_nodes: 0, requested_pairs: 0, processed_pairs: 0, engines: {}, truncated: false },
    }
    const pkg = {
      contract: 'atlas-publication-package-v1', title: 'Complete', authorship: 'analyst',
      generated_at: PINNED_AT,
      readiness: Object.fromEntries(['who', 'what', 'when', 'where', 'how', 'why'].map(key => [key, {
        status: 'missing', values: [], reason_codes: [],
      }])),
      narrative_spine: [], who_says_what: {}, gaps: [], receipts: [], method: {}, reproducibility: {},
      prose_status: 'not_requested', article: null,
    }
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>
      calls.push({ url, body })
      const response = url.endsWith('/resolve-nodes')
        ? { nodes: [], completion: { requested: 70, processed: 70, truncated: false } }
        : url.endsWith('/graph') ? graph : pkg
      return { ok: true, json: async () => response }
    }))
    const pins = Array.from({ length: 70 }, (_, i) => pin({
      anchorId: `country-X${i}`, anchorType: 'country', label: `Context ${i}`,
    }))

    const result = await buildInvestigationPublication({
      id: 'inv-complete', title: 'Complete', createdAt: PINNED_AT, updatedAt: PINNED_AT,
      pins, trail: [],
    })

    expect(result).not.toBeNull()
    expect(calls).toHaveLength(3)
    expect(calls[0].url).toBe('/api/v2/investigation/resolve-nodes')
    expect(calls[0].body.nodes).toHaveLength(70)
  })
})
