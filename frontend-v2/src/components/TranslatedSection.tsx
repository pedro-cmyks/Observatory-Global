import React, { createContext, useCallback, useContext, useEffect, useId, useMemo, useState } from 'react'
import {
    EMPTY_SECTION_PROGRESS,
    SECTION_TRANSLATION_DEFAULT,
    type ChildTranslationStatus,
    type SectionProgress,
    type SectionTranslationState,
    nextSectionStateWithProgress,
    sectionControlCopy,
    summarizeProgress,
} from '../lib/sectionTranslation'
import './TranslatedSection.css'

/**
 * Section-level translate control (Pedro 2026-08-11; made honest 2026-08-13).
 * Wrap a Brief thread section in <TranslatedSection> and every
 * TranslatableHeadline / TranslatableText inside follows the section's mode;
 * the control node is handed to the section's own markup (function-as-child)
 * so each section places it near its court-chip area. Consumers with NO
 * provider get the frozen default context — behavior byte-identical to before
 * this existed.
 *
 * W3 (re-judge 2026-08-13): the control used to flip its label the instant it
 * was clicked, decoupled from whether a single word had been translated. On
 * prod every translate request was 429-ing (the whole lane shares the `paid`
 * 20/300s bucket), so the button read SHOW ORIGINALS over a page of untouched
 * Spanish, French and Arabic. Now children REPORT their real state back here
 * and the control is derived from it: pending while requests are out, a flip
 * only when something actually landed, and an honest note when it did not.
 *
 * Honesty rails: the control only drives what was already translatable —
 * tier/court/state-media chips and source names are never inside a
 * translation lane, so they cannot be translated away.
 */

const SectionTranslationContext = createContext<SectionTranslationState>(SECTION_TRANSLATION_DEFAULT)

export function useSectionTranslation(): SectionTranslationState {
    return useContext(SectionTranslationContext)
}

type ReportFn = (key: string, status: ChildTranslationStatus) => void
type ForgetFn = (key: string) => void

const NOOP_REPORT: { report: ReportFn; forget: ForgetFn } = { report: () => {}, forget: () => {} }
const SectionReportContext = createContext(NOOP_REPORT)

/**
 * Called by every translatable child with its CURRENT real state. Outside a
 * <TranslatedSection> this is an inert no-op, so nothing changes for the
 * console / country surfaces that render translatables without a section.
 */
export function useReportTranslationStatus(status: ChildTranslationStatus): void {
    const { report, forget } = useContext(SectionReportContext)
    const key = useId()
    useEffect(() => { report(key, status) }, [report, key, status])
    useEffect(() => () => forget(key), [forget, key])
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
    const [statuses, setStatuses] = useState<Map<string, ChildTranslationStatus>>(() => new Map())

    const report = useCallback<ReportFn>((key, status) => {
        setStatuses(prev => {
            if (prev.get(key) === status) return prev // identity-stable: no render loop
            const next = new Map(prev)
            next.set(key, status)
            return next
        })
    }, [])
    const forget = useCallback<ForgetFn>(key => {
        setStatuses(prev => {
            if (!prev.has(key)) return prev
            const next = new Map(prev)
            next.delete(key)
            return next
        })
    }, [])
    const reporter = useMemo(() => ({ report, forget }), [report, forget])

    const progress: SectionProgress = useMemo(
        () => (statuses.size ? summarizeProgress(statuses.values()) : EMPTY_SECTION_PROGRESS),
        [statuses],
    )
    const copy = sectionControlCopy(state.mode, progress)

    const control = active ? (
        <span className="brief-translate-wrap">
            <button
                type="button"
                className={`brief-translate-all${copy.busy ? ' is-busy' : ''}`}
                data-tip={copy.tip}
                aria-busy={copy.busy || undefined}
                disabled={copy.busy}
                onClick={e => {
                    e.stopPropagation()
                    if (copy.busy) return
                    setState(s => nextSectionStateWithProgress(s, progress))
                }}
            >
                ⇄ {copy.label}
            </button>
            {copy.note && <span className="brief-translate-note">{copy.note}</span>}
        </span>
    ) : null

    return (
        <SectionTranslationContext.Provider value={state}>
            <SectionReportContext.Provider value={reporter}>
                {children(control)}
            </SectionReportContext.Provider>
        </SectionTranslationContext.Provider>
    )
}

export default TranslatedSection
