import { describe, it, expect } from 'vitest'
import { saveTargetTip, saveTargetToast } from './pinTarget'

describe('pin target copy (council R4 N37)', () => {
  it('says a save will START an investigation when none is open', () => {
    const t = { kind: 'new' as const, id: null, title: null, pinCount: 0 }
    expect(saveTargetTip(t)).toBe('Save — starts a new investigation for this story')
    expect(saveTargetToast(t, 'Kyiv strikes')).toBe('Started “Kyiv strikes” — saved here')
  })

  it('NAMES the open investigation a save would join (never silent mixing)', () => {
    const t = { kind: 'existing' as const, id: 'inv-1', title: 'Ukraine war', pinCount: 3 }
    expect(saveTargetTip(t)).toBe('Save into “Ukraine war” (3 pins) — the investigation now open')
    expect(saveTargetToast(t, 'Kyiv strikes')).toBe('Saved into “Ukraine war” (3 pins)')
  })

  it('keeps the pin count singular at 1 and honest at 0', () => {
    expect(saveTargetTip({ kind: 'existing', id: 'i', title: 'Solo', pinCount: 1 }))
      .toBe('Save into “Solo” (1 pin) — the investigation now open')
    expect(saveTargetTip({ kind: 'existing', id: 'i', title: 'Empty', pinCount: 0 }))
      .toBe('Save into “Empty” (no pins yet) — the investigation now open')
  })

  it('degrades to a neutral name when an existing investigation is untitled', () => {
    expect(saveTargetTip({ kind: 'existing', id: 'i', title: '', pinCount: 2 }))
      .toBe('Save into the open investigation (2 pins)')
  })
})
