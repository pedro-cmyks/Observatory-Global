/**
 * Staleness banner truth for the Brief's sealed daily edition.
 *
 * The sealed edition is built nightly on the M1 (02:30) and stored as one
 * compact row. On a bad night the seal does not complete and the L1 page falls
 * back to the always-current live brief. The banner must state, honestly:
 *   WHAT edition is served, HOW OLD it is, and WHEN the next attempt is —
 * plus an explicit sealed-vs-live split, so the reader is never misled about
 * whether they are looking at a frozen edition or the live view.
 *
 * Pure: all clock/config inputs are injected so it is deterministic under test.
 */

export interface StaleBannerInput {
    /** Seal moment (generated_at) as ISO string, or null if never sealed. */
    sealedAt: string | null
    /** Edition date (YYYY-MM-DD) of the sealed row, or null. */
    editionDate: string | null
    /** True when the served newspaper IS the sealed package (gate passed). */
    servedFromSeal: boolean
    /** Compatibility gate reason codes explaining why the seal was rejected. */
    reasonCodes?: string[]
    /** Injected clock. Defaults to now. */
    now?: Date
    /** Local wall-clock time of the nightly seal cron. */
    nextSealLocal?: string
    /**
     * REAL next attempt moment (ISO) served by the backend's seal_schedule
     * (computed from the actual launchd schedule constant). When present the
     * banner states honest relative time instead of a bare "02:30".
     */
    nextAttemptAt?: string | null
    /**
     * Backend schedule-window inference: an attempt is plausibly in flight
     * right now (inside the run window, no seal landed yet).
     */
    attemptWindowOpen?: boolean
}

export interface StaleBannerCopy {
    tone: 'fresh' | 'stale' | 'none'
    served: 'sealed' | 'live'
    /** What edition, e.g. "Today's sealed edition · Jul 17" / "Sealed edition from Jul 15". */
    edition: string
    /** How old, e.g. "sealed 2 days ago" — null when nothing was ever sealed. */
    age: string | null
    /** Why the seal is not being served (stale tone only), else ''. */
    why: string
    /** Honest live-below note when the live view is what's shown. */
    liveNote: string
    /** When the next seal will be attempted. */
    nextAttempt: string
    /** Full one-line human sentence, parts joined by ' · '. */
    sentence: string
}

const MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/** "2026-07-17" → "Jul 17" without timezone drift. */
function formatEditionDate(editionDate: string): string {
    const parts = editionDate.split('-')
    if (parts.length !== 3) return editionDate
    const month = MONTHS[Number(parts[1]) - 1]
    const day = Number(parts[2])
    if (!month || Number.isNaN(day)) return editionDate
    return `${month} ${day}`
}

function plural(n: number, unit: string): string {
    return `${n} ${unit}${n === 1 ? '' : 's'} ago`
}

/** Honest elapsed-time phrase, floored (never rounds a gap upward). */
function humanizeAge(sealedAt: string, now: Date): string {
    const ms = now.getTime() - new Date(sealedAt).getTime()
    const minutes = Math.floor(ms / 60000)
    if (minutes < 5) return 'sealed just now'
    if (minutes < 60) return `sealed ${plural(minutes, 'minute')}`
    if (minutes < 1440) return `sealed ${plural(Math.floor(minutes / 60), 'hour')}`
    return `sealed ${plural(Math.floor(minutes / 1440), 'day')}`
}

function whyPhrase(reasonCodes: string[]): string {
    if (reasonCodes.includes('contract_mismatch')) {
        return 'the sealed edition could not be read'
    }
    if (reasonCodes.includes('edition_degraded')) {
        return 'the last nightly publication did not complete'
    }
    if (reasonCodes.includes('candidate_universe_incomplete')) {
        return 'the last nightly publication did not finish reconciling'
    }
    return 'the last nightly publication did not complete'
}

/** "2026-07-17T02:30:00Z" edition date === now's UTC calendar day? */
function isTodayUtc(editionDate: string, now: Date): boolean {
    return editionDate === now.toISOString().slice(0, 10)
}

/** Honest next-attempt phrase (council N10): prefer the backend's schedule
 * truth; the hardcoded local time is only the no-schedule fallback. A past
 * nextAttemptAt (stale payload / clock skew) also falls back — the banner
 * never promises an attempt "in -2 h". */
function nextAttemptPhrase(input: StaleBannerInput, now: Date): string {
    const local = input.nextSealLocal ?? '02:30'
    if (input.attemptWindowOpen) return 'seal attempt likely in progress'
    if (input.nextAttemptAt) {
        const ms = new Date(input.nextAttemptAt).getTime() - now.getTime()
        if (!Number.isNaN(ms) && ms > 0) {
            const minutes = Math.round(ms / 60000)
            const when = minutes < 60
                ? `${minutes} min`
                : `${Math.round(minutes / 60)} h`
            return `next seal attempt in ${when} (${local})`
        }
    }
    return `next seal attempt ${local}`
}

export function buildStaleBanner(input: StaleBannerInput): StaleBannerCopy {
    const now = input.now ?? new Date()
    const reasonCodes = input.reasonCodes ?? []
    const nextAttempt = nextAttemptPhrase(input, now)
    const liveNote = 'live view below is current'

    // No edition was ever sealed — honest live-only, never invent an age.
    if (!input.sealedAt || !input.editionDate) {
        return {
            tone: 'none',
            served: 'live',
            edition: 'No sealed edition yet',
            age: null,
            why: '',
            liveNote,
            nextAttempt,
            sentence: ['No sealed edition yet', liveNote, nextAttempt].join(' · '),
        }
    }

    const dateLabel = formatEditionDate(input.editionDate)
    const age = humanizeAge(input.sealedAt, now)

    if (input.servedFromSeal) {
        const edition = isTodayUtc(input.editionDate, now)
            ? `Today's sealed edition · ${dateLabel}`
            : `Sealed edition from ${dateLabel}`
        return {
            tone: 'fresh',
            served: 'sealed',
            edition,
            age,
            why: '',
            liveNote,
            nextAttempt,
            sentence: [edition, age, nextAttempt].join(' · '),
        }
    }

    // A stale/incomplete seal exists but the live view is what's served.
    const edition = `Sealed edition from ${dateLabel}`
    const why = whyPhrase(reasonCodes)
    return {
        tone: 'stale',
        served: 'live',
        edition,
        age,
        why,
        liveNote,
        nextAttempt,
        sentence: [edition, age, why, liveNote, nextAttempt].join(' · '),
    }
}
