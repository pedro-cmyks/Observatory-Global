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
import { geoCentroid, geoGraticule10 } from 'd3-geo'
import {
    createEqualEarth,
    type ViewTransform,
    IDENTITY_TRANSFORM,
} from '../lib/equalEarthProjection'
import { heatFillColor, heatGlowColor, type CountryHeatStates } from '../lib/countryHeatStates'
import './EqualEarthMap.css'

// Land base color (slate) so countries read as land over the darker ocean, and
// heat tints ON TOP of land (single-fill alpha composite) instead of floating
// on ocean — the contrast fix.
// Land brighter than the (greyer, lighter) ocean so countries stand out — the
// Mercator basemap reads as grey sea + lighter land; match that contrast.
const LAND_RGB: [number, number, number] = [58, 76, 100]
const OCEAN = '#1b2531'

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
    /** GDELT code to pan/zoom the view to (the #234 fly-to, EE edition). */
    flyCountry?: string | null
    onCountryClick: (gdeltCode: string, name: string) => void
    /** Overlay layers (flows/markers/terminator), same data MapLibre uses. */
    overlay?: OverlayData
}

export function EqualEarthMap({
    heatStates,
    showHeatmap,
    selectedCountryCode,
    flyCountry,
    onCountryClick,
    overlay,
}: EqualEarthMapProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [size, setSize] = useState({ w: 0, h: 0 })
    const [features, setFeatures] = useState<CountryFeature[]>([])
    const [transform, setTransform] = useState<ViewTransform>(IDENTITY_TRANSFORM)
    // True only during an active pan/zoom gesture. We promote the SVG to a GPU
    // layer (will-change) ONLY then — so the gesture is smooth — and drop it when
    // idle so the browser re-rasterizes the vector crisp at the current zoom
    // (with will-change always on, the cached bitmap scales → blur/pixelation).
    const [gesturing, setGesturing] = useState(false)

    // Container size — drives the projection fit. The map can mount at 0×0
    // inside a hidden mobile tab and only get a real box when the tab is shown,
    // and ResizeObserver doesn't always fire on display:none→block. So: observe
    // AND poll via rAF until we have a non-zero box (then stop polling).
    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        let raf = 0
        const measure = () => {
            const w = el.clientWidth, h = el.clientHeight
            setSize(prev => (prev.w === w && prev.h === h ? prev : { w, h }))
            return w > 0 && h > 0
        }
        const poll = () => { if (!measure()) raf = requestAnimationFrame(poll) }
        poll()
        const ro = new ResizeObserver(measure)
        ro.observe(el)
        return () => { ro.disconnect(); cancelAnimationFrame(raf) }
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

    // Graticule (lat/long grid) — drawn over the ocean only (land covers it),
    // for the nautical-chart / radar identity. Recomputed only on resize.
    const graticulePath = useMemo(
        () => (ee ? ee.pathString(geoGraticule10()) : null),
        [ee],
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

    // Country label anchors (centroid lng/lat + name). Drawn on the canvas at a
    // constant font size only when zoomed in, so they don't scale with the map.
    const labels = useMemo(() => {
        if (features.length === 0) return []
        return features.map(f => {
            const name = String(f.properties.NAME ?? f.properties.ADMIN ?? '')
            const iso = String(f.properties.ISO_A2 ?? f.properties.ISO_A2_EH ?? '')
            if (!name || iso === '-99') return null
            try {
                const c = geoCentroid(f as never) as [number, number]
                return { name, c }
            } catch { return null }
        }).filter(Boolean) as Array<{ name: string; c: [number, number] }>
    }, [features])

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

    // Heat-conduction render (Pedro's weather-radar idea): THREE memoized SVG
    // layers, stacked per tile — (1) solid LAND base, (2) heat fills run through
    // a Gaussian blur so each country's heat BLEEDS across its shared borders
    // into neighbors (thermal conduction), (3) crisp country borders + the
    // click targets on top. Heat stays legibly per-country (the shape) but
    // diffuses at the frontier like a radar. All memoized (transform-independent;
    // the parent CSS transform pans/zooms them).
    const landEls = useMemo(() => paths.map((p, i) => (
        <path
            key={`l-${p.iso}-${i}`}
            d={p.d}
            fill={`rgb(${LAND_RGB.join(',')})`}
            stroke="rgba(150,185,215,0.22)"
            strokeWidth={0.35}
        />
    )), [paths])

    const heatEls = useMemo(() => paths.map((p, i) => {
        const st = heatStates.get(ISO_TO_GDELT[p.iso] || p.iso)
        const heat = showHeatmap && st ? st.heat : 0
        if (heat <= 0) return null
        return <path key={`h-${p.iso}-${i}`} d={p.d} fill={heatFillColor(heat)} />
    }).filter(Boolean), [paths, heatStates, showHeatmap])

    const borderEls = useMemo(() => paths.map((p, i) => {
        const st = heatStates.get(ISO_TO_GDELT[p.iso] || p.iso)
        const heat = showHeatmap && st ? st.heat : 0
        const isSel = selectedIso != null && p.iso !== '-99' && p.iso === selectedIso
        return (
            <path
                key={`b-${p.iso}-${i}`}
                d={p.d}
                className="equal-earth-country"
                fill="transparent"
                stroke={isSel ? '#68dbae' : (heat > 0.3 ? heatGlowColor(heat) : 'rgba(120,140,170,0.18)')}
                strokeWidth={isSel ? 1.8 : 0.3}
                onClick={() => handleCountryClick(p.iso, p.name)}
                style={{ cursor: 'pointer' }}
            />
        )
    }), [paths, heatStates, showHeatmap, selectedIso, handleCountryClick])

    // Fit-the-WORLD scale: the k at which the full world width fits the panel.
    // fitHeight alone over-zoomed narrow panels (a 500×625 panel opened on
    // "somewhere in Africa" and scaleExtent min=1 could never zoom OUT to the
    // world — 2026-07-01 design pass). Default + dblclick-reset now show the
    // whole world; zooming in re-enters the wrapping strip.
    const kFit = useMemo(
        () => (ee ? Math.min(1, size.w / ee.worldWidth) : 1),
        [ee, size.w],
    )

    // Wrap the raw pan into an infinite horizontal strip: X wraps modulo the
    // world period (so panning sideways rotates the globe seamlessly across the
    // ±180° seam — 3 tiles below cover the view); Y clamps to the poles (no
    // vertical pan past the top/bottom edges) and CENTERS the world vertically
    // when it is shorter than the panel (the fit-world view). The jump-by-period
    // in X is invisible because the tiles are identical.
    const period = ee ? ee.worldWidth * transform.k : 0
    const applied = useMemo<ViewTransform>(() => {
        if (!ee || period <= 0) return transform
        const x = transform.x - Math.round(transform.x / period) * period // nearest-zero window
        const wh = ee.worldHeight * transform.k
        const y = wh <= size.h
            ? (size.h - wh) / 2 // letterbox: center vertically
            : Math.max(size.h - wh, Math.min(0, transform.y))
        return { k: transform.k, x, y }
    }, [transform, ee, period, size.h])

    // --- Pan / zoom / pinch via d3-zoom (handles wheel, drag AND multi-touch
    // pinch — the mobile gesture the hand-rolled handlers couldn't do). One
    // {k,x,y} transform drives both the SVG <g> and the canvas. ---
    const zoomRef = useRef<ZoomBehavior<HTMLDivElement, unknown> | null>(null)

    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        const zb = d3zoom<HTMLDivElement, unknown>()
            .scaleExtent([1, 12])
            .on('start', () => { movedRef.current = false; setGesturing(true) })
            .on('zoom', (event) => {
                if (event.sourceEvent) movedRef.current = true
                const t = event.transform
                setTransform({ k: t.k, x: t.x, y: t.y })
            })
            .on('end', () => { setGesturing(false); setTimeout(() => { movedRef.current = false }, 120) })
        zoomRef.current = zb
        const sel = select(el)
        sel.call(zb)
        sel.on('dblclick.zoom', null) // dbl-click is our reset, not zoom
        return () => { sel.on('.zoom', null) }
    }, [])

    /** Default view: LANDSCAPE panels fit the whole world (letterboxed);
     *  PORTRAIT panels (phones) FILL the height with the wrapping strip —
     *  the world-fit default left a thin band on mobile (Pedro 2026-07-01). */
    const fitTransform = useCallback(() => {
        // h>w alone misfired on DESKTOP (the map panel is 499×625 → strip view
        // on a monitor). Phones are ~2.2 tall; panels ~1.25. Cut at 1.4.
        if (size.h > size.w * 1.4) return zoomIdentity // phone: fill height
        return zoomIdentity.translate((size.w * (1 - kFit)) / 2, 0).scale(kFit)
    }, [size.w, size.h, kFit])

    // Whenever the projection (re)fits — first mount, panel resize — allow
    // zooming out to the world and START there (also re-fits on resize).
    useEffect(() => {
        const el = containerRef.current
        const zb = zoomRef.current
        if (!el || !zb || !ee) return
        zb.scaleExtent([kFit, 12])
        select(el).call(zb.transform, fitTransform())
    }, [ee, kFit, fitTransform])

    // #234 fly-to for the EE engine: when App sets a fly target (country
    // click, thread top-country, person's dominant country), center its
    // projected centroid. MapLibre animates; EE jumps (v1 — acceptable).
    useEffect(() => {
        if (!flyCountry || !ee || features.length === 0) return
        const iso = GDELT_TO_ISO[flyCountry] ?? flyCountry
        const f = features.find(ft => String(ft.properties.ISO_A2 ?? ft.properties.ISO_A2_EH ?? '') === iso)
        if (!f) return
        try {
            const c = geoCentroid(f as never) as [number, number]
            const p = ee.project(c)
            if (!p) return
            const k = Math.max(2.5, transform.k)
            const t = zoomIdentity.translate(size.w / 2 - p[0] * k, size.h / 2 - p[1] * k).scale(k)
            const el = containerRef.current
            if (el && zoomRef.current) select(el).call(zoomRef.current.transform, t)
        } catch { /* centroid can fail on degenerate geometries */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [flyCountry, ee, features])

    const resetView = useCallback(() => {
        const el = containerRef.current
        if (el && zoomRef.current) select(el).call(zoomRef.current.transform, fitTransform())
    }, [fitTransform])

    // --- Canvas overlay: terminator + flows + markers (screen-space draw, so
    // widths/radii stay constant under zoom). Driven by a single rAF animation
    // loop so ALERT markers stay alive: anomaly rings ping (expand + fade) and
    // conflict dots pulse. Reads latest transform/overlay/ee/size via a ref so
    // the loop is stable (set up once) and never janks the SVG. ---
    const drawRef = useRef({ overlay, ee, applied, size, period, labels })
    // Sync every render (no deps array) so the rAF loop always reads the latest
    // without a deps array whose length could shift across HMR edits.
    drawRef.current = { overlay, ee, applied, size, period, labels }

    useEffect(() => {
        let raf = 0
        const num = (v: unknown, d = 0) => (typeof v === 'number' ? v : d)
        const frame = (t: number) => {
            raf = requestAnimationFrame(frame)
            const { overlay, ee, applied, size, period, labels } = drawRef.current
            const canvas = canvasRef.current
            if (!canvas || !ee || size.w === 0 || document.hidden) return
            const dpr = Math.min(window.devicePixelRatio || 1, 2)
            if (canvas.width !== size.w * dpr || canvas.height !== size.h * dpr) {
                canvas.width = size.w * dpr
                canvas.height = size.h * dpr
            }
            const ctx = canvas.getContext('2d')
            if (!ctx) return
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
            ctx.clearRect(0, 0, size.w, size.h)
            if (!overlay) return

            const pt = (c: [number, number]) => ee.toScreen([c[0], c[1]], applied)
            // Horizontal seam offsets so points show in whichever tile is in
            // view (the strip wraps). −period/+period bracket the visible window.
            const seams = period > 0 ? [0, -period, period] : [0]

            // 1. Terminator (day/night).
            for (const f of overlay.terminator.features) {
                const op = num(f.properties.opacity)
                if (op <= 0) continue
                ctx.fillStyle = `rgba(0, 8, 25, ${Math.min(op, 0.85)})`
                drawPolygon(ctx, f.geometry, pt)
                ctx.fill()
            }
            // 2. Flow arcs. On the wrapping strip a pair can be drawn the long
            // way around; pick the target's wrapped copy that gives the SHORTEST
            // on-screen line to the source, then draw it in every seam tile.
            ctx.lineCap = 'round'
            for (const f of overlay.flows.features) {
                const coords = f.geometry.coordinates as [number, number][]
                if (!Array.isArray(coords) || coords.length < 2) continue
                const a = pt(coords[0]); const b0 = pt(coords[1])
                if (!a || !b0) continue
                let bx = b0[0]
                if (period > 0) {
                    for (const o of [-period, period]) {
                        if (Math.abs((b0[0] + o) - a[0]) < Math.abs(bx - a[0])) bx = b0[0] + o
                    }
                }
                ctx.strokeStyle = 'rgba(110, 150, 195, 0.5)'
                ctx.lineWidth = 0.8 + Math.min(num(f.properties.strength), 1) * 2.2
                // Curved arc (bowed toward the top) — reads like a great-circle
                // hop on a globe instead of a flat chord. Bow scales with span.
                const dx = bx - a[0], dy = b0[1] - a[1]
                const span = Math.hypot(dx, dy)
                const mx = (a[0] + bx) / 2, my = (a[1] + b0[1]) / 2
                // perpendicular, always biased upward (negative screen-y)
                let nx = -dy / (span || 1), ny = dx / (span || 1)
                if (ny > 0) { nx = -nx; ny = -ny }
                const bow = span * 0.22
                const cx = mx + nx * bow, cy = my + ny * bow
                for (const off of seams) {
                    ctx.beginPath()
                    ctx.moveTo(a[0] + off, a[1])
                    ctx.quadraticCurveTo(cx + off, cy, bx + off, b0[1])
                    ctx.stroke()
                }
            }
            // 3. Static markers (positions, not alerts). Drawn at each seam so
            // they appear in whichever wrapped tile is on screen.
            const ringsAt = (p: [number, number], draw: (sx: number, sy: number) => void) => {
                for (const off of seams) {
                    const sx = p[0] + off
                    if (sx < -40 || sx > size.w + 40) continue
                    draw(sx, p[1])
                }
            }
            const dot = (c: unknown, r: number, fill: string, stroke?: string, sw = 0) => {
                if (!Array.isArray(c)) return
                const p = pt(c as [number, number])
                if (!p) return
                ringsAt(p, (sx, sy) => {
                    ctx.beginPath()
                    ctx.arc(sx, sy, r, 0, Math.PI * 2)
                    if (fill !== 'none') { ctx.fillStyle = fill; ctx.fill() }
                    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.stroke() }
                })
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

            // 4. ALERT markers — animated. Conflict dots pulse; anomaly rings ping.
            const pulse = 0.5 + 0.5 * Math.sin(t / 480) // 0..1, ~1.5 Hz
            overlay.acled.features.forEach((f, i) => {
                const c = f.geometry.coordinates
                if (!Array.isArray(c)) return
                const p = pt(c as [number, number]); if (!p) return
                // Smaller + lower opacity so they don't swamp the map.
                const base = Math.min(num(f.properties.radius, 3) * 0.55, 5.5)
                const ph = 0.5 + 0.5 * Math.sin(t / 480 + i * 0.7)
                ringsAt(p, (sx, sy) => {
                    ctx.beginPath(); ctx.arc(sx, sy, base * (0.85 + 0.3 * ph), 0, Math.PI * 2)
                    ctx.fillStyle = `rgba(239,90,70,${0.22 + 0.22 * ph})`; ctx.fill()
                    ctx.lineWidth = 0.8; ctx.strokeStyle = 'rgba(239,90,70,0.7)'; ctx.stroke()
                })
            })
            // anomaly = radar ping: a steady core ring + an expanding, fading ring.
            overlay.anomaly.features.forEach((f, i) => {
                const c = f.geometry.coordinates
                if (!Array.isArray(c)) return
                const p = pt(c as [number, number]); if (!p) return
                const base = num(f.properties.radius, 8)
                const ping = ((t / 1600 + i * 0.33) % 1)
                ringsAt(p, (sx, sy) => {
                    ctx.beginPath(); ctx.arc(sx, sy, base * (0.92 + 0.12 * pulse), 0, Math.PI * 2)
                    ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(239,68,68,0.95)'; ctx.stroke()
                    ctx.beginPath(); ctx.arc(sx, sy, base * (1 + ping * 1.6), 0, Math.PI * 2)
                    ctx.lineWidth = 1.5; ctx.strokeStyle = `rgba(239,68,68,${0.6 * (1 - ping)})`; ctx.stroke()
                })
            })

            // 5. Country names — appear when zoomed in (constant size, screen
            // space → never scale weird). Fade in over the threshold.
            if (applied.k > 2.2 && labels) {
                const a = Math.min(1, (applied.k - 2.2) / 1.5)
                ctx.font = '600 11px "Geist Variable", ui-sans-serif, system-ui, sans-serif'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                for (const lb of labels) {
                    const p = pt(lb.c); if (!p) continue
                    for (const off of seams) {
                        const sx = p[0] + off
                        if (sx < 0 || sx > size.w || p[1] < 0 || p[1] > size.h) continue
                        ctx.lineWidth = 3; ctx.strokeStyle = `rgba(6,10,18,${0.85 * a})`
                        ctx.strokeText(lb.name, sx, p[1])
                        ctx.fillStyle = `rgba(226,232,240,${a})`
                        ctx.fillText(lb.name, sx, p[1])
                    }
                }
            }
        }
        raf = requestAnimationFrame(frame)
        return () => cancelAnimationFrame(raf)
    }, [])

    return (
        <div
            ref={containerRef}
            className="equal-earth-map"
            onDoubleClick={resetView}
        >
            {ee && (
                // GPU-composited pan/zoom: the transform is a CSS transform on
                // this wrapper (translate3d+scale), NOT an SVG <g transform> —
                // SVG group transforms re-rasterize 177 detailed paths every
                // frame on mobile ("se tuesta"); a CSS transform is composited on
                // the GPU and stays smooth.
                <div
                    className="equal-earth-viewport"
                    style={{
                        transform: `translate3d(${applied.x}px, ${applied.y}px, 0) scale(${applied.k})`,
                        transformOrigin: '0 0',
                        willChange: gesturing ? 'transform' : 'auto',
                    }}
                >
                    <svg
                        className="equal-earth-svg"
                        width={size.w}
                        height={size.h}
                        viewBox={`0 0 ${size.w} ${size.h}`}
                        style={{ overflow: 'visible' }}
                    >
                        <defs>
                            {/* Gaussian blur → heat conduction across borders. */}
                            <filter id="atlas-heat-blur" x="-20%" y="-20%" width="140%" height="140%">
                                <feGaussianBlur stdDeviation="5" />
                            </filter>
                        </defs>
                        {/* 3 tiles → infinite horizontal wrap (rectangular proj
                            tiles perfectly at ±180°). Middle + both neighbors so a
                            seam is never visible as you pan/rotate sideways. Per
                            tile: ocean → land → blurred heat → crisp borders. */}
                        {[-ee.worldWidth, 0, ee.worldWidth].map(off => (
                            <g key={off} transform={`translate(${off},0)`}>
                                <path
                                    d={ee.pathString({ type: 'Sphere' }) ?? ''}
                                    className="equal-earth-sphere"
                                    style={{ fill: OCEAN }}
                                />
                                {graticulePath && (
                                    <path d={graticulePath} className="equal-earth-graticule" />
                                )}
                                {landEls}
                                <g filter="url(#atlas-heat-blur)">{heatEls}</g>
                                {borderEls}
                            </g>
                        ))}
                    </svg>
                </div>
            )}
            {/* Markers/flows/terminator: screen-space canvas (crisp, fixed-size
                under zoom), redrawn rAF-throttled with the transform. */}
            {ee && (
                <canvas
                    ref={canvasRef}
                    className="equal-earth-canvas"
                    style={{ width: size.w, height: size.h }}
                />
            )}
            <div className="equal-earth-vignette" />
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
