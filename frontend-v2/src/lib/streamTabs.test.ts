import { describe, it, expect } from 'vitest'
import {
  ECLIPSE_DEFAULT_TAB,
  ECLIPSE_TABS,
  STREAM_DEFAULT_TAB,
  STREAM_PRIMARY_TABS,
  STREAM_SECONDARY_TABS,
  TOPIC_PARAM_MAX,
  eclipseTopicParam,
  resolveStreamTab,
  streamRowEclipseClass,
  streamTabModel,
} from './streamTabs'
import type { EclipseData } from './attentionEclipse'

const item = (topic_id: string) => ({
  topic_id, label: topic_id, attention: 10, attention_share: 0.01, consequence: 0.8,
  language_breadth: 3, country_breadth: 9, velocity: 0, lane: 'analyst', reason_codes: [],
})

const DATA: EclipseData = {
  eclipse: true,
  dominant: { topic_id: 'dynamic-topic-8072', label: 'The Final', share: 0.31 },
  window: { top1_share: 0.31 },
  selected: [item('shadow-a'), item('dynamic-topic-99'), item('shadow-c')],
}

describe('streamTabModel', () => {
  it('keeps both category groups outside the lens', () => {
    const m = streamTabModel(false)
    expect(m.eclipse).toBe(false)
    expect(m.primary).toEqual(STREAM_PRIMARY_TABS)
    expect(m.secondary).toEqual(STREAM_SECONDARY_TABS)
    expect(m.defaultTab).toBe(STREAM_DEFAULT_TAB)
  })

  it('collapses to Eclipse/Shadow/All inside the lens', () => {
    const m = streamTabModel(true)
    expect(m.eclipse).toBe(true)
    expect(m.primary).toEqual(ECLIPSE_TABS)
    expect(m.secondary).toEqual([])
  })

  it('defaults to SHADOW in the lens — the reframe, not the eclipsing story', () => {
    expect(streamTabModel(true).defaultTab).toBe('shadow')
    expect(ECLIPSE_DEFAULT_TAB).toBe('shadow')
  })

  it('keeps ALL reachable in the lens as the escape hatch', () => {
    expect(streamTabModel(true).primary).toContain('all')
  })
})

describe('resolveStreamTab', () => {
  it('keeps a valid selection', () => {
    expect(resolveStreamTab('critical', streamTabModel(false))).toBe('critical')
    expect(resolveStreamTab('eclipse', streamTabModel(true))).toBe('eclipse')
  })

  it('falls back to the default when the tab does not exist in the model', () => {
    // entering the lens on a category tab
    expect(resolveStreamTab('maritime', streamTabModel(true))).toBe('shadow')
    // leaving the lens on a lens tab
    expect(resolveStreamTab('shadow', streamTabModel(false))).toBe('notable')
  })

  it('carries ALL across a mode flip in both directions (shared tab)', () => {
    expect(resolveStreamTab('all', streamTabModel(true))).toBe('all')
    expect(resolveStreamTab('all', streamTabModel(false))).toBe('all')
  })
})

describe('eclipseTopicParam', () => {
  it('scopes ECLIPSE to the dominant topic alone', () => {
    expect(eclipseTopicParam('eclipse', DATA)).toBe('dynamic-topic-8072')
  })

  it('scopes SHADOW to every selected topic', () => {
    expect(eclipseTopicParam('shadow', DATA)).toBe('shadow-a,dynamic-topic-99,shadow-c')
  })

  it('leaves ALL unscoped', () => {
    expect(eclipseTopicParam('all', DATA)).toBeNull()
  })

  it('leaves every category tab unscoped', () => {
    for (const tab of [...STREAM_PRIMARY_TABS, ...STREAM_SECONDARY_TABS]) {
      expect(eclipseTopicParam(tab, DATA)).toBeNull()
    }
  })

  it('is null without eclipse data', () => {
    expect(eclipseTopicParam('shadow', null)).toBeNull()
    expect(eclipseTopicParam('eclipse', undefined)).toBeNull()
  })

  it('is null — not empty — when the scope has no ids', () => {
    // An empty `topic=` means "asked, nothing valid" server-side (zero signals).
    // A dominant with no topic_id is not that: there is simply no scope.
    const noDom = { ...DATA, dominant: { label: 'x' } } as EclipseData
    expect(eclipseTopicParam('eclipse', noDom)).toBeNull()
    expect(eclipseTopicParam('shadow', { ...DATA, selected: [] })).toBeNull()
  })

  it('dedupes ids', () => {
    const dup = { ...DATA, selected: [item('a'), item('a'), item('b')] }
    expect(eclipseTopicParam('shadow', dup)).toBe('a,b')
  })

  it('caps the id list at the backend limit', () => {
    const many = { ...DATA, selected: Array.from({ length: 30 }, (_, i) => item(`t-${i}`)) }
    const out = eclipseTopicParam('shadow', many)!
    expect(out.split(',')).toHaveLength(TOPIC_PARAM_MAX)
    expect(out.split(',')[0]).toBe('t-0')
  })

  it('honours an explicit cap', () => {
    expect(eclipseTopicParam('shadow', DATA, 2)).toBe('shadow-a,dynamic-topic-99')
  })
})

describe('streamRowEclipseClass', () => {
  it('tints scoped tabs and nothing else', () => {
    expect(streamRowEclipseClass('eclipse')).toBe('ecl-row-eclipse')
    expect(streamRowEclipseClass('shadow')).toBe('ecl-row-shadow')
    expect(streamRowEclipseClass('story')).toBe('sl-row-scoped')
    expect(streamRowEclipseClass('all')).toBe('')
    expect(streamRowEclipseClass('notable')).toBe('')
  })
})

describe('story lens tab model', () => {
  it('eclipse wins over lens', () => {
    const m = streamTabModel(true, true)
    expect(m.eclipse).toBe(true)
  })
  it('lens model serves story|all with story default', () => {
    const m = streamTabModel(false, true)
    expect(m.lens).toBe(true)
    expect([...m.primary]).toEqual(['story', 'all'])
    expect(m.defaultTab).toBe('story')
  })
  it('mode flip falls back to the new default', () => {
    const lens = streamTabModel(false, true)
    expect(resolveStreamTab('notable', lens)).toBe('story')
  })
})
