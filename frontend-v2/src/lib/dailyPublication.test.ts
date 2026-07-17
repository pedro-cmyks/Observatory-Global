import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

import {
  assessDailyPublication,
  publicationThreads,
  type DailyPublicationArtifact,
} from './dailyPublication'

function artifact(status: 'ready' | 'degraded' = 'ready'): DailyPublicationArtifact {
  return {
    contract: 'atlas-daily-publication-v1',
    edition_date: '2026-07-13',
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

describe('daily publication compatibility gate', () => {
  it('uses the shared package only when the sealed artifact is ready and complete', () => {
    expect(assessDailyPublication(artifact())).toEqual({
      useSharedPackage: true,
      reasonCodes: [],
    })

    const degraded = artifact('degraded')
    degraded.completion.cursor_exhausted = false
    expect(assessDailyPublication(degraded)).toEqual({
      useSharedPackage: false,
      reasonCodes: ['edition_degraded', 'candidate_universe_incomplete'],
    })
  })

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

  it('keeps the legacy Brief as an explicit fallback until the shared edition passes', () => {
    const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')
    expect(source).toContain('/api/v2/investigation/daily-publication')
    expect(source).toContain('assessDailyPublication(dailyEdition)')
    expect(source).toContain('dailyGate.useSharedPackage ? publicationThreads(dailyEdition)')
    // The staleness banner announces the live fallback honestly (sealed/live split).
    expect(source).toContain('buildStaleBanner')
    expect(source).toContain('LIVE VIEW')
  })
})
