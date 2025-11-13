# ADR-0003: Hexagonal Tile Heatmap Architecture

**Status**: Proposed
**Date**: 2025-01-13
**Decision Makers**: Pedro Villegas, Development Team
**Tags**: visualization, geospatial, architecture, performance

## Context

Observatory Global currently visualizes information flow using country-centric circles (centroids) connected by arcs. While functional, this approach has limitations:

1. **Political boundary dependency**: Visualization is constrained by country borders
2. **Low spatial resolution**: Can't show regional variations within large countries
3. **Lacks organic feel**: Centroids don't create the "alive" blob effect
4. **Poor at visualizing density**: Can't show how information clusters across borders

We need a hexagonal tile-based heatmap system that:
- Creates smooth "blob" visualizations (like weather radar or traffic heatmaps)
- Adapts to zoom levels (showing appropriate hex resolution)
- Works seamlessly with Mapbox GL
- Feels "alive" with dynamic intensity
- Shows information flow across space, not just between countries
- Performs well (60 FPS on modern browsers)

## Research: Hexagonal Mapping Approaches

### 1. H3 (Uber's Hexagonal Hierarchical Spatial Index)

**Description**: Industry-standard geospatial indexing system with 16 hierarchical resolution levels.

**Pros**:
- ✅ Production-proven at scale (Uber, Foursquare, Mapbox)
- ✅ Multi-resolution hierarchy (0-15 levels)
- ✅ Efficient spatial queries (neighbors, containment)
- ✅ JavaScript library available (`h3-js`)
- ✅ Native integration with deck.gl (H3HexagonLayer)
- ✅ Deterministic hexagon IDs (cacheable)
- ✅ Global coverage, no singularities

**Cons**:
- ⚠️ Learning curve (H3 index concepts)
- ⚠️ Requires deck.gl for optimal rendering (adds dependency)
- ⚠️ Hexagons are not perfect (pentagonal adjustments at icosahedron vertices)

**Performance**:
- Can render 100k+ hexagons at 60 FPS with deck.gl
- Spatial queries: O(1) for neighbors, O(log n) for range

**Use Case Fit**: ⭐⭐⭐⭐⭐ (Best overall)

---

### 2. Turf.js Hex Grid

**Description**: Simple hexagon grid generation using Turf.js geospatial library.

**Pros**:
- ✅ Already in `package.json` (`@turf/turf`)
- ✅ Simple API (`turf.hexGrid(bbox, cellSize)`)
- ✅ GeoJSON output (works with Mapbox sources)
- ✅ No additional dependencies
- ✅ Easy to understand

**Cons**:
- ⚠️ No hierarchical resolution (must regenerate grid on zoom)
- ⚠️ No spatial indexing (slow neighbor queries)
- ⚠️ Projection distortion at global scale
- ⚠️ Not optimized for large grids (>10k hexes)
- ⚠️ No built-in intensity aggregation

**Performance**:
- ~1,000 hexagons: Good (60 FPS)
- ~10,000 hexagons: Degraded (30-40 FPS)
- ~100,000 hexagons: Poor (<15 FPS)

**Use Case Fit**: ⭐⭐⭐ (Good for MVP, limited scalability)

---

### 3. D3-hexbin

**Description**: D3.js hexagonal binning for 2D projections.

**Pros**:
- ✅ Well-documented, mature library
- ✅ Good for static visualizations
- ✅ Works with custom projections

**Cons**:
- ⚠️ Designed for SVG, not WebGL
- ⚠️ Poor performance at scale (SVG rendering)
- ⚠️ Not optimized for map tiles
- ⚠️ Requires D3.js geo projections (complexity)
- ⚠️ Not compatible with Mapbox GL directly

**Performance**:
- Limited to ~1,000 hexagons for interactive maps

**Use Case Fit**: ⭐ (Not recommended for interactive maps)

---

### 4. Custom WebGL Shaders

**Description**: Low-level hexagon rendering using WebGL fragment shaders.

**Pros**:
- ✅ Maximum performance (GPU-accelerated)
- ✅ Full control over rendering
- ✅ Can achieve unique visual effects

**Cons**:
- ⚠️ High implementation complexity
- ⚠️ Requires deep WebGL knowledge
- ⚠️ Must handle hexagon geometry generation manually
- ⚠️ No spatial indexing out of the box
- ⚠️ Maintenance burden
- ⚠️ Browser compatibility issues

**Performance**:
- Millions of hexagons possible, but complex to implement

**Use Case Fit**: ⭐⭐ (Overkill for MVP, consider for v2)

---

### 5. Mapbox GL Custom Layers (with H3)

**Description**: Combine Mapbox GL's custom layer API with H3 for hybrid approach.

**Pros**:
- ✅ Leverages existing Mapbox setup
- ✅ Can mix with current map layers
- ✅ Uses H3's spatial efficiency
- ✅ Moderate complexity

**Cons**:
- ⚠️ Requires understanding Mapbox GL internals
- ⚠️ Less performant than deck.gl
- ⚠️ Manual hexagon rendering logic

**Performance**:
- ~10,000 hexagons: Good
- ~50,000+ hexagons: Requires optimization

**Use Case Fit**: ⭐⭐⭐⭐ (Viable alternative to deck.gl)

---

## Decision

**Recommended Approach**: **H3 + deck.gl** (with Mapbox GL base layer)

**Rationale**:
1. **Production-ready**: Battle-tested by Uber, Mapbox, Foursquare
2. **Performance**: Can render 100k+ hexagons smoothly
3. **Multi-resolution**: 16 zoom levels map naturally to map zoom
4. **Ecosystem**: Rich tooling, examples, community support
5. **Future-proof**: Industry standard for geospatial hexagons

**Architecture Stack**:
```
Mapbox GL (base map, roads, labels)
    ↓
deck.gl (hexagon overlay)
    ↓
H3-js (spatial indexing)
    ↓
Backend API (hex intensity data)
```

**Alternative for MVP**: **Turf.js hexGrid** (simpler, lower performance ceiling)

---

## Technical Architecture

### 1. Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND                               │
├─────────────────────────────────────────────────────────────┤
│  1. Fetch trending topics per country                       │
│  2. Geocode topics to lat/lng (or use country centroids)    │
│  3. Convert lat/lng to H3 cells at resolution R             │
│  4. Aggregate intensity per H3 cell                         │
│  5. Return { h3_index: hex_id, intensity: 0-1 }             │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND                               │
├─────────────────────────────────────────────────────────────┤
│  1. Receive hex intensity data                              │
│  2. Determine resolution based on zoom level                │
│  3. Create deck.gl H3HexagonLayer                           │
│  4. Apply color scale (intensity → color)                   │
│  5. Render at 60 FPS                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. H3 Resolution Mapping

H3 has 16 resolutions (0-15). Map zoom levels to H3 resolutions:

| Map Zoom | H3 Res | Hex Edge Length | Use Case          | Hexes (Global) |
|----------|--------|-----------------|-------------------|----------------|
| 0-2      | 1      | ~1,107 km       | Global overview   | ~840           |
| 3-4      | 2      | ~418 km         | Continental       | ~5,880         |
| 5-6      | 3      | ~158 km         | Country/region    | ~41,160        |
| 7-8      | 4      | ~59 km          | State/province    | ~288,120       |
| 9-10     | 5      | ~22 km          | City clusters     | ~2M            |
| 11-12    | 6      | ~8 km           | Urban areas       | ~14M           |
| 13+      | 7+     | <3 km           | Neighborhoods     | ~100M+         |

**Recommendation**: Use resolutions 2-6 for Observatory Global (Iterations 2-3).

---

### 3. Intensity Aggregation Algorithm

**Backend**: Convert country-level data to hex-level intensity.

**Approach 1: Simple Geographic Spread** (Iteration 2)
```python
from h3 import h3

def country_to_hexes(country_code: str, intensity: float, resolution: int):
    """
    Spread country intensity across hexagons covering the country.
    """
    # Get country bounding box or geometry
    country_geom = get_country_geometry(country_code)

    # Polyfill: get all H3 cells covering the polygon
    hexes = h3.polyfill(country_geom, resolution, geo_json_conformant=True)

    # Assign intensity to each hex (uniform distribution)
    return [
        {"h3_index": hex_id, "intensity": intensity}
        for hex_id in hexes
    ]
```

**Approach 2: Weighted by Population Density** (Iteration 3)
```python
def country_to_hexes_weighted(country_code: str, intensity: float, resolution: int):
    """
    Weight intensity by population density (urban areas hotter).
    """
    hexes = h3.polyfill(get_country_geometry(country_code), resolution)

    # Get population density per hex from external dataset
    pop_density = get_population_density(hexes)

    # Normalize so sum(weights) = 1
    total_pop = sum(pop_density.values())

    return [
        {
            "h3_index": hex_id,
            "intensity": intensity * (pop_density[hex_id] / total_pop)
        }
        for hex_id in hexes
    ]
```

**Approach 3: Topic Geocoding** (Future)
```python
def topics_to_hexes(topics: List[str], resolution: int):
    """
    Geocode each trending topic to specific locations.
    Example: "San Francisco election" → [37.77, -122.42] → H3 cell
    """
    hex_intensities = defaultdict(float)

    for topic in topics:
        # Use NER + geocoding API
        locations = extract_locations(topic)

        for lat, lng in locations:
            hex_id = h3.geo_to_h3(lat, lng, resolution)
            hex_intensities[hex_id] += 1.0

    # Normalize
    max_intensity = max(hex_intensities.values())
    return [
        {"h3_index": hex_id, "intensity": val / max_intensity}
        for hex_id, val in hex_intensities.items()
    ]
```

**Iteration 2 Decision**: Use Approach 1 (simple spread).
**Iteration 3 Enhancement**: Add Approach 2 (population weighting).
**Future**: Approach 3 (topic geocoding with NER).

---

### 4. Blob Effect: Smoothing & Interpolation

**Challenge**: Raw hex tiles look discrete. We want smooth, organic blobs.

**Technique 1: Hexagon Elevation (deck.gl)**
```typescript
new H3HexagonLayer({
  id: 'hex-heatmap',
  data: hexData,
  getHexagon: d => d.h3_index,
  getFillColor: d => intensityToColor(d.intensity),
  getElevation: d => d.intensity * 5000, // Height in meters
  elevationScale: 1,
  extruded: true, // 3D columns
  coverage: 0.95, // 95% hex fill (small gaps for definition)
})
```

**Technique 2: Gaussian Blur (Post-Processing)**
- Apply CSS `filter: blur(10px)` to the deck.gl canvas
- Creates smooth gradients between hexagons
- Performance: negligible cost (GPU-accelerated)

**Technique 3: K-Ring Interpolation**
```python
def smooth_hex_intensities(hex_data, k=2):
    """
    Spread each hex's intensity to its k-ring neighbors.
    k=1: immediate neighbors (6 hexes)
    k=2: neighbors + neighbors of neighbors (~18 hexes)
    """
    smoothed = {}

    for hex_id, intensity in hex_data.items():
        # Get k-ring neighbors
        neighbors = h3.k_ring(hex_id, k)

        # Distribute intensity with distance decay
        for neighbor in neighbors:
            distance = h3.h3_distance(hex_id, neighbor)
            weight = 1.0 / (1 + distance)  # Inverse distance
            smoothed[neighbor] = smoothed.get(neighbor, 0) + intensity * weight

    # Normalize
    max_val = max(smoothed.values())
    return {h: v / max_val for h, v in smoothed.items()}
```

**Recommendation**:
- **Iteration 2**: Technique 1 (deck.gl elevation + coverage)
- **Iteration 3**: Add Technique 2 (Gaussian blur) or Technique 3 (k-ring smoothing)

---

### 5. Color Scale

**Heat → Color Mapping** (inspired by thermal imaging):

```typescript
function intensityToColor(intensity: number): [number, number, number, number] {
  // intensity: 0.0 (cold) → 1.0 (hot)

  const colorStops = [
    [0.0, [0, 0, 139, 50]],        // Dark blue (very cold, barely visible)
    [0.2, [0, 0, 255, 100]],       // Blue (cold)
    [0.4, [0, 255, 255, 150]],     // Cyan (cool)
    [0.6, [0, 255, 0, 200]],       // Green (warm)
    [0.8, [255, 255, 0, 220]],     // Yellow (hot)
    [1.0, [255, 0, 0, 255]],       // Red (very hot)
  ]

  // Linear interpolation between color stops
  return interpolateColor(intensity, colorStops)
}
```

**Alpha Channel**: Lower intensities are more transparent (creates fading effect).

---

### 6. Dynamic Zoom Handling

**Problem**: Switching H3 resolution on zoom causes jarring transitions.

**Solution 1: Tile-Based Loading** (Recommended)
```typescript
const getH3Resolution = (zoom: number): number => {
  if (zoom < 3) return 1
  if (zoom < 5) return 2
  if (zoom < 7) return 3
  if (zoom < 9) return 4
  if (zoom < 11) return 5
  return 6
}

// In map component
map.on('zoom', () => {
  const currentZoom = map.getZoom()
  const targetResolution = getH3Resolution(currentZoom)

  if (targetResolution !== currentResolution) {
    // Fetch new resolution data
    fetchHexData(targetResolution)
  }
})
```

**Solution 2: Pre-fetch Multiple Resolutions**
```typescript
// Cache 3 resolutions simultaneously
const resolutionCache = {
  low: fetchHexData(resolution - 1),
  current: fetchHexData(resolution),
  high: fetchHexData(resolution + 1),
}

// Instant switching, no loading delay
```

**Solution 3: Smooth Transitions (deck.gl)**
```typescript
new H3HexagonLayer({
  id: 'hex-heatmap',
  transitions: {
    getFillColor: 500,    // 500ms color transition
    getElevation: 500,    // 500ms elevation transition
  }
})
```

---

### 7. Performance Optimization

**Target**: 60 FPS with 50,000 hexagons on modern browsers.

**Techniques**:

1. **Viewport Culling** (deck.gl automatic)
   - Only render hexagons in view
   - Estimated 80% reduction in render load

2. **Level of Detail (LOD)**
   ```typescript
   // Use lower resolution for distant hexagons
   const resolution = zoom < 5 ? 2 : zoom < 9 ? 4 : 6
   ```

3. **Backend Aggregation**
   ```python
   # Don't send hexes with intensity < threshold
   return [hex for hex in hexes if hex.intensity >= 0.1]
   ```

4. **Response Compression**
   ```python
   # Use gzip compression (Flask/FastAPI)
   # Typical savings: 70-80% for JSON hex data
   ```

5. **Client-Side Caching**
   ```typescript
   // Cache hex data for 5 minutes
   const hexCache = new Map<string, HexData>()
   ```

6. **WebWorker for H3 Calculations**
   ```typescript
   // Offload H3 operations to background thread
   const worker = new Worker('h3-worker.js')
   worker.postMessage({ action: 'generateHexes', resolution: 4 })
   ```

**Expected Performance** (deck.gl + H3):
| Hexagon Count | FPS (Desktop) | FPS (Mobile) |
|---------------|---------------|--------------|
| 1,000         | 60            | 60           |
| 10,000        | 60            | 55           |
| 50,000        | 60            | 40           |
| 100,000       | 55            | 25           |
| 500,000       | 30            | 10           |

---

## Implementation Plan

### Phase 1: MVP Hex Grid (Iteration 2)

**Goal**: Replace country circles with hexagonal heatmap.

**Tasks**:
1. Add dependencies: `h3-js`, `deck.gl`, `@deck.gl/react`
2. Create `/v1/hexmap` API endpoint
   - Input: `resolution` (H3 level), `time_window`
   - Output: `[{ h3_index: string, intensity: float }]`
3. Implement simple geographic spread (polyfill countries)
4. Frontend: Render H3HexagonLayer with deck.gl
5. Map zoom → H3 resolution selection
6. Basic color scale (blue → red)

**Estimated Complexity**: Medium (2-3 days)
**Estimated Hexagons**: ~5,000 at resolution 3

---

### Phase 2: Blob Effect & Smoothing (Iteration 3)

**Goal**: Make hexagons look like smooth, organic blobs.

**Tasks**:
1. Add Gaussian blur to deck.gl canvas
2. Implement k-ring smoothing (k=2) in backend
3. Add elevation to hexagons (3D effect)
4. Fine-tune coverage parameter (0.9-0.95)
5. Implement smooth transitions on zoom
6. Add alpha channel to color scale

**Estimated Complexity**: Medium (2 days)
**Visual Impact**: High (transforms feel from "grid" to "blobs")

---

### Phase 3: Dynamic Flow Animation (Future)

**Goal**: Animate intensity changes over time (shows information propagating).

**Tasks**:
1. Add time slider to frontend
2. Fetch historical hex data (last 24 hours, 1-hour intervals)
3. Animate hex intensity transitions
4. Add "pulse" effect to high-activity hexes
5. Implement playback controls (play, pause, speed)

**Estimated Complexity**: High (3-4 days)
**Requires**: Historical data storage in database

---

## API Design

### Endpoint: `GET /v1/hexmap`

**Request**:
```bash
GET /v1/hexmap?resolution=4&time_window=24h&countries=US,CO,BR&threshold=0.1
```

**Parameters**:
- `resolution` (int, 0-15): H3 resolution level
- `time_window` (str): `1h`, `6h`, `12h`, `24h`
- `countries` (str, optional): Comma-separated country codes (if empty, global)
- `threshold` (float, 0-1): Minimum intensity to return (reduces payload)

**Response**:
```json
{
  "resolution": 4,
  "time_window": "24h",
  "generated_at": "2025-01-13T10:30:00Z",
  "hexagons": [
    {
      "h3_index": "844c89fffffffff",
      "intensity": 0.87,
      "country": "US",
      "top_topic": "election fraud claims"
    },
    {
      "h3_index": "844c8bfffffffff",
      "intensity": 0.53,
      "country": "US",
      "top_topic": "voting irregularities"
    }
  ],
  "metadata": {
    "total_hexagons": 1247,
    "filtered_hexagons": 892,
    "max_intensity": 0.92
  }
}
```

**Payload Size Estimate**:
- 1,000 hexes: ~50 KB (uncompressed), ~15 KB (gzipped)
- 10,000 hexes: ~500 KB (uncompressed), ~150 KB (gzipped)
- 50,000 hexes: ~2.5 MB (uncompressed), ~750 KB (gzipped)

**Caching Strategy**:
- Cache key: `hexmap:res{resolution}:window{time_window}:threshold{threshold}`
- TTL: 5 minutes (aligns with refresh interval)

---

## Frontend Integration

### Dependencies to Add

```bash
npm install h3-js deck.gl @deck.gl/react @deck.gl/core @deck.gl/layers
```

**Bundle Size Impact**:
- `h3-js`: ~50 KB
- `deck.gl` (core + layers): ~400 KB
- **Total**: ~450 KB (gzipped: ~150 KB)

**Current frontend bundle**: ~800 KB
**New bundle**: ~1.25 MB (acceptable for web app)

---

### Component Structure

```
frontend/src/components/map/
├── MapContainer.tsx          # Existing (add deck.gl overlay)
├── HexagonHeatmapLayer.tsx   # NEW: deck.gl H3 layer
├── HexZoomController.tsx     # NEW: manages resolution on zoom
├── HexLegend.tsx             # NEW: color scale legend
└── HexTooltip.tsx            # NEW: hover tooltip (shows top topic)
```

---

### Code Snippet: Hexagon Layer

```typescript
// frontend/src/components/map/HexagonHeatmapLayer.tsx

import React from 'react'
import { DeckGL } from '@deck.gl/react'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import { useMapStore } from '../../store/mapStore'

const HexagonHeatmapLayer: React.FC = () => {
  const { hexData, hoveredHex, setHoveredHex } = useMapStore()

  const layers = [
    new H3HexagonLayer({
      id: 'hex-heatmap',
      data: hexData,

      // Data accessors
      getHexagon: (d) => d.h3_index,
      getFillColor: (d) => intensityToRGBA(d.intensity),
      getElevation: (d) => d.intensity * 5000,

      // Styling
      extruded: true,
      coverage: 0.95,
      elevationScale: 1,

      // Interaction
      pickable: true,
      autoHighlight: true,
      onHover: (info) => setHoveredHex(info.object),

      // Performance
      updateTriggers: {
        getFillColor: [hexData],
        getElevation: [hexData],
      },

      // Smooth transitions
      transitions: {
        getFillColor: 500,
        getElevation: 500,
      },
    }),
  ]

  return (
    <DeckGL
      layers={layers}
      style={{ pointerEvents: 'none' }} // Let Mapbox handle interactions
    />
  )
}

// Color mapping function
function intensityToRGBA(intensity: number): [number, number, number, number] {
  if (intensity < 0.2) return [0, 0, 139, 80]     // Dark blue
  if (intensity < 0.4) return [0, 0, 255, 120]    // Blue
  if (intensity < 0.6) return [0, 255, 255, 160]  // Cyan
  if (intensity < 0.8) return [255, 255, 0, 200]  // Yellow
  return [255, 0, 0, 255]                          // Red
}

export default HexagonHeatmapLayer
```

---

### Code Snippet: Zoom Controller

```typescript
// frontend/src/components/map/HexZoomController.tsx

import { useEffect } from 'react'
import { useMap } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'

const getH3Resolution = (zoom: number): number => {
  if (zoom < 3) return 1
  if (zoom < 5) return 2
  if (zoom < 7) return 3
  if (zoom < 9) return 4
  if (zoom < 11) return 5
  return 6
}

export const HexZoomController: React.FC = () => {
  const { current: map } = useMap()
  const { fetchHexData, currentResolution, setResolution } = useMapStore()

  useEffect(() => {
    if (!map) return

    const handleZoom = () => {
      const zoom = map.getZoom()
      const targetResolution = getH3Resolution(zoom)

      if (targetResolution !== currentResolution) {
        setResolution(targetResolution)
        fetchHexData(targetResolution)
      }
    }

    map.on('zoom', handleZoom)
    return () => map.off('zoom', handleZoom)
  }, [map, currentResolution, fetchHexData, setResolution])

  return null // No visual component
}
```

---

## Backend Implementation

### Dependencies to Add

```bash
# backend/requirements.txt
h3==3.7.6
shapely==2.0.2        # For country geometries
geopandas==0.14.1     # For geospatial operations (optional)
```

---

### Code Snippet: Hexmap Endpoint

```python
# backend/app/api/v1/hexmap.py

from fastapi import APIRouter, Query
from typing import List, Optional
from app.models.hexmap import HexmapResponse, Hexagon
from app.services.hex_generator import HexGenerator
from app.services.flow_detector import FlowDetector
import h3

router = APIRouter()
hex_generator = HexGenerator()

@router.get("/hexmap", response_model=HexmapResponse)
async def get_hexmap(
    resolution: int = Query(4, ge=0, le=15, description="H3 resolution level"),
    time_window: str = Query("24h", regex="^(1h|6h|12h|24h)$"),
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
    threshold: float = Query(0.1, ge=0.0, le=1.0, description="Minimum intensity"),
):
    """
    Generate hexagonal heatmap of information flow intensity.
    """
    # Step 1: Get country-level intensities (from existing flow detector)
    flow_detector = FlowDetector()
    hotspots = await flow_detector.get_hotspots(time_window, countries)

    # Step 2: Convert countries to hexagons
    hexagons = []
    for hotspot in hotspots:
        country_hexes = hex_generator.country_to_hexes(
            country_code=hotspot.country_code,
            intensity=hotspot.intensity,
            resolution=resolution
        )
        hexagons.extend(country_hexes)

    # Step 3: Aggregate overlapping hexagons (if countries share hexes)
    aggregated = hex_generator.aggregate_hexes(hexagons)

    # Step 4: Filter by threshold
    filtered = [h for h in aggregated if h.intensity >= threshold]

    # Step 5: Return response
    return HexmapResponse(
        resolution=resolution,
        time_window=time_window,
        generated_at=datetime.utcnow(),
        hexagons=filtered,
        metadata={
            "total_hexagons": len(aggregated),
            "filtered_hexagons": len(filtered),
            "max_intensity": max((h.intensity for h in aggregated), default=0.0)
        }
    )
```

---

### Code Snippet: Hex Generator Service

```python
# backend/app/services/hex_generator.py

import h3
from typing import List, Dict
from shapely.geometry import shape
from collections import defaultdict
from app.models.hexmap import Hexagon

class HexGenerator:
    def __init__(self):
        # Load country geometries (from GeoJSON file or database)
        self.country_geometries = self._load_country_geometries()

    def country_to_hexes(
        self,
        country_code: str,
        intensity: float,
        resolution: int
    ) -> List[Hexagon]:
        """
        Convert a country's intensity to hexagons covering that country.
        """
        # Get country polygon
        geom = self.country_geometries.get(country_code)
        if not geom:
            return []

        # Convert to GeoJSON format for h3.polyfill
        geojson = {
            "type": "Polygon",
            "coordinates": [list(geom.exterior.coords)]
        }

        # Get all H3 cells covering the polygon
        hex_ids = h3.polyfill(geojson, resolution, geo_json_conformant=True)

        # Create Hexagon objects
        return [
            Hexagon(
                h3_index=hex_id,
                intensity=intensity,
                country=country_code,
                top_topic=None  # Can be enhanced later
            )
            for hex_id in hex_ids
        ]

    def aggregate_hexes(self, hexagons: List[Hexagon]) -> List[Hexagon]:
        """
        Aggregate overlapping hexagons (sum intensities, cap at 1.0).
        """
        aggregated = defaultdict(lambda: {"intensity": 0.0, "countries": set(), "topics": []})

        for hex in hexagons:
            aggregated[hex.h3_index]["intensity"] += hex.intensity
            aggregated[hex.h3_index]["countries"].add(hex.country)
            if hex.top_topic:
                aggregated[hex.h3_index]["topics"].append(hex.top_topic)

        # Convert back to Hexagon objects
        result = []
        for h3_index, data in aggregated.items():
            result.append(
                Hexagon(
                    h3_index=h3_index,
                    intensity=min(data["intensity"], 1.0),  # Cap at 1.0
                    country=",".join(data["countries"]),    # Multiple countries
                    top_topic=data["topics"][0] if data["topics"] else None
                )
            )

        return result

    def _load_country_geometries(self) -> Dict[str, any]:
        """
        Load country polygons from GeoJSON file.
        Source: https://github.com/datasets/geo-countries
        """
        import json
        with open("data/countries.geojson", "r") as f:
            geojson = json.load(f)

        geometries = {}
        for feature in geojson["features"]:
            country_code = feature["properties"]["ISO_A2"]
            geometries[country_code] = shape(feature["geometry"])

        return geometries
```

---

## Performance Estimates

### Hexagons per Zoom Level (Global Coverage)

| Zoom | H3 Res | Hexagons (Global) | Hexagons (10 Countries) | API Payload (gzip) |
|------|--------|-------------------|-------------------------|---------------------|
| 0-2  | 1      | ~840              | ~80                     | ~5 KB               |
| 3-4  | 2      | ~5,880            | ~600                    | ~30 KB              |
| 5-6  | 3      | ~41,160           | ~4,000                  | ~200 KB             |
| 7-8  | 4      | ~288,120          | ~28,000                 | ~1.4 MB             |
| 9-10 | 5      | ~2M               | ~200,000                | ~10 MB (too large)  |

**Recommendation**:
- **Resolutions 1-4**: Safe for global visualization
- **Resolution 5+**: Limit to visible viewport (bbox filtering)

---

### Expected Performance (60 FPS target)

| Resolution | Hexagons (10 Countries) | Render Performance | Suitable for |
|------------|-------------------------|-------------------|--------------|
| 1-2        | ~600                    | ✅ Excellent       | Global view  |
| 3          | ~4,000                  | ✅ Excellent       | Continental  |
| 4          | ~28,000                 | ✅ Good            | Country zoom |
| 5          | ~200,000                | ⚠️ Moderate        | Regional zoom (with viewport culling) |
| 6+         | 1M+                     | ❌ Poor            | Not recommended for Iteration 2 |

---

## Migration Strategy

### Iteration 2: Dual Rendering

**Keep existing country circles**, add hexagons as optional layer.

```typescript
<MapContainer>
  {showHexagons ? <HexagonHeatmapLayer /> : <HotspotLayer />}
  <FlowLayer />
</MapContainer>
```

**Benefits**:
- No breaking changes
- A/B testing possible
- Gradual user adoption

---

### Iteration 3: Hexagon-Only

**Remove country circles**, use hexagons exclusively.

**Migration Checklist**:
- [ ] Ensure hex performance meets targets
- [ ] User testing confirms preference for hexagons
- [ ] All features work with hexagons (tooltips, filters, etc.)
- [ ] Remove deprecated HotspotLayer component

---

## Alternative: Turf.js Approach (MVP Fallback)

**If deck.gl complexity is too high for Iteration 2**, use Turf.js:

```typescript
import * as turf from '@turf/turf'

// Generate hex grid for viewport
const bbox = map.getBounds().toArray().flat()
const cellSize = getHexSize(map.getZoom()) // km
const hexGrid = turf.hexGrid(bbox, cellSize, { units: 'kilometers' })

// Add as Mapbox source
map.addSource('hex-grid', {
  type: 'geojson',
  data: hexGrid
})

// Style by intensity
map.addLayer({
  id: 'hex-heatmap',
  type: 'fill',
  source: 'hex-grid',
  paint: {
    'fill-color': [
      'interpolate',
      ['linear'],
      ['get', 'intensity'],
      0, '#000080',
      0.5, '#00FFFF',
      1, '#FF0000'
    ],
    'fill-opacity': 0.7
  }
})
```

**Pros**: Simpler, no new dependencies
**Cons**: Limited to ~5,000 hexagons, no 3D effects, manual zoom handling

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **deck.gl bundle size** | Slower initial load | Code splitting, lazy loading |
| **Too many hexagons** | Poor performance | Viewport culling, threshold filtering |
| **Complex integration** | Delayed delivery | Start with Turf.js MVP, upgrade to deck.gl later |
| **Country geometry data** | Large dataset (~5 MB) | Load on demand, cache in browser |
| **H3 learning curve** | Development slowdown | Use examples from deck.gl docs, H3 tutorials |

---

## Success Metrics

### Iteration 2 (MVP)
- ✅ Hexagons render at 60 FPS (5,000 hexes, desktop)
- ✅ Zoom levels 2-4 work smoothly
- ✅ Hexagons change color based on intensity
- ✅ User can toggle between hexagons and circles

### Iteration 3 (Enhanced)
- ✅ Blob effect achieved (users say "looks organic, not grid-like")
- ✅ Smooth transitions on zoom
- ✅ 30,000 hexagons render at 60 FPS
- ✅ Hexagons work on mobile (30 FPS minimum)

---

## References

- [H3 Documentation](https://h3geo.org/)
- [deck.gl H3HexagonLayer](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)
- [Uber Engineering: H3](https://www.uber.com/blog/h3/)
- [Turf.js hexGrid](https://turfjs.org/docs/#hexGrid)
- [Mapbox GL Custom Layers](https://docs.mapbox.com/mapbox-gl-js/api/properties/#customlayerinterface)
- [Country GeoJSON Dataset](https://github.com/datasets/geo-countries)

---

## Decision Log

**Approved**: H3 + deck.gl for Iteration 2 (subject to complexity assessment)
**Fallback**: Turf.js hexGrid if deck.gl proves too complex
**Future**: Topic geocoding + NER for precise hex intensity (Iteration 4+)

---

**Review Date**: 2025-02-13 (after Iteration 2 implementation)
**Next Steps**: Implement proof-of-concept with 100 hexagons, measure performance.

---

*Document version: 1.0*
*Last updated: 2025-01-13*
