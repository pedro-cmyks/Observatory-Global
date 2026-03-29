import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'

export const CrisisToggle: React.FC = () => {
    const { enabled, toggleCrisis, overallSeverity } = useCrisis()

    return (
        <button
            onClick={toggleCrisis}
            style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 12px',
                background: enabled ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.1)',
                border: enabled ? '1px solid #ef4444' : '1px solid rgba(255,255,255,0.2)',
                borderRadius: '8px',
                color: enabled ? '#fca5a5' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '12px',
                transition: 'all 0.2s'
            }}
        >
            <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: enabled ? '#ef4444' : '#94a3b8',
                boxShadow: enabled ? '0 0 6px #ef4444' : 'none'
            }} />
            <span>Crisis {enabled ? 'ON' : 'OFF'}</span>
            {enabled && overallSeverity !== 'normal' && (
                <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: overallSeverity === 'critical' ? '#ef4444' : overallSeverity === 'elevated' ? '#f97316' : '#fbbf24',
                    animation: 'crisis-pulse 1.5s ease-in-out infinite'
                }} />
            )}
            <style>{`
        @keyframes crisis-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
      `}</style>
        </button>
    )
}
