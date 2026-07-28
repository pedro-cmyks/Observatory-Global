// Atlas constellation grammar — the ONE generator behind every brand surface.
//
// The identity is procedural: stars + thin connecting lines, deterministic per
// seed, zero external assets. LoadingMoment draws a fresh constellation per
// delight fact (seed = fact id); the canonical Atlas MARK is the same generator
// frozen at seed 'atlas' and fitted from the 120×36 strip into a 64×64 square
// (margin 13) — exactly the geometry shipped in public/favicon.svg and guarded
// by src/lib/faviconMark.test.ts. Changing this function changes the brand;
// the tests will tell you.
export interface Star {
    x: number
    y: number
    r: number
}

// FNV-1a hash → xorshift32 stream → 5-7 stars in a 120×36 strip.
// (Moved verbatim from LoadingMoment; do not tweak constants — every surface
// and the favicon derive from these.)
export function constellationFor(id: string): Star[] {
    let h = 2166136261
    for (let i = 0; i < id.length; i++) {
        h ^= id.charCodeAt(i)
        h = Math.imul(h, 16777619)
    }
    const stars: Star[] = []
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

export const ATLAS_MARK_SEED = 'atlas'

// The strip→square fit used to build the canonical mark: bounding box of the
// seed constellation stretched into a 64×64 frame with margin 13, star radii
// remapped from the strip's 0.8-2.2 band onto 2.6-4.2 so the smallest star
// still survives 16px favicon rendering. Coordinates rounded to 0.1 — the
// favicon file stores these exact rounded values.
export function atlasMarkStars(seed: string = ATLAS_MARK_SEED): Star[] {
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
