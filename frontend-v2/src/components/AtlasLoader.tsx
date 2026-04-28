import { useEffect, useState } from 'react'
import './AtlasLoader.css'

interface AtlasLoaderProps {
    visible: boolean
}

export function AtlasLoader({ visible }: AtlasLoaderProps) {
    const [hiding, setHiding] = useState(false)
    const [gone, setGone] = useState(false)

    useEffect(() => {
        if (!visible) {
            setHiding(true)
            const t = setTimeout(() => setGone(true), 700)
            return () => clearTimeout(t)
        } else {
            setHiding(false)
            setGone(false)
        }
    }, [visible])

    if (gone) return null

    return (
        <div className={`atlas-loader ${hiding ? 'atlas-loader--hiding' : ''}`}>
            <div className="atlas-loader-content">
                {/* Animated globe SVG */}
                <div className="atlas-globe-wrap">
                    <svg viewBox="0 0 120 120" className="atlas-globe-svg" aria-hidden="true">
                        {/* Outer circle */}
                        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(29,158,117,0.25)" strokeWidth="1" />
                        {/* Spinning meridian ring */}
                        <ellipse cx="60" cy="60" rx="52" ry="18" fill="none" stroke="rgba(29,158,117,0.5)" strokeWidth="0.8" className="atlas-meridian atlas-meridian-1" />
                        <ellipse cx="60" cy="60" rx="52" ry="34" fill="none" stroke="rgba(29,158,117,0.3)" strokeWidth="0.8" className="atlas-meridian atlas-meridian-2" />
                        {/* Latitude lines */}
                        <line x1="8" y1="60" x2="112" y2="60" stroke="rgba(29,158,117,0.2)" strokeWidth="0.6" />
                        <line x1="16" y1="40" x2="104" y2="40" stroke="rgba(29,158,117,0.15)" strokeWidth="0.5" />
                        <line x1="16" y1="80" x2="104" y2="80" stroke="rgba(29,158,117,0.15)" strokeWidth="0.5" />
                        {/* Central vertical axis */}
                        <line x1="60" y1="8" x2="60" y2="112" stroke="rgba(29,158,117,0.2)" strokeWidth="0.6" />
                        {/* Sweeping arc — the "scanning" effect */}
                        <path
                            d="M 60 8 A 52 52 0 0 1 60 112"
                            fill="none"
                            stroke="rgba(29,158,117,0.7)"
                            strokeWidth="1.2"
                            className="atlas-sweep"
                        />
                        {/* Glow dot at top of sweep */}
                        <circle cx="60" cy="8" r="3" fill="#1D9E75" className="atlas-dot" />
                        {/* Outer ring draw-in */}
                        <circle
                            cx="60" cy="60" r="52"
                            fill="none"
                            stroke="#1D9E75"
                            strokeWidth="1.5"
                            strokeDasharray="326"
                            strokeDashoffset="326"
                            className="atlas-ring-draw"
                        />
                    </svg>
                </div>

                <div className="atlas-loader-brand">ATLAS</div>
                <div className="atlas-loader-sub">Aggregating global intelligence…</div>

                {/* Scanning dots */}
                <div className="atlas-dots">
                    <span className="atlas-dot-pulse" style={{ animationDelay: '0ms' }} />
                    <span className="atlas-dot-pulse" style={{ animationDelay: '180ms' }} />
                    <span className="atlas-dot-pulse" style={{ animationDelay: '360ms' }} />
                </div>
            </div>
        </div>
    )
}
