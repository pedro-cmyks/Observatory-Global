import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'

/**
 * Crisis Mode overlay with animated diagonal scanlines.
 * Two-layer animation with intensity based on severity.
 * CSS-only, pointer-events: none for performance.
 */
export const CrisisOverlay: React.FC = () => {
    const { enabled, overallSeverity } = useCrisis()

    if (!enabled) return null

    const intensityMap: Record<string, { opacity: number; speed: number }> = {
        normal: { opacity: 0.02, speed: 12 },
        notable: { opacity: 0.04, speed: 10 },
        elevated: { opacity: 0.06, speed: 8 },
        critical: { opacity: 0.10, speed: 5 }
    }

    const config = intensityMap[overallSeverity] || intensityMap.normal

    if (overallSeverity === 'normal' && config.opacity < 0.03) {
        return null
    }

    return (
        <div
            className="crisis-overlay"
            style={{
                position: 'fixed',
                inset: 0,
                pointerEvents: 'none',
                zIndex: 750,
                overflow: 'hidden'
            }}
        >
            {/* Primary scanlines */}
            <div
                style={{
                    position: 'absolute',
                    inset: '-100%',
                    background: `repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 8px,
            rgba(251, 191, 36, ${config.opacity}) 8px,
            rgba(251, 191, 36, ${config.opacity * 0.7}) 16px,
            transparent 16px,
            transparent 24px
          )`,
                    animation: `scanline-drift-1 ${config.speed}s linear infinite`
                }}
            />
            {/* Secondary scanlines (red tint) */}
            <div
                style={{
                    position: 'absolute',
                    inset: '-100%',
                    background: `repeating-linear-gradient(
            -45deg,
            transparent,
            transparent 20px,
            rgba(239, 68, 68, ${config.opacity * 0.5}) 20px,
            rgba(239, 68, 68, ${config.opacity * 0.3}) 24px,
            transparent 24px,
            transparent 44px
          )`,
                    animation: `scanline-drift-2 ${config.speed * 1.5}s linear infinite`
                }}
            />
            <style>{`
        @keyframes scanline-drift-1 {
          0% { transform: translate(0, 0); }
          100% { transform: translate(60px, 60px); }
        }
        @keyframes scanline-drift-2 {
          0% { transform: translate(0, 0); }
          100% { transform: translate(40px, 40px); }
        }
      `}</style>
        </div>
    )
}
