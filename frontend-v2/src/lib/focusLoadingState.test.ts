/** Council R4 DESKTOP-N26 — the focus panel's loading contract.
 *
 *  Freezes the three properties the council's finding turns on: the wait is
 *  time-boxed, a lane that could not be measured says so, and an unmeasured
 *  count is never rendered as zero.
 */
import { describe, it, expect } from 'vitest'
import {
    FOCUS_SLOW_MS,
    FOCUS_TIMEOUT_MS,
    FOCUS_SLOW_MESSAGE,
    allLanesDegraded,
    focusPhase,
    hasAnyLiveLane,
    isLaneUsable,
    laneGapLabel,
    laneStatus,
    measuredTotal,
    type FocusLanePayload,
} from './focusLoadingState'

const live: FocusLanePayload = {
    lanes: { nodes: 'live', headlines: 'live', persons: 'live', ner: 'live', sources: 'live', related: 'live' },
    degraded_lanes: [],
    degraded_reasons: {},
    summary: { total_signals: 120, total_countries: 4 },
}

const nodesDegraded: FocusLanePayload = {
    lanes: { nodes: 'degraded', headlines: 'live', persons: 'live', ner: 'live', sources: 'live', related: 'live' },
    degraded_lanes: ['nodes'],
    degraded_reasons: { nodes: 'db_busy' },
    summary: { total_signals: null, total_countries: null },
}

describe('focusPhase — the wait is time-boxed', () => {
    it('is an ordinary skeleton before the slow threshold', () => {
        expect(focusPhase(0, false)).toBe('loading')
        expect(focusPhase(FOCUS_SLOW_MS - 1, false)).toBe('loading')
    })

    it('admits the subject is heavy at the threshold — the state that did not exist', () => {
        expect(focusPhase(FOCUS_SLOW_MS, false)).toBe('slow')
        expect(focusPhase(45000, false)).toBe('slow')
    })

    it('never reports slow once the request has settled', () => {
        // The N26 witness was 45-120s mute; settled must win over elapsed.
        expect(focusPhase(120000, true)).toBe('settled')
    })

    it('bounds the client below the observed hang', () => {
        expect(FOCUS_TIMEOUT_MS).toBeLessThan(45000)
        expect(FOCUS_SLOW_MS).toBeLessThan(FOCUS_TIMEOUT_MS)
    })

    it('slow copy names the cause without blaming the connection', () => {
        expect(FOCUS_SLOW_MESSAGE).toMatch(/heavy subject/i)
    })
})

describe('laneStatus — a lane that could not be measured says so', () => {
    it('reports live lanes as usable', () => {
        expect(laneStatus(live, 'nodes')).toBe('live')
        expect(isLaneUsable(live, 'nodes')).toBe(true)
    })

    it('reports a degraded lane as unusable', () => {
        expect(laneStatus(nodesDegraded, 'nodes')).toBe('degraded')
        expect(isLaneUsable(nodesDegraded, 'nodes')).toBe(false)
    })

    it('leaves sibling lanes usable when one degrades — partial render', () => {
        expect(isLaneUsable(nodesDegraded, 'headlines')).toBe(true)
        expect(hasAnyLiveLane(nodesDegraded)).toBe(true)
    })

    it('treats a pre-N26 response shape as live, not as a wall of gaps', () => {
        // A stale cached payload has no `lanes` map; rendering it as all
        // degraded would be its own dishonesty.
        expect(laneStatus({ summary: { total_signals: 5, total_countries: 1 } }, 'nodes')).toBe('live')
    })

    it('treats a missing payload as degraded', () => {
        expect(laneStatus(null, 'nodes')).toBe('degraded')
        expect(hasAnyLiveLane(null)).toBe(false)
    })
})

describe('laneGapLabel — honest grey gap, C4a voice', () => {
    it('names a timeout', () => {
        expect(laneGapLabel(nodesDegraded, 'nodes')).toMatch(/not measured/i)
        expect(laneGapLabel(nodesDegraded, 'nodes')).toMatch(/timed out/i)
    })

    it('distinguishes the deadline reason from a slow query', () => {
        const d: FocusLanePayload = {
            lanes: { related: 'degraded' }, degraded_reasons: { related: 'deadline' },
        }
        expect(laneGapLabel(d, 'related')).toMatch(/ran out of time/i)
    })

    it('never labels a live lane', () => {
        expect(laneGapLabel(live, 'nodes')).toBe('')
    })

    it('never says zero', () => {
        expect(laneGapLabel(nodesDegraded, 'nodes')).not.toMatch(/\b0\b/)
    })
})

describe('measuredTotal — the zero-as-fact guard', () => {
    it('returns the measurement when the lane was live', () => {
        expect(measuredTotal(live, 'total_signals')).toBe(120)
        expect(measuredTotal(live, 'total_countries')).toBe(4)
    })

    it('returns null — never 0 — when the lane degraded', () => {
        // THE trap: an unmeasured lane must not render a confident zero.
        expect(measuredTotal(nodesDegraded, 'total_signals')).toBeNull()
        expect(measuredTotal(nodesDegraded, 'total_countries')).toBeNull()
    })

    it('preserves a genuine measured zero', () => {
        const empty: FocusLanePayload = {
            lanes: { nodes: 'live' }, summary: { total_signals: 0, total_countries: 0 },
        }
        // A live lane that measured nothing IS a fact, and must survive.
        expect(measuredTotal(empty, 'total_signals')).toBe(0)
    })

    it('returns null with no payload at all', () => {
        expect(measuredTotal(null, 'total_signals')).toBeNull()
    })
})

describe('allLanesDegraded — measured nothing vs found nothing', () => {
    it('is true only when every lane failed', () => {
        expect(allLanesDegraded({
            lanes: { nodes: 'degraded', headlines: 'degraded' },
        })).toBe(true)
    })

    it('is false when any lane answered', () => {
        expect(allLanesDegraded(nodesDegraded)).toBe(false)
    })

    it('is false for a live-but-empty person — that is a real answer', () => {
        expect(allLanesDegraded({ lanes: { nodes: 'live' } })).toBe(false)
    })
})
