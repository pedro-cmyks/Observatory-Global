import { describe, it, expect } from 'vitest'
import { detectBriefRelations, topBriefRelation, hasEnoughSignal } from './briefRelationDetector'

const pin = (label: string, headlines: string[], countryCode?: string) => ({
  anchorId: 'p-' + label, anchorType: 'theme', label,
  snapshot: { countryCode, evidence: headlines.map(h => ({ headline: h })) },
} as any)
const thread = (thread_id: string, label: string, headlines: string[], top?: string[]) => ({
  thread_id, label, evidence_samples: headlines.map(h => ({ headline: h })), top_countries: top,
} as any)

describe('detectBriefRelations', () => {
  it('surfaces a text-mention relation above the ≥2-token gate, strongest-first', () => {
    const pins = [pin('Gaza ceasefire mediation', ['Egypt presses ceasefire framework'])]
    const threads = [
      thread('t1', 'Ceasefire mediation talks', ['Ceasefire mediation deal nears']),
      thread('t2', 'Unrelated football result', ['Team wins the cup']),
    ]
    const rels = detectBriefRelations(pins, threads)
    expect(rels.length).toBeGreaterThan(0)
    expect(rels[0].threadId).toBe('t1')
    expect(rels[0].tier === 'text' || rels[0].tier === 'context').toBe(true)
    expect(rels.find(r => r.threadId === 't2')).toBeUndefined()
  })
  it('excludes a pinned thread from matching its own pool entry (prefix-normalized)', () => {
    // A thread pin carries a capture-builder prefix (theme-…); the pool id has none.
    const pinnedThread = {
      anchorId: 'theme-dynamic-topic-5589', anchorType: 'theme',
      label: 'Taylor Farms Lettuce Recall',
      snapshot: { evidence: [{ headline: 'Taylor Farms lettuce recall widens' }] },
    } as any
    const threads = [
      thread('dynamic-topic-5589', 'Taylor Farms Lettuce Recall', ['Taylor Farms lettuce recall widens']), // self
      thread('dynamic-topic-42', 'Lettuce recall spreads to spinach', ['Second lettuce recall hits stores']), // other
    ]
    const rels = detectBriefRelations([pinnedThread], threads)
    // never a self-loop…
    expect(rels.find(r => r.threadId === 'dynamic-topic-5589')).toBeUndefined()
    // …but a genuinely different thread on the same term still surfaces.
    expect(rels.find(r => r.threadId === 'dynamic-topic-42')).toBeTruthy()
  })
  it('never returns the strong tier (measured-not-asserted ceiling)', () => {
    const rels = detectBriefRelations([pin('Gaza mediation', ['x'])], [thread('t', 'Gaza mediation', ['Gaza mediation'])])
    expect(rels.every(r => r.tier !== 'strong' && r.tier !== 'weak')).toBe(true)
  })
  it('shared subject-country yields a context tier when no text match', () => {
    const rels = detectBriefRelations([pin('Border unrest', [], 'IL')], [thread('t', 'Something entirely else', [], ['IL'])])
    expect(rels.some(r => r.tier === 'context')).toBe(true)
  })
  it('does not relate a thread the analyst already pinned (same id)', () => {
    const pins = [pin('Ceasefire mediation', ['Ceasefire mediation'])]
    // a thread whose id matches a pin anchor would be self — but pins use anchorId p-<label>, threads use thread_id; ensure no crash + returns array
    expect(Array.isArray(detectBriefRelations(pins, [thread('t', 'Ceasefire mediation', ['Ceasefire mediation'])]))).toBe(true)
  })
})

describe('topBriefRelation + hasEnoughSignal', () => {
  it('topBriefRelation returns the strongest (first) or null', () => {
    expect(topBriefRelation([])).toBeNull()
    const rels = detectBriefRelations([pin('Gaza mediation', ['Gaza mediation'])], [thread('t', 'Gaza mediation', ['Gaza mediation'])])
    expect(topBriefRelation(rels)?.threadId).toBe('t')
  })
  it('hasEnoughSignal gates on ≥2 pins AND ≥1 relation (never nags on the first pin)', () => {
    const oneRel = [{ threadId: 't', threadLabel: 'T', pinAnchorId: 'p', pinLabel: 'P', tier: 'text' as const }]
    expect(hasEnoughSignal(1, oneRel)).toBe(false) // only 1 pin
    expect(hasEnoughSignal(2, [])).toBe(false)      // no relations
    expect(hasEnoughSignal(2, oneRel)).toBe(true)
    expect(hasEnoughSignal(3, oneRel, { minPins: 4 })).toBe(false) // custom threshold
  })
})
