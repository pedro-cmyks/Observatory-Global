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

### Units

- **`lib/equalEarthProjection.ts`** (pure, the single source of coordinate
  truth): wraps `d3.geoEqualEarth`; exposes `project([lng,lat]) → [x,y]`,
  `invert([x,y]) → [lng,lat]` (for hit-testing), a `geoPath` generator, and
  applies the shared zoom/pan transform. **SVG, Canvas, and hit-testing all use
  this one instance → layers can never drift apart** (the exact failure ADR-0004
  feared, now structurally prevented).
- **`components/EqualEarthMap.tsx`** — orchestrates the projection + zoom/pan
  state (d3-zoom over one shared transform applied to both the SVG `<g>` and the
  canvas draw). Owns the sized container, renders the sub-layers, wires
  callbacks. Mounts in place of `<MapGL>` when the toggle = Equal Earth.
- **Sub-layers (each one purpose):**
  - `ChoroplethSvg` — country fills + heat ramp (world-atlas `countries-110m`,
    same CDN the L1 Brief already uses), country click/hover/hit-test via native
    SVG events. The basemap.
  - `FlowCanvas` — flow arcs (great-circle paths via `geoPath` over LineString),
    width = co-occurrence strength, same visibility rules as today.
  - `MarkerCanvas` — vessels / aircraft / ACLED / chokepoints + anomaly rings,
    projected points, toggled by the existing layer flags.
  - `TerminatorSvg` — day/night polygon, projected, toggled by `showTerminator`.

### Data flow

`useFocusData` → App.tsx (unchanged) → props → `EqualEarthMap` → sub-layers.
Read-only downward; events bubble up through the existing callbacks. #234 focus
re-scope: translate the current MapLibre fly-to-country into a pan/zoom-to-bounds
in the projected plane (compute projected bbox of the focused country/relation,
animate the shared transform).

## 4. Toggle / default

A control in the existing map control cluster (near reset/flows): **Mercator ↔
Equal Earth**. Persisted in local state (optionally localStorage). Default
Mercator at ship; flip to Equal Earth default + remove MapLibre after Pedro's OK.

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
- Offline-bundling the world-atlas topojson (reuse the existing CDN for v1;
  revisit for PWA offline later).

## 8. Open questions (none blocking)

- localStorage persistence of the projection choice: include in v1 (cheap) —
  decide during planning.
- world-atlas resolution (110m vs 50m): start 110m (Brief-proven, light);
  bump to 50m only if borders look too coarse at zoom.
