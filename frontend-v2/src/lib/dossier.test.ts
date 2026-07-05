import { describe, expect, it } from 'vitest'
import { buildDossier, dossierToMarkdown } from './dossier'
import type { Investigation } from './workbench'

const NOW = '2026-06-26T12:00:00Z'

function inv(pins: Investigation['pins']): Investigation {
  return {
    id: 'i1', title: 'Russia oil refineries', createdAt: NOW, updatedAt: NOW,
    pins,
    trail: [
      { at: '2026-06-26T11:00:00Z', action: 'search', detail: 'russia oil refineries' },
      { at: '2026-06-26T11:30:00Z', action: 'pin', detail: 'Armed conflict escalation' },
    ],
  }
}

describe('dossier', () => {
  it('summarizes the pinned items', () => {
    const d = buildDossier(inv([
      { anchorId: 'a', anchorType: 'thread', label: 'Armed conflict escalation', pinnedAt: NOW,
        snapshot: { capturedAt: NOW, summary: 'Connects to 2 threads', evidence: [{ headline: 'related → Oil and gas supply risk (89%)' }] } },
    ]), NOW)
    expect(d.pinCount).toBe(1)
    expect(d.summary).toContain('Armed conflict escalation')
    expect(d.timeline).toHaveLength(2)
  })

  it('flags keyword-only connections as a gap (honesty)', () => {
    const d = buildDossier(inv([
      { anchorId: 'a', anchorType: 'connections', label: 'Africa elections', pinnedAt: NOW,
        snapshot: { capturedAt: NOW, evidence: [{ headline: 'keyword → Election legitimacy dispute (↔ election)' }] } },
    ]), NOW)
    expect(d.gaps.some(g => /keyword-only/.test(g))).toBe(true)
  })

  it('always notes the frozen-at-pin-time caveat', () => {
    const d = buildDossier(inv([]), NOW)
    expect(d.gaps.some(g => /frozen at pin time/.test(g))).toBe(true)
    expect(d.summary).toMatch(/No pins yet/)
  })

  it('renders markdown with the report sections', () => {
    const md = dossierToMarkdown(buildDossier(inv([
      { anchorId: 'a', anchorType: 'thread', label: 'Armed conflict escalation', pinnedAt: NOW,
        note: 'corroborate with imagery',
        snapshot: { capturedAt: NOW, summary: 's', evidence: [{ headline: 'h', url: 'https://x', source: 'reuters' }] } },
    ]), NOW))
    expect(md).toContain('# Russia oil refineries')
    expect(md).toContain('## Executive summary')
    expect(md).toContain('## Gaps & uncertainty')
    expect(md).toContain('[h](https://x)')
    expect(md).toContain('**Note:** corroborate with imagery')
  })
})

// ── W3 dossier v2 (L3 review 2026-07-05) ─────────────────────────────────────

import { resolveThreadTopicId, resolvePinnedCountries, type DossierEnrichment } from './dossierEnrichment'

function invWith(pins: Partial<import('./workbench').WorkbenchPin>[]): import('./workbench').Investigation {
  return {
    id: 'inv-x', title: 'Peru election', createdAt: '2026-07-05T00:00:00Z',
    updatedAt: '2026-07-05T00:00:00Z',
    pins: pins.map((p, i) => ({
      anchorId: p.anchorId ?? `a-${i}`, anchorType: p.anchorType ?? 'thread',
      label: p.label ?? `Pin ${i}`, pinnedAt: '2026-07-05T00:00:00Z', ...p,
    })) as import('./workbench').WorkbenchPin[],
    trail: [],
  }
}

describe('dossier v2', () => {
  it('groups pins by R3 category, uncategorized last', () => {
    const inv = invWith([
      { anchorId: 'a', category: 'election-legitimacy' },
      { anchorId: 'b' },
      { anchorId: 'c', category: 'election-legitimacy' },
    ])
    const d = buildDossier(inv, '2026-07-05T01:00:00Z')
    expect(d.categoryGroups).toEqual([
      { category: 'election-legitimacy', anchorIds: ['a', 'c'] },
      { category: null, anchorIds: ['b'] },
    ])
  })

  it('renders who-says-what + voice sections in markdown, labeled measured-at-generation', () => {
    const inv = invWith([{ anchorId: 'thread-1', label: 'Election Dispute' }])
    const enrichment: DossierEnrichment = {
      measuredAt: '2026-07-05T01:00:00Z',
      whoSaysWhat: {
        'thread-1': { relationship: 'media-led', evidenceCount: 120, discussionCount: 4, moodCount: 0, rationale: 'evidence 120 outweighs discussion 4' },
      },
      voice: { PE: { selfVoiceRatio: 0.31, dominantOutsider: 'US', stateMediaPct: 5, topForeignOrigins: ['US', 'ES'] } },
    }
    const md = dossierToMarkdown(buildDossier(inv, '2026-07-05T01:00:00Z', enrichment))
    expect(md).toContain('## Who says what (press vs public)')
    expect(md).toContain('press 120 · public 4')
    expect(md).toContain('## Voice (who covers, not just who is covered)')
    expect(md).toContain('self-voice 31%')
    expect(md).toContain('dominant outsider US')
    expect(md).toContain('Measured at generation time')
  })

  it('resolves thread topic ids from research anchors and panel pins', () => {
    expect(resolveThreadTopicId({
      anchorId: 'dynamic-topic-9', anchorType: 'thread', label: 'x', pinnedAt: '',
      open: { surface: 'thread_detail', params: { thread_id: 'dynamic-topic-9' } },
    })).toBe('dynamic-topic-9')
    expect(resolveThreadTopicId({
      anchorId: 'theme-dynamic-topic-452', anchorType: 'theme', label: 'x', pinnedAt: '',
      open: { surface: 'l2_params', params: { urlParams: '?theme=dynamic-topic-452' } },
    })).toBe('dynamic-topic-452')
    expect(resolveThreadTopicId({
      anchorId: 'country-pe', anchorType: 'country', label: 'x', pinnedAt: '', open: null,
    })).toBeNull()
  })

  it('resolves pinned countries from params and anchor ids, capped and deduped', () => {
    const inv = invWith([
      { anchorId: 'country-pe', anchorType: 'country', open: { surface: 'country_brief', params: { country_code: 'PE' } } },
      { anchorId: 'country-CO', anchorType: 'country', open: { surface: 'l2_params', params: { urlParams: '?country=CO' } } },
      { anchorId: 'country-pe2', anchorType: 'country', open: { surface: 'country_brief', params: { country_code: 'PE' } } },
    ])
    expect(resolvePinnedCountries(inv.pins)).toEqual(['PE', 'CO'])
  })
})
