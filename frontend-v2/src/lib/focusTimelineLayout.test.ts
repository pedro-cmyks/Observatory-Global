import { describe, it, expect } from 'vitest'
import {
    divergingSplit,
    barPixels,
    maxVolume,
    assignSubjectColors,
    SUBJECT_LINE_PALETTE,
    lastPresentIndex,
    subjectLinePoints,
    subjectEndsEarly,
    buildSubjectSeries,
    maxPresence,
    isChannelUsable,
    channelGapLabel,
    emptyTimelineCopy,
    dissolvedKind,
    dissolvedLabel,
    isDissolvedType,
    summarizeChanges,
    describeDiffWindow,
    formatSpanHours,
    dormantForSubject,
    type TimelineBucket,
    type KeySubjectCandidate,
    type EdgeChange,
    type DormantRelationship,
    type SnapshotIntervalInfo,
} from './focusTimelineLayout'

// ------------------------------------------------------------ diverging split
describe('divergingSplit (sentiment by position, extent = volume)', () => {
    it('splits a neutral bucket 50/50 and keeps total === count', () => {
        const s = divergingSplit(100, 0)
        expect(s.up).toBe(50)
        expect(s.down).toBe(50)
        expect(s.total).toBe(100)
    })

    it('sends a fully-positive bucket entirely UP', () => {
        const s = divergingSplit(80, 1)
        expect(s.up).toBe(80)
        expect(s.down).toBe(0)
        expect(s.up + s.down).toBe(80)
    })

    it('sends a fully-negative bucket entirely DOWN', () => {
        const s = divergingSplit(80, -1)
        expect(s.up).toBe(0)
        expect(s.down).toBe(80)
    })

    it('treats null sentiment as neutral (no fabricated lean)', () => {
        expect(divergingSplit(40, null)).toEqual({ up: 20, down: 20, total: 40 })
    })

    it('clamps out-of-range tone rather than overshooting the volume', () => {
        // avg tone reported as +5 on a ±1 scale must not push up past count
        const s = divergingSplit(60, 5)
        expect(s.up).toBe(60)
        expect(s.down).toBe(0)
    })

    it('is a no-op for an empty bucket', () => {
        expect(divergingSplit(0, 0.5)).toEqual({ up: 0, down: 0, total: 0 })
    })

    it('honors a wider sentiment scale via sentFull', () => {
        // GDELT-style ±10 tone: +5 on a ±10 scale = 75% up
        const s = divergingSplit(100, 5, 10)
        expect(s.up).toBe(75)
        expect(s.down).toBe(25)
    })
})

describe('barPixels', () => {
    it('maps the max-volume all-positive bucket to the full up-band', () => {
        const { upH, downH } = barPixels(100, 1, 100, 60)
        expect(upH).toBe(60)
        expect(downH).toBe(0)
    })
    it('splits a neutral bucket across both half-bands', () => {
        const { upH, downH } = barPixels(100, 0, 100, 60)
        expect(upH).toBe(30)
        expect(downH).toBe(30)
    })
    it('is safe when the scale is degenerate', () => {
        expect(barPixels(50, 0.2, 0, 60)).toEqual({ upH: 0, downH: 0 })
        expect(barPixels(50, 0.2, 100, 0)).toEqual({ upH: 0, downH: 0 })
    })
})

describe('maxVolume', () => {
    it('returns the largest bucket count', () => {
        const buckets = [
            mkBucket('a', 10, 0),
            mkBucket('b', 40, 0),
            mkBucket('c', 25, 0),
        ]
        expect(maxVolume(buckets)).toBe(40)
    })
    it('is 0 for no buckets', () => {
        expect(maxVolume([])).toBe(0)
    })
})

// ------------------------------------------------------------ color stability
describe('assignSubjectColors (stable color per entity)', () => {
    it('assigns palette colors in candidate order', () => {
        const m = assignSubjectColors(['Trump', 'Zelensky', 'Putin'])
        expect(m.get('trump')).toBe(SUBJECT_LINE_PALETTE[0])
        expect(m.get('zelensky')).toBe(SUBJECT_LINE_PALETTE[1])
        expect(m.get('putin')).toBe(SUBJECT_LINE_PALETTE[2])
    })

    it('is case-insensitive on lookup', () => {
        const m = assignSubjectColors(['Angela Merkel'])
        expect(m.get('angela merkel')).toBe(SUBJECT_LINE_PALETTE[0])
    })

    it('keeps the same color regardless of later candidates (order-stable)', () => {
        const a = assignSubjectColors(['A', 'B', 'C'])
        const b = assignSubjectColors(['A', 'B', 'C', 'D'])
        expect(a.get('b')).toBe(b.get('b'))
    })

    it('dedupes repeated names and skips blanks', () => {
        const m = assignSubjectColors(['A', '', 'A', 'B'])
        expect(m.size).toBe(2)
        expect(m.get('a')).toBe(SUBJECT_LINE_PALETTE[0])
        expect(m.get('b')).toBe(SUBJECT_LINE_PALETTE[1])
    })

    it('cycles the palette when there are more subjects than colors', () => {
        const names = SUBJECT_LINE_PALETTE.map((_, i) => `s${i}`).concat('overflow')
        const m = assignSubjectColors(names)
        expect(m.get('overflow')).toBe(SUBJECT_LINE_PALETTE[0])
    })
})

// ------------------------------------------------------------ line shape
describe('line end detection (a line that ends = connection died)', () => {
    it('finds the last non-zero bucket', () => {
        expect(lastPresentIndex([0, 0.3, 0.1, 0, 0])).toBe(2)
    })
    it('returns -1 for an all-zero series', () => {
        expect(lastPresentIndex([0, 0, 0])).toBe(-1)
    })

    it('drops trailing zeros so the polyline stops at the last mention', () => {
        const pts = subjectLinePoints([0.2, 0.4, 0, 0])
        expect(pts.map(p => p.index)).toEqual([0, 1])
    })

    it('keeps interior zeros (went quiet, came back)', () => {
        const pts = subjectLinePoints([0.2, 0, 0.5])
        expect(pts.map(p => p.value)).toEqual([0.2, 0, 0.5])
    })

    it('has no points for an all-zero series', () => {
        expect(subjectLinePoints([0, 0])).toEqual([])
    })

    it('flags a line that ends before the final bucket', () => {
        expect(subjectEndsEarly([0.2, 0.4, 0, 0], 4)).toBe(true)
    })
    it('does not flag a line still live in the final bucket', () => {
        expect(subjectEndsEarly([0.2, 0.4, 0.1], 3)).toBe(false)
    })
    it('does not flag an entirely-absent subject as "ended"', () => {
        expect(subjectEndsEarly([0, 0, 0], 3)).toBe(false)
    })
})

describe('buildSubjectSeries', () => {
    const buckets: TimelineBucket[] = [
        {
            bucket_start: 'd1',
            volume: { count: 10, avg_sentiment: 0 },
            key_subjects: [
                { name: 'Trump', type: 'person', unverified: false, rarity_weight: 0.3, mentions: 4, presence: 0.12 },
                { name: 'Zelensky', type: 'person', unverified: false, rarity_weight: 0.9, mentions: 2, presence: 0.18 },
            ],
            voice_mix: null,
        },
        {
            bucket_start: 'd2',
            volume: { count: 8, avg_sentiment: 0 },
            key_subjects: [
                { name: 'Trump', type: 'person', unverified: false, rarity_weight: 0.3, mentions: 3, presence: 0.10 },
            ],
            voice_mix: null,
        },
        {
            bucket_start: 'd3',
            volume: { count: 5, avg_sentiment: 0 },
            key_subjects: [], // measured, nobody this bucket
            voice_mix: null,
        },
    ]
    const candidates: KeySubjectCandidate[] = [
        { name: 'Trump', type: 'person', unverified: false, signal_count: 40, rarity_weight: 0.3 },
        { name: 'Zelensky', type: 'person', unverified: false, signal_count: 6, rarity_weight: 0.9 },
    ]

    it('builds one presence array per candidate across all buckets', () => {
        const series = buildSubjectSeries(buckets, candidates)
        const trump = series.find(s => s.name === 'Trump')!
        const zel = series.find(s => s.name === 'Zelensky')!
        expect(trump.presences).toEqual([0.12, 0.10, 0])
        expect(zel.presences).toEqual([0.18, 0, 0])
    })

    it('marks Zelensky as ending early (last mention in bucket 0)', () => {
        const series = buildSubjectSeries(buckets, candidates)
        const zel = series.find(s => s.name === 'Zelensky')!
        expect(zel.lastIndex).toBe(0)
        expect(zel.endsEarly).toBe(true)
    })

    it('gives each subject a stable distinct color', () => {
        const series = buildSubjectSeries(buckets, candidates)
        expect(series[0].color).toBe(SUBJECT_LINE_PALETTE[0])
        expect(series[1].color).toBe(SUBJECT_LINE_PALETTE[1])
    })

    it('treats a null key_subjects bucket as zero presence (not a fabricated point)', () => {
        const withNull: TimelineBucket[] = [
            { ...buckets[0] },
            { bucket_start: 'd2', volume: { count: 8, avg_sentiment: 0 }, key_subjects: null, voice_mix: null },
        ]
        const series = buildSubjectSeries(withNull, candidates)
        expect(series.find(s => s.name === 'Trump')!.presences).toEqual([0.12, 0])
    })

    it('maxPresence reads the tallest line point', () => {
        const series = buildSubjectSeries(buckets, candidates)
        expect(maxPresence(series)).toBeCloseTo(0.18, 6)
    })
})

// ------------------------------------------------------------ channels
describe('channel honesty', () => {
    it('only "live" is usable', () => {
        expect(isChannelUsable('live')).toBe(true)
        expect(isChannelUsable('degraded')).toBe(false)
        expect(isChannelUsable('unavailable')).toBe(false)
        expect(isChannelUsable(undefined)).toBe(false)
    })

    it('labels a degraded channel with an honest, non-zero reason', () => {
        expect(channelGapLabel('degraded', 'db_busy')).toMatch(/timed out/)
        expect(channelGapLabel('degraded')).toMatch(/not measured/)
        expect(channelGapLabel('unavailable', 'db_unavailable')).toMatch(/offline/)
        expect(channelGapLabel('live')).toBe('')
    })
})

// ------------------------------------------------------------ edge diff
describe('edge-diff churn-vs-narrative', () => {
    it('classifies a reason-only change as narrative vs churn vs unknown', () => {
        expect(dissolvedKind({ reason: 'narrative_change' })).toBe('narrative')
        expect(dissolvedKind({ reason: 'substrate_churn' })).toBe('churn')
        expect(dissolvedKind({ reason: 'topic merged into umbrella' })).toBe('churn')
        expect(dissolvedKind({ reason: null })).toBe('unknown')
    })

    it('produces the honest endpoint labels the spec names', () => {
        expect(dissolvedLabel({ change_type: 'narrative_change' })).toBe('connection ended: narrative change')
        expect(dissolvedLabel({ change_type: 'substrate_churn' })).toBe('connection ended: substrate churn')
        expect(dissolvedLabel({ reason: undefined })).toMatch(/unrecorded/)
    })

    it('summarizes formed/died/weakened and splits died by cause', () => {
        const changes: EdgeChange[] = [
            mkChange('formed', null),
            mkChange('died', 'narrative_change'),
            mkChange('died', 'substrate_churn'),
            mkChange('died', 'mystery'),
            mkChange('weakened', null),
        ]
        const s = summarizeChanges(changes)
        expect(s).toEqual({ formed: 1, died: 3, weakened: 1, diedNarrative: 1, diedChurn: 1 })
    })

    // The wire contract has NO generic 'died' type: the backend emits
    // narrative_change / substrate_churn with prose reasons. This client used to
    // look for 'died' only, so every dissolved edge was silently dropped from
    // both the chips and the churn-vs-narrative caveat.
    it('counts the REAL backend change types, not a nonexistent "died"', () => {
        const changes: EdgeChange[] = [
            mkChange('formed', 'edge absent at the earlier snapshot, present at the later one'),
            mkChange('narrative_change',
                'both id-A and id-B are still active topics with no current edge between them — the connection dissolved'),
            mkChange('substrate_churn',
                'substrate churn, not a narrative change: id-B is retired'),
            mkChange('weakened', 'weight dropped 0.200 (>= the material threshold 0.1)'),
        ]
        const s = summarizeChanges(changes)
        expect(s).toEqual({ formed: 1, died: 2, weakened: 1, diedNarrative: 1, diedChurn: 1 })
    })

    it('reads the cause off change_type, so the churn reason is never read as narrative', () => {
        // this prose contains BOTH words — change_type is the authority
        expect(dissolvedKind({
            change_type: 'substrate_churn',
            reason: 'substrate churn, not a narrative change: id-B is retired',
        })).toBe('churn')
        expect(dissolvedKind({
            change_type: 'narrative_change',
            reason: 'both are still active topics — the connection dissolved',
        })).toBe('narrative')
        expect(dissolvedLabel({ change_type: 'substrate_churn', reason: null }))
            .toBe('connection ended: substrate churn')
        expect(isDissolvedType('narrative_change')).toBe(true)
        expect(isDissolvedType('substrate_churn')).toBe(true)
        expect(isDissolvedType('formed')).toBe(false)
    })

    it('reason-only fallback still tests churn before narrative', () => {
        expect(dissolvedKind({ reason: 'substrate churn, not a narrative change: x is retired' })).toBe('churn')
        expect(dissolvedKind({ reason: 'narrative change' })).toBe('narrative')
        expect(dissolvedKind({ reason: null })).toBe('unknown')
    })
})

// ------------------------------------------------------------ diff window label
describe('describeDiffWindow — a 2-day diff is never labeled as 1 day', () => {
    const iv = (over: Partial<SnapshotIntervalInfo>): SnapshotIntervalInfo => ({
        hours: 24, expected_hours: 24, intermediate_snapshots: 0,
        missing_snapshot_passes: 0, is_standard: true, note: 'one standard snapshot step',
        ...over,
    })

    it('anchors on the matched SNAPSHOT, not the requested since', () => {
        const out = describeDiffWindow({
            since: '2026-07-25T00:00:00+00:00',
            matched_since_snapshot_at: '2026-07-24T08:15:03+00:00',
            interval: iv({}),
        })
        expect(out.anchorIso).toBe('2026-07-24T08:15:03+00:00')
    })

    it('stays quiet on a standard nightly step', () => {
        const out = describeDiffWindow({
            matched_since_snapshot_at: '2026-07-26T08:15:03+00:00', interval: iv({}),
        })
        expect(out.isStandard).toBe(true)
        expect(out.spanLabel).toBeNull()
    })

    it('names the 07-25 gap: 48h, 2 days of change, 1 missing pass', () => {
        const out = describeDiffWindow({
            matched_since_snapshot_at: '2026-07-24T08:15:03+00:00',
            interval: iv({
                hours: 48, missing_snapshot_passes: 1, is_standard: false,
                note: '48h apart — 1 snapshot pass missing from the store',
            }),
        })
        expect(out.isStandard).toBe(false)
        expect(out.spanLabel).toContain('2d')
        expect(out.spanLabel).toContain('2 days of change')
        expect(out.spanLabel).toContain('1 snapshot pass missing')
        expect(out.tip).toContain('48h')
    })

    it('names a wide since-window as aggregating several steps', () => {
        const out = describeDiffWindow({
            matched_since_snapshot_at: '2026-07-22T08:15:00+00:00',
            interval: iv({
                hours: 120, intermediate_snapshots: 3, missing_snapshot_passes: 1,
                is_standard: false, note: '120h apart, aggregating 3 intermediate passes',
            }),
        })
        expect(out.spanLabel).toContain('4 snapshot steps')
    })

    it('names a sub-cadence step as less than one pass', () => {
        const out = describeDiffWindow({
            matched_since_snapshot_at: '2026-07-21T20:24:30+00:00',
            interval: iv({ hours: 1.42, is_standard: false, note: 'shorter than the cadence' }),
        })
        expect(out.spanLabel).toContain('1.4h')
        expect(out.spanLabel).toContain('less than one full snapshot pass')
    })

    it('names the single-snapshot case instead of implying a diff', () => {
        const out = describeDiffWindow({
            matched_since_snapshot_at: '2026-07-27T08:15:05+00:00',
            interval: iv({ hours: 0, is_standard: false, note: 'same snapshot both ends' }),
        })
        expect(out.spanLabel).toContain('nothing to compare')
    })

    it('claims nothing when the payload predates the interval field', () => {
        const out = describeDiffWindow({ since: '2026-07-24T00:00:00+00:00' })
        expect(out.spanLabel).toBeNull()
        expect(out.anchorIso).toBe('2026-07-24T00:00:00+00:00')
    })

    it('formats spans as days only on exact multiples of 24h', () => {
        expect(formatSpanHours(48)).toBe('2d')
        expect(formatSpanHours(24)).toBe('1d')
        expect(formatSpanHours(10.17)).toBe('10.2h')
        expect(formatSpanHours(0)).toBe('0h')
    })

    it('finds dormant relationships touching a subject, case-folded on either side', () => {
        const dormant: DormantRelationship[] = [
            { entity_a: 'Trump', entity_b: 'Xi Jinping', cooccur_count: 12, rarity_weight: 0.4, reason: 'no_current_thread' },
            { entity_a: 'Macron', entity_b: 'trump', cooccur_count: 5, rarity_weight: 0.7, reason: 'no_current_thread' },
            { entity_a: 'Lula', entity_b: 'Milei', cooccur_count: 3, rarity_weight: 0.8, reason: null },
        ]
        const hits = dormantForSubject('TRUMP', dormant)
        expect(hits).toHaveLength(2)
        expect(dormantForSubject('lula', dormant)).toHaveLength(1)
        expect(dormantForSubject('', dormant)).toHaveLength(0)
    })
})

// ------------------------------------------------------------ helpers
function mkBucket(day: string, count: number, sent: number): TimelineBucket {
    return {
        bucket_start: day,
        volume: { count, avg_sentiment: sent },
        key_subjects: null,
        voice_mix: null,
    }
}

function mkChange(type: string, reason: string | null): EdgeChange {
    return {
        identity_key_a: 'a', identity_key_b: 'b', change_type: type,
        weight_t0: 1, weight_t1: 0, delta: -1, reason, basis: 'entity',
    }
}

// ------------------------------------------------- N23: empty-state honesty
// Council R4 N23: the person timeline rendered "No activity in this window."
// over a starved lane — the UI repeating, as a fact about the world, a claim
// the backend had never measured. And a malformed ref produced the identical
// sentence. The three backend reasons must reach the screen as three
// different statements.
describe('emptyTimelineCopy — three empty states, never one sentence', () => {
    it('measured_zero is the only wording that claims the world was quiet', () => {
        const c = emptyTimelineCopy('measured_zero', 'person_lane_coverage_174/600')
        expect(c.tone).toBe('measured')
        expect(c.headline).toMatch(/no measured activity/i)
        // it may say how it knows, but it must not hedge into "cannot answer"
        expect(c.headline).not.toMatch(/cannot answer/i)
    })

    it('the legacy no_activity_in_window reason still renders (cached payloads)', () => {
        // Redis holds 5-minute-old payloads written before the rename.
        expect(emptyTimelineCopy('no_activity_in_window').tone).toBe('measured')
    })

    it('lane_starved says the channel cannot answer — never that nothing happened', () => {
        const c = emptyTimelineCopy('lane_starved', 'person_lane_coverage_0/600')
        expect(c.tone).toBe('gap')
        expect(c.headline).toMatch(/cannot answer/i)
        expect(c.headline).not.toMatch(/no activity|nothing happened/i)
        expect(c.detail).toMatch(/person/i)
        // the measurement that produced the verdict stays visible
        expect(c.detail).toMatch(/not (a )?measured|absence/i)
    })

    it('names the starved lane per source, so the gap is attributable', () => {
        expect(emptyTimelineCopy('lane_starved', 'country_hourly_no_source_rows_in_window').detail)
            .toMatch(/hourly/i)
        expect(emptyTimelineCopy('lane_starved', 'topic_members_no_source_rows_in_window').detail)
            .toMatch(/membership/i)
        expect(emptyTimelineCopy('lane_starved', 'person_lane_coverage_unverified').detail)
            .toMatch(/could not be verified|unverified/i)
    })

    it('invalid_ref reads as an input error, never as an observation', () => {
        const c = emptyTimelineCopy('invalid_ref', 'country_code_malformed')
        expect(c.tone).toBe('error')
        expect(c.headline).not.toMatch(/activity|quiet|cannot answer/i)
        expect(c.detail).toMatch(/2-letter/i)
        expect(emptyTimelineCopy('invalid_ref', 'person_ref_unmatchable').detail)
            .toMatch(/letter|digit/i)
        expect(emptyTimelineCopy('invalid_ref', 'empty_ref').detail).toMatch(/empty/i)
        expect(emptyTimelineCopy('invalid_ref', 'ref_too_long').detail).toMatch(/long/i)
    })

    it('keeps the existing thread + fallback reasons intact', () => {
        expect(emptyTimelineCopy('topic_not_found').headline).toMatch(/thread type/i)
        expect(emptyTimelineCopy('db_unavailable').tone).toBe('gap')
        expect(emptyTimelineCopy(undefined).headline).toMatch(/no data|no timeline/i)
    })
})
