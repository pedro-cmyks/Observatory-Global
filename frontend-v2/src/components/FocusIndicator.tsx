import { useFocus } from '../contexts/FocusContext'
import './FocusIndicator.css'

const typeIcons: Record<string, string> = {
    theme: '🏷️',
    person: '👤',
    country: '🌍',
    source: '📰'
}

const typeLabels: Record<string, string> = {
    theme: 'Theme',
    person: 'Person',
    country: 'Country',
    source: 'Source'
}

export function FocusIndicator() {
    const { focus, clearFocus, isActive } = useFocus()

    if (!isActive || !focus.type) return null

    return (
        <div className="focus-indicator">
            <span className="focus-icon">
                {typeIcons[focus.type]}
            </span>
            <div className="focus-content">
                <span className="focus-type">
                    {typeLabels[focus.type]} Focus
                </span>
                <span className="focus-value">
                    {focus.label}
                </span>
            </div>
            <button
                className="focus-clear"
                onClick={clearFocus}
                title="Clear focus"
            >
                ✕
            </button>
        </div>
    )
}
