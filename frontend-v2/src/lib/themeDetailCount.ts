/**
 * Header count + window semantics for ThemeDetail (timeout-as-absence fix,
 * cc0bf804 class).
 *
 * Two honest states the old header could not express:
 *  - DEGRADED: the backend's count query timed out or failed. The payload now
 *    carries `total: null` + `degraded: true` + a reason code (mirrors
 *    /api/v2/stats). That is NOT MEASURED — rendering it as "0 signals" turns
 *    a timeout into a measured claim of absence.
 *  - FIRST FETCH IN FLIGHT: there is no honest count OR window yet. The old
 *    branch printed "… signals · Last 24h" — a window word stamped on nothing
 *    (the N19 rule: never print an assumed window, see d822ae17).
 */

export interface ThemeCountMetaInput {
    loading: boolean
    /** Whether a resolved payload is on screen (data !== null). */
    hasData: boolean
    total?: number | null
    degraded?: boolean
    degradedReason?: string | null
    /** The requested window, only stamped on a measured count. */
    hours: number
}

export interface ThemeCountMeta {
    /** '…' while the first fetch is in flight · 'not measured' when degraded
     *  · the formatted count otherwise. */
    countText: string
    unmeasured: boolean
    /** 'Last Nh', or null when there is no measured count to window. */
    windowLabel: string | null
    /** Banner copy for degraded payloads (reason codes mapped to user
     *  language — db_error never reaches the screen raw); null otherwise. */
    notice: string | null
}

export function resolveThemeCountMeta(input: ThemeCountMetaInput): ThemeCountMeta {
    const { loading, hasData, total, degraded, degradedReason, hours } = input

    if (!hasData) {
        // First fetch in flight (or failed before any payload): no count, no
        // window word.
        return { countText: loading ? '…' : '—', unmeasured: false, windowLabel: null, notice: null }
    }

    if (degraded || total == null) {
        const notice = degradedReason === 'db_timeout'
            ? 'Counts not measured — the data query timed out under load. This is not zero; retry shortly.'
            : 'Counts not measured — the data query did not complete. This is not zero.'
        return { countText: 'not measured', unmeasured: true, windowLabel: null, notice }
    }

    return {
        countText: total.toLocaleString('en-US'),
        unmeasured: false,
        windowLabel: `Last ${hours}h`,
        notice: null,
    }
}
