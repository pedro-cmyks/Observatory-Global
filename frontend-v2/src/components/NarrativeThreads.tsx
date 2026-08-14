import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react'
import { freezeThreadOrder } from '../lib/threadOrder'
import { useFocus } from '../contexts/FocusContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { resolveCountryName } from '../lib/countryNames'
import { Flag } from './Flag'
import { buildCountryThreadEmptyState, getNarrativesForDisplay, THREAD_POOL_HOURS, threadPoolQuery } from '../lib/narrativeThreadLimits'
import {
    threadConfidencePresentation,
    confidenceBucketTip,
    type ConfidenceBucket,
    type ConfidenceBucketSource,
} from '../lib/threadConfidence'
import { threadCountryPresentation } from '../lib/threadGeography'
import { familyColor, familyGradient } from '../lib/categoryFamily'
import { decodeEntities } from '../lib/decodeEntities'
import { CountQualifierChip, countQualifier, formatCountWindow } from '../lib/countQualifier'
import { resolveSourceCount, sourceCountClause } from '../lib/briefSourceCount'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { TemporalSignatureChip, type TemporalSignatureMeta } from '../lib/temporalSignatureChip'
import { TranslatableTextInline, useTranslatableText } from './TranslatableText'
import { RelationshipChip } from './RelationshipChip'
import { fetchTopicRelationship, type TopicRelationship } from '../lib/topicRelationship'
import { canHaveThreadVoice } from '../lib/threadVoice'
import { personPin } from '../lib/capturePayloads'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { buildEclipseSets, threadEclipseRole } from '../lib/eclipseSets'
import { useStoryLens } from '../contexts/StoryLensContext'
import { buildLensSets, threadLensRole, hasLensContent, isFamilySibling, siblingChipText, type SiblingChipText, type StoryLensKind, type StoryLensSibling } from '../lib/storyLens'
import { buildThreadRelation } from '../lib/threadRelation'
import { threadRowKind, storyTitle, rowCountBase, categoryRowTip, familyRowBadge, familyRowTip } from '../lib/threadRowKind'
import { visibleEntities } from '../lib/threadRowMobile'
import { useIsMobile } from '../hooks/useIsMobile'
import './NarrativeThreads.css'

interface TimelinePoint {
    hour: string
    count: number
}

interface Narrative {
    thread_id: string
    label: string
    anchor_topics: string[]
    parent_domain: string | null
    signal_count: number
    // #214 / T4 (dataviz audit): gate lineage for the count label. Atlas topics
    // carry both; dynamic/emergent threads may not (undefined → plain count).
    gated_signal_count?: number
    gate_scored_count?: number
    /**
     * Council R4 N19: the window `signal_count` was actually counted over.
     * Dynamic rows count the latest SNAPSHOT, whose clustering window measured
     * 168h in production — so this row's chip stamping a hardcoded '24h' was
     * false. Absent for atlas rows, which genuinely are filtered to the
     * requested hours; the chip falls back to the request only there.
     */
    count_window_hours?: number | null
    discussion_count?: number
    forum_sentiment?: number | null
    country_count: number
    source_count: number
    /**
     * Which receipt sample `source_count` was counted over. Rows whose served
     * receipts saturate the list's 24-receipt slice are now counted over the
     * frozen snapshot sample instead (lib/briefSourceCount), so the hint has to
     * carry the population with the number.
     */
    source_count_basis?: 'receipt_sample' | 'snapshot_receipts' | null
    source_sample_size?: number | null
    top_sources: string[]
    first_seen: string | null
    changed_10h: number
    trend: 'accelerating' | 'stable' | 'fading'
    // N14 (council R4): confidence renders as a BAND, never a raw percent.
    // `confidence_band` is the served field; `confidence_bucket` is the
    // three-tier fold every surface reads; `confidence_bar_pct` sizes the bar
    // from that bucket and is NEVER printed. See lib/threadConfidence.ts.
    confidence_band: string | null
    confidence_bucket: ConfidenceBucket | null
    confidence_bucket_source: ConfidenceBucketSource | null
    confidence_bar_pct: number | null
    confidence_label: string
    show_confidence_bar: boolean
    confidence_trend_color: string
    // Label trust (council Phase 1): raw assignment confidence + Label Court
    // verdict, carried through so the row can render the "LABEL UNDER REVIEW"
    // chip without re-deriving the confidence presentation. `avg_confidence`
    // stays `number | undefined` to remain assignment-compatible with
    // ThreadDetail (ThreadFocusPanel reads a Narrative as a ThreadDetail).
    avg_confidence?: number
    confidence_measured: boolean
    label_status: string | null
    label_proposed: string | null
    // 2026-07-30 (gb5-blind-check "cron-safety item 2"): the court tried this
    // row and could not ground a verdict (umbrella lane only) — a stronger
    // claim than ordinary unchecked-ness, surfaced ahead of the confidence
    // floor. See lib/labelReviewChip.tsx's courtWithheld doc comment.
    court_withheld?: boolean
    // Temporal signature (mig 085): new/recurrent/resurrected chip;
    // continuous/null render nothing (default is not a badge).
    temporal_signature: string | null
    signature_meta: TemporalSignatureMeta | null
    crisis_relevant: boolean
    sentiment_swing_10h: number | null
    top_entities: string[]
    hourly_timeline: TimelinePoint[]
    top_countries: string[]
    top_country_names: string[]
    subject_countries: string[]
    subject_country_names: string[]
    subject_geography_status: string | null
    // Enrichment: public attention signals
    has_public_interest?: boolean
    trending_keywords?: string[]
    has_wiki_activity?: boolean
    wiki_views?: number
    // T11 gate fix (L1, CRIT): true for a lens-sibling row SYNTHESIZED from
    // the story-siblings payload because the panel's own fetched /threads
    // pool never carried it — measured the common case (0/107 renderable on
    // the live field), not the exception. Every quantitative field above is
    // honestly UNKNOWN for a synthesized row (0/null/empty, never a guess);
    // this flag routes the render path around the count/trend/sparkline
    // blocks that would otherwise print those placeholders as if measured.
    synthesized?: boolean
    // The one quantitative fact a synthesized row DOES carry — the measured
    // composite walk weight (whitened cosine, product over hops). Rendered
    // verbatim ("walk 0.85"), never reformatted into a fabricated count.
    lensWeight?: number
    // Z3 (2026-08-14): the LEVEL the siblings payload stated for this row. A
    // synthesized row carries no `identity_key`, so `threadRowKind` cannot read
    // the `umbrella:` marker off `anchor_topics` the way it does for a pool
    // row — the payload has to say it, and this is where it says it.
    lensKind?: StoryLensKind
    // How many stories that family rolls up; null when the backend's bounded
    // child lookup could not answer (the row stays a family regardless).
    lensChildCount?: number | null
}

// Sparkline SVG component.
// T3 (dataviz audit): every row is max-normalized to itself — 20 mini-charts,
// 20 private y-scales. The peak annotation anchors the magnitude so rows can
// be compared by number even though the amplitudes can't.
const Sparkline: React.FC<{ data: TimelinePoint[], color: string }> = ({ data, color }) => {
    if (!data || data.length < 2) return null

    const width = 200
    const height = 26
    const padding = 2
    const max = Math.max(...data.map(d => d.count), 1)

    const points = data.map((d, i) => {
        const x = padding + (i / (data.length - 1)) * (width - padding * 2)
        const y = height - padding - ((d.count / max) * (height - padding * 2))
        return `${x},${y}`
    }).join(' ')

    // Area fill polygon
    const firstX = padding
    const lastX = padding + ((data.length - 1) / (data.length - 1)) * (width - padding * 2)
    const areaPoints = `${firstX},${height} ${points} ${lastX},${height}`

    return (
        <span className="narrative-sparkline-wrap" data-tip={`Shape only — this sparkline is scaled to its own peak of ${max.toLocaleString()} signals/h; compare rows by the peak number, not the amplitude.`}>
            <svg className="narrative-sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                <polygon points={areaPoints} fill={color} />
                <polyline points={points} stroke={color} />
            </svg>
            <span className="narrative-spark-peak">peak {max > 999 ? `${(max / 1000).toFixed(1)}k` : max}/h</span>
        </span>
    )
}

// Format time ago
const timeAgo = (isoString: string | null): string => {
    if (!isoString) return ''
    const diff = Date.now() - new Date(isoString).getTime()
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return 'Started < 1h ago'
    if (hours < 24) return `Started ${hours}h ago`
    const days = Math.floor(hours / 24)
    return `Started ${days}d ago`
}

const normalizeTrend = (trend: string): Narrative['trend'] => {
    if (trend === 'surging') return 'accelerating'
    if (trend === 'fading') return 'fading'
    return 'stable'
}

const normalizeThread = (thread: any): Narrative => {
    const trend = normalizeTrend(thread.trend)
    const crisisRelevant = thread.crisis_relevant === true
    const confidence = threadConfidencePresentation({
        avgConfidence: typeof thread.avg_confidence === 'number' ? thread.avg_confidence : null,
        confidenceMeasured: thread.confidence_measured === true,
        trend,
        crisisRelevant,
        // The served band (thread_intelligence.confidence_band) — authoritative
        // over the raw number it deliberately does not track (N14).
        band: typeof thread.confidence === 'string' ? thread.confidence : null,
    })
    return {
    thread_id: thread.thread_id,
    // The title is shortened against the row's OWN category so it can never
    // collapse into a restatement of the kicker printed beside it — see
    // lib/threadRowKind.storyTitle for the three strips this refuses.
    label: storyTitle(
        decodeEntities(thread.label || thread.summary || thread.thread_id),
        thread.category ?? thread.parent_domain ?? null,
    ),
    anchor_topics: thread.anchor_topics || [],
    parent_domain: thread.parent_domain || null,
    signal_count: thread.signal_count || 0,
    gated_signal_count: thread.gated_signal_count,
    gate_scored_count: thread.gate_scored_count,
    count_window_hours: thread.count_window_hours ?? null,
    discussion_count: thread.discussion_count || 0,
    forum_sentiment: thread.forum_sentiment ?? null,
    country_count: thread.country_count || 0,
    source_count: thread.source_count || 0,
    source_count_basis: thread.source_count_basis ?? null,
    source_sample_size: thread.source_sample_size ?? null,
    top_sources: thread.top_sources || thread.source_mix?.top_sources || [],
    first_seen: thread.first_seen || null,
    changed_10h: thread.changed_10h || 0,
    trend,
    confidence_band: typeof thread.confidence === 'string' ? thread.confidence : null,
    confidence_bucket: confidence.bucket,
    confidence_bucket_source: confidence.bucketSource,
    confidence_bar_pct: confidence.barPct,
    confidence_label: confidence.confidenceLabel,
    show_confidence_bar: confidence.showConfidenceBar,
    confidence_trend_color: confidence.trendColor,
    avg_confidence: typeof thread.avg_confidence === 'number' ? thread.avg_confidence : undefined,
    confidence_measured: thread.confidence_measured === true,
    label_status: thread.label_status ?? null,
    label_proposed: thread.label_proposed ?? null,
    court_withheld: thread.court_withheld === true,
    temporal_signature: thread.temporal_signature ?? null,
    signature_meta: thread.signature_meta ?? null,
    crisis_relevant: crisisRelevant,
    sentiment_swing_10h: thread.sentiment_swing_10h ?? null,
    top_entities: thread.top_entities || thread.top_people || [],
    hourly_timeline: thread.hourly_timeline || [],
    top_countries: thread.top_countries || [],
    top_country_names: thread.top_country_names || [],
    subject_countries: thread.subject_countries || [],
    subject_country_names: thread.subject_country_names || [],
    subject_geography_status: thread.subject_geography_status || null,
    }
}

// T11 gate fix (L1, CRIT): a minimal, honest row for a lens sibling the
// panel's own /threads pool never fetched. `countries` (the backend's
// country-receipt footprint for that topic) is the only geography the
// sibling payload carries, so it fills top_countries/top_country_names —
// real, measured data, presented as "Coverage" via threadCountryPresentation
// exactly like a pool row would be. Every OTHER quantitative field is an
// explicit unknown (0 / null / [] / 'stable' as a type-satisfying default
// that the render path never surfaces — see `synthesized` below), never a
// guess dressed as a measurement.
function buildSyntheticSiblingRow(s: StoryLensSibling): Narrative {
    const countries = s.countries || []
    return {
        thread_id: s.id,
        // Sibling payloads carry no category, so the kicker-collision guard
        // has nothing to compare against — the word-count guards still apply.
        label: storyTitle(decodeEntities(s.label), null),
        anchor_topics: [],
        parent_domain: null,
        signal_count: 0,
        gated_signal_count: undefined,
        gate_scored_count: undefined,
        discussion_count: 0,
        forum_sentiment: null,
        country_count: countries.length,
        source_count: 0,
        top_sources: [],
        first_seen: null,
        changed_10h: 0,
        trend: 'stable',
        confidence_band: null,
        confidence_bucket: null,
        confidence_bucket_source: null,
        confidence_bar_pct: null,
        confidence_label: '',
        show_confidence_bar: false,
        confidence_trend_color: '#8892a0',
        avg_confidence: undefined,
        confidence_measured: false,
        label_status: s.label_status ?? null,
        label_proposed: null,
        // Story-lens siblings never carry this signal (a different, pure
        // ranker payload) — honest absence, never a guess.
        court_withheld: false,
        temporal_signature: null,
        signature_meta: null,
        crisis_relevant: false,
        sentiment_swing_10h: null,
        top_entities: [],
        hourly_timeline: [],
        top_countries: countries,
        top_country_names: countries.map(c => resolveCountryName(c)),
        subject_countries: [],
        subject_country_names: [],
        subject_geography_status: null,
        synthesized: true,
        lensWeight: s.weight,
        lensKind: s.kind,
        lensChildCount: s.child_count ?? null,
    }
}

/**
 * The thread title cell: the clamped `.narrative-label-text` span, plus — on
 * mobile only — TranslatableText's "See original"/"See translation" toggle
 * rendered as a genuine DOM SIBLING of that span instead of nested inside it.
 *
 * Why: under 768px `.narrative-label-text` is a `-webkit-line-clamp: 2` box
 * (#236). `TranslatableText` renders its text AND its toggle button inside one
 * wrapping span, so a translated title that alone filled both lines pushed the
 * toggle past the clamp's visible box — the one control that reaches the
 * label's source language was there but untappable. A clamped box hides any
 * overflowing descendant regardless of that descendant's own size, so the
 * toggle can only stay reachable by living outside the box entirely. This is
 * the same defect class, and the same remedy, as the ↔ relation-reason chip
 * hoisted out of this exact span below, and as SignalStream's headline toggle
 * (`SignalHeadlineRow`).
 *
 * `useTranslatableText` is called exactly ONCE here (not once per branch) so
 * the desktop and mobile renders share one toggle/translated state — two hook
 * instances would double the /api/v2/translate/text traffic and could desync
 * (tapping the toggle in one would never update the text rendered by the
 * other). The desktop branch renders `TranslatableTextInline` fed by that
 * shared state, which is exactly what every other TranslatableText consumer
 * renders — desktop output is byte-identical to before, and the two call
 * sites cannot drift apart later.
 */
const ThreadLabelText: React.FC<{ label: string; isMobile: boolean }> = ({ label, isMobile }) => {
    const state = useTranslatableText(label)

    // Desktop, or nothing to toggle → the shape this row has always had.
    if (!isMobile || !state.hasToggle) {
        return (
            <span className="narrative-label-text" data-tip={label}>
                <TranslatableTextInline state={state} />
            </span>
        )
    }

    return (
        <>
            <span className="narrative-label-text" data-tip={label}>
                {state.display}
            </span>
            <span className="narrative-label-toggle">
                <button
                    type="button"
                    className="th-toggle"
                    onClick={(e) => { e.stopPropagation(); state.toggle() }}
                    data-tip={state.toggleTip}
                >
                    {state.toggleLabel}
                </button>
            </span>
        </>
    )
}

interface NarrativeThreadsProps {
    onCountrySelect?: (code: string) => void
    onThreadSelect?: (thread: Narrative) => void
    activeThreadId?: string | null
    /** #236: true while mounted but hidden (the phone keeps this panel alive
     *  behind another tab). The 5-minute poll idles; the initial fetch still
     *  runs, so the list is ready the moment the tab reveals it. */
    paused?: boolean
}

export type LivingThreadSelection = Narrative

export const NarrativeThreads: React.FC<NarrativeThreadsProps> = ({ onCountrySelect, onThreadSelect, activeThreadId, paused = false }) => {
    const [narratives, setNarratives] = useState<Narrative[]>([])
    // #234: precise person→thread set from the backend (full persons array),
    // replacing the capped top_entities heuristic for the focus highlight.
    const [personMatchIds, setPersonMatchIds] = useState<Set<string> | null>(null)
    const [effectiveHours, setEffectiveHours] = useState<number | null>(null)
    const [loading, setLoading] = useState(true)
    // G5: a failed fetch (503 db_busy / 500 / network) must not read as an
    // honest "no active narratives" empty. Track it so the empty branch can
    // say "unavailable — retrying" instead.
    const [feedError, setFeedError] = useState(false)
    const { filter, setCountry, setMapFlyCountry, setPerson } = useFocus()
    // W4 (2026-07-05): thread rows are pinnable into the active investigation.
    const { pinItem, unpinItem, isPinned } = useWorkspace()
    // #236: on a phone the title leads; entity chips collapse to a counted +N.
    const isMobile = useIsMobile()

    /* ECLIPSE LENS: when the reader ENTERED a total eclipse, this panel stops
       being a volume ranking and becomes SHADOW-FIRST — the eclipsing story pins
       to the top, the consequential-but-quiet stories it drowns out come next
       (each carrying its own share next to the eclipse's, so the relation is
       physical, not asserted), everything else follows untouched. Outside lens
       mode `eclipseSets` is null and every path below is byte-identical to before. */
    const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
    const eclipseSets = useMemo(
        () => (eclipseMode === 'ambient' && eclipseData ? buildEclipseSets(eclipseData) : null),
        [eclipseMode, eclipseData])
    // Share of coverage per shadow topic, for the "x% vs y%" relation line.
    const shadowShareById = useMemo(() => {
        const m = new Map<string, number>()
        for (const it of eclipseData?.selected ?? []) m.set(it.topic_id, it.attention_share)
        return m
    }, [eclipseData])

    /* STORY LENS: a user-driven investigative re-scope (unlike eclipse's
       ambient condition) — entering the lens on an open thread pins its
       measured neighborhood (hermanos/primos walked from the substrate) to the
       top of THIS panel too, same section-per-role idiom as eclipse. Gate on
       hasLensContent (never lensSets != null): an honest-empty siblings payload
       (anchor found but zero siblings, or a degraded fetch) must not silently
       disable the pre-existing #234 sibling ordering below it while showing
       nothing itself. */
    const storyLens = useStoryLens()
    const lensOn = storyLens.state.active && hasLensContent(storyLens.data)
    const lensSets = useMemo(
        () => (lensOn ? buildLensSets(storyLens.data) : null),
        [lensOn, storyLens.data])
    // Reason chip text + structured blob flag per lens sibling id (+ folded
    // near-dup ids it absorbed) — mirrors relationReason below but sourced
    // from the measured walk instead of the client-side entity/country
    // heuristic. isBlob rides as a real field so the tooltip branches on it
    // directly, never by re-parsing the rendered chip string.
    const lensReasonById = useMemo(() => {
        const m = new Map<string, SiblingChipText>()
        for (const s of storyLens.data?.siblings ?? []) {
            const chip = siblingChipText(s)
            m.set(s.id, chip)
            for (const f of s.folded ?? []) m.set(f, chip)
        }
        return m
    }, [storyLens.data])

    // Z3: how many stories each FAMILY sibling rolls up, keyed the same way.
    // A family that is ALSO in the panel's own /threads pool renders from the
    // pool row, and `/threads` carries no child count — without this the
    // witness (dt-12927, a pool row) would show the bare `◫ FAMILY` while the
    // lens payload was holding "8" the whole time. Only ever a lookup of a
    // measured number; a family with no count still renders as a family.
    const lensFamilyCountById = useMemo(() => {
        const m = new Map<string, number>()
        for (const s of storyLens.data?.siblings ?? []) {
            if (!isFamilySibling(s) || s.child_count == null) continue
            m.set(s.id, s.child_count)
            for (const f of s.folded ?? []) m.set(f, s.child_count)
        }
        return m
    }, [storyLens.data])

    // Threads are ambient — the live day (the VIEW selector is gone,
    // 2026-07-15; the global list was already capped to 24h because
    // spread_pct is meaningless at wider windows). Looking back = the map
    // scrubber / deep-history, not a re-windowed list.
    const cappedHours = THREAD_POOL_HOURS

    // The pool this panel ranks over — and the SAME pool the phone's Lens
    // measures its `connected` section against, which is why the query is a
    // shared definition rather than one built here (see threadPoolQuery).
    const poolQuery = threadPoolQuery(filter.country, cappedHours)

    const fetchNarratives = useCallback(async () => {
        try {
            let res = await fetch(poolQuery)
            if (!res.ok) {
                // One quick retry: a cold country-scoped query can 500 once,
                // which silently left the GLOBAL list under a "Scoped to X"
                // strip until the 5-min interval (capture-doc §B, live-seen).
                await new Promise(r => setTimeout(r, 2500))
                res = await fetch(poolQuery)
                if (!res.ok) { setFeedError(true); return }   // service failure, not empty
            }
            const data = await res.json()
            setNarratives((data.threads || []).map(normalizeThread))
            setEffectiveHours(data.hours ?? null)
            setFeedError(false)
        } catch (e) {
            console.error('[NarrativeThreads] Fetch error', e)
            setFeedError(true)   // network throw = unavailable, not empty
        } finally {
            setLoading(false)
        }
    }, [poolQuery])

    // Initial fetch + 5-minute interval; re-fetch when country changes.
    // #236: the interval (not the initial fetch) idles while hidden — read
    // through a ref so a visibility flip never rebuilds the timer.
    const pausedRef = useRef(paused)
    pausedRef.current = paused
    useEffect(() => {
        setLoading(true)
        fetchNarratives()
        const interval = setInterval(() => { if (!pausedRef.current) fetchNarratives() }, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchNarratives])

    // N5: pin the visual row order while the pointer is over the list. The ref
    // always holds the current live (relation-sorted) id order; entering the
    // list snapshots it, leaving releases it. See lib/threadOrder.
    const [frozenOrder, setFrozenOrder] = useState<string[] | null>(null)
    const liveOrderIdsRef = useRef<string[]>([])
    const freezeRowOrder = useCallback(() => setFrozenOrder(liveOrderIdsRef.current.slice()), [])
    const releaseRowOrder = useCallback(() => setFrozenOrder(null), [])

    // Story lens review finding 3: entering/exiting the lens is a DELIBERATE
    // re-scope the reader asked for, not a hover hazard — an N5 freeze taken
    // before the lens engaged must not hold a stale (pre-lens) row order over
    // the newly lens-ordered list. Release the freeze on every lensOn
    // transition so the section labels/roles (computed against the RENDERED
    // order) are correct on the primary entry path. This release makes the
    // lens regroup visible; nothing re-arms frozenOrder until the pointer
    // re-enters the list, so the CURRENT hover session then runs unfrozen —
    // a poll refresh mid-session in that window can reorder rows under the
    // cursor. Accepted trade-off: lens entry is a deliberate re-scope, and
    // the next mouseEnter re-arms N5 as normal.
    useEffect(() => {
        setFrozenOrder(null)
    }, [lensOn])

    // #234: when a person is focused, fetch the PRECISE set of threads that
    // mention them (backend ?person=, full persons array) for the highlight —
    // more accurate than the capped top_entities. Cleared when no person.
    useEffect(() => {
        const person = filter.person?.trim()
        if (!person) { setPersonMatchIds(null); return }
        let cancelled = false
        fetch(`/api/v2/threads?hours=${cappedHours}&person=${encodeURIComponent(person)}`)
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (cancelled || !d) return
                setPersonMatchIds(new Set((d.threads || []).map((t: { thread_id: string }) => t.thread_id)))
            })
            .catch(() => { if (!cancelled) setPersonMatchIds(null) })
        return () => { cancelled = true }
    }, [filter.person, cappedHours])

    // When country is active, show only threads that include that country
    const displayedNarratives = getNarrativesForDisplay(narratives, filter.country ?? undefined)

    // #168: attention-relationship badges on the rows. One cheap fetch per
    // displayed topic-backed thread (client-cached 5 min on top of the
    // endpoint's own Redis cache); compact mode renders ONLY the
    // differentiating classes (public-led / social-led / silent-risk), so
    // the default media-led field stays visually quiet. Failure -> no badge.
    const [relationships, setRelationships] = useState<Record<string, TopicRelationship>>({})
    const relationshipIds = displayedNarratives
        .map(n => n.thread_id)
        .filter(id => canHaveThreadVoice(id))
        .join(',')
    useEffect(() => {
        if (!relationshipIds) return
        let alive = true
        Promise.all(
            relationshipIds.split(',').map(async id => [id, await fetchTopicRelationship(id)] as const),
        ).then(entries => {
            if (!alive) return
            setRelationships(prev => {
                let changed = false
                const next = { ...prev }
                for (const [id, rel] of entries) {
                    if (rel && prev[id]?.relationship !== rel.relationship) {
                        next[id] = rel
                        changed = true
                    }
                }
                return changed ? next : prev
            })
        })
        return () => { alive = false }
    }, [relationshipIds])

    // #234: when a person is focused, surface the threads that mention them
    // (the person appears in top_entities) and dim the rest — mirroring the
    // map's relation re-scope. top_entities is capped and noisy, so if NOTHING
    // matches we keep the global list rather than dimming everything.
    const focusPerson = filter.person?.toLowerCase().trim() || null
    const threadMatchesPerson = (n: Narrative): boolean => {
        if (!focusPerson) return false
        // Precise: the backend ?person= set (full persons array). Until it
        // arrives, fall back to the capped top_entities heuristic.
        if (personMatchIds) return personMatchIds.has(n.thread_id)
        return (n.top_entities || []).some(e => e.toLowerCase().includes(focusPerson))
    }
    const anyPersonMatch = !!focusPerson && displayedNarratives.some(threadMatchesPerson)

    // #234: when a thread is open, surface its SIBLING threads — those sharing
    // the open thread's primary geography or one of its rare actors — and dim
    // the rest. No focus-model change (thread-open clears focus by design);
    // reuses the activeThreadId prop.
    //
    // The rule itself lives in lib/threadRelation: it has a second caller (the
    // phone's Lens `connected` section), and a hand-transcribed second copy is
    // this repo's most-repeated defect. `relation.active` carries the same
    // guard this block always had — an anchor in this list, at least one basis,
    // and at least one OTHER row sharing it, or the list stays as it was.
    const relation = buildThreadRelation(displayedNarratives, activeThreadId, { resolveCountryName })
    const threadRelated = (n: Narrative): boolean => relation.isRelated(n)
    const anyThreadRelation = relation.active

    // #234 legibility (Paper 7 / reason-codes guardrail): expose WHY a sibling
    // relates — the shared distinctive entity (preferred, more specific) or the
    // shared primary country — so the re-scope is never a silent dim.
    const relationReason = (n: Narrative): string | null => relation.reason(n)

    // person focus takes precedence; else thread-sibling relation
    const relate = anyPersonMatch ? threadMatchesPerson : (anyThreadRelation ? threadRelated : null)
    // Eclipse lens ordering: eclipse row(s) first, the stories in its shadow
    // next, everything else after. Array.prototype.sort is stable, so the
    // backend's ranking survives INSIDE each group — the lens re-groups the
    // list, it never re-ranks within a group.
    const eclipseRank = (n: Narrative): number => {
        const role = eclipseSets ? threadEclipseRole(n.anchor_topics, n.thread_id, eclipseSets) : null
        return role === 'eclipse' ? 0 : role === 'shadow' ? 1 : 2
    }
    // Story lens ordering: same stable-regroup idiom as eclipse. Precedence
    // (explicit): eclipse > story-lens > person-match > #234 sibling relation
    // — an ambient eclipse always wins outright (the branch below only runs
    // when eclipseSets is falsy), and lensSets itself is only non-null when
    // hasLensContent() passed, so an honest-empty siblings payload never
    // engages this branch and falls through to person/sibling below.
    const lensRank = (n: Narrative): number => {
        if (!lensSets) return 2
        const role = threadLensRole(n.anchor_topics, n.thread_id, lensSets)
        return role === 'anchor' ? 0 : role === 'sibling' ? 1 : 2
    }
    const liveOrdered = eclipseSets
        ? [...displayedNarratives].sort((a, b) => eclipseRank(a) - eclipseRank(b))
        : lensSets
            ? [...displayedNarratives].sort((a, b) => lensRank(a) - lensRank(b))
            : relate
                ? [...displayedNarratives].sort((a, b) => Number(relate(b)) - Number(relate(a)))
                : displayedNarratives
    // N5: while the pointer is over the list, pin the row order so a relation
    // re-sort or a poll refresh can't shuffle a row out from under the cursor
    // between hover and click (the mis-open bug that survived R2+R3). Content
    // still updates live — only the order freezes. Touch devices have no hover,
    // so freezeOnList stays null there and the live order applies as before.
    // A lens on/off transition releases this freeze on its own (the effect
    // above), so frozenOrder here is never a STALE pre-lens order on the
    // primary entry path — only ordinary same-lens-state churn stays frozen.
    const orderedNarratives = freezeThreadOrder(liveOrdered, frozenOrder)
    liveOrderIdsRef.current = liveOrdered.map(n => n.thread_id)

    // T11 gate fix (L1): which sibling ids (their own id, or a folded
    // near-dup id) already have a matching row in the panel's own pool — so
    // a sibling that genuinely IS one of the panel's fetched threads is
    // never rendered a second time as a synthesized row.
    const poolSiblingCoverage = useMemo(() => {
        const covered = new Set<string>()
        if (!lensSets) return covered
        for (const n of displayedNarratives) {
            for (const id of [n.thread_id, ...(n.anchor_topics ?? [])]) {
                if (lensSets.siblings.has(id)) covered.add(id)
            }
        }
        return covered
    }, [displayedNarratives, lensSets])

    // T11 gate fix (L1, CRIT): the ◈ Measured neighborhood group could never
    // render — the panel only re-labels rows it ALREADY fetched, and the
    // walked siblings are near-never members of its own /threads pool
    // (measured 0/107 renderable on the live field, the 2026-07-29 gate run
    // — the common case, not the exception). Synthesize one minimal row per
    // sibling the pool doesn't already carry; see buildSyntheticSiblingRow.
    const synthesizedSiblingRows = useMemo<Narrative[]>(() => {
        if (!lensSets || !storyLens.data) return []
        const rows: Narrative[] = []
        const seen = new Set<string>()
        for (const s of storyLens.data.siblings) {
            if (poolSiblingCoverage.has(s.id) || seen.has(s.id)) continue
            seen.add(s.id)
            rows.push(buildSyntheticSiblingRow(s))
        }
        return rows
    }, [lensSets, storyLens.data, poolSiblingCoverage])

    // Eclipse always wins outright (matches the ordering gate above) — a
    // synthesized lens row must never join the render list while an ambient
    // eclipse is running the show. Synthesized rows join AFTER the frozen
    // pool order: they are lens-owned, not pool-owned, so N5's hover-freeze
    // (which only ever pinned pool rows) is left completely untouched.
    const showLensRows = !eclipseSets && !!lensSets
    const renderRows = showLensRows ? [...orderedNarratives, ...synthesizedSiblingRows] : orderedNarratives

    // Per-row lens role, resolved against the RENDERED order so the section
    // labels land on the first row of each group. indexOf (not "differs from the
    // previous row") keeps at most ONE label per role even if a hover-freeze
    // still in effect (e.g. from before an ambient eclipse tier flip, which is
    // not freeze-released the way a lens transition is) interleaves the groups.
    const rowRoles = eclipseSets
        ? renderRows.map(n => threadEclipseRole(n.anchor_topics, n.thread_id, eclipseSets))
        : null
    const firstEclipseIdx = rowRoles ? rowRoles.indexOf('eclipse') : -1
    const firstShadowIdx = rowRoles ? rowRoles.indexOf('shadow') : -1
    // Same idiom for the story lens, but ONLY computed when eclipse isn't
    // already running the show (precedence: eclipse wins outright, the lens
    // branch must not run at all — matches the ordering gate above). Now
    // scanning renderRows (pool + synthesized) so a synthesized sibling gets
    // its 'sibling' role exactly like a pool row would.
    const lensRowRoles = (!eclipseSets && lensSets)
        ? renderRows.map(n => threadLensRole(n.anchor_topics, n.thread_id, lensSets))
        : null
    const firstLensAnchorIdx = lensRowRoles ? lensRowRoles.indexOf('anchor') : -1
    const firstLensSiblingIdx = lensRowRoles ? lensRowRoles.indexOf('sibling') : -1
    // This shadow story's share of coverage, matched by thread id or any anchor
    // topic — the eclipse payload keys on topic id.
    const shadowShare = (n: Narrative): number | null => {
        for (const id of [n.thread_id, ...(n.anchor_topics ?? [])]) {
            const v = shadowShareById.get(id)
            if (v != null) return v
        }
        return null
    }
    // Lens reason lookup for a row: matches on thread_id first, then any
    // anchor_topics entry — a row can be a lens sibling via either.
    const lensReasonFor = (n: Narrative): SiblingChipText | null => {
        for (const id of [n.thread_id, ...(n.anchor_topics ?? [])]) {
            const chip = lensReasonById.get(id)
            if (chip) return chip
        }
        return null
    }
    // Z3: the row's own count (a synthesized lens row) first, then the lens
    // payload's count for a pool row that happens to be the same family.
    const familyCountFor = (n: Narrative): number | null => {
        if (n.lensChildCount != null) return n.lensChildCount
        for (const id of [n.thread_id, ...(n.anchor_topics ?? [])]) {
            const c = lensFamilyCountById.get(id)
            if (c != null) return c
        }
        return null
    }

    const handleClick = (n: Narrative) => {
        onThreadSelect?.(n)
        if (n.top_countries.length > 0) {
            setMapFlyCountry(n.top_countries[0])
        }
    }

    const handleCountryPipClick = (e: React.MouseEvent, code: string) => {
        e.stopPropagation()
        setCountry(code)
        setMapFlyCountry(code)
        onCountrySelect?.(code)
    }

    const clearCountryFilter = () => {
        setCountry(null)
        setMapFlyCountry(null)
    }

    // Loading skeleton
    if (loading && narratives.length === 0) {
        return (
            <div className="narrative-threads-container">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="narrative-skeleton">
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                    </div>
                ))}
            </div>
        )
    }

    if (narratives.length === 0) {
        return (
            <div className="narrative-threads-container">
                {feedError ? (
                    <div className="narrative-empty narrative-empty--error" role="status" aria-live="polite">
                        Narrative feed unavailable — retrying…
                    </div>
                ) : (
                    <div className="narrative-empty">No active narratives in this time range</div>
                )}
            </div>
        )
    }

    if (displayedNarratives.length === 0 && filter.country) {
        const emptyState = buildCountryThreadEmptyState(filter.country, resolveCountryName(filter.country))
        return (
            <div className="narrative-threads-container">
                <div className="narrative-empty narrative-empty--actionable">
                    <div className="narrative-empty-title">{emptyState.title}</div>
                    <p>{emptyState.body}</p>
                    <button type="button" className="narrative-empty-action" onClick={clearCountryFilter}>
                        {emptyState.actionLabel}
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div
            className="narrative-threads-container"
            onMouseEnter={freezeRowOrder}
            onMouseLeave={releaseRowOrder}
        >
            {(filter.country || (anyPersonMatch && focusPerson)) && (() => {
                // A3 scope strip: make silent re-scopes legible + reversible.
                const scopedToCountry = !!filter.country
                const scopeName = scopedToCountry
                    ? resolveCountryName(filter.country!)
                    : (filter.person || '')
                const clearScope = scopedToCountry ? clearCountryFilter : () => setPerson(null)
                return (
                    <div className="narrative-scope-strip" data-tip={scopedToCountry ? 'Stories filtered to this country by backend quality gates' : 'Stories that mention this person'}>
                        <span className="narrative-scope-label">
                            Scoped to <strong>{scopeName}</strong>
                        </span>
                        <button type="button" className="narrative-scope-clear" onClick={clearScope} data-tip="Clear scope" aria-label="Clear scope">✕</button>
                    </div>
                )
            })()}
            {effectiveHours != null && effectiveHours < cappedHours && (
                <div className="narrative-cap-notice">
                    Story details show last {effectiveHours}h · counts reflect full {cappedHours}h window
                </div>
            )}
            {renderRows.map((n, rowIdx) => {
                const eclipseRole = rowRoles ? rowRoles[rowIdx] : null
                const lensRole = lensRowRoles ? lensRowRoles[rowIdx] : null
                const sectionLabel = rowIdx === firstEclipseIdx
                    ? '◤ The eclipse'
                    : rowIdx === firstShadowIdx ? '◢ In its shadow'
                    : rowIdx === firstLensAnchorIdx ? '◈ The story'
                    : rowIdx === firstLensSiblingIdx ? '◈ Measured neighborhood' : null
                const isFocused = activeThreadId === n.thread_id
                // T11 gate fix (L1): this row was synthesized from the lens
                // sibling payload, not fetched by the panel — every block
                // below that would print a fabricated count/trend/sparkline
                // is routed around instead.
                const isSynthRow = !!n.synthesized
                // Dim conditions:
                //  - a country is locked AND this thread doesn't cover it -> dim
                //  - a person is focused, some thread mentions them, this one doesn't -> dim (#234)
                const dimByCountry = !!filter.country && !n.top_countries.includes(filter.country)
                const dimByPerson = anyPersonMatch && !threadMatchesPerson(n)
                // The #234 relation arm (sort/chip/dim) is dormant while lens
                // ordering is active — belt-and-suspenders alongside the
                // per-row override below, so this arm never even computes a
                // "should dim" verdict for a lens-organized panel.
                const dimByThread = !anyPersonMatch && anyThreadRelation && !threadRelated(n) && !lensSets
                // Lens rows are NEVER dimmed — a cross-country primo is
                // exactly the row the measured walk exists to surface, and it
                // must not be asserted (cyan border + ↔ chip) AND
                // de-emphasized as noise in the same row by the #234
                // country/entity heuristic. Non-lens rows keep their dims
                // unaffected, so country/person focus still works on the rest
                // of the list. NOT the same gate as dimByThread's `!lensSets`
                // above (that only silences the #234 arm's OWN verdict) —
                // this is the per-row rule that wins regardless of source.
                const isDimmed = lensRole != null ? false : (dimByCountry || dimByPerson || dimByThread)
                // Story lens reason chip (measured walk) — takes precedence
                // over the #234 heuristic chip below; a row never shows both.
                const lensReason = lensRole === 'sibling' ? lensReasonFor(n) : null
                // #234 legibility: show the relation reason on surfaced
                // siblings. Dormant while lens ordering is active (!lensSets)
                // so a client-side heuristic chip can never render visually
                // identical to a measured lens chip on the same panel;
                // !lensReason stays as a per-row belt-and-suspenders.
                const siblingReason = (!lensReason && !lensSets && anyThreadRelation && !anyPersonMatch && !filter.country
                    && !isFocused && !isDimmed) ? relationReason(n) : null
                // P1 vocabulary made visible (Pedro's live read, 2026-08-14): a
                // CATEGORY row is the R3 lens over many stories, not a peer of
                // the stories beneath it. Typed from the payload, never guessed.
                const rowKind = threadRowKind({
                    thread_id: n.thread_id,
                    anchor_topics: n.anchor_topics,
                    lens_kind: n.lensKind,
                })
                const isCategoryRow = rowKind === 'category'
                // Z3: an R2 umbrella — a FAMILY of stories. Same affordance
                // class as the category badge (Pedro: reuse it, don't invent a
                // second visual language), because it is the same misread one
                // level down: a container rendered as a peer story.
                const isFamilyRow = rowKind === 'umbrella'
                const familyChildCount = isFamilyRow ? familyCountFor(n) : null
                const trendArrow = n.trend === 'accelerating' ? '▲' : n.trend === 'fading' ? '▼' : '→'
                // Plain-language hover hint; falls back to label when no description is available.
                // T11 gate fix (L1): a synthesized row carries no measured
                // count/source/country stats — say so honestly instead of
                // printing the fabricated zeros the type defaults carry.
                // The outlet count is a count over a receipt SAMPLE, and which
                // sample now varies per row (the frozen snapshot one wins when
                // the served slice saturates), so the clause carries its own
                // population instead of this sentence assuming one.
                const sourceBasis = resolveSourceCount(n)
                const sourceClause = sourceBasis ? sourceCountClause(sourceBasis) : `${n.source_count} sources`
                const rowHint = isSynthRow
                    ? 'From the measured walk — not in the current top stories. Click to open.'
                    : isCategoryRow
                    ? `${n.label} is a CATEGORY, not a story — a lens over every story filed under it. ${n.signal_count.toLocaleString()} signals across ${n.country_count} countries from ${sourceClause}, summed over the whole category. Click to open it.`
                    : `${n.label}: ${n.signal_count.toLocaleString()} signals across ${n.country_count} countries from ${sourceClause}. Click to open the unified story detail.`
                const domainLabel = (n.parent_domain || 'story').replace(/-/g, ' ')
                const geography = threadCountryPresentation(n)
                // Unified threads (Pedro 2026-06-24): no living/aggregate source
                // tier — every row is a narrative thread, ranked by movement +
                // volume + coherence. The trend arrow carries the movement; the
                // count its weight. No source-origin badge.

                // Dataviz audit fix 2: color by CATEGORY FAMILY (parent_domain),
                // never by row index — a thread keeps its color when its rank
                // changes. The visible domain label is the secondary encoding.
                const threadAccent = familyColor(n.parent_domain)
                const threadGradient = familyGradient(n.parent_domain)
                // #236: on a phone, cap the entity chips and count what's
                // genuinely hidden. n.top_entities is NOT bounded by the
                // backend; the .slice(0, 4) below is a separate, pre-existing
                // desktop ceiling. If we counted the mobile remainder against
                // that already-sliced array, a thread with (say) 10 entities
                // would read "+2" while 8 are actually not shown — a silent
                // drop moved one truncation earlier than the one being
                // counted. Count against the TRUE total instead so "+N" is
                // honest. Desktop keeps its own separate, pre-existing silent
                // 4-cap unchanged (out of scope here — see task report).
                const cappedEntities = n.top_entities.slice(0, 4)
                const { shown: shownEntities } = visibleEntities(cappedEntities, isMobile)
                const hiddenEntityCount = isMobile ? n.top_entities.length - shownEntities.length : 0
                return (
                    <React.Fragment key={n.thread_id}>
                    {sectionLabel && (
                        rowIdx === firstEclipseIdx || rowIdx === firstShadowIdx ? (
                            <div className={`section-label ecl-section-label ecl-section-label--${rowIdx === firstEclipseIdx ? 'eclipse' : 'shadow'}`}>
                                {sectionLabel}
                            </div>
                        ) : (
                            <div className="section-label sl-section-label">
                                {sectionLabel}
                            </div>
                        )
                    )}
                    <div
                        className={`narrative-row ${isCategoryRow ? 'narrative-row--category' : ''} ${isFocused ? 'focused' : ''} ${isDimmed ? 'dimmed' : ''} ${eclipseRole === 'eclipse' ? 'ecl-row-eclipse' : eclipseRole === 'shadow' ? 'ecl-row-shadow' : ''} ${lensRole === 'anchor' ? 'sl-row-anchor' : lensRole === 'sibling' ? 'sl-row-sibling' : ''} ${isSynthRow ? 'sl-row-synth' : ''}`}
                        data-tip={rowHint}
                        onClick={() => handleClick(n)}
                        style={{ borderLeftColor: threadAccent }}
                    >
                        {/* Row 1: Label + stats */}
                        <div className="narrative-header">
                            <div className="narrative-label">
                                <span className={`sentiment-dot ${n.sentiment_swing_10h && n.sentiment_swing_10h > 0.1 ? 'pos' : n.sentiment_swing_10h && n.sentiment_swing_10h < -0.1 ? 'neg' : 'neu'}`} data-tip={`10h sentiment swing: ${n.sentiment_swing_10h == null ? 'not available' : n.sentiment_swing_10h.toFixed(2)}`} />
                                {!isSynthRow && <span className={`trend-arrow ${n.trend}`}>{trendArrow}</span>}
                                {/* The category row's own affordance: a leading badge in the
                                    TITLE line (not the kicker), so the level is legible before
                                    the eye reaches the label — the kicker alone was what Pedro
                                    read as the row's identity. */}
                                {isCategoryRow && (
                                    <span
                                        className="badge narrative-kind-badge"
                                        data-tip="A CATEGORY (Atlas theme) — the lens that groups every story of this kind. Its number, countries and entities describe the whole group, not a single story."
                                    >◫ CATEGORY</span>
                                )}
                                {isFamilyRow && (
                                    <span
                                        className="badge narrative-kind-badge"
                                        data-tip={familyRowTip(n.label, familyChildCount)}
                                    >{familyRowBadge(familyChildCount)}</span>
                                )}
                                <ThreadLabelText label={n.label} isMobile={isMobile} />
                                {/* #236 review fix: this used to live INSIDE .narrative-label-text,
                                    which on mobile is a -webkit-line-clamp box — a long title could
                                    fill both clamped lines and silently swallow the ↔ relation-reason
                                    chip with no indication, defeating the no-silent-filtering rail it
                                    exists to satisfy. Hoisted to a sibling of .narrative-label-text so
                                    it gets the same treatment as LabelReviewChip/TemporalSignatureChip
                                    below: never inside the clamp, always wraps onto its own line. */}
                                <span className="narrative-cluster-label">
                                    {domainLabel}
                                    {lensReason ? (
                                        <span
                                            className="narrative-sibling-reason"
                                            data-tip={lensReason.isBlob
                                                ? `Measured relation: ${lensReason.text} — flagged as a possible multi-story blob; relation may be inflated`
                                                : `Measured relation: ${lensReason.text}`}
                                        >
                                            ↔ {lensReason.text}
                                        </span>
                                    ) : siblingReason && (
                                        <span className="narrative-sibling-reason" data-tip={`Related to the open story via ${siblingReason}`}>
                                            ↔ {siblingReason}
                                        </span>
                                    )}
                                </span>
                                <LabelReviewChip
                                    labelStatus={n.label_status}
                                    avgConfidence={n.avg_confidence}
                                    confidenceMeasured={n.confidence_measured}
                                    labelProposed={n.label_proposed}
                                    courtWithheld={n.court_withheld}
                                />
                                <TemporalSignatureChip
                                    signature={n.temporal_signature}
                                    meta={n.signature_meta}
                                />
                            </div>
                            {/* Fix round 2026-07-17 item 2: the row number has TWO different
                                true bases depending on the row's engine path, and the chip must
                                state the right one — labeling both "raw" made the row (42) and
                                the detail (347) contradict under identical tooltips.
                                - Atlas rows (gate fields served): signal_count IS the raw
                                  assigned count → "raw" + verified lineage.
                                - Dynamic rows (gate fields null): signal_count is the SERVED
                                  membership for the window → "gated"; the detail's raw count
                                  is honestly larger. */}
                            {isSynthRow ? (
                                // T11 gate fix (L1): a synthesized row has no signal count to
                                // show — the ONLY quantitative fact it carries is the measured
                                // walk weight. Rendered verbatim, never reformatted into a
                                // fabricated count/thin/limited badge.
                                <span
                                    className="narrative-count sl-row-synth-weight"
                                    data-tip="Measured composite walk weight (whitened cosine, product over hops) — not a signal count. This story is not in the panel's current top-ranked pool; open it to see its own numbers."
                                >
                                    walk {n.lensWeight != null ? n.lensWeight.toFixed(2) : '—'}
                                </span>
                            ) : (() => {
                                /* Fix round 2026-08-14: a CATEGORY row's number is the signal
                                   total for the whole lens, summed over every story inside it —
                                   a different question from a story's count, so it gets its own
                                   base word and its own tip. Story/umbrella rows keep the
                                   pre-existing raw/gated lineage split untouched. */
                                const rowBase = rowCountBase(rowKind, n)
                                /* N19: the window word must follow the row's engine path the
                                   same way `rowBase` already does. Dynamic rows count the
                                   latest snapshot (measured 168h → "7d"); atlas rows really
                                   are filtered to the request, so they keep "24h". Hardcoding
                                   '24h' for both made the row contradict the detail on the
                                   window as well as the number. */
                                const rowWindow = formatCountWindow(n.count_window_hours) ?? '24h'
                                return (
                            <span
                                className="narrative-count"
                                data-tip={isCategoryRow
                                    ? categoryRowTip(n.label, n.signal_count, rowWindow)
                                    : n.gate_scored_count && n.gated_signal_count != null && n.gated_signal_count !== n.signal_count
                                    ? `${countQualifier(n.signal_count, rowWindow, 'raw').tip} ${(n.gated_signal_count ?? 0).toLocaleString()} verified by the relevance gate — the detail view shows the verified set.`
                                    : countQualifier(n.signal_count, rowWindow, rowBase).tip}
                            >
                                {n.signal_count > 999 ? `${(n.signal_count / 1000).toFixed(1)}k` : n.signal_count}
                                <CountQualifierChip count={n.signal_count} windowLabel={rowWindow} base={rowBase} />
                                {!!n.gate_scored_count && n.gated_signal_count != null && n.gated_signal_count !== n.signal_count && (
                                    <span className="narrative-count-lineage" data-tip={countQualifier(n.gated_signal_count, rowWindow, 'verified').tip}>
                                        {n.gated_signal_count.toLocaleString()} verified
                                    </span>
                                )}
                                {n.signal_count < 10 && (
                                    <span className="badge coverage-badge coverage-badge--thin" data-tip={`Only ${n.signal_count} signals — treat as indicative only`}>thin</span>
                                )}
                                {n.signal_count >= 10 && n.signal_count < 50 && (
                                    <span className="badge coverage-badge coverage-badge--limited" data-tip={`${n.signal_count} signals — limited coverage`}>~</span>
                                )}
                                {/* Eclipse lens: the relation made physical — this story's sliver
                                    of coverage next to the share the eclipse is holding. */}
                                {eclipseRole === 'shadow' && eclipseData?.dominant?.share != null && (
                                    <span className="ecl-share-vs" data-tip="This story's share of coverage vs the eclipsing story">
                                        {`${((shadowShare(n) ?? 0) * 100).toFixed(1)}% vs ${Math.round(eclipseData.dominant.share * 100)}%`}
                                    </span>
                                )}
                            </span>
                                )
                            })()}
                            <button
                                className={`narrative-pin ${isPinned(`theme-${n.thread_id}`) ? 'narrative-pin--active' : ''}`}
                                data-tip={isPinned(`theme-${n.thread_id}`) ? 'Unpin from investigation' : 'Pin story to investigation'}
                                onClick={e => {
                                    e.stopPropagation()
                                    const id = `theme-${n.thread_id}`
                                    if (isPinned(id)) unpinItem(id)
                                    else pinItem({ id, type: 'theme', title: n.label, urlParams: `?theme=${encodeURIComponent(n.thread_id)}` })
                                }}
                            >◆</button>
                        </div>

                        {/* Row 2: Countries, Persons, attention badges + age */}
                        <div className="narrative-detail">
                            <div className="narrative-entities">
                                {geography.codes.map((c, index) => (
                                    <button key={c} className={`country-pip country-pip--btn${filter.country === c ? ' country-pip--active' : ''}`} onClick={e => handleCountryPipClick(e, c)} data-tip={`${geography.label}: ${geography.names[index] || resolveCountryName(c, c)}`}><Flag code={c} /> {c}</button>
                                ))}
                                {shownEntities.map(p => {
                                    const personPinId = `person-${p}`
                                    const personPinned = isPinned(personPinId)
                                    return (
                                        <span key={p} className={`person-pip${filter.person === p ? ' person-pip--active' : ''}`}>
                                            <button
                                                type="button"
                                                className="person-pip-focus"
                                                onClick={e => { e.stopPropagation(); setPerson(p) }}
                                                data-tip={`Focus on ${p}`}
                                            >{p}</button>
                                            <button
                                                type="button"
                                                className={`person-pip-pin${personPinned ? ' person-pip-pin--active' : ''}`}
                                                data-tip={personPinned ? 'Unpin from investigation' : 'Pin person to investigation'}
                                                onClick={e => {
                                                    e.stopPropagation()
                                                    if (personPinned) unpinItem(personPinId)
                                                    else pinItem(personPin(p))
                                                }}
                                            >◆</button>
                                        </span>
                                    )
                                })}
                                {/* Deliberate v1 trade-off: the entities folded into +N lose
                                    their individual focus/pin affordances on mobile — the count
                                    is honest, but it offers no way to act on any one of them.
                                    Not a bug; do not "fix" by expanding the cap without deciding
                                    that trade-off on purpose. */}
                                {hiddenEntityCount > 0 && (
                                    <span className="narrative-entity-more" data-tip="More entities in this story">
                                        +{hiddenEntityCount}
                                    </span>
                                )}
                                {n.has_public_interest && (
                                    <span className="attention-badge search" data-tip={`Trending searches: ${(n.trending_keywords || []).join(', ')}`}>
                                        SEARCH
                                    </span>
                                )}
                                {n.has_wiki_activity && (
                                    <span className="attention-badge wiki" data-tip={`${(n.wiki_views || 0).toLocaleString()} Wikipedia views`}>
                                        WIKI {n.wiki_views && n.wiki_views > 1000 ? `${Math.round(n.wiki_views / 1000)}K` : ''}
                                    </span>
                                )}
                                {n.discussion_count != null && n.discussion_count > 0 && (
                                    <span className="attention-badge forum" data-tip={`${n.discussion_count} forum post(s) discussing this — people-side, not evidence.${n.forum_sentiment != null ? ` Public mood ${n.forum_sentiment > 0.1 ? 'positive' : n.forum_sentiment < -0.1 ? 'negative' : 'neutral'} (${n.forum_sentiment.toFixed(1)}).` : ''}`}>
                                        FORUM {n.discussion_count}{n.forum_sentiment != null ? ` · ${n.forum_sentiment > 0.1 ? '▲' : n.forum_sentiment < -0.1 ? '▼' : '–'}` : ''}
                                    </span>
                                )}
                                <RelationshipChip rel={relationships[n.thread_id]} compact />
                            </div>
                            <span className="narrative-age">{timeAgo(n.first_seen)}</span>
                        </div>

                        {/* Row 3: Spread bar + trend — T11 gate fix (L1): a synthesized row
                            has no confidence measurement and no trend; neither exists to
                            show, so the row omits them rather than printing the type's
                            placeholder defaults ('' / 'stable') as if they were measured. */}
                        {!isSynthRow && (
                        <div className="spread-row">
                            {n.show_confidence_bar && n.confidence_bar_pct != null && (
                                <div className="narrative-grad-bar-track"
                                     data-tip={confidenceBucketTip(n.confidence_bucket, n.confidence_bucket_source)}>
                                    <div
                                        className="narrative-grad-bar-fill"
                                        style={{
                                            // Bucket level, not the raw assignment number: the bar
                                            // must not paint a full track under a "medium" word.
                                            width: `${Math.min(n.confidence_bar_pct, 100)}%`,
                                            background: threadGradient,
                                        }}
                                    />
                                </div>
                            )}
                            <span className="spread-label spread-label--confidence" data-tip={confidenceBucketTip(n.confidence_bucket, n.confidence_bucket_source)}>{n.confidence_label}</span>
                            <span className={`trend-label ${n.trend}`} data-tip="Trend: Accelerating = volume growing, Fading = volume declining, Stable = consistent">
                                {n.trend === 'accelerating' ? '▲ Accelerating' : n.trend === 'fading' ? '▼ Fading' : '→ Stable'}
                            </span>
                        </div>
                        )}

                        {/* Row 4: Sparkline — omitted for a synthesized row (no hourly
                            timeline exists; Sparkline would render null anyway, but the
                            wrapping tooltip div would still show a misleading hover). */}
                        {!isSynthRow && (
                        <div data-tip="Signal volume over time: each point is one hour. Rising = growing coverage, falling = cooling off.">
                            <Sparkline data={n.hourly_timeline} color={n.confidence_trend_color} />
                        </div>
                        )}
                    </div>
                    </React.Fragment>
                )
            })}
        </div>
    )
}
