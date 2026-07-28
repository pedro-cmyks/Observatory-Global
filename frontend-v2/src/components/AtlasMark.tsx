// AtlasMark — the canonical constellation glyph, inline and token-driven.
//
// Same fixed-seed geometry as public/favicon.svg and the PWA icons (seed
// 'atlas' through lib/constellation.atlasMarkStars). Renders in currentColor
// so each surface's accent token paints it: reader surfaces set
// color: var(--r-accent), console surfaces var(--color-accent-primary).
// No background — the dark rounded plate belongs to the icon files only.
import { atlasMarkStars } from '../lib/constellation'
import './AtlasMark.css'

const STARS = atlasMarkStars()

interface AtlasMarkProps {
    // Rendered square size in px. The geometry is a 64×64 viewBox; anything
    // from 12px up stays legible (the favicon test guards the radii floor).
    size?: number
    className?: string
}

export function AtlasMark({ size = 16, className }: AtlasMarkProps) {
    return (
        <svg
            className={`atlas-mark${className ? ` ${className}` : ''}`}
            width={size}
            height={size}
            viewBox="0 0 64 64"
            aria-hidden="true"
            focusable="false"
        >
            <polyline
                points={STARS.map(s => `${s.x},${s.y}`).join(' ')}
                fill="none"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinejoin="round"
                strokeLinecap="round"
                strokeOpacity={0.55}
            />
            {STARS.map((s, i) => (
                <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="currentColor" />
            ))}
        </svg>
    )
}
