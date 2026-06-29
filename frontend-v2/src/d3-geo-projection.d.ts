// Minimal ambient types for d3-geo-projection (no @types package published).
// We only use the cylindrical equal-area projection factory.
declare module 'd3-geo-projection' {
    import type { GeoProjection } from 'd3-geo'
    export function geoCylindricalEqualArea(): GeoProjection & {
        parallel(): number
        parallel(value: number): GeoProjection
    }
}
