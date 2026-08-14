import { useCallback } from 'react'
import {
    PAGE_LANGUAGE_OPTIONS,
    getStoredPageLanguage,
    setPageLanguage,
    usePageLanguage,
} from '../lib/pageLanguage'
import { UI_LANGS, useUiCopy, uiLang } from '../lib/uiCopy'
import { track } from '../lib/telemetry'
import './ReaderLanguagePicker.css'

/**
 * The language control, in the masthead where a reader who cannot read the
 * page will actually find it. Settings → Page Language exists, but it lives
 * inside the console — unreachable from /brief, which is the door a phone
 * reader arrives at.
 *
 * It writes the EXISTING page-language store, so one choice moves two things
 * at once: the chrome (this app's own labels, authored in en/es) and the
 * translation target for content (headlines, excerpts — any language). No
 * reload, no scroll loss: the store is a `useSyncExternalStore` subscription,
 * so switching re-renders in place.
 *
 * Honesty: a language with no authored chrome keeps ENGLISH chrome rather
 * than a machine-translated interface, and the option list says which
 * languages the interface itself is written in.
 */
export function ReaderLanguagePicker() {
    const { t } = useUiCopy()
    const active = usePageLanguage()
    const stored = getStoredPageLanguage()

    const onChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
        const value = e.target.value
        const next = value === 'auto' ? null : value
        setPageLanguage(next)
        track('brief_language_change', {
            to: next ?? 'auto',
            chrome: uiLang(next ?? active),
        })
    }, [active])

    // The chip prints the ACTIVE code (what you are reading now), while the
    // select holds the stored choice — 'auto' is a real, distinct state.
    const activeLabel = PAGE_LANGUAGE_OPTIONS.find(o => o.code === active)?.label ?? active.toUpperCase()

    return (
        <label className="reader-chip reader-lang" data-tip={t('brief.lang.tip')}>
            <span className="reader-lang-glyph" aria-hidden="true">◍</span>
            <span className="reader-lang-code" aria-hidden="true">{active.toUpperCase()}</span>
            <select
                className="reader-lang-select"
                value={stored ?? 'auto'}
                onChange={onChange}
                aria-label={`${t('brief.lang.label')} — ${activeLabel}`}
            >
                <option value="auto">{t('brief.lang.auto')}</option>
                {PAGE_LANGUAGE_OPTIONS.map(o => (
                    <option key={o.code} value={o.code}>
                        {/* A dot marks the languages the INTERFACE is written in;
                            the rest translate content only. Stated, not implied. */}
                        {UI_LANGS.includes(o.code as 'en' | 'es') ? `${o.label} ·` : o.label}
                    </option>
                ))}
            </select>
        </label>
    )
}
