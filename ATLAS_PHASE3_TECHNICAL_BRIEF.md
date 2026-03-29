# ATLAS Phase 3 Technical Brief

**Date**: 2026-03-29
**Purpose**: Research findings on World Monitor architecture, 3D globe implementation, and atmospheric aesthetics
**Status**: Research complete, ready for implementation planning

---

## 1. World Monitor -- Key Learnings

### Architecture Overview

World Monitor (github.com/koala73/worldmonitor) is the closest open-source analog to Atlas: 44,900 stars, 45 data layers, 2M+ users, dual map engine.

**Tech stack**: Vanilla TypeScript (no React/Vue), Deck.gl + MapLibre (flat map), globe.gl + Three.js (3D globe), D3.js (mobile SVG fallback), Supercluster (clustering), Transformers.js (in-browser ML), Vite, Tauri (desktop app). Bundle: ~250KB gzipped.

**Backend**: No traditional server. 60+ Vercel Edge Functions, each handling one data source. Cloudflare edge caching. No database -- all state is ephemeral or in localStorage/IndexedDB.

### Globe/Flat Toggle Mechanism

World Monitor maintains **two separate rendering components** sharing the same data:
- **Flat map**: Deck.gl + MapLibre GL JS (`DeckGLMap.ts`) -- primary rendering path
- **3D Globe**: globe.gl + Three.js -- optional enhancement, toggled via `VITE_MAP_INTERACTION_MODE` env var and a runtime setting in UnifiedSettings

The two modes are not blended -- the user switches between them. Settings persist to localStorage and apply immediately without reload.

### Layer Management Pattern

- 40-49 toggleable layers, each a standard Deck.gl layer (ScatterplotLayer, IconLayer, etc.) within `DeckGLMap.ts`
- Layer toggle state syncs to URL for shareable links
- **Zoom-adaptive opacity**: markers fade from 0.2 at world view to 1.0 at street level (progressive disclosure)
- Time filtering (1h, 6h, 24h, 48h, 7d) applies across all visible layers simultaneously
- Each panel fetches its own data independently while sharing configuration lifecycle

### Performance Techniques

| Technique | How They Use It |
|-----------|----------------|
| **Supercluster** | Groups markers at low zoom, expands on zoom-in. Threshold adapts to zoom level |
| **Web Workers** | ML only (NER, sentiment, embeddings via ONNX). Not for data fetching |
| **Virtual scrolling** | News panels render only visible items + 3-item overscan. ~30 DOM nodes vs thousands |
| **WebSocket** | Only for AIS vessel data. Auto-reconnects with 30s backoff. Disconnects when Ships layer disabled |
| **REST polling** | Everything else. Edge functions with Cache-Control headers |
| **No framework** | Direct DOM manipulation keeps bundle at ~250KB and gives fine-grained rendering control |

### What Atlas Should Adopt

1. **Zoom-adaptive opacity** -- markers fade based on zoom level. Simple, effective, prevents clutter without viewport culling
2. **Layer toggle state in URL** -- shareable links that restore exact layer configuration
3. **WebSocket only for high-frequency streams** (AIS), REST polling for everything else -- pragmatic hybrid
4. **Supercluster for dense point layers** -- aircraft and vessels will need clustering at low zoom
5. **Time filtering across all layers** -- a single time control that scopes all visible data

### What Atlas Should NOT Copy

1. **No-framework approach** -- Atlas already uses React, and the narrative intelligence UI (panels with complex state, contexts, interactive filtering) benefits from React's declarative model. World Monitor's vanilla TS works because their panels are simpler data displays.
2. **Serverless-only backend** -- Atlas has a FastAPI + PostgreSQL/TimescaleDB backend that stores time-series narrative data. This is essential for drift detection, historical analysis, and narrative correlation. World Monitor's ephemeral architecture can't do temporal analysis.
3. **Separate globe rendering component** -- World Monitor maintains two entirely separate map codebases (Deck.gl flat + globe.gl 3D). Atlas should use MapLibre Globe (see Section 2) which provides a single codebase with a toggle.
4. **In-browser ML** -- Atlas's narrative intelligence runs server-side with access to the full signal database. Client-side ML makes sense for World Monitor's offline-capable Tauri app, not for Atlas's real-time analysis pipeline.

---

## 2. 3D Globe -- Recommendation

### Option Comparison

| Criterion | A: globe.gl | B: Deck.gl GlobeView | C: MapLibre Globe |
|-----------|-------------|----------------------|-------------------|
| Migration effort | 5/5 (full rewrite) | 2/5 (moderate) | **1/5 (trivial)** |
| Visual quality | 4/5 | 2/5 | **5/5** |
| Performance impact | Moderate-High | Low | **Low-Moderate** |
| Atmosphere effects | Built-in | Limited (SunLight only) | **Built-in** |
| Layer compatibility | None (rewrite all) | Full (experimental) | **Full (stable)** |
| New dependencies | react-globe.gl + three | None | **None** |
| Stability | Stable | Experimental (years) | **Stable (v5+)** |
| Vector basemap | No (static textures) | No | **Yes** |

### Recommendation: Option C -- MapLibre Globe Projection

**MapLibre Globe is the clear winner.** The reasons:

1. **Zero new dependencies** -- Atlas already uses `maplibre-gl: ^5.13.0` and `deck.gl: ^9.2.2`, both of which support globe projection natively
2. **Trivial migration** -- a single `map.setProjection({ type: 'globe' })` call toggles the mode
3. **All existing layers work unchanged** -- HeatmapLayer, ScatterplotLayer, ArcLayer, IconLayer, and the custom TerminatorLayer all render correctly on the globe surface (confirmed in deck.gl v9.1+ with MapLibre collaboration)
4. **Best visual quality** -- full CARTO dark-matter vector tiles render on the 3D sphere. No static textures, no quality loss
5. **Built-in atmosphere** -- sky-color, horizon-color, fog-color, atmosphere-blend are all native MapLibre v5 style properties
6. **Adaptive projection** -- automatically transitions from globe to Mercator around zoom level 5-7, so detailed analysis at high zoom remains pixel-perfect

### Migration Path

The only file that needs modification is `frontend-v2/src/App.tsx`:

```tsx
// 1. Add a ref to access the MapLibre map instance
import { useRef } from 'react';
import type { MapRef } from 'react-map-gl/maplibre';

// 2. Add state for globe mode
const [isGlobe, setIsGlobe] = useState(false);
const mapRef = useRef<MapRef>(null);

// 3. Toggle function
const toggleGlobe = useCallback(() => {
  const map = mapRef.current?.getMap();
  if (!map) return;
  const next = !isGlobe;
  map.setProjection({ type: next ? 'globe' : 'mercator' });
  setIsGlobe(next);
}, [isGlobe]);

// 4. Add ref to MapGL component
<MapGL
  ref={mapRef}
  mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
  onLoad={(e) => {
    setMapReady(true);
    // Configure atmosphere for globe mode
    e.target.setStyle({
      ...e.target.getStyle(),
      sky: {
        'sky-color': '#0a0f1a',
        'horizon-color': '#1a3050',
        'fog-color': '#0a0f1a',
        'sky-horizon-blend': 0.5,
        'horizon-fog-blend': 0.8,
        'atmosphere-blend': 0.85,
      }
    });
  }}
/>

// 5. Add GLOBE toggle button alongside existing GLOW/FLOW/NODES
<button onClick={toggleGlobe} className={isGlobe ? 'active' : ''}>
  GLOBE
</button>
```

**That's it.** No layer rewrites. No new dependencies. No separate rendering component.

### Effort Estimate

| Task | Hours |
|------|-------|
| Add MapRef and globe toggle state | 0.5h |
| Toggle button in Globe panel header | 0.5h |
| Atmosphere configuration | 1h |
| View state adjustments for globe (initial zoom, min/max zoom) | 1h |
| Testing all existing layers on globe surface | 1h |
| Polish (transition animation, persistence to localStorage) | 1h |
| **Total** | **5h (~1-2 sessions)** |

### What Globe Mode Provides

- **Orientation**: See the whole world at once. Understand where narrative activity is concentrated.
- **Immersion**: The globe feels like looking at the real Earth, not a flat data grid.
- **Context**: Adjacent regions visible without Mercator distortion. Africa looks its real size.
- **Toggle**: Users switch between globe (feeling/orientation) and flat map (analysis/detail) freely.

### What Globe Mode Does NOT Provide (and shouldn't)

- Globe mode is not for detailed layer comparison at city level -- that's what flat Mercator is for
- Globe mode should not try to replicate globe.gl's 3D spike visualizations -- Atlas's data layers already work
- Globe mode should not auto-rotate or animate -- this is an intelligence tool, not a screensaver

---

## 3. Anno 1800 Aesthetic -- Implementation Techniques

The goal: Atlas's globe should feel **warm, alive, atmospheric, crafted** -- not cold and technical. Five specific techniques, ordered by impact.

### Technique 1: Atmospheric Haze (Horizon Glow)

**What it looks like**: A soft blue-teal glow where the globe meets the dark background. The Earth appears to have a thin atmosphere.

**How MapLibre implements it**: Native sky/atmosphere style properties.

```json
{
  "sky": {
    "sky-color": "#0a0f1a",
    "horizon-color": "#1a4060",
    "fog-color": "#0a0f1a",
    "sky-horizon-blend": 0.5,
    "horizon-fog-blend": 0.8,
    "atmosphere-blend": 0.85
  }
}
```

**Tuning for warmth**: Instead of cold blue `#1a4060`, use warm teal `#1a5050` or even amber-tinted `#2a4040` for the horizon color. This makes the atmosphere feel like golden-hour light rather than clinical satellite imagery.

**Performance**: Negligible. Built into MapLibre's rendering pipeline.

**Reference**: [MapLibre Globe with Atmosphere Example](https://maplibre.org/maplibre-gl-js/docs/examples/display-a-globe-with-an-atmosphere/)

### Technique 2: Warm Data Glow (Bloom on Hotspots)

**What it looks like**: Bright data points (crisis zones, high-activity regions) emit a soft glow that bleeds into surrounding pixels. The hotspots feel like they're radiating energy.

**How to implement in Atlas**: Atlas already has a HeatmapLayer with a blue-to-red colorRange. The current colorRange's opacity values create a natural glow effect on the flat map. On the globe, the heatmap paints directly onto the sphere surface, which gives it an organic, "glowing from within" quality.

**Enhancement**: Increase the radiusPixels slightly in globe mode (the sphere curvature makes the heatmap look tighter). Consider a CSS `filter: blur(1px)` on the canvas when in globe mode for a subtle softness.

**Performance**: Negligible (already implemented, just tuning values).

### Technique 3: Day/Night Terminator (Already Exists)

**What it looks like**: The night side of the globe is darker, creating a natural light gradient across the Earth.

**Atlas already has this**: `frontend-v2/src/layers/TerminatorLayer.ts` renders a solar terminator. On the flat map, it draws a semi-transparent dark polygon over the night hemisphere. On the MapLibre globe, this same polygon will wrap around the sphere naturally.

**Enhancement for warmth**: Add a thin warm-orange band at the terminator boundary (sunrise/sunset line). This is the single most effective technique for making a globe feel "alive" rather than clinical.

```typescript
// In TerminatorLayer, add a second polygon for the twilight band
// with a warm orange fill (#ff8040, opacity 0.15)
// between the day/night boundary +-6 degrees
```

**Performance**: Negligible (one additional polygon).

### Technique 4: Subtle Star Field (CSS Background)

**What it looks like**: Tiny points of light behind the globe, barely visible but giving the sense of space.

**Simplest implementation**: A CSS background on the globe panel using a radial gradient with scattered white dots. No WebGL needed.

```css
.terminal-panel.radar {
  background:
    radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.3), transparent),
    radial-gradient(1px 1px at 70% 80%, rgba(255,255,255,0.2), transparent),
    radial-gradient(1px 1px at 45% 15%, rgba(255,255,255,0.25), transparent),
    /* ... 20-30 more scattered points ... */
    #050510;
}
```

**Alternative**: Use a pre-rendered tiny star texture as `background-image`. Less CSS but same effect.

**Performance**: Zero -- pure CSS, no JS/WebGL involvement.

### Technique 5: Vignette Effect (Focus the Eye)

**What it looks like**: Darkening around the edges of the globe panel, naturally drawing the eye to the center (the globe itself).

**Implementation**: CSS overlay with pointer-events disabled.

```css
.globe-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    ellipse at center,
    transparent 50%,
    rgba(10, 15, 26, 0.4) 80%,
    rgba(10, 15, 26, 0.8) 100%
  );
  z-index: 1;
}
```

**Performance**: Zero -- pure CSS compositing.

### Recommended Globe Color Palette

| Element | Color | Notes |
|---------|-------|-------|
| Space background | `#050510` | Near-black with slight blue tint |
| Atmosphere horizon | `#1a5050` | Warm teal (not cold blue) |
| Ocean (basemap) | Already dark via CARTO dark-matter | No change needed |
| Land (basemap) | Already subtle via CARTO dark-matter | No change needed |
| Heatmap low | `#141e50` | Deep blue (existing) |
| Heatmap mid | `#b48228` | Warm gold (existing) |
| Heatmap high | `#e61e0a` | Red-orange (existing) |
| Arc flows | `#3b82f6` to `#ef4444` | Blue to red (existing) |
| Vignette edge | `rgba(10, 15, 26, 0.8)` | Matches app background |

### What Creates the "Anno 1800 Feel"

The warmth comes from **four properties working together**:

1. **Warm horizon** -- teal/amber atmosphere instead of cold blue
2. **Twilight band** -- orange glow at the day/night boundary
3. **Vignette** -- darkened edges focus the eye and create intimacy
4. **Living motion** -- existing data updates (heatmap pulses, arc animations) provide the organic movement

What to **avoid**:
- Auto-rotation (screensaver feel, not intelligence tool)
- Particle systems (complex, performance-heavy, distracting from actual data)
- Heavy bloom/post-processing (fights with data readability)
- Star field in the data area (competes with signal visualization)

---

## 4. Phase 3 Recommended Sequence

### Order of Implementation

| # | Deliverable | Effort | Visual Impact | Dependencies |
|---|-------------|--------|---------------|-------------|
| 1 | **3D Globe Toggle** | 5h (~1-2 sessions) | Very High | None |
| 2 | **Aircraft Layer** | 8h (~2 sessions) | Very High | None |
| 3 | **Maritime Layer** | 11h (~3 sessions) | High | None |
| 4 | **Markets Panel** | 13h (~3-4 sessions) | Medium | None |

**Total: ~37 hours / 10-12 sessions**

### Why This Order

**Globe first (not aircraft first)**:

1. **Lowest effort, highest transformation** -- 5 hours to fundamentally change how Atlas feels. A single `setProjection()` call plus atmosphere config turns Atlas from "a dashboard with a map" into "a globe-based intelligence system." All existing layers (heatmap, arcs, scatterplot, terminator) work immediately on the globe.

2. **Sets the visual foundation** -- Aircraft and vessel layers look dramatically more impressive on a 3D globe than on a flat map. Implementing them after the globe means they benefit from the atmospheric context on day one.

3. **Validates the approach** -- If MapLibre globe has any issues with existing layers, it's better to discover them before building new layers on top.

4. **Emotional impact** -- The first time a user opens Atlas and sees the Earth rotating into view with atmospheric haze and heatmap data glowing on the surface, the product makes an impression. This is the "Windy.com for narratives" moment.

**Aircraft second**: OpenSky Network is the simplest API (REST, JSON, no auth required for anonymous). Planes moving across the globe is immediately impressive and universally understood. The IconLayer with heading rotation is straightforward.

**Maritime third**: AISStream.io WebSocket relay is slightly more complex infrastructure than REST polling. Vessel type classification adds analytical depth (cargo vs tanker vs military). Shipping lane visualization through chokepoints (Suez, Hormuz, Malacca) tells a geopolitical story.

**Markets last**: Most complex integration (4 APIs to orchestrate, panel UI instead of map layer, rate limit juggling). Also lowest visual impact on the globe itself since markets display in a status bar, not as map markers.

### Dependencies and Parallelism

All four deliverables are independent -- they could theoretically be implemented in parallel by different agents. However, the sequential order above maximizes cumulative visual impact at each checkpoint:

- After step 1: Atlas has a 3D globe with all existing layers
- After step 2: Planes are flying across the globe
- After step 3: Ships are moving through shipping lanes
- After step 4: Market data contextualizes the narrative signals

Each checkpoint is a shippable product improvement.

---

## Appendix: Key References

### World Monitor
- [GitHub Repository](https://github.com/koala73/worldmonitor)
- [Documentation](https://github.com/koala73/worldmonitor/blob/main/docs/DOCUMENTATION.md)
- [DeepWiki Analysis](https://deepwiki.com/koala73/worldmonitor)

### MapLibre Globe
- [Globe with Atmosphere Example](https://maplibre.org/maplibre-gl-js/docs/examples/display-a-globe-with-an-atmosphere/)
- [Globe Developer Guide](https://github.com/maplibre/maplibre-gl-js/blob/main/developer-guides/globe.md)
- [Sky Style Spec](https://maplibre.org/maplibre-style-spec/sky/)
- [Stadia Maps Globe Tutorial](https://docs.stadiamaps.com/tutorials/3d-globe-view-with-maplibre-gl-js/)

### Deck.gl + MapLibre Globe Integration
- [deck.gl v9.1 What's New (globe support)](https://deck.gl/docs/whats-new)
- [deck.gl + MapLibre Guide](https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre)

### Aesthetic References
- [How We Built the GitHub Globe](https://github.blog/engineering/engineering-principles/how-we-built-the-github-globe/)
- [Stripe Globe](https://stripe.com/blog/globe)
- [earth.nullschool.net Source](https://github.com/cambecc/earth)
- [WebGL Wind (GPU particles)](https://github.com/mapbox/webgl-wind)
- [Three.js Atmospheric Glow](https://stemkoski.github.io/Three.js/Shader-Glow.html)
- [three-globe Solar Terminator](https://github.com/vasturiano/three-globe/blob/master/example/solar-terminator/index.html)
