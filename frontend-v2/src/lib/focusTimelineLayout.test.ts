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
    diedReasonKind,
    diedReasonLabel,
    summarizeChanges,
    dormantForSubject,
    type TimelineBucket,
    type KeySubjectCandidate,
    type EdgeChange,
    type DormantRelationship,
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
    it('classifies a died reason as narrative vs churn vs unknown', () => {
        expect(diedReasonKind('narrative_change')).toBe('narrative')
        expect(diedReasonKind('substrate_churn')).toBe('churn')
        expect(diedReasonKind('topic merged into umbrella')).toBe('churn')
        expect(diedReasonKind(null)).toBe('unknown')
    })

    it('produces the honest endpoint labels the spec names', () => {
        expect(diedReasonLabel('narrative_change')).toBe('connection ended: narrative change')
        expect(diedReasonLabel('substrate_churn')).toBe('connection ended: substrate churn')
        expect(diedReasonLabel(undefined)).toMatch(/unrecorded/)
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
