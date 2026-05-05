import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFocus } from '../contexts/FocusContext'
import type { TimeRange } from '../lib/timeRanges'

/**
 * Bidirectional sync between FocusContext filter state and URL search params.
 *
 * On mount: reads URL params → hydrates FocusContext.
 * On filter change: pushes filter state to URL (replace, not push to avoid history spam).
 *
 * URL format:
 *   /app?theme=ARMEDCONFLICT&country=CO&time=24h
 *   /app?concept=blood-diamonds&region=africa
 *   /app?person=petro&time=1w
 */
export function useUrlSync() {
    const { filter, setCountry, setTheme, setPerson, setTimeRange } = useFocus()
    const [searchParams, setSearchParams] = useSearchParams()
    const isHydrating = useRef(true)
    const prevFilterRef = useRef<string>('')

    // On mount: read URL → hydrate FocusContext (once)
    useEffect(() => {
        const theme = searchParams.get('theme')
        const country = searchParams.get('country')
        const person = searchParams.get('person')
        const time = searchParams.get('time') as TimeRange | null

        let hydrated = false
        if (theme) { setTheme(theme); hydrated = true }
        if (country) { setCountry(country); hydrated = true }
        if (person) { setPerson(person); hydrated = true }
        if (time && ['24h', '1w', '1m', '3m', 'record'].includes(time)) {
            setTimeRange(time)
            hydrated = true
        }

        // Small delay to let hydration settle before enabling write-back
        setTimeout(() => { isHydrating.current = false }, 500)
        if (!hydrated) { isHydrating.current = false }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps — intentionally mount-only

    // On filter change: write to URL
    useEffect(() => {
        if (isHydrating.current) return

        const params = new URLSearchParams()
        if (filter.theme) params.set('theme', filter.theme)
        if (filter.country) params.set('country', filter.country)
        if (filter.person) params.set('person', filter.person)
        if (filter.timeRange && filter.timeRange !== '24h') params.set('time', filter.timeRange)

        const serialized = params.toString()
        if (serialized !== prevFilterRef.current) {
            prevFilterRef.current = serialized
            setSearchParams(params, { replace: true })
        }
    }, [filter.theme, filter.country, filter.person, filter.timeRange, setSearchParams])
}
