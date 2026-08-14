import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import {
  deskEmptyCopy,
  furnitureNote,
  instrumentReading,
  isUnmeasured,
  laneState,
  laneUnansweredNote,
  mapDensityNote,
  type BriefDesk,
  type BriefLane,
} from './briefLanes'

const ALL_LANES: BriefLane[] = ['stories', 'gaps', 'countries', 'sources', 'themes', 'categories']
const ALL_DESKS: BriefDesk[] = ['world', 'culture', 'gaps', 'country']

/** The judge's phrase — a verdict only a gate that RAN is entitled to print. */
const GATE_VERDICT = /cleared the quality gate/

describe('laneState — reads the payload\'s own degradation report', () => {
  it('serves when nothing is degraded', () => {
    expect(laneState('stories', { degradedSegments: [] })).toBe('served')
    expect(laneState('gaps', {})).toBe('served')
  })

  it('marks the lane unanswered when the backend named its segment', () => {
    expect(laneState('stories', { degradedSegments: ['top_threads'] })).toBe('unanswered')
    expect(laneState('sources', { degradedSegments: ['top_sources', 'theme_country'] })).toBe('unanswered')
  })

  it('does not leak one lane\'s failure into another', () => {
    const evidence = { degradedSegments: ['top_sources'] }
    expect(laneState('sources', evidence)).toBe('unanswered')
    expect(laneState('stories', evidence)).toBe('served')
    expect(laneState('gaps', evidence)).toBe('served')
  })

  it('marks EVERY lane unanswered when the briefing fetch itself failed', () => {
    for (const lane of ALL_LANES) {
      expect(laneState(lane, { briefUnavailable: true })).toBe('unanswered')
      expect(isUnmeasured(lane, { briefUnavailable: true })).toBe(true)
    }
  })

  it('never infers a failure from emptiness — a served lane with zero rows stays served', () => {
    // The inverse sin: claiming an outage because a measurement came back empty.
    expect(laneState('gaps', { degradedSegments: [] })).toBe('served')
    expect(furnitureNote('sources', { degradedSegments: [] }, 0))
      .toBe('Nothing measured in this window.')
  })
})

describe('THE FROZEN WITNESS — a lane that did not answer can never print a gate verdict', () => {
  it('no unanswered desk copy claims the gate reached a verdict', () => {
    for (const desk of ALL_DESKS) {
      expect(deskEmptyCopy(desk, 'unanswered')).not.toMatch(GATE_VERDICT)
    }
  })

  it('a rejected/timeout briefing fetch produces gate-free copy on every desk', () => {
    const evidence = { briefUnavailable: true }
    for (const desk of ALL_DESKS) {
      const state = laneState(desk === 'gaps' ? 'gaps' : 'stories', evidence)
      expect(state).toBe('unanswered')
      expect(deskEmptyCopy(desk, state)).not.toMatch(GATE_VERDICT)
    }
  })

  it('a degraded top_threads segment produces gate-free copy on both story desks', () => {
    const state = laneState('stories', { degradedSegments: ['top_threads'] })
    expect(deskEmptyCopy('world', state)).not.toMatch(GATE_VERDICT)
    expect(deskEmptyCopy('culture', state)).not.toMatch(GATE_VERDICT)
  })

  it('keeps the real verdict verbatim when the lane DID answer', () => {
    expect(deskEmptyCopy('world', 'served')).toMatch(GATE_VERDICT)
    expect(deskEmptyCopy('culture', 'served')).toMatch(GATE_VERDICT)
    expect(deskEmptyCopy('country', 'served')).toMatch(GATE_VERDICT)
  })

  it('a country edition that failed to assemble claims no verdict for that country', () => {
    // The same den, one door deeper: a degraded country build used to print
    // "No coherent story cleared the quality gate for this country".
    expect(deskEmptyCopy('country', 'unanswered')).not.toMatch(GATE_VERDICT)
    expect(deskEmptyCopy('country', 'unanswered')).toMatch(/unknown, not empty/)
  })

  it('no unanswered copy anywhere in the module claims a measured zero', () => {
    const everyUnansweredString = [
      ...ALL_DESKS.map(d => deskEmptyCopy(d, 'unanswered')),
      ...ALL_LANES.map(laneUnansweredNote),
      ...ALL_LANES.map(l => instrumentReading(0, l, { briefUnavailable: true }, 'm').tip),
    ]
    for (const copy of everyUnansweredString) {
      expect(copy).not.toMatch(GATE_VERDICT)
      expect(copy.toLowerCase()).toMatch(/did not answer/)
    }
  })
})

describe('Spanish — the honesty voice survives translation', () => {
  it('every desk still refuses a gate verdict it did not reach', () => {
    for (const desk of ALL_DESKS) {
      expect(deskEmptyCopy(desk, 'unanswered', 'es')).not.toMatch(GATE_VERDICT)
      // …and does not accidentally print the English one either.
      expect(deskEmptyCopy(desk, 'unanswered', 'es')).toMatch(/no respondió|no se pudo/)
    }
  })

  it('a served desk still prints a real verdict, in Spanish', () => {
    for (const desk of ['world', 'culture', 'country'] as BriefDesk[]) {
      expect(deskEmptyCopy(desk, 'served', 'es')).toMatch(/superó|pasó|cleared/)
    }
  })

  it('served and unanswered copy stay DIFFERENT in Spanish (the distinction is the point)', () => {
    for (const desk of ALL_DESKS) {
      expect(deskEmptyCopy(desk, 'served', 'es')).not.toBe(deskEmptyCopy(desk, 'unanswered', 'es'))
    }
  })

  it('every lane names itself in Spanish and still says it did not answer', () => {
    for (const lane of ALL_LANES) {
      const note = laneUnansweredNote(lane, 'es')
      expect(note).toMatch(/no respondió/)
      expect(note).not.toBe(laneUnansweredNote(lane))
    }
  })

  it('an unmeasured tile tip is Spanish; a measured tip is whatever the caller passed', () => {
    expect(instrumentReading(0, 'gaps', { degradedSegments: ['coverage_gaps'] }, 'x', 'es').tip)
      .toMatch(/no respondió/)
    expect(instrumentReading(4, 'gaps', { degradedSegments: [] }, 'consejo medido', 'es').tip)
      .toBe('consejo medido')
  })

  it('furniture and the map speak Spanish too', () => {
    expect(furnitureNote('themes', { degradedSegments: [] }, 0, 'es'))
      .toBe('Nada medido en esta ventana.')
    expect(mapDensityNote({ degradedSegments: ['top_countries'] }, 0, 'es'))
      .toMatch(/no respondió/)
  })

  it('defaults to English when no language is passed — every existing caller is untouched', () => {
    expect(deskEmptyCopy('world', 'served')).toBe(deskEmptyCopy('world', 'served', 'en'))
    expect(laneUnansweredNote('gaps')).toBe(laneUnansweredNote('gaps', 'en'))
    expect(furnitureNote('themes', {}, 0)).toBe(furnitureNote('themes', {}, 0, 'en'))
  })
})

describe('instrumentReading — a tile never fabricates a zero', () => {
  it('prints the measured count and its own tip when the lane answered', () => {
    const reading = instrumentReading(4, 'gaps', { degradedSegments: [] }, 'categories with attention')
    expect(reading).toEqual({ value: '4', unmeasured: false, tip: 'categories with attention' })
  })

  it('prints an em dash + reason when the lane did not answer', () => {
    const reading = instrumentReading(0, 'gaps', { degradedSegments: ['coverage_gaps'] }, 'measured tip')
    expect(reading.value).toBe('—')
    expect(reading.unmeasured).toBe(true)
    expect(reading.tip).toContain('coverage-gap lane did not answer')
    expect(reading.tip).not.toBe('measured tip')
  })

  it('prints an em dash for the story count when the story lane died', () => {
    // The judge's pair: "Tracked stories 0" beside a console full of stories.
    const reading = instrumentReading(0, 'stories', { degradedSegments: ['top_threads'] }, 'ranked stories')
    expect(reading.value).toBe('—')
  })

  it('a real measured zero still prints 0 — absence that WAS measured is a finding', () => {
    expect(instrumentReading(0, 'gaps', { degradedSegments: [] }, 't').value).toBe('0')
  })

  it('formats large counts for the reader', () => {
    expect(instrumentReading(41898, 'countries', {}, 't').value).toBe('41,898')
  })
})

describe('furniture — a heading never stands over a silent void', () => {
  it('says nothing when the section has rows', () => {
    expect(furnitureNote('sources', { degradedSegments: ['top_sources'] }, 5)).toBeNull()
  })

  it('names the failed lane under an empty heading', () => {
    expect(furnitureNote('sources', { degradedSegments: ['top_sources'] }, 0))
      .toContain('source lane did not answer')
  })

  it('says plainly that nothing was measured when the lane answered empty', () => {
    expect(furnitureNote('themes', { degradedSegments: [] }, 0))
      .toBe('Nothing measured in this window.')
  })

  it('the grey map speaks with the same voice', () => {
    expect(mapDensityNote({ degradedSegments: ['top_countries'] }, 0))
      .toContain('country lane did not answer')
    expect(mapDensityNote({ degradedSegments: [] }, 180)).toBeNull()
  })
})

describe('BriefNewspaper wiring — the copy has exactly one home', () => {
  const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')

  it('the page carries no gate-verdict string of its own', () => {
    // If this fails, someone re-inlined a verdict where the lane check cannot
    // reach it — which is exactly how the outage got dressed as an editorial
    // principle the first time.
    expect(source).not.toMatch(GATE_VERDICT)
  })

  it('the page reads the payload\'s degradation report', () => {
    expect(source).toContain('degraded_segments')
  })

  it('the page renders desk emptiness through the lane-aware copy', () => {
    expect(source).toContain('deskEmptyCopy')
    expect(source).toContain('instrumentReading')
    expect(source).toContain('furnitureNote')
  })
})
