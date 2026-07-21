import { useFocus } from '../contexts/FocusContext'
import { resolveThreadLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import './FocusIndicator.css'

interface FocusChip {
    key: string
    typeLabel: string
    value: string
    onRemove: () => void
}

export function FocusIndicator({ onClear }: { onClear?: () => void } = {}) {
    const { filter, clearFilter, setThread, setPerson, setCountry, setTheme, isActive } = useFocus()

    if (!isActive) return null

    // Compound focus (#country ∧ #theme ∧ #person can all be active at once,
    // see nextFocusDims in lib/focusReducer.ts) needs ONE chip PER dimension,
    // each independently dismissible — a single collapsed chip (the old
    // priority thread>person>country>theme) hid the other active dimensions.
    // filter.thread is exclusive with country/theme/person (opening a full
    // thread resets the others; setting any of the three clears thread), so
    // it renders as its own chip and never co-occurs with the compound trio.
    const chips: FocusChip[] = []

    if (filter.thread) {
        chips.push({
            key: 'thread',
            typeLabel: 'Thread',
            value: resolveThreadLabel(filter.thread, filter.themeLabel),
            onRemove: () => setThread(null),
        })
    }
    if (filter.person) {
        chips.push({
            key: 'person',
            typeLabel: 'Person',
            value: filter.person,
            onRemove: () => setPerson(null),
        })
    }
    if (filter.country) {
        chips.push({
            key: 'country',
            typeLabel: 'Country',
            value: resolveCountryName(filter.country), // "Australia", never a raw "AU"
            onRemove: () => setCountry(null),
        })
    }
    if (filter.theme) {
        chips.push({
            key: 'theme',
            typeLabel: 'Theme',
            value: resolveThreadLabel(filter.theme, filter.themeLabel),
            onRemove: () => setTheme(null),
        })
    }

    if (chips.length === 0) return null

    return (
        <div className="focus-indicator" role="status">
            <span className="focus-dot" aria-hidden="true" />
            <div className="focus-chips">
                {chips.map(chip => (
                    <span className="focus-chip" key={chip.key}>
                        <span className="focus-meta">{chip.typeLabel}</span>
                        <span className="focus-value">{chip.value}</span>
                        <button
                            className="focus-clear focus-chip-clear"
                            onClick={chip.onRemove}
                            data-tip={`Clear ${chip.typeLabel.toLowerCase()} focus — keep the rest`}
                            aria-label={`Clear ${chip.typeLabel} focus`}
                        >
                            ×
                        </button>
                    </span>
                ))}
            </div>
            {/* Pedro 2026-07-16: the floating chip covered the layer chips.
                Now a full-width in-flow band — and since EVERY surface
                re-scopes to the focus, the band says so. */}
            <span className="focus-scope-note">map · threads · stream · universe re-scoped</span>
            <button
                className="focus-clear focus-clear-all"
                data-tour="focus-clear"
                onClick={onClear ?? clearFilter}
                data-tip="Clear all focus — back to the whole view"
                aria-label="Clear all focus"
            >
                ×
            </button>
        </div>
    )
}
