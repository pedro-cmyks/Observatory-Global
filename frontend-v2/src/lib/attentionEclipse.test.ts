import { describe, it, expect } from 'vitest'
import {
  shouldShowEclipse,
  eclipseDominantLine,
  formatEclipseItem,
  buildEclipsePin,
  type EclipseData,
  type EclipseItem,
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
