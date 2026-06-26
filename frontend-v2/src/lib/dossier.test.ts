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
