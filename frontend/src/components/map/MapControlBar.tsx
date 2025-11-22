import React from 'react'
import ViewModeToggle from './controls/ViewModeToggle'
import TimeWindowSelector from './controls/TimeWindowSelector'
import CountryFilter from './controls/CountryFilter'
import AutoRefreshControl from './controls/AutoRefreshControl'

const MapControlBar: React.FC = () => {
    return (
        <div
            style={{
                position: 'absolute',
                top: '1rem',
                left: '50%',
                transform: 'translateX(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                padding: '0.75rem 1.5rem',
                backgroundColor: 'rgba(15, 23, 42, 0.8)', // Dark slate with opacity
                backdropFilter: 'blur(12px)',
                borderRadius: '9999px', // Pill shape
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
                zIndex: 10,
                maxWidth: '90vw',
                overflowX: 'auto',
            }}
        >
            {/* Logo / Title (Optional, small) */}
            <div style={{
                fontWeight: 700,
                color: 'white',
                fontSize: '0.9rem',
                marginRight: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
            }}>
                <span style={{ fontSize: '1.2rem' }}>📡</span>
                <span className="hidden sm:inline">RADAR</span>
            </div>

            <div style={{ width: '1px', height: '24px', backgroundColor: 'rgba(255,255,255,0.2)' }} />

            <ViewModeToggle />

            <div style={{ width: '1px', height: '24px', backgroundColor: 'rgba(255,255,255,0.2)' }} />

            <TimeWindowSelector />

            <div style={{ width: '1px', height: '24px', backgroundColor: 'rgba(255,255,255,0.2)' }} />

            <CountryFilter />

            <div style={{ width: '1px', height: '24px', backgroundColor: 'rgba(255,255,255,0.2)' }} />

            <AutoRefreshControl />
        </div>
    )
}

export default MapControlBar
