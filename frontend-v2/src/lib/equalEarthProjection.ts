/**
 * Equal Earth projection — the single source of coordinate truth for the L2
 * Equal Earth map (#212, ADR-0005). SVG (basemap/choropleth/hit-test), Canvas
 * (flows/markers), and hit-testing all go through ONE instance here, so the
 * layers can never drift apart — the exact failure ADR-0004 feared, now
 * structurally prevented.
 *
 * Render model (standard d3-zoom-on-map): the projection is fitted to the
 * container size ONCE (base coords, k=1). Pan/zoom is a {k,x,y} transform owned
 * by the map component and applied at draw time (an SVG <g transform> and a
 * canvas ctx.translate/scale). We never re-fit the projection on zoom — cheap
 * and keeps every layer using identical math.
 */
import { geoEqualEarth, geoPath, type GeoProjection, type GeoPath } from 'd3-geo'

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
    /** [lng,lat] -> base [x,y] (k=1, untransformed). null if unprojectable. */
    project(lngLat: [number, number]): [number, number] | null
    /** [lng,lat] -> screen [x,y] under the given pan/zoom transform. */
    toScreen(lngLat: [number, number], t?: ViewTransform): [number, number] | null
    /** screen [x,y] under a transform -> [lng,lat] (for canvas hit-testing). */
    toLngLat(screen: [number, number], t?: ViewTransform): [number, number] | null
    /** base SVG path string for a GeoJSON feature (k=1; <g transform> scales). */
    pathString(feature: object): string | null
}

/**
 * Build an Equal Earth helper fitted to `width`×`height`. The graticule sphere
 * is fit with a small inset so the world doesn't touch the edges.
 */
export function createEqualEarth(
    width: number,
    height: number,
    inset = 8,
): EqualEarth {
    const w = Math.max(1, width)
    const h = Math.max(1, height)
    const projection = geoEqualEarth()
    // fitExtent over the whole sphere centers + scales the world into the box.
    projection.fitExtent(
        [
            [inset, inset],
            [w - inset, h - inset],
        ],
        { type: 'Sphere' },
    )
    const path = geoPath(projection)

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

    return { projection, path, width: w, height: h, project, toScreen, toLngLat, pathString }
}

/** Clamp a zoom scale to a sane range for the world map. */
export function clampScale(k: number, min = 1, max = 12): number {
    return Math.min(max, Math.max(min, k))
}
