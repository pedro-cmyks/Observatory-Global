/**
 * Constellation Thread View layout math.
 * Spec: docs/specs/2026-07-17-constellation-thread-view.md
 * Reconciled with the tri-surface evaluation
 * (docs/research/dataviz/2026-07-17-tri-surface-evaluation.md, §5 Option A —
 * the EGO constellation: a hub "story-core" node + member stars + edges).
 *
 * The constellation re-code of the Orbital Thread View. Same MEASURED engine
 * quantities, star-graph grammar to match the dossier's InvestigativeUniverse.
 * Pure + deterministic. Key honesty upgrades over the orbit (all from the eval):
 *
 *   position radius = ABSOLUTE cosine distance to the story centroid on a FIXED
 *                     domain → cross-thread comparable (fixes eval U3; the orbit
 *                     used per-thread min-max, which is incomparable across
 *                     stories). Angle = deterministic seed only (fixed shape).
 *   hub spoke       = length carries the distance; width/opacity are UNIFORM —
 *                     cosine NEVER thickens a link (dossier canon §5.3).
 *   co-occurrence   = moons become REAL weighted edges to their parent (width ∝
 *                     measured shared-signal overlap), not a fake sub-orbit.
 *   presence        = presenceAlpha (scrubber lights stars on/off, §I).
 *   ignition        = cumulative-activity luminosity (re-codes the orbit's sweep;
 *                     the eval was fine dropping angle entirely — we keep the
 *                     measurement as brightness instead of discarding it).
 *   comet/tone/volume = conserved from orbitalLayout.
 */
import {
    interactionsUpTo,
    isComet,
    orbitRadius,
    seedAngle,
    type OrbitalBody,
    type OrbitalWindow,
} from './orbitalLayout'

// Presence decay is unified with the UNIVERSE FIELD (eval P1-7): a story fades
// at the same rate — and to the same floor — inside its constellation as it does
// in the population field, so "aliveness" means one thing system-wide. These are
// the universeLayout constants (72h / 0.14), NOT the orbit's 36h / 0.22.
const PRESENCE_DECAY_HOURS = 72
const PRESENCE_FLOOR = 0.14

/**
 * Presence opacity at scrub time t — matches the field's `universeAlpha`:
 * 0 before entry, exponential decay from last activity, floored (never cliffs).
 */
export function presenceAlphaField(body: OrbitalBody, t: number): number {
    const first = Date.parse(body.first_seen)
    if (t < first) return 0
    let lastActivity = first
    for (const ts of body.timestamps) {
        const ms = Date.parse(ts)
        if (ms <= t && ms > lastActivity) lastActivity = ms
    }
    const ageHours = (t - lastActivity) / 3_600_000
    const alpha = Math.exp(-Math.LN2 * (ageHours / PRESENCE_DECAY_HOURS))
    return Math.max(PRESENCE_FLOOR, Math.min(1, alpha))
}

/**
 * Fixed cosine-distance domain for the radial axis. A star at this distance sits
 * at the outer edge of the field. 0.20 ≈ the semantic-assignment boundary
 * (cosine sim ~0.80), so a rim star is literally at the edge of the story, and —
 * crucially — the same distance maps to the same radius in EVERY thread, so
 * positions are comparable across stories (fixes the orbit's U3: per-thread
 * min-max made a diffuse thread look as tight as a coherent one). Members past
 * the domain clamp to the rim (honestly "beyond the edge").
 */
export const RADIUS_DOMAIN_MAX = 0.20

/** Normalized radial fraction [0,1] for an absolute cosine distance. */
export function radiusFraction(dist: number): number {
    return Math.max(0, Math.min(1, dist / RADIUS_DOMAIN_MAX))
}

/**
 * Cumulative-activity luminosity: the fraction of a body's interactions that
 * have landed by scrub time t — 0 at birth, 1 once its whole story is in. This
 * RE-CODES the orbit's angular sweep ("velocity IS intensity"): instead of the
 * star racing around a ring, it burns brighter as its coverage fills in. Same
 * measured number (interaction count), new visual channel (luminosity).
 */
export function ignitionGlow(body: OrbitalBody, t: number): number {
    const total = body.timestamps.length
    if (total === 0) return 0
    return Math.min(1, Math.max(0, interactionsUpTo(body, t) / total))
}

export interface ConstellationGeom {
    cx: number
    cy: number
    rMin: number
    rMax: number
    /** Elliptical panel-fill stretch — a UNIFORM stretch of the radial field, so
        the radial ORDER (semantic distance) is preserved exactly. */
    ex: number
    ey: number
}

export interface PlacedStar {
    body: OrbitalBody
    x: number
    y: number
    /** Presence opacity (birth + decay, floor 0.14 — the field's PRESENCE_FLOOR). */
    alpha: number
    /** Cumulative-activity luminosity [0,1] at the scrubbed moment. */
    ignition: number
    comet: boolean
    moon: boolean
    /** Radial fraction [0,1] on the FIXED cosine domain (cross-thread comparable). */
    distFraction: number
    /** Parent star id when this is a co-occurrence satellite (draws a weighted
        edge to that star); null otherwise. */
    moonParentId: string | null
}

/**
 * Fixed constellation placement. Radius = ABSOLUTE cosine distance on the fixed
 * domain (comparable across threads), angle = deterministic seed ONLY (the shape
 * is stable; it does not spin — time lives in alpha/ignition + the scrubber).
 * Moons are placed by their OWN distance like any member; their co-occurrence to
 * a parent is drawn as a real weighted EDGE, not a fake sub-orbit position.
 */
export function placeConstellation(
    bodies: OrbitalBody[],
    scrubT: number,
    geom: ConstellationGeom,
    window_: OrbitalWindow,
): PlacedStar[] {
    const { cx, cy, rMin, rMax, ex, ey } = geom
    return bodies.map(body => {
        const frac = radiusFraction(body.dist)
        const r = orbitRadius(frac, rMin, rMax)
        const a = seedAngle(body.id)
        return {
            body,
            x: cx + r * ex * Math.cos(a),
            y: cy + r * ey * Math.sin(a),
            alpha: presenceAlphaField(body, scrubT),
            ignition: ignitionGlow(body, scrubT),
            comet: isComet(body, window_),
            moon: !!body.moon_of,
            distFraction: frac,
            moonParentId: body.moon_of ?? null,
        }
    })
}
