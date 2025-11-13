# Hexagonal Heatmap: Quick Reference Guide

**For**: Development team implementing Iteration 2
**Purpose**: Quick lookup of key decisions, code patterns, and troubleshooting

---

## Key Decisions at a Glance

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Hex System** | H3 (Uber) | Industry standard, 16 resolutions, fast queries |
| **Rendering** | deck.gl | High performance, 100k+ hexes at 60 FPS |
| **Resolutions** | 1-4 (Iteration 2) | Safe performance range (600-28k hexes) |
| **Color Scale** | Blue → Cyan → Yellow → Red | Thermal mapping (intuitive) |
| **Smoothing** | Iteration 3 | Gaussian blur + k-ring interpolation |
| **Fallback** | Turf.js hexGrid | If deck.gl too complex |

---

## Zoom → Resolution Mapping

```typescript
function getH3Resolution(zoom: number): number {
  if (zoom < 3) return 1   // Global: ~600 hexes
  if (zoom < 5) return 2   // Continental: ~6k hexes
  if (zoom < 7) return 3   // Country: ~40k hexes
  if (zoom < 9) return 4   // Regional: ~280k hexes
  return 4                 // Cap at 4 for Iteration 2
}
```

---

## Color Mapping Function

```typescript
function intensityToRGBA(intensity: number): [number, number, number, number] {
  const i = Math.max(0, Math.min(1, intensity))

  if (i < 0.2) return [0, 0, 139, 60]      // Dark blue
  if (i < 0.4) return [0, 0, 255, 100]     // Blue
  if (i < 0.6) return [0, 255, 255, 140]   // Cyan
  if (i < 0.8) return [255, 255, 0, 200]   // Yellow
  return [255, 0, 0, 255]                   // Red
}
```

---

## API Quick Reference

### Request
```bash
GET /v1/hexmap?resolution=4&time_window=24h&countries=US,BR&threshold=0.1
```

### Response Structure
```typescript
interface HexmapResponse {
  resolution: number
  time_window: string
  generated_at: string
  hexagons: Array<{
    h3_index: string      // e.g., "844c89fffffffff"
    intensity: number     // 0.0 - 1.0
    country: string       // e.g., "US" or "US,CA" (overlapping)
    top_topic?: string    // Optional
  }>
  metadata: {
    total_hexagons: number
    filtered_hexagons: number
    max_intensity: number
    countries_included: string[]
    avg_intensity: number
  }
}
```

---

## Backend: Key Code Patterns

### 1. Polyfill Country with Hexagons

```python
import h3
from shapely.geometry import shape

def country_to_hexes(country_code: str, intensity: float, resolution: int):
    geom = country_geometries[country_code]
    geojson = {"type": "Polygon", "coordinates": [list(geom.exterior.coords)]}
    hex_ids = h3.polyfill_geojson(geojson, resolution)

    return [
        {"h3_index": hex_id, "intensity": intensity, "country": country_code}
        for hex_id in hex_ids
    ]
```

### 2. Aggregate Overlapping Hexagons

```python
from collections import defaultdict

def aggregate_hexes(hexagons: List[Hexagon]) -> List[Hexagon]:
    agg = defaultdict(lambda: {"intensity": 0.0, "countries": set()})

    for hex in hexagons:
        agg[hex.h3_index]["intensity"] += hex.intensity
        agg[hex.h3_index]["countries"].add(hex.country)

    return [
        Hexagon(
            h3_index=h3_id,
            intensity=min(data["intensity"], 1.0),
            country=",".join(data["countries"])
        )
        for h3_id, data in agg.items()
    ]
```

### 3. K-Ring Smoothing (Iteration 3)

```python
import h3

def smooth_hexes(hexagons: List[Hexagon], k: int = 2):
    smoothed = defaultdict(float)

    for hex in hexagons:
        neighbors = h3.k_ring(hex.h3_index, k)

        for neighbor in neighbors:
            distance = h3.h3_distance(hex.h3_index, neighbor)
            weight = 0.5 ** distance  # Exponential decay
            smoothed[neighbor] += hex.intensity * weight

    # Normalize to [0, 1]
    max_val = max(smoothed.values())
    return {h: v / max_val for h, v in smoothed.items()}
```

---

## Frontend: Key Code Patterns

### 1. deck.gl H3HexagonLayer

```typescript
import { H3HexagonLayer } from '@deck.gl/geo-layers'

const layers = [
  new H3HexagonLayer({
    id: 'hex-heatmap',
    data: hexData,

    // Required accessors
    getHexagon: (d) => d.h3_index,
    getFillColor: (d) => intensityToRGBA(d.intensity),

    // Optional 3D
    getElevation: (d) => d.intensity * 5000,
    extruded: true,

    // Styling
    coverage: 0.95,  // 95% hex fill (small gaps)
    elevationScale: 1,

    // Interaction
    pickable: true,
    autoHighlight: true,
    onHover: (info) => setHoveredHex(info.object),

    // Performance
    updateTriggers: {
      getFillColor: [hexData],
      getElevation: [hexData]
    },

    // Smooth transitions
    transitions: {
      getFillColor: { duration: 500 },
      getElevation: { duration: 500 }
    }
  })
]
```

### 2. Zoom Event Handler

```typescript
import { useMap } from 'react-map-gl'

useEffect(() => {
  if (!map) return

  const handleZoom = () => {
    const zoom = map.getZoom()
    const targetRes = getH3Resolution(zoom)

    if (targetRes !== currentResolution) {
      setResolution(targetRes)
      fetchHexData(targetRes)
    }
  }

  map.on('zoom', handleZoom)
  return () => map.off('zoom', handleZoom)
}, [map, currentResolution])
```

### 3. Blob Effect (Gaussian Blur)

```typescript
<DeckGL
  layers={layers}
  style={{
    filter: smoothing ? 'blur(8px)' : 'none',
    transition: 'filter 0.3s ease'
  }}
>
  <Map mapboxAccessToken={MAPBOX_TOKEN} />
</DeckGL>
```

---

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| **FPS (Desktop, 5k hexes)** | 60 | 30 |
| **FPS (Mobile, 5k hexes)** | 30 | 15 |
| **API Response (cache hit)** | <200ms | <500ms |
| **API Response (cache miss)** | <2s | <5s |
| **Bundle Size** | <1.5 MB | <2 MB |

---

## Common Issues & Solutions

### Issue: Poor FPS (<30)

**Possible Causes**:
1. Too many hexagons (>10,000 at high zoom)
2. deck.gl not using WebGL
3. Browser limitations

**Solutions**:
```typescript
// 1. Reduce resolution
const maxResolution = 3 // Instead of 4

// 2. Add viewport culling
const hexData = allHexes.filter(hex => isInViewport(hex))

// 3. Increase threshold
const threshold = 0.2 // Instead of 0.1 (reduces hex count by ~50%)
```

---

### Issue: Hexagons Look Like Grid (Not Blobs)

**Iteration 2 (Basic Smoothness)**:
```typescript
new H3HexagonLayer({
  coverage: 0.98,  // Increase from 0.95 (less gap)
  transitions: { getFillColor: 800 }  // Longer transition
})
```

**Iteration 3 (Blob Effect)**:
```typescript
// Add Gaussian blur
<DeckGL style={{ filter: 'blur(10px)' }} />

// Backend: K-ring smoothing
smoothed = smooth_hexes(hexagons, k=2)
```

---

### Issue: API Response Too Slow (>5s)

**Diagnose**:
```bash
# Check resolution and hex count
curl "http://localhost:8000/v1/hexmap?resolution=5"
# If >50k hexes, resolution too high
```

**Solutions**:
```python
# 1. Cap resolution in backend
if resolution > 4:
    raise HTTPException(400, "Max resolution is 4 for global queries")

# 2. Add Redis caching
@cache(ttl=300)
def get_hexmap(...):
    ...

# 3. Increase threshold
threshold = max(threshold, 0.15)  # Force minimum
```

---

### Issue: Country GeoJSON Not Loading

**Error**: `FileNotFoundError: countries.geojson`

**Solution**:
```bash
# Download dataset
cd data
curl -o countries.geojson \
  https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson

# Verify
ls -lh data/countries.geojson
# Should be ~5 MB
```

---

### Issue: H3 Polyfill Errors

**Error**: `h3.polyfill_geojson() failed for country XX`

**Causes**:
1. Invalid geometry (self-intersecting polygon)
2. Country code not in GeoJSON
3. Multi-polygon countries

**Solution**:
```python
try:
    hex_ids = h3.polyfill_geojson(geojson, resolution)
except Exception as e:
    logger.warning(f"Polyfill failed for {country_code}: {e}")
    return []  # Graceful degradation
```

---

## Testing Checklist

### Backend Tests
```bash
# Run tests
pytest backend/tests/test_hex_generator.py -v

# Key test cases
- test_country_to_hexes_us()          # US polyfill works
- test_aggregate_hexes()              # Overlapping hexes merged
- test_threshold_filtering()          # Low-intensity hexes excluded
- test_invalid_country_code()         # Graceful error handling
```

### Frontend Tests
```typescript
// Visual QA (manual)
- [ ] Hexagons render at all zoom levels (0-12)
- [ ] Colors match intensity (blue = low, red = high)
- [ ] Hover tooltip shows correct data
- [ ] Toggle between Classic/Heatmap modes works
- [ ] No console errors

// Performance (Chrome DevTools)
- [ ] FPS counter shows >55 FPS (desktop)
- [ ] Network tab: API response <2s
- [ ] Memory usage stable (no leaks)
```

---

## Debugging Tools

### 1. Visualize H3 Index

```bash
# Open H3 Inspector
https://observablehq.com/@nrabinowitz/h3-index-inspector

# Paste H3 index (e.g., 844c89fffffffff)
# See exact location and neighbors
```

### 2. Export Hexagons to GeoJSON

```python
import json
import h3

def export_hexes(hexagons, filename):
    features = []
    for hex in hexagons:
        boundary = h3.h3_to_geo_boundary(hex.h3_index, geo_json=True)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [boundary]},
            "properties": {"intensity": hex.intensity}
        })

    with open(filename, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

# Upload to geojson.io for visualization
```

### 3. Check deck.gl Rendering

```typescript
// Enable debug mode
import { Deck } from '@deck.gl/core'

const deck = new Deck({
  debug: true,  // Shows layer info in console
  onError: (error) => console.error('deck.gl error:', error)
})
```

---

## Quick Commands

```bash
# Backend: Start server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend: Start dev server
cd frontend
npm run dev

# Test hexmap endpoint
curl "http://localhost:8000/v1/hexmap?resolution=3&time_window=24h&threshold=0.1" | jq

# Build frontend
npm run build

# Check bundle size
du -sh frontend/dist/assets/*.js
```

---

## Dependencies Installation

### Frontend
```bash
cd frontend
npm install h3-js deck.gl @deck.gl/react @deck.gl/geo-layers @deck.gl/core
```

### Backend
```bash
cd backend
pip install h3==3.7.6 shapely==2.0.2 geopandas==0.14.1
```

---

## File Locations

```
backend/
├── app/
│   ├── api/v1/hexmap.py              # API endpoint
│   ├── models/hexmap.py              # Pydantic models
│   ├── services/hex_generator.py     # H3 logic
│   └── db/migrations/
│       └── 003_create_hex_cache.sql  # Optional: DB cache
├── tests/
│   └── test_hex_generator.py         # Unit tests
└── data/
    └── countries.geojson             # Country geometries

frontend/
├── src/
│   ├── components/map/
│   │   ├── HexagonHeatmapLayer.tsx   # Main hex layer
│   │   ├── HexZoomController.tsx     # Zoom handler
│   │   ├── ViewModeToggle.tsx        # Classic/Heatmap toggle
│   │   └── HexLegend.tsx             # Color scale legend
│   ├── store/
│   │   └── mapStore.ts               # Add hexData, resolution
│   └── lib/
│       └── hexUtils.ts               # Color mapping, resolution calc
└── package.json                      # Add deck.gl deps
```

---

## Key Constants

```typescript
// Frontend
const MAX_HEXAGONS = 10000      // Alert if exceeded
const CACHE_TTL_MS = 300000     // 5 minutes
const DEFAULT_RESOLUTION = 3    // Starting resolution
const MIN_INTENSITY = 0.1       // Threshold for filtering

// Backend
HEAT_HALFLIFE_HOURS = 6         // From ADR-0002
FLOW_THRESHOLD = 0.5            // From ADR-0002
HEX_CACHE_TTL_SECONDS = 300     // 5 minutes
MAX_RESOLUTION = 4              // Safety cap for Iteration 2
```

---

## Next Steps (Post-Implementation)

1. **Monitor Performance** (Week 1)
   - Track FPS in production (Google Analytics events)
   - Monitor API response times (CloudWatch/Stackdriver)
   - Check cache hit rates (Redis metrics)

2. **Collect Feedback** (Week 2)
   - User survey: "Do hexagons feel organic?"
   - A/B test: Classic vs Heatmap default
   - Identify pain points

3. **Plan Iteration 3** (Week 3)
   - If feedback positive → add blob smoothing
   - If performance issues → optimize or reduce max resolution
   - If users confused → improve color legend

---

## Contact & Resources

**Questions?** Ask in `#observatory-dev` Slack channel

**Documentation**:
- ADR-0003: Hexagonal Heatmap Architecture
- Iteration 2 Plan: `docs/planning/iter2-hexmap-implementation.md`
- POC Code: `docs/examples/hex-poc-*.{tsx,py}`

**External Resources**:
- [H3 Docs](https://h3geo.org/)
- [deck.gl API](https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer)
- [Mapbox GL API](https://docs.mapbox.com/mapbox-gl-js/api/)

---

*Last Updated: 2025-01-13*
*Version: 1.0*
