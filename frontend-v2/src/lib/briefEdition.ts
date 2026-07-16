// Edition sectioning for the L1 Brief (the Atlas Edition re-skin).
//
// The Edition model splits the day's tracked threads into three color-coded
// sections — The World (emerald) / Under the Radar (ochre) / Culture, Sport &
// Life (plum). NOTHING is dropped: culture/sport/lifestyle threads get their
// own section instead of crowding the front page or being silently damped
// out of view. Classification is deterministic:
//
//   1. the thread's own category (R3.1 open category, served as `category`
//      or `parent_domain`) resolved through the shared famOf keyword map —
//      when the engine typed the story, trust the engine;
//   2. only when no category is served, fall back to the same keyword map
//      over the LABEL (the artifact-spec behavior for untyped threads).

import { famOf } from './categoryFamily'

export interface EditionThreadLike {
    label: string
    category?: string | null
    parent_domain?: string | null
}

/** Deterministic: category (when served) wins; label keywords only as fallback. */
export function isCultureThread(t: EditionThreadLike): boolean {
    const cat = t.category ?? t.parent_domain
    if (cat) return famOf(cat) === 'culture'
    return famOf(t.label) === 'culture'
}

/** Stable partition (original order preserved inside each section). */
export function splitEditionThreads<T extends EditionThreadLike>(
    threads: readonly T[],
): { world: T[]; culture: T[] } {
    const world: T[] = []
    const culture: T[] = []
    for (const t of threads) {
        ;(isCultureThread(t) ? culture : world).push(t)
    }
    return { world, culture }
}

export interface ShareCaptionInput {
    leadLabel: string | null
    signals: number
    countries: number
    sources: number
}

/**
 * LinkedIn caption for the share dialog. Honest framing: measured coverage,
 * explicit base, no editorial verdict. `<your link>` stays a placeholder the
 * user replaces — we never fabricate a URL.
 */
export function buildShareCaption({ leadLabel, signals, countries, sources }: ShareCaptionInput): string {
    const leadLine = leadLabel
        ? ` Today's edition leads with: ${leadLabel}.`
        : ''
    return (
        `The news of the world, measured — not editorialized.${leadLine}\n\n` +
        `Measured from ${signals.toLocaleString()} signals across ${countries} countries` +
        ` and ${sources.toLocaleString()} sources, in the last 24 hours.\n\n` +
        `Read today's full Atlas Edition → <your link>`
    )
}
