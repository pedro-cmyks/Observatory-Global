/**
 * Equal Earth L2 map (#212, ADR-0005) — real equal-area projection rendered
 * with SVG (basemap/choropleth/country hit-test) + a Canvas overlay
 * (flows/markers/terminator, added in later phases). No WebGL → immune to the
 * mobile GL-context blank-map (the bug c883988 couldn't recover).
 *
 * Coordinate truth = `lib/equalEarthProjection` (one instance for SVG + canvas
 * + hit-test). Heat = `lib/countryHeatStates` (shared with the MapLibre map).
 * Read-only: App owns the data + the focus model; this component renders + emits
 * the same callbacks MapLibre does.
 */
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { zoom as d3zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom'
import { select } from 'd3-selection'
import {
    createEqualEarth,
    type ViewTransform,
    IDENTITY_TRANSFORM,
} from '../lib/equalEarthProjection'
import { heatFillColor, heatGlowColor, glowWidth, type CountryHeatStates } from '../lib/countryHeatStates'
import './EqualEarthMap.css'

// Land base color (slate) so countries read as land over the darker ocean, and
// heat tints ON TOP of land (single-fill alpha composite) instead of floating
// on ocean — the contrast fix.
const LAND_RGB: [number, number, number] = [34, 48, 66]
const OCEAN = '#0a1422'

/** Alpha-composite an rgba() string over the solid land base → solid rgb. */
function heatOverLand(heat: number): string {
    const m = heatFillColor(heat).match(/[\d.]+/g)
    if (!m) return `rgb(${LAND_RGB.join(',')})`
    const [r, g, b, a = 1] = m.map(Number)
    const mix = (over: number, base: number) => Math.round(over * a + base * (1 - a))
    return `rgb(${mix(r, LAND_RGB[0])}, ${mix(g, LAND_RGB[1])}, ${mix(b, LAND_RGB[2])})`
}

// ISO_A2 (Natural Earth) → GDELT/FIPS where they differ. Mirrors App.tsx's map
// so a click resolves to the same code the rest of Atlas keys on.
const ISO_TO_GDELT: Record<string, string> = {
    CN: 'CH', ID: 'RI', RS: 'RB', XK: 'KV', MK: 'MK',
    CD: 'CG', CG: 'CF', TZ: 'TZ', KR: 'KS', KP: 'KN',
    PS: 'GZ', EI: 'EI',
}
// Inverse: GDELT code → ISO_A2, to highlight the selected country's shape.
const GDELT_TO_ISO: Record<string, string> = Object.fromEntries(
    Object.entries(ISO_TO_GDELT).map(([iso, gdelt]) => [gdelt, iso]),
)

const GEOJSON_URL = '/data/countries.geojson'

interface CountryFeature {
    type: 'Feature'
    properties: Record<string, unknown>
    geometry: unknown
}

/** GeoJSON FeatureCollection (the shape App's nativeOverlayData already emits). */
interface FC {
    type: 'FeatureCollection'
    features: Array<{ geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }>
}

export interface OverlayData {
    flows: FC
    anomaly: FC
    chokepoints: FC
    aircraft: FC
    vessels: FC
    acled: FC
    terminator: FC
}

export interface EqualEarthMapProps {
    heatStates: CountryHeatStates
    showHeatmap: boolean
    selectedCountryCode: string | null
    onCountryClick: (gdeltCode: string, name: string) => void
    /** Overlay layers (flows/markers/terminator), same data MapLibre uses. */
    overlay?: OverlayData
}

export function EqualEarthMap({
    heatStates,
    showHeatmap,
    selectedCountryCode,
    onCountryClick,
    overlay,
}: EqualEarthMapProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [size, setSize] = useState({ w: 0, h: 0 })
    const [features, setFeatures] = useState<CountryFeature[]>([])
    const [transform, setTransform] = useState<ViewTransform>(IDENTITY_TRANSFORM)

    // Container size (ResizeObserver) — drives the projection fit. Works even
    // when the panel mounts at 0×0 then grows (the mobile tab case).
    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight })
        measure()
        const ro = new ResizeObserver(measure)
        ro.observe(el)
        return () => ro.disconnect()
    }, [])

    // Country shapes — fetched once (local file, no CDN, offline-safe).
    useEffect(() => {
        let cancelled = false
        fetch(GEOJSON_URL)
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(json => { if (!cancelled) setFeatures(json?.features ?? []) })
            .catch(() => { if (!cancelled) setFeatures([]) })
        return () => { cancelled = true }
    }, [])

    const ee = useMemo(
        () => (size.w > 0 && size.h > 0 ? createEqualEarth(size.w, size.h) : null),
        [size.w, size.h],
    )

    // Base path strings (k=1) — the <g> transform scales them, so we only
    // recompute when shapes or container size change, not on pan/zoom.
    const paths = useMemo(() => {
        if (!ee || features.length === 0) return []
        return features.map(f => ({
            iso: String(f.properties.ISO_A2 ?? f.properties.ISO_A2_EH ?? ''),
            name: String(f.properties.NAME ?? f.properties.ADMIN ?? ''),
            d: ee.pathString(f) ?? '',
        })).filter(p => p.d)
    }, [ee, features])

    const selectedIso = selectedCountryCode
        ? (GDELT_TO_ISO[selectedCountryCode] ?? selectedCountryCode)
        : null

    // True during/just after a pan-zoom gesture — swallows the click that fires
    // at gesture end so a pan ≠ a country select.
    const movedRef = useRef(false)

    const handleCountryClick = useCallback((iso: string, name: string) => {
        if (movedRef.current) return // a pan, not a select
        if (!iso || iso === '-99') return
        const gdelt = ISO_TO_GDELT[iso] || iso
        onCountryClick(gdelt, name)
    }, [onCountryClick])

    // The country <path>s do NOT depend on the pan/zoom transform (the parent
    // <g transform> handles that), so memoize them — otherwise every zoom frame
    // re-creates 177 elements and the gesture janks ("se tuesta") on mobile.
    const countryEls = useMemo(() => paths.map((p, i) => {
        const st = heatStates.get(ISO_TO_GDELT[p.iso] || p.iso)
        const heat = showHeatmap && st ? st.heat : 0
        const isSel = selectedIso != null && p.iso !== '-99' && p.iso === selectedIso
        const fill = heat > 0 ? heatOverLand(heat) : `rgb(${LAND_RGB.join(',')})`
        return (
            <path
                key={`${p.iso}-${i}`}
                d={p.d}
                className="equal-earth-country"
                fill={fill}
                stroke={isSel ? '#68dbae' : (heat > 0.3 ? heatGlowColor(heat) : 'rgba(120,140,170,0.22)')}
                strokeWidth={isSel ? 1.8 : (st && heat > 0.3 ? glowWidth(st.intensity) * 0.3 + 0.3 : 0.3)}
                onClick={() => handleCountryClick(p.iso, p.name)}
                style={{ cursor: 'pointer' }}
            />
        )
    }), [paths, heatStates, showHeatmap, selectedIso, handleCountryClick])

    // --- Pan / zoom / pinch via d3-zoom (handles wheel, drag AND multi-touch
    // pinch — the mobile gesture the hand-rolled handlers couldn't do). One
    // {k,x,y} transform drives both the SVG <g> and the canvas. ---
    const zoomRef = useRef<ZoomBehavior<HTMLDivElement, unknown> | null>(null)

    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        const zb = d3zoom<HTMLDivElement, unknown>()
            .scaleExtent([1, 12])
            .on('start', () => { movedRef.current = false })
            .on('zoom', (event) => {
                if (event.sourceEvent) movedRef.current = true
                const t = event.transform
                setTransform({ k: t.k, x: t.x, y: t.y })
            })
            .on('end', () => { setTimeout(() => { movedRef.current = false }, 120) })
        zoomRef.current = zb
        const sel = select(el)
        sel.call(zb)
        sel.on('dblclick.zoom', null) // dbl-click is our reset, not zoom
        return () => { sel.on('.zoom', null) }
    }, [])

    const resetView = useCallback(() => {
        const el = containerRef.current
        if (el && zoomRef.current) select(el).call(zoomRef.current.transform, zoomIdentity)
    }, [])

    // --- Canvas overlay: terminator + flows + markers (screen-space draw, so
    // widths/radii stay constant under zoom). Same projection + transform as the
    // SVG, so layers can't drift. rAF-coalesced so a fast pinch doesn't trigger
    // a full redraw per event (mobile jank). ---
    useEffect(() => {
        let raf = 0
        raf = requestAnimationFrame(() => {
        const canvas = canvasRef.current
        if (!canvas || !ee || size.w === 0) return
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        canvas.width = size.w * dpr
        canvas.height = size.h * dpr
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        ctx.clearRect(0, 0, size.w, size.h)
        if (!overlay) return

        const pt = (c: [number, number]) => ee.toScreen([c[0], c[1]], transform)
        const num = (v: unknown, d = 0) => (typeof v === 'number' ? v : d)

        // 1. Terminator (day/night) — filled polygons.
        for (const f of overlay.terminator.features) {
            const op = num(f.properties.opacity)
            if (op <= 0) continue
            ctx.fillStyle = `rgba(0, 8, 25, ${Math.min(op, 0.85)})`
            drawPolygon(ctx, f.geometry, pt)
            ctx.fill()
        }
        // 2. Flow arcs — lines, width by strength.
        ctx.lineCap = 'round'
        for (const f of overlay.flows.features) {
            const coords = f.geometry.coordinates as [number, number][]
            if (!Array.isArray(coords) || coords.length < 2) continue
            const a = pt(coords[0]); const b = pt(coords[1])
            if (!a || !b) continue
            ctx.beginPath()
            ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1])
            ctx.strokeStyle = 'rgba(100, 140, 180, 0.5)'
            ctx.lineWidth = 0.8 + Math.min(num(f.properties.strength), 1) * 2.2
            ctx.stroke()
        }
        // 3. Point markers.
        const dot = (c: unknown, r: number, fill: string, stroke?: string, sw = 0) => {
            if (!Array.isArray(c)) return
            const p = pt(c as [number, number])
            if (!p) return
            ctx.beginPath()
            ctx.arc(p[0], p[1], r, 0, Math.PI * 2)
            if (fill !== 'none') { ctx.fillStyle = fill; ctx.fill() }
            if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.stroke() }
        }
        for (const f of overlay.chokepoints.features) {
            const active = f.properties.active === true
            dot(f.geometry.coordinates, active ? 9 : 6,
                active ? 'rgba(0,220,200,0.16)' : 'rgba(0,180,160,0.08)',
                active ? 'rgba(0,255,210,0.8)' : 'rgba(0,180,160,0.35)', active ? 2 : 1)
        }
        for (const f of overlay.aircraft.features) {
            const alt = num(f.properties.alt)
            const col = alt > 10000 ? 'rgba(255,255,255,0.78)' : alt > 5000 ? 'rgba(255,210,80,0.72)' : 'rgba(255,140,40,0.68)'
            dot(f.geometry.coordinates, alt > 10000 ? 2 : 3, col)
        }
        for (const f of overlay.vessels.features) {
            dot(f.geometry.coordinates, 2.5, 'rgba(120,200,255,0.7)')
        }
        for (const f of overlay.acled.features) {
            dot(f.geometry.coordinates, Math.min(num(f.properties.radius, 4), 12), 'rgba(239,68,68,0.55)', 'rgba(239,68,68,0.9)', 1)
        }
        // anomaly rings on top
        for (const f of overlay.anomaly.features) {
            dot(f.geometry.coordinates, num(f.properties.radius, 8), 'none', 'rgba(239,68,68,0.95)', 2)
        }
        })
        return () => cancelAnimationFrame(raf)
    }, [overlay, transform, ee, size.w, size.h])

    return (
        <div
            ref={containerRef}
            className="equal-earth-map"
            onDoubleClick={resetView}
        >
            {ee && (
                <svg
                    className="equal-earth-svg"
                    width={size.w}
                    height={size.h}
                    viewBox={`0 0 ${size.w} ${size.h}`}
                >
                    <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
                        {/* sphere backdrop (ocean) */}
                        <path
                            d={ee.pathString({ type: 'Sphere' }) ?? ''}
                            className="equal-earth-sphere"
                            style={{ fill: OCEAN }}
                        />
                        {countryEls}
                    </g>
                </svg>
            )}
            {ee && (
                <canvas
                    ref={canvasRef}
                    className="equal-earth-canvas"
                    style={{ width: size.w, height: size.h }}
                />
            )}
        </div>
    )
}

/** Draw a GeoJSON Polygon/MultiPolygon onto a 2D context using a projector. */
function drawPolygon(
    ctx: CanvasRenderingContext2D,
    geometry: { type: string; coordinates: unknown },
    pt: (c: [number, number]) => [number, number] | null,
) {
    const rings: [number, number][][] =
        geometry.type === 'MultiPolygon'
            ? (geometry.coordinates as [number, number][][][]).flat()
            : (geometry.coordinates as [number, number][][])
    ctx.beginPath()
    for (const ring of rings) {
        let started = false
        for (const c of ring) {
            const p = pt(c)
            if (!p) continue
            if (!started) { ctx.moveTo(p[0], p[1]); started = true }
            else ctx.lineTo(p[0], p[1])
        }
        ctx.closePath()
    }
}
