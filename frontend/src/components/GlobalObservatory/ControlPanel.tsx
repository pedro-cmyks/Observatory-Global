import React from 'react'
import { LayerState } from './GlobalObservatory'
import { TimeWindow } from '../../lib/mapTypes'

interface ControlPanelProps {
    activeLayers: LayerState
    onToggleLayer: (layer: keyof LayerState) => void
    timeWindow: TimeWindow
    onTimeWindowChange: (window: TimeWindow) => void
}

const ControlPanel: React.FC<ControlPanelProps> = ({
    activeLayers,
    onToggleLayer,
    timeWindow,
    onTimeWindowChange
}) => {
    return (
        <div style={{
            position: 'absolute',
            top: 20,
            right: 60, // Left of NavigationControl
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            alignItems: 'flex-end'
        }}>

            {/* Time Window Selector */}
            <div style={{
                background: 'rgba(30, 30, 30, 0.9)',
                backdropFilter: 'blur(10px)',
                padding: '4px',
                borderRadius: '8px',
                display: 'flex',
                gap: '4px',
                border: '1px solid rgba(255,255,255,0.1)'
            }}>
                {(['1h', '6h', '12h', '24h'] as TimeWindow[]).map((tw) => (
                    <button
                        key={tw}
                        onClick={() => onTimeWindowChange(tw)}
                        style={{
                            background: timeWindow === tw ? '#3b82f6' : 'transparent',
                            color: timeWindow === tw ? 'white' : 'rgba(255,255,255,0.6)',
                            border: 'none',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            fontWeight: 500,
                            transition: 'all 0.2s'
                        }}
                    >
                        {tw}
                    </button>
                ))}
            </div>

            {/* Layer Toggles */}
            <div style={{
                background: 'rgba(30, 30, 30, 0.9)',
                backdropFilter: 'blur(10px)',
                padding: '12px',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                border: '1px solid rgba(255,255,255,0.1)',
                minWidth: '160px'
            }}>
                <div style={{
                    color: 'rgba(255,255,255,0.5)',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    marginBottom: '4px'
                }}>
                    Layers
                </div>

                {Object.entries(activeLayers).map(([key, active]) => (
                    <label key={key} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        cursor: 'pointer',
                        color: 'white',
                        fontSize: '14px'
                    }}>
                        <input
                            type="checkbox"
                            checked={active}
                            onChange={() => onToggleLayer(key as keyof LayerState)}
                            style={{ accentColor: '#3b82f6' }}
                        />
                        <span style={{ textTransform: 'capitalize' }}>{key}</span>
                    </label>
                ))}
            </div>

        </div>
    )
}

export default ControlPanel
