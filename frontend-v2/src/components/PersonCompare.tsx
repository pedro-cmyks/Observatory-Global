import { EntityPanel } from './EntityPanel'
import { CompareDashboard } from './CompareDashboard'

interface PersonCompareProps {
    personA: string
    personB: string
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
}

export function PersonCompare({ personA, personB, onClose, onThemeSelect, onCountrySelect, onSourceClick }: PersonCompareProps) {
    return (
        <CompareDashboard
            modeLabel="Person Compare"
            leftLabel={personA}
            rightLabel={personB}
            accent="#a78bfa"
            onClose={onClose}
        >
            <EntityPanel
                inline
                focusType="person"
                focusValue={personA}
                onClose={onClose}
                onThemeSelect={onThemeSelect}
                onCountrySelect={onCountrySelect}
                onSourceClick={onSourceClick}
            />
            <EntityPanel
                inline
                focusType="person"
                focusValue={personB}
                onClose={onClose}
                onThemeSelect={onThemeSelect}
                onCountrySelect={onCountrySelect}
                onSourceClick={onSourceClick}
            />
        </CompareDashboard>
    )
}
