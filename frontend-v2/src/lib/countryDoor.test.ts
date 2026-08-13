import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import { countryDoorCopy, WAY_BACK } from './countryDoor'

describe('countryDoorCopy — a door that says it is a door', () => {
  it('names the destination country before the click', () => {
    const copy = countryDoorCopy('Tajikistan')
    expect(copy.cue).toBe('Open Tajikistan →')
    expect(copy.tip).toContain('Tajikistan')
    expect(copy.ariaLabel).toContain('Tajikistan')
  })

  it('names the way back in every register — cue, tip, accessible name', () => {
    const copy = countryDoorCopy('Malta')
    expect(copy.tip).toContain(WAY_BACK)
    expect(copy.ariaLabel).toContain(WAY_BACK)
  })

  it('names the scope the reader will land in, matching the console\'s crumb', () => {
    expect(countryDoorCopy('Colombia').tip).toContain('World ▸ Colombia')
  })

  it('warns that the destination is a different, denser surface', () => {
    expect(countryDoorCopy('Yemen').tip).toMatch(/denser surface/)
  })

  it('folds the reason the reader is looking at this country into the tip', () => {
    expect(countryDoorCopy('Rwanda', 'where its heat is measured').tip)
      .toContain('where its heat is measured')
  })

  it('never prints a bare ISO code as the promise', () => {
    const copy = countryDoorCopy('   ')
    expect(copy.cue).toBe('Open this country →')
  })

  it('reads cleanly for a country whose name ends in s', () => {
    // "United States's folder" is how a door announces it was written by a machine.
    expect(countryDoorCopy('United States').tip).not.toContain("States's")
  })
})

describe('BriefNewspaper wiring — every country door speaks with one voice', () => {
  const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')

  it('the heat strip and the back-matter country rows use the shared door copy', () => {
    expect(source).toContain('countryDoorCopy')
  })

  it('the destination still carries the scope the console\'s breadcrumb reads', () => {
    expect(source).toMatch(/country=\$\{h\.code\}/)
  })
})
