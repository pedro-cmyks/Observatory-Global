// Guards the procedural favicon: it must stay DERIVED from the same
// constellationFor() geometry LoadingMoment uses (fixed seed = the brand
// name 'atlas'), keep the emerald identity, and be the icon index.html +
// the PWA manifest actually reference. No external assets, deterministic.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const EMERALD = '#1d9e75' // --color-accent-primary, the LoadingMoment default

// --- reproduction of LoadingMoment.constellationFor (do NOT import; that file
// is off-limits to this slice) + the strip->square fit used to build the mark.
function constellationFor(id: string) {
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
        stars.push({ x: 8 + next() * 104, y: 6 + next() * 24, r: 0.8 + next() * 1.4 })
    }
    return stars
}

function fittedMark(seed: string) {
    const S = 64, M = 13
    const raw = constellationFor(seed)
    const xs = raw.map(s => s.x), ys = raw.map(s => s.y)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const sx = (S - 2 * M) / ((maxX - minX) || 1)
    const sy = (S - 2 * M) / ((maxY - minY) || 1)
    return raw.map(s => ({
        x: +((s.x - minX) * sx + M).toFixed(1),
        y: +((s.y - minY) * sy + M).toFixed(1),
        r: +(2.6 + (s.r - 0.8) / 1.4 * 1.6).toFixed(1),
    }))
}

const favicon = readFileSync(resolve(ROOT, 'public/favicon.svg'), 'utf8')

describe('favicon.svg constellation mark', () => {
    it('carries the emerald identity (no palette drift)', () => {
        expect(favicon).toContain(EMERALD)
    })

    it('has one <circle> per star in the fixed-seed constellation', () => {
        const stars = fittedMark('atlas')
        const circles = favicon.match(/<circle\b/g) ?? []
        expect(circles.length).toBe(stars.length)
    })

    it('places every star at its constellationFor-derived coordinate', () => {
        for (const s of fittedMark('atlas')) {
            expect(favicon).toContain(`cx="${s.x}" cy="${s.y}" r="${s.r}"`)
        }
    })

    it('is a self-contained SVG (no external references)', () => {
        expect(favicon).toContain('viewBox="0 0 64 64"')
        expect(favicon).not.toMatch(/href|url\(|<image|xlink/i)
    })
})

describe('favicon wiring', () => {
    it('index.html points its icon at favicon.svg, not the stock vite.svg', () => {
        const html = readFileSync(resolve(ROOT, 'index.html'), 'utf8')
        expect(html).toContain('rel="icon" type="image/svg+xml" href="/favicon.svg"')
        expect(html).not.toContain('href="/vite.svg"')
    })

    it('the PWA manifest references the SVG mark', () => {
        const cfg = readFileSync(resolve(ROOT, 'vite.config.ts'), 'utf8')
        expect(cfg).toContain("src: 'favicon.svg'")
    })
})
