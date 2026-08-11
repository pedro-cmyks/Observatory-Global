import { describe, it, expect } from 'vitest'
import {
  buildSections, connectedLane, nodesQueryFor, readNodesResponse, whereItLivesLane,
  SECTION_LABELS, SHEET_SECTION_NAMES, SOURCES_SECTION_LABEL,
  type LaneStatuses, type LensPayload,
} from './lensSections'

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

  it('separates "the subject was not in the pool" from "the pool held no neighbour"', () => {
    // The #234 relation measures a thread against the ranked pool it is IN. A
    // thread reached by deep link can be outside that pool, and then nothing
    // was compared at all — which is not the same claim as "we compared and
    // found none", the sentence `none` makes.
    const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: 'no_subject' })
    expect(s.connected.state).toBe('empty')
    expect(s.connected.reason).toBe('This story is not in the current ranked field, so no neighbourhood was measured.')
    expect(s.connected.reason).not.toBe('No measured neighbour cleared the bar.')
  })

  it('reports a failing lane as degraded even when it returned some rows', () => {
    // Partial data from a broken lane is still partial. Rendering it as `ok`
    // would present an unknown fraction of the neighbourhood as all of it.
    const s = buildSections(full, { connected: 'db_error' })
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
    // Every status in the union, so adding one without copy fails here rather
    // than shipping a section that is blank and silent.
    const cases: LaneStatuses[] = [
      {}, { connected: 'loading' }, { connected: 'no_anchor' },
      { connected: 'unavailable' }, { connected: 'db_error' },
      { connected: 'no_subject' }, { connected: 'scope_is_self' },
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

describe('connectedLane', () => {
  it('sends a thread away to be measured instead of settling it here', () => {
    // The one scope with a real relation (lib/threadRelation, over the ranked
    // thread pool). `null` means "go and measure"; any sentence returned here
    // would be describing an absence while the section renders rows.
    expect(connectedLane('thread')).toBeNull()
  })

  it('says nothing was attempted at the scopes that have no relation', () => {
    // Not "refused": the ranked walk is keyed by a thread_id (story.py:300),
    // and a `story` scope's id is a free-text research query, so there is no
    // id to ask with. Nothing is attempted at any of these.
    for (const kind of ['story', 'country', 'person', 'attention', 'chokepoint', 'signal']) {
      expect(connectedLane(kind)).toBe('unavailable')
    }
    expect(connectedLane('field')).toBe('no_anchor')
  })

  it('never produces copy claiming a refusal, now that a relation is shown', () => {
    // The rail this reconciliation exists for: no scope may render a sentence
    // about neighbours being withheld while another scope renders receipted
    // neighbour rows. Every settled status here is an "it was not attempted"
    // statement, and none of them mentions a gate.
    for (const kind of ['field', 'story', 'country', 'person', 'attention', 'chokepoint', 'signal']) {
      const lane = connectedLane(kind)
      expect(lane).not.toBeNull()
      const s = buildSections({ countries: [], connected: [], attention: [] }, { connected: lane! })
      expect(s.connected.reason).toBeTruthy()
      expect(s.connected.reason!.toLowerCase()).not.toContain('gate')
      expect(s.connected.reason!.toLowerCase()).not.toContain('withheld')
    }
  })
})

describe('whereItLivesLane', () => {
  it('refuses to ask a question that restates itself', () => {
    // /api/v2/nodes filters `country_code = $1` and groups by f.country_code
    // (workspace.py:202), so a country scope can only ever get itself back —
    // and tapping that row re-scopes to the scope it is already in.
    expect(whereItLivesLane({ kind: 'country', id: 'UA' })).toBe('scope_is_self')
    const s = buildSections(
      { countries: [], connected: [], attention: [] },
      { whereItLives: 'scope_is_self' },
    )
    expect(s.whereItLives.reason).toBe('This scope is a country — its footprint is itself.')
  })

  it('defers to the endpoint for the scopes it can answer', () => {
    expect(whereItLivesLane({ kind: 'field', id: '*' })).toBeNull()
    expect(whereItLivesLane({ kind: 'thread', id: 'dynamic-topic-1' })).toBeNull()
    expect(whereItLivesLane({ kind: 'person', id: 'x' })).toBeNull()
  })

  it('reports the scopes the endpoint has no key for, off ONE list', () => {
    // Shares nodesQueryFor's answer rather than re-listing the kinds, so the
    // lane and the query cannot disagree about what is answerable.
    for (const kind of ['story', 'attention', 'chokepoint', 'signal']) {
      expect(whereItLivesLane({ kind, id: 'x' })).toBe('unavailable')
      expect(nodesQueryFor({ kind, id: 'x' })).toBeNull()
    }
  })

  it('states a reason at every non-measured whereItLives status', () => {
    for (const lane of ['unavailable', 'no_anchor', 'scope_is_self'] as const) {
      const s = buildSections({ countries: [], connected: [], attention: [] }, { whereItLives: lane })
      expect(s.whereItLives.state).toBe('empty')
      expect(s.whereItLives.reason && s.whereItLives.reason.length > 0).toBe(true)
    }
  })
})

describe('SHEET_SECTION_NAMES', () => {
  it('names every section the sheet holds, in anatomy order', () => {
    // The bar is the only promise the reader gets before opening the sheet, so
    // it has to list what is inside — this is the list both of them read.
    // Order is the Lens anatomy's (identity, what it says, where it lives,
    // connected, attention) with `sources` last, since it has no slot in the
    // five and is not going to borrow one.
    expect(SHEET_SECTION_NAMES).toEqual([
      SECTION_LABELS.whereItLives,
      SECTION_LABELS.connected,
      SECTION_LABELS.attention,
      SOURCES_SECTION_LABEL,
    ])
  })

  it('carries the intel organ R4-N29 found missing', () => {
    // Public attention and source health had ZERO mobile surface after the
    // Brief|Lens|Live IA retired the Pulse tab. Both are named here now, which
    // is what makes them reachable — a section absent from this list is a
    // section with no door.
    expect(SHEET_SECTION_NAMES).toContain('attention')
    expect(SHEET_SECTION_NAMES).toContain('sources')
  })

  it('keeps `sources` distinct from `attention`', () => {
    // Source diversity is a fact about the PRESS; attention is a fact about
    // what the public searches and reads. Folding one under the other's
    // heading would mislabel the only number on the surface about outlets.
    expect(SOURCES_SECTION_LABEL).not.toBe(SECTION_LABELS.attention)
    expect(new Set(SHEET_SECTION_NAMES).size).toBe(SHEET_SECTION_NAMES.length)
  })
})
