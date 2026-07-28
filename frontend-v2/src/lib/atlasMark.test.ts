// Guards the SHARED constellation grammar: one generator (lib/constellation)
// must sit behind every brand surface — the favicon file, the inline
// AtlasMark component, and LoadingMoment's per-fact constellations. A drift
// in any copy breaks the "same sky everywhere" identity.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import { atlasMarkStars, constellationFor, ATLAS_MARK_SEED } from './constellation'

const ROOT = resolve(__dirname, '../..')
const favicon = readFileSync(resolve(ROOT, 'public/favicon.svg'), 'utf8')
const atlasMarkSrc = readFileSync(resolve(ROOT, 'src/components/AtlasMark.tsx'), 'utf8')
const loadingMomentSrc = readFileSync(resolve(ROOT, 'src/components/LoadingMoment.tsx'), 'utf8')

describe('shared constellation grammar', () => {
    it('atlasMarkStars reproduces the shipped favicon geometry exactly', () => {
        const stars = atlasMarkStars()
        const circles = favicon.match(/<circle\b/g) ?? []
        expect(circles.length).toBe(stars.length)
        for (const s of stars) {
            expect(favicon).toContain(`cx="${s.x}" cy="${s.y}" r="${s.r}"`)
        }
    })

    it('the mark seed is the brand name', () => {
        expect(ATLAS_MARK_SEED).toBe('atlas')
    })

    it('constellationFor is deterministic per seed', () => {
        expect(constellationFor('atlas')).toEqual(constellationFor('atlas'))
        expect(constellationFor('atlas')).not.toEqual(constellationFor('other'))
    })

    it('AtlasMark renders from the shared generator in currentColor (no palette fork)', () => {
        expect(atlasMarkSrc).toContain("atlasMarkStars")
        expect(atlasMarkSrc).toContain('currentColor')
        // No hardcoded hex: color always comes from the surface's accent token.
        expect(atlasMarkSrc).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    })

    it('LoadingMoment consumes the shared generator (no private copy left)', () => {
        expect(loadingMomentSrc).toContain("import { constellationFor } from '../lib/constellation'")
        expect(loadingMomentSrc).not.toContain('2166136261') // the FNV seed lives in ONE file
    })
})
