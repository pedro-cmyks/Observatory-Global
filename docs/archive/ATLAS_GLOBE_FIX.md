# ATLAS Globe Fix — Technical Research Brief

Date: 2026-03-30
Status: Research complete, ready for implementation

---

## 1. ROOT CAUSE

Atlas's Deck.gl layers don't render on the MapLibre globe surface because of **two independent problems**:

### Problem A: Wrong Integration Mode

Atlas uses **"reverse-controlled" mode** — the `DeckGL` component wraps `MapGL` and manages its own viewport:

```tsx
// Current App.tsx (lines 459-499)
<DeckGL
  viewState={viewState}
  onViewStateChange={...}
  controller={true}
  layers={layers}
>
  <MapGL ref={mapRef} ... />
</DeckGL>
```

In this mode, Deck.gl maintains its own Mercator projection matrix. When MapLibre switches to globe via `map.setProjection({ type: 'globe' })`, MapLibre renders a sphere, but Deck.gl's viewport is still computing flat Mercator coordinates. The layers render in Mercator space above a spherical basemap — they "float" in space instead of wrapping the globe.

**The fix is to switch to `MapboxOverlay` mode**, where Deck.gl renders directly into MapLibre's WebGL2 context and inherits its projection matrix (including globe):

```tsx
import { MapboxOverlay } from '@deck.gl/mapbox';
import { useControl } from 'react-map-gl/maplibre';

function DeckGLOverlay(props) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

<Map mapLib={maplibregl} projection={isGlobe ? 'globe' : 'mercator'}>
  <DeckGLOverlay layers={layers} interleaved={true} />
</Map>
```

This is how deck.gl officially supports MapLibre globe as of v9.1 (January 2025). Atlas has deck.gl ^9.2.2 and maplibre-gl ^5.13.0 — both are compatible.

### Problem B: HeatmapLayer Is Fundamentally Incompatible with Globe

HeatmapLayer performs GPU-based screen-space aggregation that is hardcoded to a planar coordinate system. The deck.gl GlobeView documentation **explicitly lists HeatmapLayer as unsupported**:

> Not supported: HeatmapLayer, ContourLayer, TerrainLayer, MaskExtension
> — [deck.gl GlobeView docs](https://deck.gl/docs/api-reference/core/globe-view)

This is not a bug — it's a fundamental architectural limitation. HeatmapLayer's aggregation math breaks when the coordinate space is spherical. **No configuration change will fix this.** The heatmap must be auto-disabled in globe mode and replaced with an alternative visualization (e.g., sized ScatterplotLayer circles).

### Summary of Root Causes

| Problem | Cause | Fixable? |
|---------|-------|----------|
| All layers float above globe | Reverse-controlled mode doesn't share projection matrix | YES — switch to MapboxOverlay |
| HeatmapLayer doesn't render on globe | GPU aggregation incompatible with spherical projection | NO — must disable or replace |
| Layers don't re-project on toggle | Stale layer IDs after projection change (bug #9466) | YES — dynamic layer IDs |

---

## 2. WORLD MONITOR'S SOLUTION

### Architecture: Two Separate Rendering Engines

World Monitor does **not** solve the Deck.gl-on-globe problem. They **avoid it entirely** by running two completely independent rendering systems:

| Mode | Renderer | Layers |
|------|----------|--------|
| **Flat map** | MapLibre + Deck.gl (MapboxOverlay, interleaved) | ScatterplotLayer, IconLayer, GeoJsonLayer, PathLayer, ArcLayer, HeatmapLayer, H3HexagonLayer, TextLayer |
| **3D globe** | globe.gl v2.45.0 (Three.js) | htmlElementsData, arcsData, pathsData, polygonsData — NO Deck.gl |

**Key files:**
- `/tmp/worldmonitor/src/components/MapContainer.ts` — facade that delegates to whichever engine is active
- `/tmp/worldmonitor/src/components/DeckGLMap.ts` — flat map (Deck.gl + MapLibre, interleaved)
- `/tmp/worldmonitor/src/components/GlobeMap.ts` — 3D globe (globe.gl, pure Three.js)

### How the Toggle Works

```
switchToGlobe():
  1. Snapshot viewport state + center
  2. Disconnect resize observer
  3. DESTROY flat map entirely (DeckGLMap.destroy())
  4. Create brand new GlobeMap instance
  5. Restore viewport (convert deck.gl zoom → globe.gl altitude)
  6. Rehydrate all cached data onto globe

switchToFlat():
  (reverse — destroy globe, create DeckGLMap from scratch)
```

The MapContainer caches all data so it can rehydrate whichever engine is active. Zoom level conversion:
```
deck.gl zoom 2 (world)    → globe.gl altitude 1.8
deck.gl zoom 3 (continent) → globe.gl altitude 0.6
deck.gl zoom 6+ (city)     → globe.gl altitude 0.15
```

### What Layers They Lose on Globe

| Data Type | Flat Map | Globe | Degradation |
|-----------|----------|-------|-------------|
| Point markers | ScatterplotLayer / IconLayer | HTML elements on globe surface | Full parity (HTML elements are more flexible) |
| Arcs (trade routes) | ArcLayer | globe.gl arcsData | Full parity |
| Paths (cables, pipes) | PathLayer | globe.gl pathsData | Full parity |
| Polygons (zones) | GeoJsonLayer | globe.gl polygonsData | Full parity |
| **Climate heatmap** | HeatmapLayer | **HTML marker dots** | **Degraded — no heatmap on globe** |
| **GPS jamming** | H3HexagonLayer | **HTML marker dots** | **Degraded — no hexagons on globe** |
| Text clusters | TextLayer | HTML elements | Slight visual change |

**Critical insight**: World Monitor also cannot render HeatmapLayer on their globe. They degrade to simple dot markers. This confirms HeatmapLayer-on-globe is a universal limitation, not an Atlas-specific bug.

### Dependency Versions (World Monitor)
- `deck.gl`: ^9.2.6
- `globe.gl`: ^2.45.0
- `maplibre-gl`: ^5.16.0
- `three`: ^0.175.0 (transitive via globe.gl)

### Flat Map Integration Pattern (What Atlas Should Adopt)

World Monitor's flat map uses `MapboxOverlay` with `interleaved: true`:

```ts
// DeckGLMap.ts line 811-814
this.deckOverlay = new MapboxOverlay({
  interleaved: true,
  layers: this.buildLayers(),
  getTooltip: (info) => this.getTooltip(info),
  onClick: (info) => this.handleClick(info),
});
```

They also use "ghost" sentinel layers to maintain stable layer IDs:
```ts
private createEmptyGhost(id: string): ScatterplotLayer {
  return new ScatterplotLayer({
    id: `${id}-ghost`, data: [], getPosition: () => [0, 0], visible: false
  });
}
```

---

## 3. RECOMMENDED FIX FOR ATLAS

### Three Options Evaluated

| Option | Approach | Effort | Globe Quality | Deps Added |
|--------|----------|--------|---------------|------------|
| **A** | Fix MapLibre globe + Deck.gl via MapboxOverlay | 8-12h | Good (no heatmap) | `@deck.gl/mapbox` |
| **B** | Use globe.gl for 3D mode (World Monitor pattern) | 30-40h | Excellent | globe.gl, three |
| **C** | Use Deck.gl standalone GlobeView | 15-20h | Poor (experimental, no rotation, no basemap tiles) | None |

### Recommendation: Option A — MapboxOverlay Integration

**Justification:**
- Lowest effort (8-12h vs 30-40h for globe.gl)
- Zero new heavy dependencies (globe.gl would add Three.js at ~600KB)
- ScatterplotLayer, ArcLayer, and TerminatorLayer all work on globe
- Only HeatmapLayer needs graceful degradation (auto-disable or replace with sized circles)
- Matches deck.gl's officially supported globe integration path
- Already using compatible versions (deck.gl ^9.2.2, maplibre-gl ^5.13.0)

**Why not Option B (globe.gl)?**
- 3-4x more effort for marginal visual improvement
- Requires maintaining two completely separate rendering codebases
- Adds ~600KB+ of Three.js dependencies
- Every new layer must be implemented twice
- World Monitor can afford this because they have 45+ layers and a huge community; Atlas has 5 layers

**Why not Option C (Deck.gl GlobeView)?**
- Still experimental (note the underscore: `_GlobeView`)
- No camera rotation (north always up, no pitch/bearing)
- No basemap tiles built in (must use deck.gl's own TileLayer)
- Same HeatmapLayer limitation as Option A
- Blocking issues: distorted bitmaps near poles (#7104), collision bugs (#6088)

---

## 4. WORKING CODE SKELETON

### Step 1: Add @deck.gl/mapbox dependency

```bash
cd frontend-v2 && npm install @deck.gl/mapbox
```

### Step 2: Create DeckGLOverlay hook

```tsx
// frontend-v2/src/components/DeckGLOverlay.tsx
import { MapboxOverlay, MapboxOverlayProps } from '@deck.gl/mapbox';
import { useControl } from 'react-map-gl/maplibre';

export function DeckGLOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}
```

### Step 3: Refactor App.tsx — Replace DeckGL wrapper with Map + overlay

**Before** (reverse-controlled — broken on globe):
```tsx
<DeckGL
  viewState={viewState}
  onViewStateChange={({ viewState: vs }) => vs && setViewState(vs)}
  controller={true}
  layers={mapReady ? layers : []}
>
  <MapGL ref={mapRef} mapStyle="..." />
</DeckGL>
```

**After** (MapboxOverlay — works on globe):
```tsx
import Map, { useMap } from 'react-map-gl/maplibre';
import { DeckGLOverlay } from './components/DeckGLOverlay';

<Map
  ref={mapRef}
  {...viewState}
  onMove={(evt) => setViewState(evt.viewState)}
  mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
  projection={isGlobe ? 'globe' : 'mercator'}
  attributionControl={false}
  onLoad={(e) => {
    setMapReady(true);
    const map = e.target;
    map.setFog({
      'color': 'rgba(10, 15, 26, 0.8)',
      'horizon-blend': 0.08,
      'high-color': '#1a3050',
      'space-color': '#050510',
      'star-intensity': 0.15
    });
  }}
>
  <DeckGLOverlay
    layers={mapReady ? layers : []}
    interleaved={true}
    getTooltip={({ object }) => {
      if (!object) return null;
      return `${object.name}: ${object.signalCount} signals`;
    }}
  />
</Map>
```

### Step 4: Auto-disable HeatmapLayer in globe mode

```tsx
// In the layers array, gate the heatmap:
showHeatmap && !isGlobe && new HeatmapLayer({
  id: 'signal-heatmap',
  // ... existing config
}),

// Optional: add a ScatterplotLayer as globe-mode heatmap substitute
showHeatmap && isGlobe && new ScatterplotLayer({
  id: 'signal-heat-dots',
  data: enhancedNodes,
  getPosition: (d) => [d.lon, d.lat],
  getRadius: (d) => Math.sqrt(d.signalCount) * 800,
  getFillColor: (d) => {
    const t = Math.min(d.signalCount / 500, 1);
    return [
      30 + t * 200,    // R: blue → red
      60 - t * 40,     // G: teal → dark
      120 - t * 100,   // B: blue → dim
      80 + t * 140     // A: translucent → opaque
    ];
  },
  radiusMinPixels: 6,
  radiusMaxPixels: 40,
  opacity: 0.6,
  pickable: false,
}),
```

### Step 5: Dynamic layer IDs for projection toggle (workaround for bug #9466)

```tsx
// Append projection mode to layer IDs to force reinitialization on toggle
const projSuffix = isGlobe ? '-globe' : '-flat';

new ScatterplotLayer({
  id: `nodes-core${projSuffix}`,
  // ...
}),

new ArcLayer({
  id: `flows${projSuffix}`,
  // ...
}),
```

### Step 6: Simplify toggleGlobe (projection now declarative)

```tsx
const toggleGlobe = useCallback(() => {
  const next = !isGlobe;
  setIsGlobe(next);
  setViewState(prev => ({
    ...prev,
    zoom: next ? 1.8 : 1.5,
    pitch: next ? 20 : 0,
  }));
  localStorage.setItem('atlas-globe-mode', String(next));
}, [isGlobe]);
```

No more `map.setProjection()` call — the `projection` prop on `<Map>` handles it declaratively.

### Step 7: Remove old imports, clean up

```diff
- import { DeckGL } from '@deck.gl/react'
+ import { DeckGLOverlay } from './components/DeckGLOverlay'
```

The `@deck.gl/react` package is no longer needed for the map. It can be removed from dependencies if not used elsewhere.

---

## 5. DATA PIPELINE LEARNINGS

Top 5 things Atlas should adopt from World Monitor's data approach:

### 1. Source Tier System

World Monitor rates every source on a 1-4 tier scale:
- **Tier 1**: Wire services (Reuters, AP, AFP, Bloomberg), government sources (White House, UN, IAEA)
- **Tier 2**: Major outlets (BBC, Guardian, CNN, Al Jazeera)
- **Tier 3**: Specialty/think tanks (Bellingcat, RAND, CSIS)
- **Tier 4**: Aggregators/blogs (defaults for unknown sources)

Within duplicate story clusters, the highest-tier source is selected as the representative. Unknown sources default to tier 4.

**Atlas application**: GDELT already provides source URLs. Atlas could maintain a `SOURCE_TIERS` lookup and weight signal importance by source tier. This would deprioritize tabloid/blog noise without dropping it entirely.

### 2. Keyword Threat Classification with Suppressed Terms

World Monitor classifies every headline into threat levels (critical/high/medium/low/info) using ~100 keyword patterns mapped to categories (military, conflict, terrorism, cyber, economic, disaster, health).

More importantly, they maintain a **massive blocklist of ~300+ suppressed terms** that are excluded from trending keyword detection: generic verbs ("said", "says", "new"), URL fragments, date words, financial generic terms. This prevents "breaking" from always trending.

**Atlas application**: The existing `NOISE_HEADLINE_PATTERNS` in SignalStream.tsx catches sports/entertainment. Adding a suppressed-terms list for the backend narrative analysis would dramatically improve trending theme quality.

### 3. Two-Stage Deduplication (Jaccard + Semantic)

Stage 1: Tokenize headlines, remove stop words, compute Jaccard similarity. Cluster at 0.5 threshold using an inverted index for O(n log n) performance.

Stage 2: If ML is available and there are 5+ Jaccard clusters, embed cluster titles with `all-MiniLM-L6-v2` and merge semantically similar clusters at 0.75 cosine threshold.

Within each cluster, select the item from the highest-tier source as the representative.

**Atlas application**: Atlas's narrative endpoint currently groups by GDELT theme codes, which produces coarse clusters ("ECON_*" captures everything from inflation to sports contracts). Jaccard-based headline clustering would produce tighter, more meaningful narrative threads.

### 4. Propaganda Risk Assessment

World Monitor explicitly flags state-affiliated media with risk levels:
- **High risk**: Xinhua, TASS, RT, CGTN, Press TV, KCNA
- **Medium risk**: Al Jazeera, TRT World, France 24, DW, Voice of America
- **Low risk**: Reuters, AP, BBC, Bellingcat

Each entry includes `stateAffiliated: boolean`, `knownBiases: string[]`, and explanatory notes.

**Atlas application**: Atlas's Source Integrity panel currently shows concentration metrics. Adding a state-media flag to the backend response would let the frontend display when a narrative is being amplified primarily by state-affiliated sources — a genuine narrative intelligence signal.

### 5. Integrated Signal Quality (ISQ) Scoring

World Monitor computes a composite quality score from 4 weighted dimensions:
- **Confidence** (35%): Source count (1=0.4, 2=0.7, 3+=1.0), source tier bonus, alert status
- **Intensity** (30%): Threat level, focal point score, Country Instability Index
- **Expectation Gap** (20%): Whether signal comes from a watched vs unexpected country
- **Timeliness** (15%): Velocity (spike=1.0, elevated=0.6, normal=0.2) + rising trend bonus

Score maps to tiers: `strong (>=0.75) | notable (>=0.50) | weak (>=0.25) | noise (<0.25)`

**Atlas application**: Atlas currently treats all GDELT signals equally. An ISQ-style composite score would let the Signal Stream and Narrative Threads panels surface genuinely important signals instead of volume-weighted averages dominated by routine coverage.

---

## 6. LAYERS COMPATIBILITY TABLE

| Atlas Layer | Type | Works on Globe (MapboxOverlay)? | Fix Needed? |
|-------------|------|---------------------------------|-------------|
| `signal-heatmap` | HeatmapLayer | **NO** — explicitly unsupported | Auto-disable in globe mode; replace with sized ScatterplotLayer circles |
| `nodes-core` | ScatterplotLayer | **YES** | Append projection suffix to ID (`nodes-core-globe` / `nodes-core-flat`) |
| `nodes-anomaly-pulse` | ScatterplotLayer | **YES** | Append projection suffix to ID |
| `flows` | ArcLayer | **YES** — `greatCircle: true` already set | Append projection suffix to ID |
| `terminator` | PolygonLayer (custom) | **YES** | Append projection suffix to ID |

### Known Bugs Affecting Atlas

| Bug | Status | Impact | Workaround |
|-----|--------|--------|------------|
| [#9466](https://github.com/visgl/deck.gl/issues/9466) — Globe sync | OPEN | Layers don't re-project when toggling flat↔globe | Change layer IDs on projection toggle |
| [#9554](https://github.com/visgl/deck.gl/issues/9554) — IconLayer on globe | OPEN | Billboard icons occluded by globe tiles | Atlas doesn't use IconLayer (no impact) |
| [#8602](https://github.com/visgl/deck.gl/issues/8602) — Interleaved checkerboard | OPEN | Rare visual artifact in interleaved mode | Monitor; fallback to `interleaved: false` if observed |

### Globe Atmosphere (Already Compatible)

Atlas's existing fog configuration works with MapboxOverlay mode:

```ts
map.setFog({
  'color': 'rgba(10, 15, 26, 0.8)',
  'horizon-blend': 0.08,
  'high-color': '#1a3050',
  'space-color': '#050510',
  'star-intensity': 0.15
});
```

For enhanced globe atmosphere, add MapLibre sky properties on globe toggle:

```ts
if (isGlobe) {
  map.setSky({
    'sky-color': '#0a0f1a',
    'horizon-color': '#1a5050',
    'fog-color': '#0a0f1a',
    'atmosphere-blend': 0.85
  });
}
```

---

## 7. IMPLEMENTATION SEQUENCE

| Step | Description | Effort | Risk |
|------|-------------|--------|------|
| 1 | `npm install @deck.gl/mapbox` | 5 min | None |
| 2 | Create `DeckGLOverlay.tsx` hook (6 lines) | 15 min | None |
| 3 | Refactor App.tsx: DeckGL wrapper → Map + DeckGLOverlay | 2-3h | Medium — must re-wire viewState, callbacks, tooltip |
| 4 | Gate HeatmapLayer with `!isGlobe`, add ScatterplotLayer substitute | 1h | Low |
| 5 | Add projection suffix to all layer IDs | 30 min | Low |
| 6 | Simplify toggleGlobe to declarative projection prop | 15 min | Low |
| 7 | Test: flat mode works identically to before | 1h | — |
| 8 | Test: globe mode renders ScatterplotLayer + ArcLayer on surface | 1h | — |
| 9 | Add globe atmosphere (sky properties) | 30 min | Low |
| **Total** | | **6-8h** | |

### Migration Risk: Tooltip and Picking

The biggest refactoring risk is tooltip/picking behavior. In reverse-controlled mode, `DeckGL` manages hover/click events directly. In MapboxOverlay mode, events are handled via the overlay's `getTooltip` and `onClick` props. The `onHover` callbacks on individual layers should still work, but need testing.

### Fallback Plan

If MapboxOverlay introduces regressions in flat mode (unlikely but possible due to interleaved rendering differences), the change can be gated behind the globe toggle:
- Flat mode: keep current reverse-controlled DeckGL (proven working)
- Globe mode: mount Map + DeckGLOverlay (new code path)

This is the World Monitor pattern (two renderers) but lighter — same library, just different integration modes.

---

## 8. REFERENCES

### Deck.gl Documentation
- [Using with MapLibre](https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre)
- [MapboxOverlay API](https://deck.gl/docs/api-reference/mapbox/mapbox-overlay)
- [GlobeView (Experimental)](https://deck.gl/docs/api-reference/core/globe-view)
- [HeatmapLayer](https://deck.gl/docs/api-reference/aggregation-layers/heatmap-layer)

### Relevant GitHub Issues
- [#7920](https://github.com/visgl/deck.gl/issues/7920) — Original globe integration request (CLOSED, shipped v9.1)
- [#9466](https://github.com/visgl/deck.gl/issues/9466) — Globe synchronization bug (OPEN)
- [#9554](https://github.com/visgl/deck.gl/issues/9554) — IconLayer globe occlusion (OPEN)
- [#9199](https://github.com/visgl/deck.gl/issues/9199) — GlobeView graduation tracker (OPEN)
- [#8602](https://github.com/visgl/deck.gl/issues/8602) — Interleaved checkerboard (OPEN)

### World Monitor
- [Repository](https://github.com/koala73/worldmonitor) — 44.9K stars
- Architecture: Vanilla TS, globe.gl + Three.js (globe), Deck.gl + MapLibre (flat)
- Key insight: They avoid the Deck.gl-on-globe problem entirely by using a separate Three.js renderer

### Atlas Current Stack
- deck.gl ^9.2.2 | maplibre-gl ^5.13.0 | react-map-gl ^8.1.0
- Integration: Reverse-controlled (DeckGL wrapping MapGL) — must migrate to MapboxOverlay
