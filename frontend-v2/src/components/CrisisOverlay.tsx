import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'

/**
 * Diagonal scanline overlay that appears when Crisis Mode is ON.
 * CSS-only animation, pointer-events: none for performance.
 */
export const CrisisOverlay: React.FC = () => {
    const { enabled, overallSeverity } = useCrisis()

    if (!enabled) return null

    const opacityMap = {
        normal: 0,
        notable: 0.03,
        elevated: 0.05,
        critical: 0.08
    }
    const opacity = opacityMap[overallSeverity]

    if (opacity === 0) return null

    return (
        <div
            className="crisis-scanline-overlay"
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                pointerEvents: 'none',
                zIndex: 750,
                overflow: 'hidden'
            }}
        >
            <div
                style={{
                    position: 'absolute',
                    top: '-50%',
                    left: '-50%',
                    right: '-50%',
                    bottom: '-50%',
                    background: `repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 10px,
            rgba(251, 191, 36, ${opacity}) 10px,
            rgba(251, 191, 36, ${opacity}) 20px
          )`,
                    animation: 'crisis-scanline-drift 8s linear infinite'
                }}
            />
            <style>{`
        @keyframes crisis-scanline-drift {
          0% { transform: translate(0, 0); }
          100% { transform: translate(40px, 40px); }
        }
      `}</style>
        </div>
    )
}
