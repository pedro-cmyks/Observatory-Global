import { ThemeDetail } from './ThemeDetail'
import { CompareDashboard } from './CompareDashboard'
import { getThemeLabel } from '../lib/themeLabels'

interface ThemeCompareProps {
    themeA: string
    themeB: string
    hours: number
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountryCardClick?: (code: string, name: string) => void
    onPersonClick?: (name: string) => void
    onSourceClick?: (domain: string) => void
}

export function ThemeCompare({ themeA, themeB, hours, onClose, onThemeSelect, onCountryCardClick, onPersonClick, onSourceClick }: ThemeCompareProps) {
    return (
        <CompareDashboard
            modeLabel="Theme Compare"
            leftLabel={getThemeLabel(themeA)}
            rightLabel={getThemeLabel(themeB)}
            accent="#10b981"
            onClose={onClose}
        >
            <ThemeDetail
                theme={themeA}
                hours={hours}
                onClose={() => {}}
                onThemeSelect={onThemeSelect}
                onCountryCardClick={onCountryCardClick}
                onPersonClick={onPersonClick}
                onSourceClick={onSourceClick}
            />
            <ThemeDetail
                theme={themeB}
                hours={hours}
                onClose={() => {}}
                onThemeSelect={onThemeSelect}
                onCountryCardClick={onCountryCardClick}
                onPersonClick={onPersonClick}
                onSourceClick={onSourceClick}
            />
        </CompareDashboard>
    )
}
