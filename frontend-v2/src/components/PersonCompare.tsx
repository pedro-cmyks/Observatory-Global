import { EntityPanel } from './EntityPanel'
import { CompareDashboard } from './CompareDashboard'
import { type TimeRange } from '../lib/timeRanges'

interface PersonCompareProps {
    personA: string
    personB: string
    timeRange: TimeRange
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
}

export function PersonCompare({ personA, personB, timeRange, onClose, onThemeSelect, onCountrySelect, onSourceClick }: PersonCompareProps) {
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
                timeRange={timeRange}
                onClose={onClose}
                onThemeSelect={onThemeSelect}
                onCountrySelect={onCountrySelect}
                onSourceClick={onSourceClick}
            />
            <EntityPanel
                inline
                focusType="person"
                focusValue={personB}
                timeRange={timeRange}
                onClose={onClose}
                onThemeSelect={onThemeSelect}
                onCountrySelect={onCountrySelect}
                onSourceClick={onSourceClick}
            />
        </CompareDashboard>
    )
}
