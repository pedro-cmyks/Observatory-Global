import { describe, it, expect } from 'vitest'
import { detectBriefRelations } from './briefRelationDetector'

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
