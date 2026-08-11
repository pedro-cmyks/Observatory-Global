/**
 * Section-level translation state (#Brief translate-all — Pedro 2026-08-11).
 *
 * A thread section in the Brief (lead / card / unassembled entry) can drive
 * ALL its translatable children (headlines, labels, excerpts) at once:
 *   - 'auto'       — default: each child shows its translation when one
 *                    exists (the Instagram-style default), original otherwise.
 *   - 'translated' — the section asked for everything translated; children
 *                    that previously failed or skipped retry their fetch.
 *   - 'original'   — the section asked for originals.
 *
 * `epoch` increments on every section action so children can (a) reset their
 * per-item toggle to follow the new section mode and (b) retry fetches on an
 * explicit Translate. A child's own "See original / See translation" toggle
 * ALWAYS wins after the section action (local override, cleared by the next
 * section action) — the per-item affordance never dies.
 *
 * Pure state helpers live here (node-testable); the context + control button
 * live in components/TranslatedSection.tsx.
 */

export type SectionTranslationMode = 'auto' | 'translated' | 'original'

export interface SectionTranslationState {
    mode: SectionTranslationMode
    epoch: number
}

export const SECTION_TRANSLATION_DEFAULT: SectionTranslationState = { mode: 'auto', epoch: 0 }

/** The section control was clicked: advance the mode, bump the epoch. */
export function nextSectionState(s: SectionTranslationState): SectionTranslationState {
    return {
        mode: s.mode === 'translated' ? 'original' : 'translated',
        epoch: s.epoch + 1,
    }
}

/**
 * What a child should show: its own toggle when the user touched it since the
 * last section action, else the section's preference ('auto' = translated
 * by default, i.e. NOT the original — today's behavior).
 */
export function resolveShowOriginal(
    localOriginal: boolean | null,
    mode: SectionTranslationMode,
): boolean {
    return localOriginal ?? (mode === 'original')
}

/** True when an explicit section Translate should retry a missing translation. */
export function shouldRetryFetch(state: SectionTranslationState): boolean {
    return state.mode === 'translated' && state.epoch > 0
}

export function sectionControlCopy(mode: SectionTranslationMode): { label: string; tip: string } {
    return mode === 'translated'
        ? {
            label: 'Show originals',
            tip: 'Show every headline and quote in this section in its original language',
        }
        : {
            label: 'Translate all',
            tip: 'Translate every headline and quote in this section to your page language (Settings → Page Language)',
        }
}
