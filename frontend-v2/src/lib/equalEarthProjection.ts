/**
 * Atlas world map projection — the single source of coordinate truth for the L2
 * map (#212, ADR-0005). SVG (basemap/choropleth/hit-test), Canvas
 * (flows/markers), and hit-testing all go through ONE instance here, so the
 * layers can never drift apart.
 *
 * Projection: **cylindrical equal-area (Behrmann, 30° standard parallel)** —
 * rectangular + equal-area. Chosen over the rounded Equal Earth because Pedro's
 * map is an INFINITE HORIZONTAL STRIP: a rectangular projection tiles perfectly
 * at ±180° so the world can wrap seamlessly on horizontal pan (rotate-the-globe
 * feel), while staying area-honest (the whole point vs Mercator). The map is fit
 * to the panel HEIGHT (poles at the top/bottom edges); width overflows and wraps.
 *
 * Render model (standard d3-zoom-on-map): the projection is fitted to the
 * container ONCE (base coords, k=1). Pan/zoom is a {k,x,y} transform owned by
 * the map component and applied at draw time (a GPU CSS transform on the SVG
 * wrapper + a screen-space canvas). We never re-fit on zoom.
 */
import { geoPath, type GeoProjection, type GeoPath } from 'd3-geo'
import { geoCylindricalEqualArea } from 'd3-geo-projection'

/** Pan/zoom transform (d3-zoom shape: scale + translate). */
export interface ViewTransform {
    k: number
    x: number
    y: number
}

export const IDENTITY_TRANSFORM: ViewTransform = { k: 1, x: 0, y: 0 }

export interface EqualEarth {
    readonly projection: GeoProjection
    readonly path: GeoPath
    readonly width: number
    readonly height: number
    /** projected width of 360° of longitude at k=1 (the wrap period). */
    readonly worldWidth: number
    /** projected height of the sphere (pole to pole) at k=1. */
    readonly worldHeight: number
    /** [lng,lat] -> base [x,y] (k=1, untransformed). null if unprojectable. */
    project(lngLat: [number, number]): [number, number] | null
    /** [lng,lat] -> screen [x,y] under the given pan/zoom transform. */
    toScreen(lngLat: [number, number], t?: ViewTransform): [number, number] | null
    /** screen [x,y] under a transform -> [lng,lat] (for canvas hit-testing). */
    toLngLat(screen: [number, number], t?: ViewTransform): [number, number] | null
    /** base SVG path string for a GeoJSON feature (k=1). */
    pathString(feature: object): string | null
}

/**
 * Build the map helper fitted to `width`×`height`. Fit to HEIGHT so the poles
 * sit at the top/bottom edges (fills vertically); the world is centered
 * horizontally and overflows — the strip the caller wraps.
 */
export function createEqualEarth(
    width: number,
    height: number,
): EqualEarth {
    const w = Math.max(1, width)
    const h = Math.max(1, height)
    const projection = geoCylindricalEqualArea().parallel(30)
    // Fit the sphere's HEIGHT to the panel; centers it in the box.
    projection.fitHeight(h, { type: 'Sphere' })
    const path = geoPath(projection)

    // Wrap period + pole-to-pole height from the projected sphere bounds.
    const [[x0, y0], [x1, y1]] = path.bounds({ type: 'Sphere' })
    const worldWidth = x1 - x0
    const worldHeight = y1 - y0
    // Re-center horizontally so the prime meridian sits at panel center.
    const tx = projection.translate()[0] + (w / 2 - (x0 + x1) / 2)
    projection.translate([tx, projection.translate()[1]])

    const project = (lngLat: [number, number]): [number, number] | null => {
        const p = projection(lngLat)
        return p ? [p[0], p[1]] : null
    }

    const toScreen = (
        lngLat: [number, number],
        t: ViewTransform = IDENTITY_TRANSFORM,
    ): [number, number] | null => {
        const p = project(lngLat)
        if (!p) return null
        return [p[0] * t.k + t.x, p[1] * t.k + t.y]
    }

    const toLngLat = (
        screen: [number, number],
        t: ViewTransform = IDENTITY_TRANSFORM,
    ): [number, number] | null => {
        const base: [number, number] = [(screen[0] - t.x) / t.k, (screen[1] - t.y) / t.k]
        const inv = projection.invert?.(base)
        return inv ? [inv[0], inv[1]] : null
    }

    const pathString = (feature: object): string | null => path(feature as never) || null

    return {
        projection, path, width: w, height: h, worldWidth, worldHeight,
        project, toScreen, toLngLat, pathString,
    }
}

/** Clamp a zoom scale to a sane range for the world map. */
export function clampScale(k: number, min = 1, max = 12): number {
    return Math.min(max, Math.max(min, k))
}
