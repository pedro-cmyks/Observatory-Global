import { describe, it, expect } from 'vitest'
import { buildSections, nodesQueryFor, readNodesResponse, type LaneStatuses, type LensPayload } from './lensSections'

const full: LensPayload = {
  countries: [{ code: 'IL', name: 'Israel', count: 68 }, { code: 'PS', name: 'Gaza Strip', count: 31 }],
  connected: [{ id: 'dynamic-topic-99', label: 'Gaza aid corridor', receipt: '2 countries shared' }],
  attention: [{ source: 'politics@lemmy.world', title: 'Trump says Iran facing last chance', score: 0.89 }],
}

describe('buildSections', () => {
  it('renders a populated section with its rows', () => {
    const s = buildSections(full)
    expect(s.whereItLives.state).toBe('ok')
    expect(s.whereItLives.rows).toHaveLength(2)
    expect(s.connected.state).toBe('ok')
    expect(s.attention.state).toBe('ok')
  })

  it('states an honest reason instead of hiding an empty section', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] })
    expect(s.whereItLives).toEqual({ state: 'empty', reason: 'No country resolved for this scope.', rows: [] })
    expect(s.connected).toEqual({ state: 'empty', reason: 'No measured neighbour cleared the bar.', rows: [] })
    expect(s.attention).toEqual({ state: 'empty', reason: 'No public attention matched this scope.', rows: [] })
  })

  it('marks a lane degraded rather than pretending it is empty', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'db_error' })
    expect(s.connected.state).toBe('degraded')
    expect(s.connected.reason).toBe('Neighbours could not be measured right now.')
  })

  it('never drops a receipt from a connected row', () => {
    const s = buildSections(full)
    expect(s.connected.rows[0]).toMatchObject({ label: 'Gaza aid corridor', receipt: '2 countries shared' })
  })

  // --- the states three could not express -----------------------------------

  it('does not call an unanswered lane empty', () => {
    // The defect this guards is one this codebase already shipped and removed:
    // a timed-out lane rendered as "No results", so the heaviest subjects
    // looked emptiest. "Not measured yet" must not read as "measured none".
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'loading' })
    expect(s.connected.state).toBe('loading')
    expect(s.connected.reason).toBe('Measuring the neighbourhood…')
    expect(s.connected.reason).not.toBe('No measured neighbour cleared the bar.')
  })

  it('keeps rows it already has while more are in flight', () => {
    const s = buildSections(full, { whereItLives: 'loading' })
    expect(s.whereItLives.state).toBe('ok')
    expect(s.whereItLives.rows).toHaveLength(2)
  })

  it('says nothing was measured, not that nothing matched, when there is no subject', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'no_anchor' })
    expect(s.connected.state).toBe('empty')
    expect(s.connected.reason).toBe('Open a thread, a country or a person — neighbours are measured against a subject.')
  })

  it('says a scope has no such lane rather than claiming a measured zero', () => {
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'unavailable' })
    expect(s.connected.state).toBe('empty')
    expect(s.connected.reason).toBe('Neighbours are not measured for this scope yet.')
  })

  it('reports a failing lane as degraded even when it returned some rows', () => {
    // Partial data from a broken lane is still partial. Rendering it as `ok`
    // would present an unknown fraction of the neighbourhood as all of it.
    const s = buildSections(full, { connected: 'timeout' })
    expect(s.connected.state).toBe('degraded')
    expect(s.connected.rows).toHaveLength(1)
  })

  // --- the receipt bar, and not being silent about it -----------------------

  it('drops an unreceipted neighbour and counts the drop', () => {
    const s = buildSections({
      countries: [],
      connected: [
        { id: 'a', label: 'Has a basis', receipt: '2 countries shared' },
        { id: 'b', label: 'No basis', receipt: '' },
        { id: 'c', label: 'Blank basis', receipt: '   ' },
      ],
      attention: [],
    })
    expect(s.connected.rows.map((r) => r.id)).toEqual(['a'])
    expect(s.connected.withheld).toBe(2)
  })

  it('leaves withheld unset when nothing was withheld', () => {
    // Pins the shape the empty-section assertion above depends on: a section
    // nothing was withheld from carries exactly three keys.
    expect(buildSections(full).connected.withheld).toBeUndefined()
  })

  it('still states a reason when the receipt bar is what emptied the section', () => {
    const s = buildSections({
      countries: [],
      connected: [{ id: 'b', label: 'No basis', receipt: '' }],
      attention: [],
    })
    expect(s.connected.state).toBe('empty')
    expect(s.connected.reason).toBe('No measured neighbour cleared the bar.')
    expect(s.connected.withheld).toBe(1)
  })

  it('gives every section a reason whenever it has no rows to show', () => {
    // The rule that must hold across all of the above: never blank and silent.
    const cases: LaneStatuses[] = [
      {}, { connected: 'loading' }, { connected: 'no_anchor' },
      { connected: 'unavailable' }, { connected: 'db_error' }, { connected: 'timeout' },
    ]
    for (const lanes of cases) {
      const s = buildSections({ countries: [], connected: [], attention: [] }, lanes)
      for (const sec of [s.whereItLives, s.connected, s.attention]) {
        expect(sec.rows).toHaveLength(0)
        expect(sec.state).not.toBe('ok')
        expect(sec.reason && sec.reason.length > 0).toBe(true)
      }
    }
  })
})

describe('nodesQueryFor', () => {
  it('asks the endpoint for the scope it is actually naming', () => {
    // Pins the mapping measured against the live endpoint: a thread is
    // `focus_type=theme`, and it genuinely narrows (dynamic-topic-9987
    // returned 20 countries led by IR 60, against 177 led by US 21,149
    // globally). A wrong key here would return the global field and print it
    // under the thread's name.
    expect(nodesQueryFor({ kind: 'thread', id: 'dynamic-topic-9987' }))
      .toContain('focus_type=theme&focus_value=dynamic-topic-9987')
    expect(nodesQueryFor({ kind: 'country', id: 'UA' }))
      .toContain('focus_type=country&focus_value=UA')
    expect(nodesQueryFor({ kind: 'person', id: 'donald trump' }))
      .toContain('focus_type=person&focus_value=donald%20trump')
  })

  it('asks for the whole field, unfocused, at field scope', () => {
    const q = nodesQueryFor({ kind: 'field', id: '*' })
    expect(q).toBeTruthy()
    expect(q).not.toContain('focus_type')
  })

  it('refuses to guess a key for a scope the endpoint cannot answer', () => {
    // null means "never asked", which the section states differently from
    // "asked and got nothing". Guessing would put a real-looking country list
    // under a scope it was never measured for.
    for (const kind of ['story', 'attention', 'chokepoint', 'signal']) {
      expect(nodesQueryFor({ kind, id: 'x' })).toBeNull()
    }
  })

  it('escapes a scope id that would otherwise break the query', () => {
    expect(nodesQueryFor({ kind: 'person', id: 'a&b=c' }))
      .toContain('focus_value=a%26b%3Dc')
  })
})

describe('readNodesResponse', () => {
  it('reads a real payload into ranked rows', () => {
    const { rows, lane } = readNodesResponse({
      nodes: [
        { id: 'US', name: 'United States', signalCount: 14 },
        { id: 'IR', name: 'Iran', signalCount: 60 },
      ],
    })
    expect(lane).toBe('ok')
    expect(rows.map((r) => r.code)).toEqual(['IR', 'US'])
  })

  it('treats an EMPTY-STRING error as a failure, not as a measured zero', () => {
    // The load-bearing case. /api/v2/nodes answers 200 on failure
    // (workspace.py:412 `except Exception as e: return {..., "error": str(e)}`)
    // and a timeout stringifies to ''. Truthiness-testing the value would call
    // this success and print "No country resolved for this scope." over a query
    // that never ran. Measured: five consecutive identical calls returned
    // count=0/error='' four times and count=20 once.
    const { rows, lane } = readNodesResponse({ nodes: [], count: 0, error: '', hours: 24 })
    expect(lane).toBe('db_error')
    expect(rows).toEqual([])
    // And the section must then say so, rather than claim an absence.
    const s = buildSections({ countries: rows, connected: [], attention: [] }, { whereItLives: lane })
    expect(s.whereItLives.state).toBe('degraded')
    expect(s.whereItLives.reason).toBe('Where this lives could not be measured right now.')
  })

  it('still reports a failure when the error string is populated', () => {
    expect(readNodesResponse({ nodes: [], error: 'boom' }).lane).toBe('db_error')
  })

  it('accepts a genuinely empty success as a measured zero', () => {
    // No `error` key at all is the success shape — an empty list then really
    // does mean no country resolved, and the section may say so.
    const { rows, lane } = readNodesResponse({ nodes: [], count: 0, hours: 24 })
    expect(lane).toBe('ok')
    expect(rows).toEqual([])
    expect(buildSections({ countries: rows, connected: [], attention: [] }, { whereItLives: lane }).whereItLives.reason)
      .toBe('No country resolved for this scope.')
  })

  it('does not trust a malformed body', () => {
    expect(readNodesResponse(null).lane).toBe('db_error')
    expect(readNodesResponse({ nodes: 'not-an-array' }).lane).toBe('db_error')
  })

  it('resolves names through the caller and caps the list', () => {
    const { rows } = readNodesResponse(
      { nodes: [{ id: 'YE', signalCount: 3 }, { id: 'IR', signalCount: 60 }] },
      { resolveName: (c) => (c === 'YE' ? 'Yemen' : c), cap: 1 },
    )
    expect(rows).toEqual([{ code: 'IR', name: 'IR', count: 60 }])
  })
})
