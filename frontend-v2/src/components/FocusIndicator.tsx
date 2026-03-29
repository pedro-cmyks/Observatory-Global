import { useFocus } from '../contexts/FocusContext'
import './FocusIndicator.css'

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
            <span className="focus-icon" style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                borderRadius: '4px',
                background: 'var(--color-accent-primary)',
                color: 'var(--color-bg-primary)',
                fontSize: '10px',
                fontWeight: 'bold'
            }}>
                {focus.type.charAt(0).toUpperCase()}
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
                ×
            </button>
        </div>
    )
}

