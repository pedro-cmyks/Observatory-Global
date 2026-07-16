import { useFocus } from '../contexts/FocusContext'
import { resolveThreadLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import './FocusIndicator.css'

const typeLabels: Record<string, string> = {
    thread: 'Thread',
    theme: 'Theme',
    entity: 'Entity',
    person: 'Person',
    country: 'Country',
    source: 'Source'
}

export function FocusIndicator({ onClear }: { onClear?: () => void } = {}) {
    const { focus, clearFocus, isActive } = useFocus()

    if (!isActive || !focus.type) return null

    // For a theme/thread focus, focus.label is the raw filter.theme id
    // (dynamic-topic-N / atlas slug). Resolve it to a human label — never show
    // the raw id — while GDELT theme codes still route through getThemeLabel.
    const displayLabel = (focus.type === 'theme' || focus.type === 'thread')
        ? resolveThreadLabel(focus.label)
        : focus.type === 'country'
            ? resolveCountryName(focus.label)   // "Australia", never a raw "AU"
            : focus.label

    return (
        <div className="focus-indicator" role="status">
            <span className="focus-dot" aria-hidden="true" />
            <span className="focus-meta">{typeLabels[focus.type]} focus</span>
            <span className="focus-value">{displayLabel}</span>
            {/* Pedro 2026-07-16: the floating chip covered the layer chips.
                Now a full-width in-flow band — and since EVERY surface
                re-scopes to the focus, the band says so. */}
            <span className="focus-scope-note">map · threads · stream · universe re-scoped</span>
            <button
                className="focus-clear"
                data-tour="focus-clear"
                onClick={onClear ?? clearFocus}
                data-tip="Clear focus — back to the whole view"
                aria-label="Clear focus"
            >
                ×
            </button>
        </div>
    )
}
