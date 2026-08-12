import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

import {
  editionDegradationLabels,
  publicationThreads,
  resolveEditionServing,
  SEAL_FRESH_MAX_HOURS,
  type DailyPublicationArtifact,
} from './dailyPublication'

function artifact(status: 'ready' | 'degraded' = 'ready'): DailyPublicationArtifact {
  return {
    contract: 'atlas-daily-publication-v1',
    edition_date: '2026-07-13',
    sealed_at: '2026-07-13T02:00:00Z',
    status,
    graph: {
      contract: 'atlas-investigation-graph-v1',
      nodes: [{
        node_id: 'node-story-1',
        node_type: 'story',
        label: 'Iran water pressure',
        live_ref: { kind: 'thread', id: 'dynamic-topic-1' },
        snapshot: {
          edition_role: 'lead',
          live: {
            thread_id: 'dynamic-topic-1',
            signal_count: 18,
            source_count: 4,
            top_countries: ['IR'],
            movement: { velocity: 0.42, surprise: 1.7, prediction_claim: false },
            evidence_samples: [{
              id: 9,
              headline: 'Reservoir levels fall',
              source_name: 'Example',
              source_url: 'https://example.com/9',
              source_lang: 'en',
              timestamp: '2026-07-13T01:00:00Z',
              country_code: 'IR',
            }],
          },
        },
      }],
      edges: [],
      completion: { truncated: false },
    },
    package: {
      contract: 'atlas-publication-package-v1',
      title: 'Atlas Daily Investigation',
      authorship: 'system',
      generated_at: '2026-07-13T02:00:00Z',
      readiness: Object.fromEntries(
        ['who', 'what', 'when', 'where', 'how', 'why'].map(key => [key, {
          status: 'ready', values: [key], reason_codes: [],
        }]),
      ) as DailyPublicationArtifact['package']['readiness'],
      narrative_spine: [],
      who_says_what: {},
      gaps: [],
      receipts: [{ n: 1 }],
      method: { llm_used: false },
      reproducibility: {},
      prose_status: 'not_requested',
      article: null,
    },
    completion: {
      cursor_exhausted: true,
      truncated: false,
      candidate_count: 458,
      rows_scanned: 458,
      data_lag_hours: 2,
      edition_start: '2026-07-12T02:00:00Z',
      edition_end: '2026-07-13T02:00:00Z',
    },
  }
}

describe('daily publication mapping', () => {
  it('maps every story node into the existing newspaper thread contract', () => {
    expect(publicationThreads(artifact())).toEqual([expect.objectContaining({
      thread_id: 'dynamic-topic-1',
      label: 'Iran water pressure',
      signal_count: 18,
      source_count: 4,
      top_countries: ['IR'],
      edition_role: 'lead',
      why_now: 'Measured movement: velocity +0.4200 · surprise 1.7000. Not a forecast.',
      evidence_samples: [expect.objectContaining({
        id: 9,
        source: 'Example',
        url: 'https://example.com/9',
      })],
    })])
  })

  it('keeps the sealed edition wired to the Brief, with the live view as the fallback', () => {
    const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')
    expect(source).toContain('/api/v2/investigation/daily-publication')
    // T3.3: freshness, not status, decides what is served.
    expect(source).toContain('resolveEditionServing(dailyEdition, now)')
    expect(source).toContain("serving.serve === 'sealed' ? publicationThreads(dailyEdition)")
    // The staleness banner announces the live fallback honestly (sealed/live split).
    expect(source).toContain('buildStaleBanner')
    expect(source).toContain('LIVE VIEW')
  })
})

describe('serving policy — a fresh seal is served, its degradation is labelled', () => {
  const now = new Date('2026-07-13T08:00:00Z')

  it('serves a fresh sealed edition even when it sealed degraded', () => {
    const degraded = artifact('degraded')
    degraded.completion.cursor_exhausted = false
    const serving = resolveEditionServing(degraded, now)
    expect(serving.serve).toBe('sealed')
    expect(serving.fresh).toBe(true)
    expect(serving.ageHours).toBe(6)
    // Nothing is hidden: the reasons it sealed degraded become visible labels.
    expect(serving.degradation).toEqual([
      'partial edition · 6 of 6 answered',
      'candidate scan did not finish',
    ])
  })

  it('falls back to live only when no fresh seal exists', () => {
    const stale = artifact()
    stale.sealed_at = '2026-07-11T02:00:00Z'
    const serving = resolveEditionServing(stale, now)
    expect(serving.serve).toBe('live')
    expect(serving.fresh).toBe(false)
    expect(serving.reasonCodes).toContain('seal_stale')

    expect(resolveEditionServing(null, now)).toEqual(expect.objectContaining({
      serve: 'live',
      ageHours: null,
      fresh: false,
      reasonCodes: ['edition_unavailable'],
    }))
  })

  it('holds the freshness window at 26h — an edition sealed 25h ago still serves', () => {
    expect(SEAL_FRESH_MAX_HOURS).toBe(26)
    const almost = artifact()
    almost.sealed_at = new Date(now.getTime() - 25 * 3600_000).toISOString()
    expect(resolveEditionServing(almost, now).serve).toBe('sealed')
    const past = artifact()
    past.sealed_at = new Date(now.getTime() - 26.5 * 3600_000).toISOString()
    expect(resolveEditionServing(past, now).serve).toBe('live')
  })

  it('still refuses an edition it cannot read — freshness never overrides unreadable', () => {
    const broken = artifact()
    broken.graph.nodes = []
    expect(resolveEditionServing(broken, now)).toEqual(expect.objectContaining({
      serve: 'live',
      reasonCodes: ['no_story_nodes'],
    }))

    const mismatch = artifact()
    mismatch.contract = 'atlas-daily-publication-v2' as DailyPublicationArtifact['contract']
    expect(resolveEditionServing(mismatch, now).reasonCodes).toContain('contract_mismatch')

    const undated = artifact()
    undated.sealed_at = null
    expect(resolveEditionServing(undated, now).reasonCodes).toContain('seal_time_unknown')
  })

  it('labels a ready, complete edition with nothing at all', () => {
    expect(resolveEditionServing(artifact(), now).degradation).toEqual([])
  })

  it('reads the readiness fraction from whatever the payload carries', () => {
    const partial = artifact('degraded')
    partial.package.readiness.who = { status: 'missing', values: [], reason_codes: ['no_subject'] }
    partial.package.readiness.why = { status: 'partial', values: [], reason_codes: [] }
    expect(editionDegradationLabels(partial)).toContain('partial edition · 4 of 6 answered, 1 partial')

    // No readiness map at all (an older or future shape) — still labelled, never silent.
    const bare = artifact('degraded')
    bare.package.readiness = undefined as unknown as DailyPublicationArtifact['package']['readiness']
    expect(editionDegradationLabels(bare)).toContain('partial edition')
  })

  it('passes through a backend-served status reason without needing to know it', () => {
    const graded = artifact('degraded')
    graded.status_reasons = ['lead synthesis unavailable']
    expect(editionDegradationLabels(graded)).toContain('lead synthesis unavailable')
  })

  it('names a truncated candidate universe', () => {
    const truncated = artifact()
    truncated.graph.completion.truncated = true
    expect(editionDegradationLabels(truncated)).toEqual(['candidate universe truncated'])
  })
})
