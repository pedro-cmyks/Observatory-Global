import { describe, it, expect, beforeEach } from 'vitest'
import { parseTouch, captureAcquisition, acquisitionProps, isEmptyTouch } from './acquisition'

class MemStorage {
  m = new Map<string, string>()
  getItem(k: string) { return this.m.has(k) ? this.m.get(k)! : null }
  setItem(k: string, v: string) { this.m.set(k, v) }
  removeItem(k: string) { this.m.delete(k) }
  clear() { this.m.clear() }
  key() { return null }
  get length() { return this.m.size }
}

describe('parseTouch', () => {
  it('reads the campaign UTMs + entry, reduces the referrer to its host', () => {
    const t = parseTouch(
      '?theme=dynamic-topic-42&entry=linkedin&utm_source=linkedin&utm_medium=organic&utm_campaign=sow-2026-w37&utm_content=dynamic-topic-42',
      'https://www.linkedin.com/feed/update/urn:li:activity:123/',
      'atlas.example',
    )
    expect(t).toEqual({
      source: 'linkedin', medium: 'organic', campaign: 'sow-2026-w37',
      content: 'dynamic-topic-42', entry: 'linkedin', ref: 'www.linkedin.com',
    })
  })

  it('absent tags = absent keys; own-origin referrer dropped; junk referrer dropped', () => {
    expect(parseTouch('?theme=x', '', 'atlas.example')).toEqual({})
    expect(parseTouch('', 'https://atlas.example/brief', 'atlas.example')).toEqual({})
    expect(parseTouch('', 'not a url', 'atlas.example')).toEqual({})
    expect(isEmptyTouch(parseTouch('', null))).toBe(true)
  })

  it('clips oversized values — a tag is a label, not a payload', () => {
    const t = parseTouch(`?utm_source=${'x'.repeat(500)}`)
    expect(t.source?.length).toBe(80)
  })
})

describe('captureAcquisition', () => {
  const store = new MemStorage()
  beforeEach(() => {
    store.clear()
    Object.defineProperty(globalThis, 'localStorage', { value: store, configurable: true })
  })

  it('first visit writes first touch; a later tagged visit never rewrites it', () => {
    const a = captureAcquisition('?utm_source=linkedin&utm_campaign=sow-2026-w37', 'https://lnkd.in/x', 'atlas.example', () => '2026-09-11T13:00:00Z')
    expect(a.isNew).toBe(true)
    expect(a.first.campaign).toBe('sow-2026-w37')
    const b = captureAcquisition('?utm_source=twitter', null, 'atlas.example')
    expect(b.isNew).toBe(false)
    expect(b.first.campaign).toBe('sow-2026-w37')   // first touch of record holds
    expect(b.current.source).toBe('twitter')         // today's touch is separate
  })

  it('an untagged direct first visit is recorded as an EMPTY first touch (no later laundering)', () => {
    const a = captureAcquisition('', '', 'atlas.example')
    expect(a.isNew).toBe(true)
    expect(isEmptyTouch(a.first)).toBe(true)
    const b = captureAcquisition('?utm_source=linkedin', null, 'atlas.example')
    expect(isEmptyTouch(b.first)).toBe(true)
    expect(b.current.source).toBe('linkedin')
  })

  it('acquisitionProps only emits non-empty touches', () => {
    const a = captureAcquisition('', '', 'atlas.example')
    expect(acquisitionProps(a)).toEqual({})
    const b = captureAcquisition('?utm_source=linkedin', null, 'atlas.example')
    expect(acquisitionProps(b)).toEqual({ acq: { source: 'linkedin' } })
    expect(acquisitionProps(null)).toEqual({})
  })

  it('storage failure degrades to current-only, never throws', () => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: { getItem() { throw new Error('blocked') }, setItem() { throw new Error('blocked') } },
      configurable: true,
    })
    const a = captureAcquisition('?utm_source=linkedin', null, 'atlas.example')
    expect(a.current.source).toBe('linkedin')
    expect(a.first.source).toBe('linkedin')
  })
})
