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
import { geoArea, geoCentroid, geoGraticule10 } from 'd3-geo'
import {
    createEqualEarth,
    type ViewTransform,
    IDENTITY_TRANSFORM,
} from '../lib/equalEarthProjection'
import { heatFillColor, heatGlowColor, lensFillColor, type CountryHeatStates } from '../lib/countryHeatStates'
import { resolveInboundIso, LEGACY_GDELT_TO_ISO } from '../lib/countryCodeBoundary'
import { MICRO_CENTROIDS } from '../lib/microstates'
import { resolveCountryName } from '../lib/countryNames'
import './EqualEarthMap.css'

// Inverse of the legacy alias table — lets the heat lookup fall back to a
// legacy-keyed backend row (e.g. heat under 'GZ' painting the PS polygon).
const ISO_TO_LEGACY: Record<string, string> = Object.fromEntries(
    Object.entries(LEGACY_GDELT_TO_ISO).map(([legacy, iso]) => [iso, legacy]),
)

// Land base color (slate) so countries read as land over the darker ocean, and
// heat tints ON TOP of land (single-fill alpha composite) instead of floating
// on ocean — the contrast fix.
// Land brighter than the (greyer, lighter) ocean so countries stand out — the
// Mercator basemap reads as grey sea + lighter land; match that contrast.
//
// R3c defect 13 — CANVAS POLICY DECISION (see DESIGN.md "Deep-field canvas
// policy"): the basemap is DARK-BY-DESIGN in every theme. The G1 heat ramp
// (lib/countryHeatStates.heatFillColor) was CVD-validated for monotonic
// effective luminance OVER THIS DARK GROUND — its max-heat core is near-white
// [255,226,205], which would vanish on a light basemap. Theming the ocean/land
// without re-deriving that validated ramp would silently break the heat
// encoding, so the map stays a deliberate dark viewport inside light chrome
// (emerald-light frames it via EqualEarthMap.css).
const LAND_RGB: [number, number, number] = [58, 76, 100]
const OCEAN = '#1b2531'

// Country codes are ISO end-to-end (fix round 2026-07-17 item 1): the geojson
// carries ISO_A2 and every click consumer (focus, CountryBrief, /evidence/day,
// resolveCountryName) keys ISO too — clicks pass the polygon's ISO through
// UNCONVERTED. The old ISO→GDELT conversion here turned CN into FIPS 'CH',
// which ISO consumers read as Switzerland ("click China opens Switzerland").
// Inbound codes (selectedCountryCode / flyCountry) may still carry legacy
// GDELT residue with no ISO meaning (GZ, KS…) — resolved ISO-first via
// lib/countryCodeBoundary.resolveInboundIso.

const GEOJSON_URL = '/data/countries.geojson'

// G4 (dataviz audit): GDELT CAMEO event descriptions → 3 marker classes.
// Rendered as SHAPES (circle/triangle/square) because three warm hues at ~3px
// are indistinguishable on the map — and for CVD viewers, always.
type ConflictClass = 'battle' | 'unrest' | 'coercion'
function conflictClass(type: string): ConflictClass {
    const t = type.toLowerCase()
    if (/fight|artillery|aerial weapon|military force|assassinat|unconventional violence|ethnic cleansing|small arms/.test(t)) return 'battle'
    if (/protest|riot|repress|physically assault|abduct|hostage|arrest/.test(t)) return 'unrest'
    return 'coercion'
}
const CONFLICT_CLASS_COLORS: Record<ConflictClass, string> = {
    battle: '239,68,68',    // red circle — armed force
    unrest: '249,115,22',   // orange triangle — unrest / repression
    coercion: '234,179,8',  // amber square — coercion / posture
}
// Human names for the shape classes — the hover card says WHAT the shape means
// (Pedro 2026-07-12: "no se entiende ni siquiera por qué lo ponen triangular").
const CONFLICT_CLASS_LABELS: Record<ConflictClass, string> = {
    battle: 'Armed force',
    unrest: 'Unrest / repression',
    coercion: 'Coercion / posture',
}

type MarkerKind = 'chokepoint' | 'acled' | 'disaster' | 'anomaly'

// ── Click-reliability helpers (council 2026-07-17, P1-8 / wish 14) ──────────
// Pure + exported so the hit-test priorities are frozen by tests.

/** Pointer slop (px) below which a press-release is a CLICK, not a pan. */
export const CLICK_SLOP_PX = 6

/** Drawn screen radii of the point-marker glyphs (see the canvas draw code —
 *  markers are screen-space, they do not scale with zoom). */
const MARKER_DRAWN_RADIUS: Record<'acled' | 'disaster' | 'chokepoint', number> = {
    acled: 5.5, disaster: 8, chokepoint: 9,
}

export type PointMarkerKind = 'acled' | 'disaster' | 'chokepoint'

/** Hit tolerance for a marker at zoom k: near the drawn glyph at world zoom
 *  (a generous fixed 12-14px let a Cape Town event card steal a click made
 *  near Brazil), finger-friendly once zoomed in. */
export function markerHitTolerance(kind: PointMarkerKind, k: number): number {
    return MARKER_DRAWN_RADIUS[kind] + (k < 2 ? 2.5 : 6.5)
}

export interface MarkerCandidate { kind: PointMarkerKind; dist: number; index: number }

/** NEAREST marker within its tolerance wins — never array/layer order. A miss
 *  (null) lets the click fall through to the country polygon. */
export function pickMarkerHit(cands: MarkerCandidate[], k: number): MarkerCandidate | null {
    let best: MarkerCandidate | null = null
    for (const c of cands) {
        if (c.dist > markerHitTolerance(c.kind, k)) continue
        if (!best || c.dist < best.dist) best = c
    }
    return best
}

// ── Tiny-island assist (fix round 2026-07-17, item 7) ───────────────────────
// Country paths down to 1.4×2.9px at world zoom are untargetable. A click or
// hover that misses every polygon searches SMALL countries whose bbox is
// within ISLAND_NEAR_PX of the pointer and picks the nearest. Runs only on
// true misses, so the marker > polygon > assist priority holds.

/** Screen-px reach of the assist around a tiny country's bbox. */
export const ISLAND_NEAR_PX = 5
/** A country only gets the assist while its drawn bbox is at most this many
 *  screen px in BOTH dimensions — once zoomed in, the real path takes over. */
export const ISLAND_SMALL_PX = 12

export interface IslandCandidate {
    iso: string
    name: string
    /** bbox in BASE (k=1) projected coordinates. */
    x0: number; y0: number; x1: number; y1: number
}

/**
 * Nearest SMALL country whose bbox sits within `nearPx` (screen px at zoom k)
 * of the pointer (`base` = pointer in base coordinates). Null = no assist.
 */
export function pickNearestSmallCountry(
    cands: IslandCandidate[],
    base: { x: number; y: number },
    k: number,
    nearPx: number = ISLAND_NEAR_PX,
    smallPx: number = ISLAND_SMALL_PX,
): IslandCandidate | null {
    let best: IslandCandidate | null = null
    let bestD = Infinity
    for (const c of cands) {
        if ((c.x1 - c.x0) * k > smallPx || (c.y1 - c.y0) * k > smallPx) continue
        const dx = Math.max(c.x0 - base.x, 0, base.x - c.x1) * k
        const dy = Math.max(c.y0 - base.y, 0, base.y - c.y1) * k
        const d = Math.hypot(dx, dy)
        if (d > nearPx) continue
        if (d < bestD) { best = c; bestD = d }
    }
    return best
}

/** Did a d3-zoom gesture actually MOVE? Sub-slop jitter during a click used to
 *  mark the gesture as a pan and silently swallow the country select. */
export function gestureMoved(
    a: { x: number; y: number; k: number },
    b: { x: number; y: number; k: number },
    slop: number = CLICK_SLOP_PX,
): boolean {
    return b.k !== a.k || Math.hypot(b.x - a.x, b.y - a.y) > slop
}

/** ISO code of a geojson feature. Prefers a VALID 2-letter ISO_A2; falls back
 *  to ISO_A2_EH when ISO_A2 is Natural Earth's '-99' or a compound like
 *  'CN-TW' (Taiwan) — that fallback is what gives Taiwan (TW) and Kosovo (XK)
 *  their real polygons. '-99' when neither field is usable, so the existing
 *  click/label guards keep filtering the truly code-less features. */
export function featureIso(props: Record<string, unknown>): string {
    const a = String(props.ISO_A2 ?? '')
    if (/^[A-Z]{2}$/.test(a)) return a
    const eh = String(props.ISO_A2_EH ?? '')
    if (/^[A-Z]{2}$/.test(eh)) return eh
    return '-99'
}

/** Round-2 item 2: fly-to target for an ISO code. Polygon anchor when the
 *  country has a feature; MICRO_CENTROIDS fallback for polygon-less
 *  microstates (Malta class) — flyCountry must never silently no-op and leave
 *  the camera parked over the previous country. Null only for unknown codes. */
export function flyTarget(
    features: Array<{ geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }>,
    iso: string,
): [number, number] | null {
    const f = features.find(ft => featureIso(ft.properties) === iso)
    const anchor = f ? flyAnchor(f.geometry) : null
    return anchor ?? MICRO_CENTROIDS[iso] ?? null
}

/** Camera anchor for a country: the centroid of its LARGEST landmass. The
 *  whole-feature centroid area-averages scattered territories (the council's
 *  "fly-to averages coordinates" / Mongolia-class bug), pulling the camera off
 *  the country people mean. Null on degenerate geometry — skip the fly. */
export function flyAnchor(geometry: { type: string; coordinates: unknown }): [number, number] | null {
    try {
        if (geometry.type === 'MultiPolygon') {
            const polys = geometry.coordinates as unknown[]
            if (!Array.isArray(polys) || polys.length === 0) return null
            let best: unknown = null
            let bestArea = -1
            for (const p of polys) {
                const area = geoArea({ type: 'Polygon', coordinates: p } as never)
                if (area > bestArea) { bestArea = area; best = p }
            }
            if (best == null) return null
            return geoCentroid({ type: 'Polygon', coordinates: best } as never) as [number, number]
        }
        if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length === 0) return null
        const c = geoCentroid(geometry as never) as [number, number]
        return Number.isFinite(c[0]) && Number.isFinite(c[1]) ? c : null
    } catch { return null }
}

/** A clickable source line on a marker card — the receipt link (#255). */
export type SourceLink = { label: string; url: string }

/** Hover card state: country shape hover vs marker (hazard/conflict/chokepoint).
 *  `iso` rides the country variant so the ◆ capture affordance can pin it. */
type HoverState =
    | { kind: 'country'; iso: string; name: string; heat: number; x: number; y: number }
    | { kind: 'marker'; title: string; meta: string[]; hint: string | null; sourceLink: SourceLink | null; x: number; y: number }

/** True when a mouse event's target sits inside the hover tooltip. The
 *  interactive tooltip (◆ capture) is a pointer-events:auto child of the map
 *  container, so the container's capture/bubble hover handlers still see moves
 *  over it — this lets them bow out so hovering the tooltip never re-evaluates
 *  or clears the hover it belongs to (Task 3.7). */
function targetInTooltip(e: React.MouseEvent): boolean {
    return !!(e.target as Element | null)?.closest?.('.equal-earth-tooltip')
}

/** Compact host label for a source link ("earthquake.usgs.gov" from its URL).
 *  Only http(s) URLs earn a link — anything else returns null (omit honestly). */
export function sourceLinkFrom(rawUrl: unknown): SourceLink | null {
    const url = String(rawUrl || '').trim()
    if (!/^https?:\/\//i.test(url)) return null
    try {
        const host = new URL(url).hostname.replace(/^www\./, '')
        if (!host) return null
        return { label: `Source: ${host}`, url }
    } catch {
        return null
    }
}

/** "2026-07-11T14:32:00Z" → "Jul 11, 14:32" · date-only strings stay date-only
 *  (rendered in UTC so "2026-07-10" never slips a day in negative offsets). */
function formatEventDate(iso: string): string | null {
    if (!iso) return null
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    if (!iso.includes('T')) {
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
    }
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** Build the hover-card content for a hit marker. Pure — testable shape. */
export function markerHoverContent(
    kind: MarkerKind,
    p: Record<string, unknown>,
): { title: string; meta: string[]; hint: string | null; sourceLink: SourceLink | null } {
    if (kind === 'disaster') {
        const dtype = String(p.dtype || 'hazard')
        const title = dtype.charAt(0).toUpperCase() + dtype.slice(1)
        const meta: string[] = []
        const mag = typeof p.magnitude === 'number' ? p.magnitude : null
        if (mag != null) meta.push(`Magnitude ${mag.toFixed(1)}`)
        const alert = String(p.alert || '')
        if (alert) meta.push(`${alert.toUpperCase()} alert`)
        // USGS quake titles repeat "M 4.7 - " — strip it, magnitude has its line.
        // What remains names the epicenter ("northern Mid-Atlantic Ridge") — the
        // honest answer to "why is there a dot in the ocean".
        const place = String(p.title || '').replace(/^M\s*[\d.]+\s*[-–]\s*/, '') || String(p.country || '')
        if (place) meta.push(place)
        const when = formatEventDate(String(p.time || ''))
        if (when) meta.push(when)
        // #255: when the payload carries the USGS/GDACS event URL, the source
        // becomes a CLICKABLE receipt line; otherwise fall back to the plain
        // attribution text (never fabricate a link).
        const sourceLink = sourceLinkFrom(p.url)
        const src = String(p.source || '').toUpperCase()
        if (src && !sourceLink) meta.push(`Source: ${src}`)
        return { title, meta, hint: `Click opens the ${src || 'official'} event page`, sourceLink }
    }
    if (kind === 'anomaly') {
        // #255: the baseline ring is a DERIVED attention signal, not a discrete
        // real-world event — the receipt must say so (the honest answer to
        // "why is this country pinging").
        const name = String(p.country_name || p.country_code || 'Country')
        const meta: string[] = []
        const mult = Number(p.multiplier)
        if (Number.isFinite(mult) && mult > 0) meta.push(`${mult.toFixed(1)}× its own baseline volume`)
        const z = Number(p.zscore)
        if (Number.isFinite(z) && z !== 0) meta.push(`z-score ${z.toFixed(1)}`)
        const cur = Number(p.current_count)
        if (Number.isFinite(cur) && cur > 0) meta.push(`${cur.toLocaleString()} signals in the window`)
        const level = String(p.level || '')
        if (level && level !== 'normal') meta.push(`Level: ${level}`)
        return {
            title: `Baseline spike · ${name}`,
            meta,
            hint: 'Derived attention signal (volume vs this country’s own norm) — not a discrete event. Click opens the country.',
            sourceLink: null,
        }
    }
    if (kind === 'acled') {
        const cls = conflictClass(String(p.type || ''))
        const meta: string[] = []
        const type = String(p.type || '')
        if (type) meta.push(type)
        const where = [String(p.place || ''), String(p.country || '')].filter(Boolean).join(', ')
        if (where) meta.push(where)
        const when = formatEventDate(String(p.date || ''))
        if (when) meta.push(when)
        const fat = Number(p.fatalities)
        if (Number.isFinite(fat) && fat > 0) meta.push(`${fat} reported killed`)
        // #255: link straight to the ACLED source page when the event carries
        // its URL; omit honestly when it does not.
        const sourceLink = sourceLinkFrom(p.url)
        return { title: `Conflict event · ${CONFLICT_CLASS_LABELS[cls]}`, meta, hint: 'Click for event details', sourceLink }
    }
    return {
        title: String(p.name || 'Maritime chokepoint'),
        meta: [p.active === true ? 'Active vessel traffic' : 'Maritime chokepoint'],
        hint: 'Click for chokepoint panel',
        sourceLink: null,
    }
}


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
    disasters?: FC
    terminator: FC
}

export interface EqualEarthMapProps {
    heatStates: CountryHeatStates
    showHeatmap: boolean
    selectedCountryCode: string | null
    /** GDELT code to pan/zoom the view to (the #234 fly-to, EE edition). */
    flyCountry?: string | null
    /** Bump to reset the view (the toolbar ↺ — was MapLibre-only). */
    resetNonce?: number
    onCountryClick: (isoCode: string, name: string) => void
    /** Marker click (Mercator parity): chokepoint / conflict-event dots. */
    onMarkerClick?: (kind: 'chokepoint' | 'acled' | 'disaster', properties: Record<string, unknown>) => void
    /** Exploration Flywheel (Task 3.7): pin the hovered COUNTRY as a WHERE-lane
     *  entity pin. OPTIONAL — the ◆ affordance renders only when supplied, so
     *  callers that don't pass it stay byte-identical (no interactive tooltip). */
    onPinCountry?: (iso: string, name: string) => void
    /** Pin the hovered event MARKER (acled/disaster) as an un-gated receipt. */
    onPinMarker?: (payload: { title: string; sourceLink: SourceLink | null; source?: string }) => void
    /** Overlay layers (flows/markers/terminator), same data MapLibre uses. */
    overlay?: OverlayData
}

export function EqualEarthMap({
    heatStates,
    showHeatmap,
    selectedCountryCode,
    flyCountry,
    resetNonce,
    onCountryClick,
    onMarkerClick,
    onPinCountry,
    onPinMarker,
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
    // Parity gap vs Mercator (capture-doc audit): hover tooltip with the
    // country name — plus marker hover cards (hazard/conflict/chokepoint).
    // Screen-space; cleared on leave/pan.
    const [hover, setHover] = useState<HoverState | null>(null)

    // ── ◆ capture (Exploration Flywheel, Task 3.7) ──────────────────────────
    // The tooltip normally tracks the cursor and clears the instant you leave
    // the country/marker — hostile to a button inside it (it runs ahead of the
    // pointer and vanishes before a click lands). When a pin callback is
    // supplied we make the matching tooltip INTERACTIVE: the country card freezes
    // on first contact (a stationary ◆ target) and a short dismiss timer bridges
    // the hand-off from the shape/marker to the tooltip. With NEITHER callback
    // the timer never arms and the tooltip clears immediately — byte-identical to
    // before, so existing callers are untouched.
    const canPinCountry = !!onPinCountry
    const canPinMarker = !!onPinMarker
    const dismissRef = useRef<number | null>(null)
    const cancelDismiss = useCallback(() => {
        if (dismissRef.current != null) { window.clearTimeout(dismissRef.current); dismissRef.current = null }
    }, [])
    // Fixed countdown (not restarted while pending) so the tooltip reliably
    // dies ~420ms after you leave a marker/shape unless you reach it in time.
    const armDismiss = useCallback(() => {
        if (dismissRef.current != null) return
        dismissRef.current = window.setTimeout(() => { dismissRef.current = null; setHover(null) }, 420)
    }, [])
    useEffect(() => () => { if (dismissRef.current != null) window.clearTimeout(dismissRef.current) }, [])

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
            iso: featureIso(f.properties),
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
            const iso = featureIso(f.properties)
            if (!name || iso === '-99') return null
            try {
                const c = geoCentroid(f as never) as [number, number]
                return { name, c }
            } catch { return null }
        }).filter(Boolean) as Array<{ name: string; c: [number, number] }>
    }, [features])

    // ISO codes that actually have a polygon — the keyspace for ISO-first
    // resolution of inbound codes (selectedCountryCode / flyCountry).
    const isoSet = useMemo(() => new Set(paths.map(p => p.iso)), [paths])
    const hasIso = useCallback((c: string) => isoSet.has(c), [isoSet])

    const selectedIso = resolveInboundIso(selectedCountryCode, hasIso)

    // True during/just after a pan-zoom gesture — swallows the click that fires
    // at gesture end so a pan ≠ a country select.
    const movedRef = useRef(false)

    const handleCountryClick = useCallback((iso: string, name: string) => {
        if (movedRef.current) return // a pan, not a select
        if (!iso || iso === '-99') return
        // ISO passes through UNCONVERTED — consumers key ISO (item-1 fix).
        onCountryClick(iso, name)
    }, [onCountryClick])

    // Heat rows may still arrive keyed by legacy GDELT residue (GZ for PS…):
    // look up the polygon's ISO first, then its legacy alias.
    const heatFor = useCallback((iso: string) => (
        heatStates.get(iso) ?? (ISO_TO_LEGACY[iso] ? heatStates.get(ISO_TO_LEGACY[iso]) : undefined)
    ), [heatStates])

    // Item 7: base-coordinate bboxes for the tiny-island assist. Computed once
    // per projection fit (walks every ring, so memoized hard).
    const islandBoxes = useMemo<IslandCandidate[]>(() => {
        if (!ee || features.length === 0) return []
        const out: IslandCandidate[] = []
        for (const f of features) {
            const iso = featureIso(f.properties)
            const name = String(f.properties.NAME ?? f.properties.ADMIN ?? '')
            if (!iso || iso === '-99') continue
            const geom = f.geometry as { type: string; coordinates: unknown }
            const rings: [number, number][][] =
                geom.type === 'MultiPolygon'
                    ? (geom.coordinates as [number, number][][][]).flat()
                    : geom.type === 'Polygon'
                        ? (geom.coordinates as [number, number][][])
                        : []
            let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
            for (const ring of rings) {
                for (const c of ring) {
                    const p = ee.project(c)
                    if (!p) continue
                    if (p[0] < x0) x0 = p[0]
                    if (p[0] > x1) x1 = p[0]
                    if (p[1] < y0) y0 = p[1]
                    if (p[1] > y1) y1 = p[1]
                }
            }
            if (Number.isFinite(x0)) out.push({ iso, name, x0, y0, x1, y1 })
        }
        // Round-2 item 2: polygon-less microstates (Malta class — absent from
        // the 110m geojson) join the assist as ZERO-SIZE bboxes at their
        // projected centroid, so hover/click work within the same tolerance.
        const seen = new Set(out.map(b => b.iso))
        for (const [iso, lonlat] of Object.entries(MICRO_CENTROIDS)) {
            if (seen.has(iso)) continue
            const p = ee.project(lonlat)
            if (!p) continue
            out.push({ iso, name: resolveCountryName(iso), x0: p[0], y0: p[1], x1: p[0], y1: p[1] })
        }
        return out
    }, [ee, features])


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
        const st = heatFor(p.iso)
        const heat = showHeatmap && st ? st.heat : 0
        if (heat <= 0) return null
        // Eclipse Lens: membership overrides the hue; heat still carries the
        // opacity/glow. lensFillColor is null off-lens → byte-identical render.
        const fill = (showHeatmap ? lensFillColor(st?.lens) : null) ?? heatFillColor(heat)
        return <path key={`h-${p.iso}-${i}`} d={p.d} fill={fill} />
    }).filter(Boolean), [paths, heatFor, showHeatmap])

    const borderEls = useMemo(() => paths.map((p, i) => {
        const st = heatFor(p.iso)
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
                onMouseMove={(e) => {
                    cancelDismiss()
                    // Freeze the card on first contact when it carries a ◆ so the
                    // affordance is a stationary target (a cursor-tracking tooltip
                    // is unclickable — it runs ahead of the pointer).
                    setHover(prev =>
                        canPinCountry && prev?.kind === 'country' && prev.iso === p.iso
                            ? prev
                            : { kind: 'country', iso: p.iso, name: p.name, heat, x: e.clientX, y: e.clientY })
                }}
                onMouseLeave={() => { if (canPinCountry) armDismiss(); else setHover(null) }}
                style={{ cursor: 'pointer' }}
            />
        )
    }), [paths, heatFor, showHeatmap, selectedIso, handleCountryClick, canPinCountry, cancelDismiss, armDismiss])

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

    /** Item 7: nearest small country to a container-space pointer, across the
     *  3 wrap tiles. Null when nothing small is within reach. */
    const findIslandAt = useCallback((cx: number, cy: number): IslandCandidate | null => {
        if (!ee || islandBoxes.length === 0) return null
        const bx = (cx - applied.x) / applied.k
        const by = (cy - applied.y) / applied.k
        let best: IslandCandidate | null = null
        let bestD = Infinity
        for (const off of [0, -ee.worldWidth, ee.worldWidth]) {
            const hit = pickNearestSmallCountry(islandBoxes, { x: bx + off, y: by }, applied.k)
            if (!hit) continue
            const dx = Math.max(hit.x0 - (bx + off), 0, (bx + off) - hit.x1) * applied.k
            const dy = Math.max(hit.y0 - by, 0, by - hit.y1) * applied.k
            const d = Math.hypot(dx, dy)
            if (d < bestD) { best = hit; bestD = d }
        }
        return best
    }, [ee, islandBoxes, applied])

    // --- Pan / zoom / pinch via d3-zoom (handles wheel, drag AND multi-touch
    // pinch — the mobile gesture the hand-rolled handlers couldn't do). One
    // {k,x,y} transform drives both the SVG <g> and the canvas. ---
    const zoomRef = useRef<ZoomBehavior<HTMLDivElement, unknown> | null>(null)
    // Transform at gesture start — a click is only demoted to a pan when the
    // transform ACTUALLY moved past the slop (P1-8: any 1px jitter used to
    // swallow country clicks at world zoom, silently).
    const gestureStartRef = useRef<{ x: number; y: number; k: number } | null>(null)

    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        const zb = d3zoom<HTMLDivElement, unknown>()
            .scaleExtent([1, 12])
            // ◆ capture (Task 3.7): a press that STARTS on the interactive
            // tooltip must reach the button's click, not d3 — otherwise d3's
            // native pointerdown listener (on this container, above React in the
            // bubble order) fires 'start' → setHover(null) and unmounts the
            // button mid-click. Replicates d3-zoom's default filter + the tooltip
            // veto (no-op when the tooltip is pointer-events:none, i.e. no ◆).
            .filter((event) => {
                const t = event.target as Element | null
                if (t?.closest?.('.equal-earth-tooltip')) return false
                return (!event.ctrlKey || event.type === 'wheel') && !event.button
            })
            // d3's own click suppressor defaults to 0px — pair it with our slop
            // so a jittery click still reaches the country path.
            .clickDistance(CLICK_SLOP_PX)
            .on('start', (event) => {
                const t = event.transform
                gestureStartRef.current = { x: t.x, y: t.y, k: t.k }
                movedRef.current = false
                setGesturing(true)
                setHover(null)
            })
            .on('zoom', (event) => {
                const t = event.transform
                const s = gestureStartRef.current
                if (event.sourceEvent && s && gestureMoved(s, { x: t.x, y: t.y, k: t.k })) {
                    movedRef.current = true
                }
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
        // Pedro (2026-07-02): the strip EVERYWHERE — the world-fit letterbox
        // left dead black space above/below on desktop. Default/reset = fill
        // the available height (fitHeight = k1 identity); the world stays
        // reachable by zooming OUT (scaleExtent min = kFit).
        return zoomIdentity
    }, [])

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
        const iso = resolveInboundIso(flyCountry, hasIso) ?? flyCountry
        // Largest-landmass anchor for polygon countries (council wish 22 — the
        // whole-feature centroid area-averages scattered territories); the
        // MICRO_CENTROIDS fallback for polygon-less microstates (round-2
        // item 2 — searching "Malta" used to silently no-op and leave the
        // camera over the previous country).
        const c = flyTarget(
            features as Array<{ geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }>,
            iso,
        )
        if (!c) return
        const p = ee.project(c)
        if (!p) return
        const k = Math.max(2.5, transform.k)
        const t = zoomIdentity.translate(size.w / 2 - p[0] * k, size.h / 2 - p[1] * k).scale(k)
        const el = containerRef.current
        if (el && zoomRef.current) select(el).call(zoomRef.current.transform, t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [flyCountry, ee, features])

    // Shared marker hit test — the same projected positions the canvas draws,
    // used by BOTH the click capture (open panel / event page) and the hover
    // card. NEAREST marker within a zoom-aware tolerance wins (pickMarkerHit);
    // a miss falls through to the country polygon — the P1-8 fix for a click
    // near Brazil opening a Cape Town event card at world zoom.
    const findMarkerAt = useCallback((cx: number, cy: number): { kind: MarkerKind; properties: Record<string, unknown> } | null => {
        if (!ee || !overlay) return null
        const per = ee.worldWidth * applied.k
        const seams = per > 0 ? [0, -per, per] : [0]
        const distTo = (coords: unknown): number | null => {
            if (!Array.isArray(coords)) return null
            const p = ee.toScreen(coords as [number, number], applied)
            if (!p) return null
            let best = Infinity
            for (const off of seams) best = Math.min(best, Math.hypot(p[0] + off - cx, p[1] - cy))
            return Number.isFinite(best) ? best : null
        }
        const layers: Array<{ kind: PointMarkerKind; features: FC['features'] }> = [
            { kind: 'acled', features: overlay.acled.features },
            { kind: 'disaster', features: overlay.disasters?.features ?? [] },
            { kind: 'chokepoint', features: overlay.chokepoints.features },
        ]
        const cands: MarkerCandidate[] = []
        for (const layer of layers) {
            layer.features.forEach((f, i) => {
                const d = distTo(f.geometry.coordinates)
                if (d != null) cands.push({ kind: layer.kind, dist: d, index: i })
            })
        }
        const hit = pickMarkerHit(cands, applied.k)
        if (hit) {
            const layer = layers.find(l => l.kind === hit.kind)
            const f = layer?.features[hit.index]
            if (f) return { kind: hit.kind, properties: f.properties }
        }
        // Anomaly rings LAST (largest + background — never steal a point marker's
        // hover). Tolerance follows the drawn core-ring radius.
        for (const f of overlay.anomaly.features) {
            const r = typeof f.properties.radius === 'number' ? f.properties.radius : 8
            const tol = Math.min(Math.max(r, 8), 24) + 4
            const d = distTo(f.geometry.coordinates)
            if (d != null && d <= tol) return { kind: 'anomaly', properties: f.properties }
        }
        return null
    }, [ee, overlay, applied])

    // Mercator parity: clicking a chokepoint/conflict/disaster dot opens its
    // panel (or event page) instead of falling through to the country.
    const handleMarkerCapture = useCallback((e: React.MouseEvent) => {
        if (targetInTooltip(e)) return // a ◆ click never falls through to a marker
        if (!onMarkerClick || movedRef.current) return
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return
        const hit = findMarkerAt(e.clientX - rect.left, e.clientY - rect.top)
        // Anomaly rings are hover-receipt only (#255): the click falls through
        // to the country path — opening the country IS the right action.
        if (hit && hit.kind !== 'anomaly') {
            e.stopPropagation()
            onMarkerClick(hit.kind, hit.properties)
        }
    }, [onMarkerClick, findMarkerAt])

    // Hover card for markers (Pedro 2026-07-12: clicking an unexplained ocean
    // triangle threw him blind onto a USGS page — say what it IS first).
    // Capture phase so a marker hit beats the country path's own hover, and
    // stopPropagation keeps the country tooltip from overwriting it.
    const handleHoverCapture = useCallback((e: React.MouseEvent) => {
        if (targetInTooltip(e)) return // moving onto the ◆ card must not clear it
        if (gesturing) return
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return
        const hit = findMarkerAt(e.clientX - rect.left, e.clientY - rect.top)
        if (hit) {
            e.stopPropagation()
            const { title, meta, hint, sourceLink } = markerHoverContent(hit.kind, hit.properties)
            cancelDismiss()
            setHover({ kind: 'marker', title, meta, hint, sourceLink, x: e.clientX, y: e.clientY })
        } else if (canPinMarker) {
            // Left a marker with a ◆ in play: bridge to the tooltip instead of
            // clearing instantly (the dismiss timer clears it if unreached).
            armDismiss()
        } else {
            // Left a marker over open ocean: no country path will overwrite the
            // stale card — clear it ourselves. Country hovers stay untouched.
            setHover(prev => (prev?.kind === 'marker' ? null : prev))
        }
    }, [gesturing, findMarkerAt, canPinMarker, cancelDismiss, armDismiss])

    // Item 7 — tiny-island assist, CLICK side. Runs in the bubble phase, so:
    // markers already won (their capture handler stopPropagation'd), and a real
    // country-path hit handled itself (skip via target check). Only a true
    // ocean/graticule miss reaches the assist.
    const handleMissClick = useCallback((e: React.MouseEvent) => {
        if (movedRef.current) return // a pan, not a select
        if (targetInTooltip(e)) return // ◆ / source-link clicks are not map clicks
        const target = e.target as Element | null
        if (target?.closest?.('.equal-earth-country')) return // polygon priority
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return
        const hit = findIslandAt(e.clientX - rect.left, e.clientY - rect.top)
        if (hit) onCountryClick(hit.iso, hit.name)
    }, [findIslandAt, onCountryClick])

    // Item 7 — HOVER side: an ocean-move near a tiny island shows its tooltip
    // (same card the polygon hover shows). Real polygon/marker hovers win.
    const handleMissHover = useCallback((e: React.MouseEvent) => {
        if (targetInTooltip(e)) return // moving onto the ◆ card must not clear it
        if (gesturing) return
        const target = e.target as Element | null
        if (target?.closest?.('.equal-earth-country')) return
        const rect = containerRef.current?.getBoundingClientRect()
        if (!rect) return
        const hit = findIslandAt(e.clientX - rect.left, e.clientY - rect.top)
        if (hit) {
            const st = heatFor(hit.iso)
            cancelDismiss()
            setHover(prev =>
                prev?.kind === 'marker' ? prev
                : (canPinCountry && prev?.kind === 'country' && prev.iso === hit.iso) ? prev
                : { kind: 'country', iso: hit.iso, name: hit.name, heat: st ? st.heat : 0, x: e.clientX, y: e.clientY })
        } else if (canPinCountry) {
            armDismiss()
        } else {
            // Over open ocean with no island in reach: clear a stale country
            // card (the path's own mouseleave already fired when we left it).
            setHover(prev => (prev?.kind === 'country' ? null : prev))
        }
    }, [gesturing, findIslandAt, heatFor, canPinCountry, cancelDismiss, armDismiss])

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

            // L7: natural hazards — static triangles (a hazard is a fact, not an
            // alarm), cool-hued + white stroke, distinct from the warm conflict
            // pulse. Screen-space size so zoom doesn't scale them.
            const DISASTER_COLORS: Record<string, string> = {
                earthquake: 'rgba(251,191,36,0.85)', volcano: 'rgba(248,113,113,0.85)',
                flood: 'rgba(56,189,248,0.85)', cyclone: 'rgba(167,139,250,0.85)',
                wildfire: 'rgba(249,115,22,0.85)', drought: 'rgba(202,138,4,0.85)',
            }
            for (const f of overlay.disasters?.features ?? []) {
                const c = f.geometry.coordinates
                if (!Array.isArray(c)) continue
                const p = pt(c as [number, number]); if (!p) continue
                const r = Math.min(num(f.properties.radius, 5), 8)
                const col = DISASTER_COLORS[String(f.properties.dtype)] ?? 'rgba(148,163,184,0.8)'
                ringsAt(p, (sx, sy) => {
                    ctx.beginPath()
                    ctx.moveTo(sx, sy - r)
                    ctx.lineTo(sx - r * 0.87, sy + r * 0.5)
                    ctx.lineTo(sx + r * 0.87, sy + r * 0.5)
                    ctx.closePath()
                    ctx.fillStyle = col; ctx.fill()
                    ctx.lineWidth = 1; ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.stroke()
                })
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
                // G4 (dataviz audit): three near-identical warm hues at ~3px are
                // indistinguishable — at marker size SHAPE beats hue. Circle =
                // armed force, triangle = unrest/repression, square = coercion.
                const cls = conflictClass(String(f.properties.type || ''))
                const col = CONFLICT_CLASS_COLORS[cls]
                ringsAt(p, (sx, sy) => {
                    const r = base * (0.85 + 0.3 * ph)
                    ctx.beginPath()
                    if (cls === 'unrest') {
                        ctx.moveTo(sx, sy - r)
                        ctx.lineTo(sx - r * 0.87, sy + r * 0.5)
                        ctx.lineTo(sx + r * 0.87, sy + r * 0.5)
                        ctx.closePath()
                    } else if (cls === 'coercion') {
                        const q = r * 0.85
                        ctx.rect(sx - q, sy - q, q * 2, q * 2)
                    } else {
                        ctx.arc(sx, sy, r, 0, Math.PI * 2)
                    }
                    ctx.fillStyle = `rgba(${col},${(0.22 + 0.22 * ph).toFixed(3)})`; ctx.fill()
                    ctx.lineWidth = 0.8; ctx.strokeStyle = `rgba(${col},0.7)`; ctx.stroke()
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

    // Toolbar ↺ (was dead on EE — it only spoke MapLibre).
    useEffect(() => {
        if (resetNonce) resetView()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [resetNonce])

    return (
        <div
            ref={containerRef}
            className="equal-earth-map"
            onDoubleClick={resetView}
            onClickCapture={handleMarkerCapture}
            onClick={handleMissClick}
            onMouseMoveCapture={handleHoverCapture}
            onMouseMove={handleMissHover}
            onMouseLeave={() => { cancelDismiss(); setHover(null) }}
            style={hover?.kind === 'marker' ? { cursor: 'pointer' } : undefined}
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
            {hover && hover.kind === 'country' && (
                <div
                    className={`equal-earth-tooltip${canPinCountry ? ' equal-earth-tooltip--interactive' : ''}`}
                    style={{ left: hover.x + 12, top: hover.y - 10 }}
                    onMouseEnter={canPinCountry ? cancelDismiss : undefined}
                    onMouseLeave={canPinCountry ? () => setHover(null) : undefined}
                >
                    {hover.name}
                    <span className="equal-earth-tooltip-heat">
                        {hover.heat > 0.66 ? ' · strongly above its norm'
                            : hover.heat > 0.33 ? ' · above its norm'
                            : hover.heat > 0.05 ? ' · slightly above its norm'
                            : ' · at its baseline'}
                    </span>
                    {canPinCountry && (
                        <button
                            type="button"
                            className="equal-earth-tooltip-pin"
                            aria-label="Pin this to your investigation"
                            data-tip="Pin this to your investigation"
                            onPointerDown={e => e.stopPropagation()}
                            onClick={e => {
                                e.preventDefault()
                                e.stopPropagation()
                                onPinCountry?.(hover.iso, hover.name)
                            }}
                        >◆</button>
                    )}
                </div>
            )}
            {hover && hover.kind === 'marker' && (
                <div
                    className={`equal-earth-tooltip equal-earth-tooltip--marker${canPinMarker ? ' equal-earth-tooltip--interactive' : ''}`}
                    style={{ left: hover.x + 12, top: hover.y - 10 }}
                    onMouseEnter={canPinMarker ? cancelDismiss : undefined}
                    onMouseLeave={canPinMarker ? () => setHover(null) : undefined}
                >
                    <div className="equal-earth-tooltip-title">{hover.title}</div>
                    {hover.meta.map((m, i) => (
                        <div key={i} className="equal-earth-tooltip-meta">{m}</div>
                    ))}
                    {hover.sourceLink && (
                        <a
                            className="equal-earth-tooltip-source"
                            href={hover.sourceLink.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={e => e.stopPropagation()}
                        >
                            {hover.sourceLink.label}
                        </a>
                    )}
                    {hover.hint && (
                        <div className="equal-earth-tooltip-hint">{hover.hint}</div>
                    )}
                    {canPinMarker && (
                        <button
                            type="button"
                            className="equal-earth-tooltip-pin equal-earth-tooltip-pin--block"
                            aria-label="Pin this to your investigation"
                            data-tip="Pin this to your investigation"
                            onPointerDown={e => e.stopPropagation()}
                            onClick={e => {
                                e.preventDefault()
                                e.stopPropagation()
                                // Best-effort source name off the receipt line ("Source: host")
                                // or a "Source: X" meta row — un-gated event data, so the
                                // citation stays gateStatus:'unknown' downstream (honesty rail).
                                const src = hover.sourceLink
                                    ? hover.sourceLink.label.replace(/^Source:\s*/i, '')
                                    : hover.meta.find(m => /^Source:/i.test(m))?.replace(/^Source:\s*/i, '')
                                onPinMarker?.({ title: hover.title, sourceLink: hover.sourceLink, source: src || undefined })
                            }}
                        >◆ Pin to investigation</button>
                    )}
                </div>
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
