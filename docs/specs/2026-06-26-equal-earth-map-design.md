# Equal Earth Map View (L2) — Design

**Date:** 2026-06-26
**Status:** Approved (Pedro, 2026-06-26) — pending spec review → writing-plans
**Tracking:** #212 (ux(map): Equal Earth projection mode), ADR-0005
**Supersedes (technically):** ADR-0004 once Equal Earth is promoted to default

## 1. Motivation

Two forces converge on the same fix:

1. **Honest geographic framing (product identity).** Atlas uses the world map
   as an analytical surface, not decoration. The production L2 map is Web
   Mercator (`react-map-gl/maplibre`, `projection='mercator'`, `isGlobe`
   hardcoded `false` at `App.tsx:337`). Mercator inflates northern-latitude area
   and silently encodes "Europe/North = central, large = important." That
   contradicts Atlas's whole thesis (volume ≠ importance; the same principle
   behind composite heat #231 and voice-diversity). Equal Earth is an equal-area
   pseudocylindrical projection that preserves relative country area — the map
   stops lying about size. This is the ADR-0005 product principle.

2. **The mobile blank-map bug (live, recurring).** On mobile Safari the L2 map
   renders pure black — no basemap, no country shapes, no heat — even on the Map
   tab with the panel fully sized (verified: screenshot 2026-06-26, Map tab
   active, GLOBE/HEAT shown, container has full height between header and tab
   bar). `c883988` (lazy-mount + WebGL-context-loss recovery) did NOT cure it:
   the panel is mounted and sized, so the failure is the **WebGL render itself**
   not painting on the device's GL context, not a mount-timing or container-size
   problem. **Equal Earth (SVG + Canvas 2D) removes the WebGL context entirely**,
   so this class of bug cannot recur. Because the container is confirmed sized,
   an SVG/Canvas map will NOT inherit the blank — the cause is GPU/WebGL, which
   we are deleting.

Equal Earth is therefore not cosmetic polish — it is the permanent fix for the
mobile map and the honest-framing upgrade in one move.

### Why not just `globe`?

MapLibre GL 5.13 supports only `mercator`, `globe`, `vertical-perspective`
(verified in the installed dist). `globe` is area-honest (real sphere) and
native, but (a) it is still WebGL, so it does NOT fix the mobile blank map, and
(b) it is not Equal Earth. Pedro chose real Equal Earth (2026-06-26).

### Why feasible now (ADR-0004 no longer blocks)

ADR-0004 accepted Mercator because the old **deck.gl** globe integration drifted.
**deck.gl is gone** — the L2 map is now pure native MapLibre layers (geojson
sources + fill/line/circle layers + feature-state heat; no `@deck.gl` in
`package.json`). The original blocker does not apply to a fresh d3-geo engine.

## 2. Strategy (approved)

- **Parallel mode → default.** Build the real Equal Earth engine as a
  **switchable view** alongside the MapLibre map (toggle Mercator ↔ Equal
  Earth). Default **Mercator** initially → zero production risk while validating.
  After Pedro's visual verification (incl. mobile), promote Equal Earth to
  default and retire MapLibre in a later commit (out of scope for v1).
- **Full layer parity in v1** (approved): all current L2 layers, not a subset.

## 3. Architecture (isolation)

The Equal Earth view consumes the **same data App.tsx already computes** — no
re-fetch. App passes read-only props (`nodes`, `flows`, `unfilteredFlows`,
`acledConflicts`, `heatComposite`, `selectedCountryCode`, focus state, layer
toggles) and the same callbacks MapLibre uses today (`handleCountryClick`,
focus/fly-to). Clicks/hover behave identically.

### Units (as built)

- **`lib/equalEarthProjection.ts`** (pure, the single source of coordinate
  truth): wraps `d3.geoEqualEarth` fitted to the container; exposes `project`,
  `toScreen`/`toLngLat` (apply/undo the pan/zoom transform), `pathString`,
  `clampScale`. **SVG, Canvas, and hit-testing all use this one instance →
  layers can never drift apart.** Tested.
- **`lib/countryHeatStates.ts`** (pure, NEW): `computeCountryHeatStates` — the
  per-country `{heat,intensity}` map, the **single source of truth shared by the
  MapLibre map and the Equal Earth map** (the MapLibre feature-state effect was
  refactored to consume it; no more two divergent implementations). Plus
  `heatFillColor`/`heatGlowColor`/`glowWidth` mirroring the #231 ramp. Tested.
- **`components/EqualEarthMap.tsx`** — orchestrates projection + pan/zoom state
  (**native pointer/wheel handlers**, no d3-zoom dep — zoom-to-cursor + drag,
  drag swallows the click so pan ≠ select) applied as one shared transform to the
  SVG `<g>` and the canvas. Mounts in place of `<MapGL>` when the toggle = Equal
  Earth. Two render layers in one component:
  - **SVG choropleth** — country fills + heat (from `heatStates`), border glow,
    selected-country highlight, click/hover hit-test via native SVG events. Reads
    **`/data/countries.geojson`** (local Natural Earth 110m, the file the
    MapLibre heat source already uses — offline, no CDN), keyed by `ISO_A2` with
    the `ISO_TO_GDELT` remap so clicks resolve to Atlas codes.
  - **Canvas overlay** (`pointer-events:none`, above the SVG, screen-space draw
    so widths/radii stay constant under zoom): terminator polygons → flow lines
    (width by strength) → markers (chokepoints, aircraft, vessels, ACLED,
    anomaly rings). Fed by App's existing `nativeOverlayData` GeoJSON (same data
    MapLibre draws). Markers are non-interactive in v1.

### Data flow

`useFocusData` → App.tsx (unchanged) → props → `EqualEarthMap` → sub-layers.
Read-only downward; events bubble up through the existing callbacks. #234 focus
re-scope: translate the current MapLibre fly-to-country into a pan/zoom-to-bounds
in the projected plane (compute projected bbox of the focused country/relation,
animate the shared transform).

## 4. Toggle / default

A `MERCATOR`/`EQ EARTH` `layer-btn` in the map control cluster (after reset).
Persisted in **localStorage** (`atlas.mapProjection`). Default Mercator at ship;
flip default + remove MapLibre after Pedro's visual OK. Double-click the Equal
Earth map resets the view.

## 5. Trade-offs

- **Gain:** area-honest map; **no WebGL** → mobile blank-map bug eliminated by
  construction; cleaner abstract basemap on-brand (country-level worldview).
- **Lose:** the carto raster basemap (streets/city labels). Atlas is
  country-level and abstract — acceptable, arguably cleaner.
- **Risk #1 — marker density perf:** mitigated by drawing flows + movement
  markers on Canvas (not SVG); only the basemap/choropleth + country hit-test are
  SVG.
- **Risk #2 — layer alignment:** mitigated by the single shared projection
  instance (§3).

## 6. Testing & verification

- **Unit (pure):** `equalEarthProjection` — `project`/`invert` round-trip within
  tolerance; projected bbox of a known country; transform application.
- **Visual verification (mandatory before promote-to-default, ADR-0005
  acceptance criteria):** heat choropleth, flow arcs, all markers, hover + click
  country selection, zoom/pan, responsive layout, and **mobile specifically**
  (the bug this fixes) — desktop + phone. Do not ship as default until alignment
  + interaction are demonstrably correct.

## 7. Out of scope (v1)

- Promotion to default + removal of MapLibre/`react-map-gl` (separate commit
  after visual sign-off).
- Equal Earth on the L1 Brief (already `geoEqualEarth` via react-simple-maps).
- New layers or data sources — strict parity with today's L2 map.
- Basemap data is the existing local `/data/countries.geojson` (already shipped,
  offline-safe) — no CDN/topojson dependency.

### Known v1 gaps (parity follow-ups, tracked under #212)
- **#234 camera fly-to** is MapLibre-only — Equal Earth re-scopes HEAT (shared
  `heatStates`) but does not yet pan/zoom-to-bounds on focus. Add via the
  projected bbox of the focused country/relation animating the shared transform.
- **Markers non-interactive** on the canvas overlay (click/hover) — ACLED event
  click + chokepoint open are MapLibre-only for now.
- **Aircraft/vessels live refresh** redraws on data change (correct) but no
  per-frame animation of heading — parity with current static markers is fine.

## Implementation TODO

- [x] **P0 deps.** `d3-geo` + `@types/d3-geo` installed.
- [x] **P1 projection (pure).** `lib/equalEarthProjection.ts`: configure
  `geoEqualEarth`, `project`/`invert`, `geoPath`, fit-to-size, shared zoom
  transform. Unit tests (`equalEarthProjection.test.ts`): project/invert
  round-trip, country bbox, transform.
- [x] **P2 choropleth + hit-test.** `EqualEarthMap.tsx` + SVG choropleth from
  local `/data/countries.geojson`, fills/glow from shared `heatStates`,
  selected-country highlight, click/hover → callbacks, native pointer/wheel
  pan/zoom (no d3-zoom), drag swallows click. `countryHeatStates` helper +
  MapLibre effect refactored to it (single source). Both libs unit-tested.
- [x] **P3 flows.** Canvas overlay flow lines (width by strength) from
  `nativeOverlayData`, shared projection + transform, screen-space.
- [x] **P4 markers + terminator.** Canvas overlay: terminator polygons +
  chokepoints/aircraft/vessels/ACLED markers + anomaly rings (layer-flag toggled
  via the same `nativeOverlayData`). Markers non-interactive in v1 (gap above).
- [x] **P5 toggle + wire.** `MERCATOR`/`EQ EARTH` toggle (localStorage), renders
  `EqualEarthMap` in place of `<MapGL>`, App data props + `onCountryClick`
  callback. Default Mercator. (#234 fly-to-bounds deferred — gap above.)
- [~] **P6 verify.** Unit + build green (17 new tests; full suite 110 pass / 1
  pre-existing unrelated fail). **Visual check on desktop + mobile PENDING** —
  Pedro flips the EQ EARTH toggle; required before promote-to-default. Default
  Mercator means prod is unaffected until then.

## 8. Open questions (none blocking)

- localStorage persistence of the projection choice: include in v1 (cheap) —
  decide during planning.
- world-atlas resolution (110m vs 50m): start 110m (Brief-proven, light);
  bump to 50m only if borders look too coarse at zoom.
