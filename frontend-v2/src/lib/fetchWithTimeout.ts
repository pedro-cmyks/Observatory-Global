/** Council R4 DESKTOP-N26 — the missing bound.
 *
 *  An audit of every loading surface found that only 8 fetch sites in the
 *  whole app paired an `AbortController` with a timer. Many components have
 *  a cleanup-only controller, which aborts a STALE request on unmount but
 *  does nothing about a HUNG one — so a slow endpoint left the skeleton up
 *  forever. `/api/v2/focus` was the worst case (45-120s mute), but the shape
 *  is shared by several panels.
 *
 *  This is the primitive those call sites were missing. It does not change
 *  any component's error semantics: a timeout surfaces as a rejected promise,
 *  which every one of these call sites already handles as "failed" — the
 *  difference is that now it eventually rejects instead of hanging.
 *
 *  Deliberately NOT a retry helper. `UniverseView` retries once because its
 *  payload is a cold-built artifact; the panels below want a bound, not a
 *  second heavy request.
 */

/** Default bound for ordinary panel fetches. Generous enough that a warm
 *  request never trips it, short enough that a user is not left staring at a
 *  skeleton wondering whether the app is alive. */
export const DEFAULT_FETCH_TIMEOUT_MS = 15000

export interface FetchWithTimeoutOptions extends RequestInit {
    timeoutMs?: number
    /** An outer signal (e.g. a component's cleanup controller). When it
     *  aborts, so does this request — the two bounds compose rather than
     *  one replacing the other. */
    parentSignal?: AbortSignal
}

/** `fetch` that is guaranteed to settle. Rejects with an AbortError once
 *  `timeoutMs` elapses. */
export function fetchWithTimeout(
    url: string,
    { timeoutMs = DEFAULT_FETCH_TIMEOUT_MS, parentSignal, ...init }: FetchWithTimeoutOptions = {},
): Promise<Response> {
    // Already-cancelled caller: reject without issuing a request at all,
    // rather than starting one and trusting fetch to honour a pre-aborted
    // signal. Saves a pointless round trip on every unmount-then-refetch.
    if (parentSignal?.aborted) {
        return Promise.reject(
            Object.assign(new Error('aborted'), { name: 'AbortError' }),
        )
    }

    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), timeoutMs)
    if (parentSignal) {
        parentSignal.addEventListener('abort', () => ctrl.abort(), { once: true })
    }

    return fetch(url, { ...init, signal: ctrl.signal })
        .finally(() => clearTimeout(timer))
}

/** The common "fetch JSON or give up" shape. Returns `fallback` on ANY
 *  failure — non-2xx, network error, or timeout — so callers that already
 *  treat absence as a state keep working unchanged, but can no longer hang.
 *
 *  Callers that must DISTINGUISH failure from emptiness should use
 *  `fetchWithTimeout` directly and keep their own error state; collapsing
 *  the two is exactly the dishonesty this track is closing, so this helper
 *  is only for call sites where the fallback is already the honest answer.
 */
export async function fetchJsonWithTimeout<T>(
    url: string,
    fallback: T,
    opts: FetchWithTimeoutOptions = {},
): Promise<T> {
    try {
        const res = await fetchWithTimeout(url, opts)
        if (!res.ok) return fallback
        return (await res.json()) as T
    } catch {
        return fallback
    }
}
