import { EntityPanel } from './EntityPanel'
import { type TimeRange } from '../lib/timeRanges'
import './PersonCompare.css'

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
        <div className="person-compare-overlay">
            <div className="person-compare-header">
                <div className="person-compare-title">
                    Comparing: <span style={{ color: '#a5b4fc' }}>{personA}</span> vs <span style={{ color: '#a5b4fc' }}>{personB}</span>
                </div>
                <button className="person-compare-close" onClick={onClose}>×</button>
            </div>
            <div className="person-compare-content">
                <div className="person-compare-pane" style={{ position: 'relative' }}>
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
                </div>
                <div className="person-compare-pane" style={{ position: 'relative' }}>
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
                </div>
            </div>
        </div>
    )
}
