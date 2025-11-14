# Observatory Global - Visualization & UX Flow

**Document Version:** 1.0
**Date:** 2025-01-14
**Purpose:** Complete specification of dual-layer visualization architecture and user experience flows

---

## Table of Contents

1. [Overview](#overview)
2. [Layer Architecture](#layer-architecture)
3. [User Interaction Flows](#user-interaction-flows)
4. [Component Hierarchy](#component-hierarchy)
5. [Data Flow](#data-flow)
6. [Animation Specifications](#animation-specifications)
7. [State Management](#state-management)
8. [Performance Requirements](#performance-requirements)
9. [Debugging Guide](#debugging-guide)
10. [Implementation Checklist](#implementation-checklist)

---

## Overview

### Vision Statement
> "Visualize the traffic of global information the same way a weather radar shows storms. Users should see WHERE information is heating up (heatmap) and HOW narratives travel between regions (flows) simultaneously."

### Key Design Principles

1. **Dual Perception** - Two complementary views of the same data
2. **Unified Control** - Single set of filters applies to both layers
3. **Progressive Disclosure** - Show essentials first, details on demand
4. **Live Feeling** - Animations, updates, breathing effects
5. **Clarity Over Decoration** - Visual hierarchy serves understanding

---

## Layer Architecture

### Layer Stack (Z-Index Order)

```
┌─────────────────────────────────────────┐
│  5. Labels & UI Overlays (z-index: 50) │
│     • Country names                      │
│     • Tooltips                           │
│     • Legend                             │
├─────────────────────────────────────────┤
│  4. Country Centroids (z-index: 40)     │
│     • Pulsing circles                    │
│     • Click targets                      │
├─────────────────────────────────────────┤
│  3. Flow Lines (z-index: 30)            │
│     • Bezier curves                      │
│     • Animated particles                 │
├─────────────────────────────────────────┤
│  2. Heatmap (z-index: 20)               │
│     • H3 hexagons                        │
│     • Gaussian blur                      │
├─────────────────────────────────────────┤
│  1. Mapbox Base Map (z-index: 10)       │
│     • dark-v11 style                     │
│     • Globe projection                   │
└─────────────────────────────────────────┘
```

### Layer Visibility Matrix

| View Mode | Mapbox | Heatmap | Flows | Centroids | Labels |
|-----------|--------|---------|-------|-----------|--------|
| **Classic Only** | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Heatmap Only** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Combined** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## User Interaction Flows

### Flow 1: Initial Page Load

```
User lands on page
    ↓
API health check (200ms)
    ↓
Fetch default data (/v1/flows with default countries)
    ↓
Render Classic View
    ├→ FlowLayer: Calculate flow lines
    ├→ HotspotLayer: Position centroids
    └→ HotspotsTable: Display country list
    ↓
Auto-refresh starts (5 min interval)
```

**Expected Time:** < 2 seconds from load to interactive

### Flow 2: Toggle to Heatmap View

```
User clicks "Heatmap View" button
    ↓
viewMode state updates to 'heatmap'
    ↓
Fetch hexmap data (/v1/hexmap?time_window=24h&zoom=2&k_ring=2)
    ↓
Unmount Classic layers (FlowLayer, HotspotLayer)
    ↓
Mount HexagonHeatmapLayer
    ├→ Receive hexmapData from store
    ├→ Create H3HexagonLayer with data
    ├→ Apply Gaussian blur (filter: blur(12px))
    └→ Sync viewState with Mapbox camera
    ↓
Render hexagons with color gradient
```

**Expected Time:** < 500ms from click to visible hexagons

### Flow 3: Combined View (Future Enhancement)

```
User enables both toggles
    ↓
viewMode = 'combined'
    ↓
Fetch both /v1/flows AND /v1/hexmap
    ↓
Render all layers simultaneously
    ├→ Heatmap (background intensity)
    ├→ Flow lines (narrative connections)
    └→ Centroids (interaction points)
```

### Flow 4: Country Filter Selection

```
User opens country filter dropdown
    ↓
Display list of available countries (from flowsData.hotspots)
    ↓
User selects/deselects countries
    ↓
selectedCountries state updates
    ↓
Trigger data refetch with countries parameter
    ↓
Update visualization with filtered data
```

**Expected Time:** < 300ms from selection to visual update

### Flow 5: Time Window Change

```
User selects different time window (e.g., 6h → 24h)
    ↓
timeWindow state updates
    ↓
Trigger appropriate API call
    ├→ Classic: /v1/flows?time_window=24h
    └→ Heatmap: /v1/hexmap?time_window=24h&zoom=2&k_ring=2
    ↓
Smooth transition between states
    └→ Fade out old data
    └→ Fade in new data
```

### Flow 6: "Why is this heating up?" Interaction

```
User hovers over high-intensity region
    ↓
Identify country under cursor
    ↓
Fetch country details from current data
    ↓
Display tooltip with:
    ├→ Country name
    ├→ Intensity score (0-1)
    ├→ Top 3-5 themes (GDELT codes → human labels)
    ├→ Sentiment (tone score)
    ├→ Key actors (persons, organizations)
    └→ Sample headlines
```

**Expected Time:** < 50ms from hover to tooltip display

---

## Component Hierarchy

### React Component Tree

```
<App>
  └─ <Home>
       ├─ <MapContainer>
       │    ├─ <Map> {/* Mapbox */}
       │    │    ├─ <NavigationControl />
       │    │    └─ {viewMode === 'classic' && (
       │    │         <>
       │    │           <FlowLayer />
       │    │           <HotspotLayer />
       │    │         </>
       │    │       )}
       │    │
       │    ├─ {viewMode === 'heatmap' && (
       │    │    <HexagonHeatmapLayer viewState={viewState} />
       │    │  )}
       │    │
       │    ├─ <ViewModeToggle />
       │    ├─ <TimeWindowSelector />
       │    ├─ <CountryFilter />
       │    ├─ <AutoRefreshControl />
       │    ├─ <CountrySidebar />
       │    └─ <DataStatusBar />
       │
       └─ <HotspotsTable />
```

### Component Responsibilities

**MapContainer** (`frontend/src/components/map/MapContainer.tsx`)
- Owns viewState (camera position)
- Orchestrates layer visibility
- Manages data fetching
- Coordinates all child components

**HexagonHeatmapLayer** (`frontend/src/components/map/HexagonHeatmapLayer.tsx`)
- Renders DeckGL overlay
- Creates H3HexagonLayer
- Applies visual styling (colors, blur, opacity)
- Syncs with Mapbox viewState

**FlowLayer** (`frontend/src/components/map/FlowLayer.tsx`)
- Renders flow lines as Mapbox layers
- Calculates Bezier curves
- Handles line styling (color, width, opacity)

**HotspotLayer** (`frontend/src/components/map/HotspotLayer.tsx`)
- Renders country centroids
- Handles pulsing animations
- Manages click/hover interactions

**HotspotsTable** (`frontend/src/components/map/HotspotsTable.tsx`)
- Displays country list sorted by intensity
- Shows top themes per country
- Synchronized with map data (same source)

---

## Data Flow

### Zustand Store Structure

**File:** `frontend/src/store/mapStore.ts`

```typescript
interface MapState {
  // Data
  flowsData: FlowsResponse | null        // Classic view data
  hexmapData: HexmapResponse | null      // Heatmap view data
  loading: boolean
  error: string | null
  lastUpdate: Date | null

  // Filters
  timeWindow: TimeWindow                  // '1h' | '6h' | '24h' | '7d'
  selectedCountries: string[]             // ['US', 'CO', 'BR']
  autoRefresh: boolean
  refreshInterval: number                 // milliseconds

  // UI State
  viewMode: ViewMode                      // 'classic' | 'heatmap' | 'combined'
  selectedHotspot: CountryHotspot | null
  hoveredFlow: string | null

  // Actions
  setViewMode: (mode) => void
  setTimeWindow: (window) => void
  setSelectedCountries: (countries) => void
  toggleCountry: (country) => void
  fetchFlowsData: () => Promise<void>
  fetchHexmapData: () => Promise<void>
}
```

### Data Transformation Pipeline

```
Backend API Response
    ↓
SignalsService.fetch_trending_signals()
    ↓
{
  "US": ([Topic, Topic, ...], timestamp),
  "CO": ([Topic, Topic, ...], timestamp),
  ...
}
    ↓
FlowDetector.detect_flows()
    ↓
{
  hotspots: [{country_code, intensity, top_themes, ...}],
  flows: [{source, target, strength, ...}],
  metadata: {...}
}
    ↓
Frontend mapStore.flowsData
    ↓
React Components
```

### API Endpoints Used

**Classic View:**
```http
GET /v1/flows?time_window=24h&countries=US,CO,BR&threshold=0.5
```

**Heatmap View:**
```http
GET /v1/hexmap?time_window=24h&zoom=2&k_ring=2&countries=US,CO,BR
```

**Future: Topic/Entity View:**
```http
GET /v1/narratives/topic?theme=ECON_INFLATION&time_window=24h
```

---

## Animation Specifications

### 1. Pulsing Centroids

**Purpose:** Indicate real-time activity, draw attention to hotspots

**Implementation:**
```javascript
// Breathing effect using sine wave
const time = Date.now() * 0.001 // Convert to seconds
const pulseScale = 1.0 + 0.2 * Math.sin(time * 2.0)
const pulseOpacity = 0.6 + 0.4 * Math.sin(time * 2.0)

// Apply to circle layer
circle.setRadius(baseRadius * pulseScale)
circle.setOpacity(baseOpacity * pulseOpacity)
```

**Parameters:**
- Base radius: 8px
- Pulse amplitude: 20% (±1.6px)
- Frequency: 2 Hz (1 complete cycle per 500ms)
- Base opacity: 0.6
- Opacity range: 0.6 - 1.0

### 2. Animated Flow Particles

**Purpose:** Show direction and speed of narrative flow

**Implementation:**
```javascript
class FlowParticle {
  constructor(pathPoints, speed) {
    this.path = pathPoints           // Bezier curve points
    this.progress = 0.0              // 0 to 1
    this.speed = speed               // 0.1 to 1.0
  }

  update(deltaTime) {
    this.progress += deltaTime * this.speed
    if (this.progress > 1.0) {
      this.progress = 0.0  // Loop
    }
  }

  getPosition() {
    return interpolateBezier(this.path, this.progress)
  }
}

// Render loop
function animate() {
  particles.forEach(p => {
    p.update(deltaTime)
    renderParticle(p.getPosition())
  })
  requestAnimationFrame(animate)
}
```

**Parameters:**
- Particle count per flow: 3-5
- Particle size: 3px
- Particle color: Same as flow line, higher opacity
- Speed: 0.2 (20% of path per second)
- Trail length: 5 particles

### 3. Heatmap Gradient Transitions

**Purpose:** Smooth visual changes when data updates

**Implementation:**
```javascript
// Linear interpolation between old and new tone values
function lerpColor(oldTone, newTone, progress) {
  const oldColor = getToneColor(oldTone)
  const newColor = getToneColor(newTone)

  return {
    r: oldColor.r + (newColor.r - oldColor.r) * progress,
    g: oldColor.g + (newColor.g - oldColor.g) * progress,
    b: oldColor.b + (newColor.b - oldColor.b) * progress,
  }
}

// Ease-in-out timing function
function easeInOutCubic(t) {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2
}
```

**Parameters:**
- Transition duration: 800ms
- Easing: Cubic ease-in-out
- Update trigger: On data refetch

### 4. Temporal Glow

**Purpose:** Highlight recently updated regions

**Implementation:**
```javascript
// Calculate recency factor
const timeSinceUpdate = Date.now() - signal.timestamp
const halfLife = 15 * 60 * 1000  // 15 minutes in ms
const recencyFactor = Math.exp(-timeSinceUpdate / halfLife)

// Apply to opacity
const finalOpacity = baseOpacity * (1.0 + recencyFactor * 0.5)

// Apply to blur radius
const finalBlur = baseBlur + recencyFactor * 8  // Extra 8px blur when fresh
```

**Parameters:**
- Half-life: 15 minutes (matches GDELT publish frequency)
- Opacity boost: Up to +50%
- Blur boost: Up to +8px
- Minimum opacity: 0.3

---

## State Management

### ViewMode State Machine

```
┌──────────┐
│ classic  │ ◄──┐
└─────┬────┘    │
      │         │
      ├── Toggle to Heatmap
      │         │
      ▼         │
┌──────────┐    │
│ heatmap  │ ───┘
└─────┬────┘
      │
      ├── Toggle to Combined (future)
      │
      ▼
┌──────────┐
│ combined │
└──────────┘
```

### Filter Synchronization

All filters apply to both views:

```typescript
// When user changes time window
setTimeWindow('6h')
  ↓
if (viewMode === 'classic') {
  fetchFlowsData()   // Uses timeWindow from state
} else if (viewMode === 'heatmap') {
  fetchHexmapData()  // Uses same timeWindow
}
```

### Auto-Refresh Logic

```typescript
useEffect(() => {
  if (!autoRefresh) return

  const interval = setInterval(() => {
    if (viewMode === 'classic') {
      fetchFlowsData()
    } else {
      fetchHexmapData()
    }
  }, refreshInterval)  // Default: 5 minutes

  return () => clearInterval(interval)
}, [autoRefresh, refreshInterval, viewMode])
```

---

## Performance Requirements

### Rendering Performance

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Initial Load | < 2s | ~1.5s | ✅ |
| Layer Toggle | < 100ms | ~50ms | ✅ |
| API Response | < 500ms | ~200ms | ✅ |
| Frame Rate | 60 FPS | Variable | ⚠️ Heatmap not rendering |
| Memory Usage | < 200 MB | ~150 MB | ✅ |

### Data Volume Constraints

**Current (Placeholder Data):**
- 10 countries
- 5 topics per country
- ~50 data points total

**Target (Real GDELT):**
- 10-200 countries
- 50 themes per country
- 500-10,000 data points total

**Optimization Strategy:**
- Server-side aggregation (don't send raw signals)
- Client-side caching (5-min TTL in memory)
- Lazy loading (only fetch visible regions)
- Level of detail (reduce complexity at low zoom)

### Bundle Size Targets

| Asset | Current | Target | Budget |
|-------|---------|--------|--------|
| index.js | 985 KB | < 1 MB | ✅ |
| mapbox-gl.js | 1,663 KB | N/A | External |
| deck.gl (future) | ? | < 500 KB | TBD |
| Total | ~2.6 MB | < 3 MB | ✅ |

---

## Debugging Guide

### Issue: Heatmap Not Rendering

**Symptoms:**
- Heatmap toggle works
- API returns valid data
- No hexagons visible
- No console errors

**Debugging Steps:**

#### Step 1: Verify Data Flow
```javascript
// Add to HexagonHeatmapLayer.tsx
useEffect(() => {
  console.group('🗺️ HexagonHeatmapLayer Debug')
  console.log('Mounted:', !!hexmapData)
  console.log('Hexes count:', hexmapData?.hexes?.length)
  console.log('First hex:', hexmapData?.hexes?.[0])
  console.log('Layers:', layers)
  console.groupEnd()
}, [hexmapData, layers])
```

**Expected Output:**
```
🗺️ HexagonHeatmapLayer Debug
  Mounted: true
  Hexes count: 47
  First hex: {h3_index: "8226effffffffff", intensity: 1.0}
  Layers: [H3HexagonLayer]
```

#### Step 2: Verify DeckGL Mounting
```javascript
// Add to HexagonHeatmapLayer.tsx return statement
return (
  <div>
    <div style={{position: 'absolute', top: 0, left: 0, zIndex: 100, background: 'white', padding: '10px'}}>
      Debug: {hexmapData?.hexes?.length || 0} hexes
    </div>
    <DeckGL ... />
  </div>
)
```

**Expected:** Text overlay showing hex count

#### Step 3: Test Minimal Configuration
```javascript
// Simplify H3HexagonLayer to minimal config
new H3HexagonLayer({
  id: 'h3-test',
  data: [{h3_index: '8226effffffffff', value: 1}],  // Hardcoded hex over US
  getHexagon: d => d.h3_index,
  getFillColor: [255, 0, 0, 255],  // Solid red
  filled: true,
  extruded: false,
})
```

**Expected:** Single red hexagon over central US

#### Step 4: Check WebGL Context
```javascript
// Add to MapContainer.tsx useEffect
useEffect(() => {
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
  console.log('WebGL available:', !!gl)
  if (gl) {
    console.log('WebGL vendor:', gl.getParameter(gl.VENDOR))
    console.log('WebGL renderer:', gl.getParameter(gl.RENDERER))
  }
}, [])
```

**Expected:** WebGL available: true

#### Step 5: Inspect DOM
```
Chrome DevTools → Elements → Search for "deck-canvas"
```

**Expected:** `<canvas class="deck-canvas">` element exists

#### Step 6: Check H3 Index Validity
```javascript
import { h3IsValid, h3ToGeo } from 'h3-js'

hexmapData.hexes.forEach(hex => {
  const valid = h3IsValid(hex.h3_index)
  console.log(`${hex.h3_index}: valid=${valid}`)
  if (valid) {
    const [lat, lng] = h3ToGeo(hex.h3_index)
    console.log(`  → lat=${lat}, lng=${lng}`)
  }
})
```

**Expected:** All hexes valid, coordinates reasonable

### Common Issues & Solutions

**Issue:** deck.gl not in bundle
**Solution:** Rebuild with `--no-cache`, verify package.json

**Issue:** ViewState mismatch
**Solution:** Ensure DeckGL viewState exactly matches Mapbox camera

**Issue:** Layer not pickable
**Solution:** Set `pickable: true` in layer config

**Issue:** Blur hiding hexagons
**Solution:** Temporarily remove `filter: 'blur(12px)'` to test

**Issue:** Coordinate system mismatch
**Solution:** Verify `coordinateSystem: 0` (COORDINATE_SYSTEM.LNGLAT)

---

## Implementation Checklist

### Phase 1: Heatmap Rendering (Current Priority)
- [ ] Verify @deck.gl/react properly bundled
- [ ] Add comprehensive debug logging
- [ ] Test minimal H3HexagonLayer configuration
- [ ] Validate H3 index strings from API
- [ ] Check WebGL context availability
- [ ] Inspect DOM for deck-canvas element
- [ ] Test without blur filter
- [ ] Verify viewState synchronization
- [ ] Document findings in Issue #13

### Phase 2: Visual Polish
- [ ] Implement pulsing centroids animation
- [ ] Add flow particle animations
- [ ] Implement heatmap gradient transitions
- [ ] Add temporal glow effect
- [ ] Test performance at 60 FPS
- [ ] Optimize render loop

### Phase 3: Combined View
- [ ] Add 'combined' viewMode state
- [ ] Fetch both datasets simultaneously
- [ ] Render all layers with proper z-index
- [ ] Test layer interactions
- [ ] Ensure performance targets met

### Phase 4: Advanced Interactions
- [ ] Implement "Why is this heating up?" tooltip
- [ ] Add zoom-to-region functionality
- [ ] Implement timeline scrubber
- [ ] Add theme/entity search
- [ ] Create keyboard shortcuts

### Phase 5: Production Hardening
- [ ] Error boundaries for each layer
- [ ] Fallback UI for WebGL unavailable
- [ ] Loading states for all data fetches
- [ ] Retry logic for failed requests
- [ ] Analytics tracking for user interactions

---

## Next Steps for Visualization Specialists

1. **Immediate:** Debug heatmap rendering using steps in this document
2. **Short-term:** Implement animation specifications
3. **Medium-term:** Build combined view architecture
4. **Long-term:** Advanced interactions and performance optimization

---

## References

- **deck.gl Documentation:** https://deck.gl/docs
- **H3 Spatial Index:** https://h3geo.org/
- **Mapbox GL JS:** https://docs.mapbox.com/mapbox-gl-js/
- **Issue #13:** Heatmap rendering bug
- **Issue #15:** Dual-layer visualization architecture
- **GDELT Schema Analysis:** `/docs/GDELT_SCHEMA_ANALYSIS.md`

---

**Document Status:** Complete
**Next Review:** After heatmap rendering issue resolved
**Maintained By:** Frontend Visualization Team + Orchestrator
