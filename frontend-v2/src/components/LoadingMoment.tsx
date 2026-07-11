// LoadingMoment — the shared "loading delight" card. Shown inside existing
// load states (app shell, Brief entry, universe assembly, thread hydration)
// instead of leaving the user with a bare spinner. Reads its rotation
// SYNCHRONOUSLY from lib/delight (localStorage-cached measured facts +
// bundled evergreen facts) — the delight itself never waits on the network.
import { useEffect, useMemo, useState } from 'react'
import { factLabel, readDelightRotation } from '../lib/delight'
import './LoadingMoment.css'

const ROTATE_MS = 4500

// Tiny procedural constellation derived from the fact id — option (b) of the
// delight plan: generated vector art, zero assets. Deterministic per fact.
function constellationFor(id: string): { x: number; y: number; r: number }[] {
    let h = 2166136261
    for (let i = 0; i < id.length; i++) {
        h ^= id.charCodeAt(i)
        h = Math.imul(h, 16777619)
    }
    const stars: { x: number; y: number; r: number }[] = []
    let x = h >>> 0
    const next = () => {
        x ^= x << 13; x >>>= 0
        x ^= x >> 17
        x ^= x << 5; x >>>= 0
        return x / 0xffffffff
    }
    const n = 5 + Math.floor(next() * 3)
    for (let i = 0; i < n; i++) {
        stars.push({
            x: 8 + next() * 104,
            y: 6 + next() * 24,
            r: 0.8 + next() * 1.4,
        })
    }
    return stars
}

interface LoadingMomentProps {
    // Visual density: 'full' for the app-shell overlay, 'compact' for panels.
    compact?: boolean
}

export function LoadingMoment({ compact = false }: LoadingMomentProps) {
    const rotation = useMemo(() => readDelightRotation(), [])
    const [idx, setIdx] = useState(0)
    const reducedMotion = useMemo(
        () => typeof window !== 'undefined'
            && typeof window.matchMedia === 'function'
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        [],
    )

    useEffect(() => {
        if (rotation.length < 2) return
        const t = setInterval(() => setIdx(i => (i + 1) % rotation.length), ROTATE_MS)
        return () => clearInterval(t)
    }, [rotation.length])

    if (rotation.length === 0) return null
    const fact = rotation[idx % rotation.length]
    const stars = constellationFor(fact.id)

    return (
        <div
            className={`loading-moment ${compact ? 'loading-moment--compact' : ''} ${reducedMotion ? 'loading-moment--still' : ''}`}
            aria-live="polite"
        >
            <svg
                className="loading-moment-sky"
                viewBox="0 0 120 36"
                aria-hidden="true"
            >
                <polyline
                    className="loading-moment-lines"
                    points={stars.map(s => `${s.x.toFixed(1)},${s.y.toFixed(1)}`).join(' ')}
                    fill="none"
                />
                {stars.map((s, i) => (
                    <circle
                        key={i}
                        className="loading-moment-star"
                        cx={s.x.toFixed(1)}
                        cy={s.y.toFixed(1)}
                        r={s.r.toFixed(1)}
                        style={{ animationDelay: `${i * 260}ms` }}
                    />
                ))}
            </svg>
            {/* key remounts the block so the fade-in plays per fact */}
            <div className="loading-moment-fact" key={fact.id}>
                <p className="loading-moment-text">{fact.text}</p>
                <span className="loading-moment-label">{factLabel(fact)}</span>
            </div>
        </div>
    )
}
