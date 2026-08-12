import { describe, it, expect } from 'vitest'
import {
  computeFocusRelation,
  relationBasisLabel,
  trackFocusNodes,
  MIN_LEADER_SIGNALS,
} from './focusRelation'

describe('computeFocusRelation (#234 shared focus-relation context)', () => {
  it('no focus → inactive, panels stay global', () => {
    const r = computeFocusRelation({ focusType: null, focusValue: null, filterCountry: null, nodes: [] })
    expect(r.relationActive).toBe(false)
    expect(r.dominantCountry).toBeNull()
  })

  it('country focus → the country is its own dominant', () => {
    const r = computeFocusRelation({ focusType: 'country', focusValue: 'CO', filterCountry: 'CO', nodes: [] })
    expect(r.kind).toBe('country')
    expect(r.dominantCountry).toBe('CO')
    expect(r.relationActive).toBe(true)
  })

  it('person focus → dominant is the top-volume node, relations volume-normalised', () => {
    const r = computeFocusRelation({
      focusType: 'person', focusValue: 'trump', filterCountry: null,
      nodes: [{ id: 'US', signalCount: 2497 }, { id: 'IR', signalCount: 917 }, { id: 'IL', signalCount: 325 }],
    })
    expect(r.dominantCountry).toBe('US')
    expect(r.relationActive).toBe(true)
    expect(r.relationCountries['US']).toBe(1)               // max → weight 1
    expect(r.relationCountries['IR']).toBeCloseTo(917 / 2497, 4)
  })

  it('entity focus with no nodes → inactive (no fabricated relation)', () => {
    const r = computeFocusRelation({ focusType: 'person', focusValue: 'nobody', filterCountry: null, nodes: [] })
    expect(r.relationActive).toBe(false)
  })

  it('theme/thread focus also resolves a dominant country', () => {
    const r = computeFocusRelation({
      focusType: 'theme', focusValue: 'flood', filterCountry: null,
      nodes: [{ id: 'IN', signalCount: 50 }, { id: 'US', signalCount: 80 }],
    })
    expect(r.dominantCountry).toBe('US')
    expect(r.kind).toBe('theme')
  })

  // ── The ghost-scope regression (a cold console rendered "SLOVENIA · OWN
  //    INSTRUMENTS" with no action taken). Two independent defects; these pin
  //    the first one — an arbitrary argmax.

  it('tie on the top count → NO dominant country (never the first node)', () => {
    // /api/v2/nodes is sorted by ANOMALY HEAT, not volume (workspace.py:391),
    // so the first element is structurally the tiniest-corpus country. The old
    // `>`-seeded reduce kept nodes[0] on every tie and handed it the scope.
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 'dynamic-topic-42', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: 7 }, { id: 'US', signalCount: 7 }, { id: 'DE', signalCount: 4 }],
    })
    expect(r.dominantCountry).toBeNull()
    expect(r.relationActive).toBe(false)
    // The field was still measured — dimming/lighting weights survive the
    // refused scope claim (only the *claim* is gated).
    expect(r.relationCountries['SI']).toBe(1)
    expect(r.relationCountries['DE']).toBeCloseTo(4 / 7, 4)
  })

  it('a 1-signal lead never claims a scope (absolute support floor)', () => {
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 'dynamic-topic-42', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: 1 }],
    })
    expect(r.dominantCountry).toBeNull()
    expect(r.relationActive).toBe(false)
  })

  it('a lead below the support floor never claims a scope, even when strict', () => {
    const r = computeFocusRelation({
      focusType: 'person', focusValue: 'someone', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: MIN_LEADER_SIGNALS - 1 }, { id: 'US', signalCount: 1 }],
    })
    expect(r.dominantCountry).toBeNull()
    expect(r.relationActive).toBe(false)
  })

  it('a single country carrying the whole focus IS a genuine leader', () => {
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 'dynamic-topic-7', filterCountry: null,
      nodes: [{ id: 'UA', signalCount: MIN_LEADER_SIGNALS }],
    })
    expect(r.dominantCountry).toBe('UA')
    expect(r.relationActive).toBe(true)
  })

  it('exposes the measured basis: leader count + relation total', () => {
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 'dynamic-topic-42', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: 7 }, { id: 'US', signalCount: 3 }, { id: 'DE', signalCount: 2 }],
    })
    expect(r.dominantCountry).toBe('SI')
    expect(r.leaderSignals).toBe(7)
    expect(r.totalSignals).toBe(12)
  })

  it('nodes without an id are ignored, never counted as the leader', () => {
    const r = computeFocusRelation({
      focusType: 'person', focusValue: 'x', filterCountry: null,
      nodes: [{ id: '', signalCount: 900 }, { id: 'US', signalCount: 40 }],
    })
    expect(r.dominantCountry).toBe('US')
    expect(r.totalSignals).toBe(40)
  })

  it('does not mutate the caller\'s node array (it is context state)', () => {
    const nodes = [{ id: 'DE', signalCount: 2 }, { id: 'US', signalCount: 40 }]
    computeFocusRelation({ focusType: 'person', focusValue: 'x', filterCountry: null, nodes })
    expect(nodes.map(n => n.id)).toEqual(['DE', 'US'])
  })
})

describe('relationBasisLabel (the measured basis panels must print)', () => {
  it('names the leader, the count and the denominator', () => {
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 'dynamic-topic-42', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: 7 }, { id: 'US', signalCount: 3 }, { id: 'DE', signalCount: 2 }],
    })
    expect(relationBasisLabel(r)).toBe('SI leads this thread with 7 of 12 signals')
  })

  it('accepts a display name for the country', () => {
    const r = computeFocusRelation({
      focusType: 'person', focusValue: 'trump', filterCountry: null,
      nodes: [{ id: 'US', signalCount: 20 }, { id: 'IR', signalCount: 5 }],
    })
    expect(relationBasisLabel(r, 'United States')).toBe('United States leads this person with 20 of 25 signals')
  })

  it('has nothing to say when no scope was claimed', () => {
    const r = computeFocusRelation({
      focusType: 'thread', focusValue: 't', filterCountry: null,
      nodes: [{ id: 'SI', signalCount: 7 }, { id: 'US', signalCount: 7 }],
    })
    expect(relationBasisLabel(r)).toBeNull()
  })

  it('has nothing to say for a direct country focus (no discovery happened)', () => {
    const r = computeFocusRelation({ focusType: 'country', focusValue: 'CO', filterCountry: 'CO', nodes: [] })
    expect(relationBasisLabel(r)).toBeNull()
  })
})

describe('trackFocusNodes (stale-nodes guard, mirrors App.tsx fly-to)', () => {
  const globalNodes = [{ id: 'SI', signalCount: 7 }]
  const focusNodes = [{ id: 'US', signalCount: 40 }]

  it('no focus → nothing to track, nothing stale', () => {
    expect(trackFocusNodes(null, null, globalNodes)).toEqual({ tracker: null, stale: false })
  })

  it('the render the focus changes on is STALE — nodes are still the old focus\'s', () => {
    const { tracker, stale } = trackFocusNodes(null, 'thread:dt-42', globalNodes)
    expect(stale).toBe(true)
    expect(tracker).toEqual({ key: 'thread:dt-42', nodesAtChange: globalNodes })
  })

  it('stays stale while the focus-scoped fetch is in flight (same array identity)', () => {
    const first = trackFocusNodes(null, 'thread:dt-42', globalNodes)
    const second = trackFocusNodes(first.tracker, 'thread:dt-42', globalNodes)
    expect(second.stale).toBe(true)
    expect(second.tracker).toBe(first.tracker)   // tracker is not re-seeded
  })

  it('clears once the focus\'s own nodes arrive (new array identity)', () => {
    const first = trackFocusNodes(null, 'thread:dt-42', globalNodes)
    const second = trackFocusNodes(first.tracker, 'thread:dt-42', focusNodes)
    expect(second.stale).toBe(false)
  })

  it('re-arms when the focus changes again', () => {
    const a = trackFocusNodes(null, 'thread:dt-42', globalNodes)
    const b = trackFocusNodes(a.tracker, 'thread:dt-42', focusNodes)
    expect(b.stale).toBe(false)
    const c = trackFocusNodes(b.tracker, 'person:trump', focusNodes)
    expect(c.stale).toBe(true)                   // focusNodes now belong to the PREVIOUS focus
    expect(c.tracker).toEqual({ key: 'person:trump', nodesAtChange: focusNodes })
  })
})
