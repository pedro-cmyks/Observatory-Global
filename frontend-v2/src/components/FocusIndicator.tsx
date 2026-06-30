import { useFocus } from '../contexts/FocusContext'
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

    return (
        <div className="focus-indicator">
            <span className="focus-dot" aria-hidden="true" />
            <span className="focus-meta">{typeLabels[focus.type]}</span>
            <span className="focus-value">{focus.label}</span>
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
