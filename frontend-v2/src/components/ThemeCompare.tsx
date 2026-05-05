import { ThemeDetail } from './ThemeDetail'
import { getThemeLabel } from '../lib/themeLabels'
import './ThemeCompare.css'

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
        <div className="theme-compare-overlay">
            <div className="theme-compare-header">
                <div className="theme-compare-title">
                    Comparing: <span style={{ color: '#10b981' }}>{getThemeLabel(themeA)}</span> vs <span style={{ color: '#10b981' }}>{getThemeLabel(themeB)}</span>
                </div>
                <button className="theme-compare-close" onClick={onClose}>×</button>
            </div>
            <div className="theme-compare-content">
                <div className="theme-compare-pane">
                    <ThemeDetail 
                        theme={themeA} 
                        hours={hours} 
                        onClose={() => {}} 
                        onThemeSelect={onThemeSelect}
                        onCountryCardClick={onCountryCardClick}
                        onPersonClick={onPersonClick}
                        onSourceClick={onSourceClick}
                    />
                </div>
                <div className="theme-compare-pane">
                    <ThemeDetail 
                        theme={themeB} 
                        hours={hours} 
                        onClose={() => {}} 
                        onThemeSelect={onThemeSelect}
                        onCountryCardClick={onCountryCardClick}
                        onPersonClick={onPersonClick}
                        onSourceClick={onSourceClick}
                    />
                </div>
            </div>
        </div>
    )
}
