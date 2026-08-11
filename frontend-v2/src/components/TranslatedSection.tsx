import React, { createContext, useContext, useState } from 'react'
import {
    SECTION_TRANSLATION_DEFAULT,
    type SectionTranslationState,
    nextSectionState,
    sectionControlCopy,
} from '../lib/sectionTranslation'

/**
 * Section-level translate control (Pedro 2026-08-11). Wrap a Brief thread
 * section in <TranslatedSection> and every TranslatableHeadline /
 * TranslatableText inside follows the section's mode; the control node is
 * handed to the section's own markup (function-as-child) so each section
 * places it near its court-chip area. Consumers with NO provider get the
 * frozen default context — behavior byte-identical to before this existed.
 *
 * Honesty rails: the control only drives what was already translatable —
 * tier/court/state-media chips and source names are never inside a
 * translation lane, so they cannot be translated away.
 */

const SectionTranslationContext = createContext<SectionTranslationState>(SECTION_TRANSLATION_DEFAULT)

export function useSectionTranslation(): SectionTranslationState {
    return useContext(SectionTranslationContext)
}

interface Props {
    /** Gate: render no control (still provides the inert default) when the
     *  section has nothing translatable — no dead buttons on all-native
     *  sections. */
    active?: boolean
    children: (translateControl: React.ReactNode) => React.ReactNode
}

export const TranslatedSection: React.FC<Props> = ({ active = true, children }) => {
    const [state, setState] = useState<SectionTranslationState>(SECTION_TRANSLATION_DEFAULT)
    const copy = sectionControlCopy(state.mode)
    const control = active ? (
        <button
            type="button"
            className="brief-translate-all"
            data-tip={copy.tip}
            onClick={e => { e.stopPropagation(); setState(nextSectionState) }}
        >
            ⇄ {copy.label}
        </button>
    ) : null
    return (
        <SectionTranslationContext.Provider value={state}>
            {children(control)}
        </SectionTranslationContext.Provider>
    )
}

export default TranslatedSection
