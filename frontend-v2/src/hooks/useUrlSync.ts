import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFocus } from '../contexts/FocusContext'
import { mergeFocusIntoParams } from '../lib/navParams'

/**
 * Bidirectional sync between FocusContext filter state and URL search params.
 *
 * On mount: reads URL params → hydrates FocusContext.
 * On filter change: pushes filter state to URL (replace, not push to avoid history spam).
 *
 * URL format:
 *   /app?theme=ARMEDCONFLICT&country=CO
 *   /app?concept=blood-diamonds&region=africa
 *   /app?person=petro
 *
 * `time=` is no longer read or written (2026-07-15): the VIEW selector is
 * gone — the map scrubber is time and it is session-local, not URL state.
 */
export function useUrlSync() {
    const { filter, setCountry, setTheme, setPerson } = useFocus()
    const [searchParams, setSearchParams] = useSearchParams()
    const isHydrating = useRef(true)
    const prevFilterRef = useRef<string>('')
    // Track the live params in a ref so the write-back can PRESERVE non-focus
    // carry-context params (q/label/attention/entry) without adding
    // `searchParams` to the effect deps (which would re-fire on our own write).
    const searchParamsRef = useRef(searchParams)
    searchParamsRef.current = searchParams

    // On mount: read URL → hydrate FocusContext (once)
    useEffect(() => {
        const theme = searchParams.get('theme')
        const country = searchParams.get('country')
        const person = searchParams.get('person')

        let hydrated = false
        if (theme) { setTheme(theme); hydrated = true }
        if (country) { setCountry(country); hydrated = true }
        if (person) { setPerson(person); hydrated = true }

        // Small delay to let hydration settle before enabling write-back
        setTimeout(() => { isHydrating.current = false }, 500)
        if (!hydrated) { isHydrating.current = false }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // On filter change: write to URL, MERGING focus dims into the live params
    // (so carry-context params q/label/attention/entry survive — the prior
    // fresh-URLSearchParams build deleted them on every focus change).
    useEffect(() => {
        if (isHydrating.current) return

        const serialized = mergeFocusIntoParams(searchParamsRef.current.toString(), {
            theme: filter.theme,
            country: filter.country,
            person: filter.person,
        })
        if (serialized !== prevFilterRef.current) {
            prevFilterRef.current = serialized
            setSearchParams(new URLSearchParams(serialized), { replace: true })
        }
    }, [filter.theme, filter.country, filter.person, setSearchParams])
}
