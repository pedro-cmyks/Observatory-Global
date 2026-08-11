import { describe, it, expect } from 'vitest'
import {
  shouldShowEclipse,
  eclipseDominantLine,
  eclipseDominantLabel,
  formatEclipseItem,
  buildEclipsePin,
  eclipseTier,
  episodeKey,
  nextEclipseMode,
  applyEclipseAction,
  type EclipseData,
  type EclipseItem,
  type EclipseModeState,
} from './attentionEclipse'

const eclipseOn: EclipseData = {
  eclipse: true,
  dominant: { topic_id: 'sport', label: 'World Cup Final', attention: 9000, share: 0.45, lane: 'sports' },
  window: { top1_share: 0.45, hhi: 0.21 },
  selected: [
    { topic_id: 'dynamic-topic-42', label: 'EU launches $1bn Gaza aid', attention: 42,
      attention_share: 0.001, consequence: 0.67, language_breadth: 4, country_breadth: 18,
      velocity: -0.2, lane: 'general', reason_codes: ['under_radar_selected'] },
  ],
}

describe('shouldShowEclipse', () => {
  it('shows only when eclipsed AND something is under the radar', () => {
    expect(shouldShowEclipse(eclipseOn)).toBe(true)
  })
  it('hides on a diffuse day (no eclipse)', () => {
    expect(shouldShowEclipse({ ...eclipseOn, eclipse: false })).toBe(false)
  })
  it('hides when eclipse is on but nothing cleared the floor', () => {
    expect(shouldShowEclipse({ ...eclipseOn, selected: [] })).toBe(false)
  })
  it('hides on null/undefined payload (silent degrade)', () => {
    expect(shouldShowEclipse(null)).toBe(false)
    expect(shouldShowEclipse(undefined)).toBe(false)
  })
})

describe('eclipseDominantLine', () => {
  it('names the dominant event and its coverage share', () => {
    const line = eclipseDominantLine(eclipseOn)
    expect(line).toContain('World Cup Final')
    expect(line).toContain('45%')
  })
  it('names a category-bucket dominant in human copy, never its slug (N28)', () => {
    const line = eclipseDominantLine(eclipseCategoryDominant)
    expect(line).toContain('Earthquake Volcano Disaster')
    expect(line).not.toContain('earthquake-volcano-disaster')
  })
})

// Council R4 N28 (T-N17 / D-N19 / P-N24, three seats independently): today's
// dominant is `earthquake-volcano-disaster` — an atlas CATEGORY BUCKET whose
// served label IS its raw slug. The once-in-weeks takeover, the ambient ribbon
// and the AnomalyPanel row all read this one resolver.
const eclipseCategoryDominant: EclipseData = {
  ...eclipseOn,
  tier: 'total',
  dominant: { topic_id: 'earthquake-volcano-disaster', label: 'earthquake-volcano-disaster',
              attention: 12000, share: 0.31, lane: 'general', identity_key: undefined },
  window: { top1_share: 0.31, hhi: 0.4 },
}

describe('eclipseDominantLabel (N28: never headline a raw slug)', () => {
  it('resolves a category-bucket slug into human copy', () => {
    expect(eclipseDominantLabel(eclipseCategoryDominant)).toBe('Earthquake Volcano Disaster')
  })
  it('passes a real story label through untouched', () => {
    expect(eclipseDominantLabel(eclipseOn)).toBe('World Cup Final')
  })
  it('never returns an opaque topic id', () => {
    expect(eclipseDominantLabel({
      ...eclipseOn,
      dominant: { topic_id: 'dynamic-topic-8072', label: 'dynamic-topic-8072', share: 0.3 },
    })).toBe('Narrative Thread')
  })
  it('degrades to the honest generic on an empty dominant', () => {
    expect(eclipseDominantLabel({ ...eclipseOn, dominant: {} })).toBe('one story')
    expect(eclipseDominantLabel(null)).toBe('one story')
  })
})

describe('formatEclipseItem', () => {
  it('formats breadth and a rounded share', () => {
    const f = formatEclipseItem(eclipseOn.selected[0])
    expect(f.breadthLabel).toBe('4 languages · 18 countries')
    expect(f.sharePct).toBe('0.1%')
  })
  it('marks a rising story so a fresh eclipsed story is distinguishable', () => {
    expect(formatEclipseItem({ ...eclipseOn.selected[0], velocity: 0.46 }).rising).toBe(true)
    expect(formatEclipseItem({ ...eclipseOn.selected[0], velocity: -0.2 }).rising).toBe(false)
  })
})

describe('buildEclipsePin', () => {
  const item: EclipseItem = eclipseOn.selected[0]

  it('builds a workbench pin that reuses the shared theme/l2_params ramp', () => {
    const pin = buildEclipsePin(item, ' 2026-07-14T00:00:00Z')
    expect(pin.anchorId).toBe('eclipse-dynamic-topic-42')
    expect(pin.anchorType).toBe('theme')
    expect(pin.label).toBe('EU launches $1bn Gaza aid')
    // opens the same console theme surface every other pin uses
    expect(pin.open?.surface).toBe('l2_params')
    expect(pin.open?.params.urlParams).toBe('?theme=dynamic-topic-42&entry=eclipse')
  })

  it('freezes an honest snapshot (why it was under the radar)', () => {
    const pin = buildEclipsePin(item, '2026-07-14T00:00:00Z')
    expect(pin.snapshot?.capturedAt).toBe('2026-07-14T00:00:00Z')
    expect(pin.snapshot?.summary).toContain('under the radar')
    expect(pin.snapshot?.summary).toContain('18 countries')
    expect(pin.snapshot?.metrics?.attention_share).toBe(0.001)
    expect(pin.snapshot?.metrics?.consequence).toBe(0.67)
  })

  it('encodes topic ids safely into the deep link', () => {
    const pin = buildEclipsePin({ ...item, topic_id: 'a b&c' }, 't')
    expect(pin.open?.params.urlParams).toBe('?theme=a%20b%26c&entry=eclipse')
  })
})

const total = (idk = 'k1'): EclipseData => ({
  eclipse: true, tier: 'total', dominant: { topic_id: 't', identity_key: idk },
  window: {}, selected: [],
})

describe('eclipse pure helpers', () => {
  it('eclipseTier falls back to boolean when tier absent', () => {
    expect(eclipseTier({ eclipse: true, dominant: {}, window: {}, selected: [] })).toBe('total')
    expect(eclipseTier({ eclipse: false, dominant: {}, window: {}, selected: [] })).toBe('none')
    expect(eclipseTier(null)).toBe('none')
  })
  it('episodeKey only for total, keyed on identity_key', () => {
    expect(episodeKey(total('abc'))).toBe('abc')
    expect(episodeKey({ eclipse: false, tier: 'partial', dominant: {}, window: {}, selected: [] })).toBeNull()
  })
  it('nextEclipseMode arms takeover once, then ambient, auto-exits', () => {
    const s0: EclipseModeState = { mode: 'normal', seenEpisode: null }
    const s1 = nextEclipseMode(s0, 'total', 'k1')
    expect(s1.mode).toBe('takeover')
    const s2 = nextEclipseMode({ mode: 'ambient', seenEpisode: 'k1' }, 'total', 'k1')
    expect(s2.mode).toBe('ambient')
    const s3 = nextEclipseMode({ mode: 'ambient', seenEpisode: 'k1' }, 'none', null)
    expect(s3).toEqual({ mode: 'normal', seenEpisode: null })
    const s4 = nextEclipseMode({ mode: 'muted', seenEpisode: 'k1' }, 'total', 'k2')
    expect(s4.mode).toBe('takeover')
  })
  it('applyEclipseAction transitions', () => {
    expect(applyEclipseAction({ mode: 'takeover', seenEpisode: 'k' }, 'enter').mode).toBe('ambient')
    expect(applyEclipseAction({ mode: 'ambient', seenEpisode: 'k' }, 'mute').mode).toBe('muted')
    expect(applyEclipseAction({ mode: 'muted', seenEpisode: 'k' }, 'restore').mode).toBe('ambient')
  })
})
