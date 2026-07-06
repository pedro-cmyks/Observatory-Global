import { useFocus } from '../contexts/FocusContext'
import { resolveThreadLabel } from '../lib/themeLabels'
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
        : focus.label

    return (
        <div className="focus-indicator">
            <span className="focus-dot" aria-hidden="true" />
            <span className="focus-meta">{typeLabels[focus.type]}</span>
            <span className="focus-value">{displayLabel}</span>
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
