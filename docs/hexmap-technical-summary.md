# Hexagonal Heatmap System: Technical Summary

**Project**: Observatory Global
**Feature**: Dynamic Hexagonal Blob Heatmap Visualization
**Date**: 2025-01-13
**Status**: Design Complete, Ready for Implementation

---

## Executive Summary

This document summarizes the technical architecture, implementation strategy, and proof-of-concept code for transforming Observatory Global's map visualization from country-centric circles to a dynamic hexagonal heatmap with smooth "blob" effects.

**Key Decision**: Use **H3 (Uber's Hexagonal Hierarchical Spatial Index) + deck.gl** for production-ready, performant hexagonal visualization.

**Estimated Implementation Time**: 5-7 days (Iteration 2)

**Expected Performance**: 60 FPS with 5,000+ hexagons on desktop browsers

---

## Problem Statement

**Current Visualization Limitations**:
1. ❌ Country-centric circles tied to political borders
2. ❌ Low spatial resolution (one point per country)
3. ❌ Lacks organic, "alive" feel
4. ❌ Can't show regional variations within large countries
5. ❌ Doesn't visualize information density naturally

**User Need**: "I want to see information flow as a living, breathing heatmap—like weather radar or traffic maps—not just dots on countries."

---

## Proposed Solution

### Visual Transformation

**Before (Current)**:
```
         🔵 US
          ↓
         arc
          ↓
         🔵 CO
```

**After (Iteration 2)**:
```
    🔷🔶🔷🔶      North America
    🔶🔴🔴🔶      (red = high intensity)
    🔷🔶🔷🔶
         ⬇️  (organic gradient flow)
      🔷🔶🔷        South America
      🔶🟡🔶        (yellow = medium)
      🔷🔶🔷
```

**After (Iteration 3 - with blob smoothing)**:
```
      ☁️☁️☁️         Smooth, cloud-like blobs
    ☁️🔥🔥☁️         (fire = hotspots)
      ☁️☁️☁️
         ⬇️  (blurred gradient)
      ☁️🌤️☁️         Cooler regions
        ☁️☁️
```

---

## Architecture Overview

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND                                │
├─────────────────────────────────────────────────────────────┤
│  Mapbox GL (base map, roads, labels)                        │
│       ↓                                                      │
│  deck.gl (hexagon overlay layer)                            │
│       ↓                                                      │
│  H3-js (spatial calculations, resolution mapping)           │
│       ↓                                                      │
│  React + Zustand (state management)                         │
└─────────────────────────────────────────────────────────────┘
                         ↕️ HTTP/JSON
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND                                 │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (/v1/hexmap endpoint)                              │
│       ↓                                                      │
│  H3 Python (polyfill countries → hexagons)                  │
│       ↓                                                      │
│  Shapely + GeoJSON (country geometries)                     │
│       ↓                                                      │
│  FlowDetector (country-level intensity data)                │
│       ↓                                                      │
│  Redis Cache (5-min TTL)                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Technical Decisions

### 1. Hexagon System: H3 (Uber)

**Why H3?**
- ✅ Industry standard (used by Uber, Foursquare, Mapbox)
- ✅ Hierarchical resolution (16 levels: global → neighborhood)
- ✅ Fast spatial queries (O(1) for neighbors)
- ✅ Native deck.gl integration (H3HexagonLayer)
- ✅ Deterministic hex IDs (perfect for caching)

**Alternative Considered**: Turf.js hexGrid
- ⚠️ Simpler but limited scalability (~5,000 hex max)
- 🟢 Valid MVP fallback if H3 proves too complex

**Decision**: H3 + deck.gl for Iteration 2, with Turf.js as documented fallback

---

### 2. Zoom-Resolution Mapping

| Map Zoom | H3 Res | Hex Size | Use Case          | Hexes (10 Countries) |
|----------|--------|----------|-------------------|----------------------|
| 0-2      | 1      | ~1,100km | Global overview   | ~100                 |
| 3-4      | 2      | ~400km   | Continental       | ~600                 |
| 5-6      | 3      | ~150km   | Country/region    | ~4,000               |
| 7-8      | 4      | ~60km    | State/province    | ~28,000              |
| 9-10     | 5      | ~22km    | City clusters     | ~200,000 (⚠️ heavy) |

**Iteration 2 Scope**: Resolutions 1-4 (safe performance range)

**Iteration 3+**: Add resolution 5-6 with viewport culling

---

### 3. Color Scale (Thermal Mapping)

```
Intensity   Color        RGBA              Visual
─────────────────────────────────────────────────────
0.0-0.2     Dark Blue    [0, 0, 139, 60]   ████ (barely visible)
0.2-0.4     Blue         [0, 0, 255, 100]  ████
0.4-0.6     Cyan         [0, 255, 255, 140] ████
0.6-0.8     Yellow       [255, 255, 0, 200] ████
0.8-1.0     Red          [255, 0, 0, 255]  ████ (fully opaque)
```

**Design Principle**: Lower intensities = more transparent (creates fading effect)

---

### 4. Blob Effect Techniques

**Phase 1 (Iteration 2)**: Basic smoothness
- ✅ Coverage parameter (0.95 = small gaps between hexes)
- ✅ Smooth color interpolation (deck.gl transitions)

**Phase 2 (Iteration 3)**: Enhanced organic feel
- 🔲 Gaussian blur (`filter: blur(8px)` on deck.gl canvas)
- 🔲 K-ring smoothing (backend spreads intensity to neighbor hexes)
- 🔲 3D elevation (hex height = intensity)

**Expected Result**: Transformation from "hexagonal grid" → "organic blobs"

---

### 5. Performance Optimizations

| Technique | Impact | Implemented |
|-----------|--------|-------------|
| **Viewport culling** (deck.gl automatic) | 80% render reduction | Iteration 2 ✅ |
| **Threshold filtering** (intensity < 0.1 excluded) | 50% payload reduction | Iteration 2 ✅ |
| **Resolution LOD** (zoom-based) | 90% hex count reduction | Iteration 2 ✅ |
| **Response compression** (gzip) | 70% bandwidth savings | Iteration 2 ✅ |
| **Redis caching** (5-min TTL) | 95% faster responses | Iteration 2 ✅ |
| **WebWorker for H3** (offload calculations) | 30% smoother interactions | Iteration 3 🔲 |

**Performance Targets**:
- Desktop: 60 FPS with 5,000 hexagons
- Mobile: 30 FPS with 5,000 hexagons
- API response: <200ms (cache hit), <2s (cache miss)

---

## Data Flow

### Request Flow

```
1. User zooms map to level 5
        ↓
2. Frontend calculates H3 resolution = 3
        ↓
3. Check if cached resolution data exists
        ↓ (cache miss)
4. GET /v1/hexmap?resolution=3&time_window=24h&threshold=0.1
        ↓
5. Backend fetches country intensities (from FlowDetector)
        ↓
6. Backend polyfills countries with H3 hexagons
        ↓
7. Backend aggregates overlapping hexes
        ↓
8. Backend filters by threshold (intensity >= 0.1)
        ↓
9. Return JSON: [{ h3_index, intensity, country, top_topic }]
        ↓
10. Frontend creates deck.gl H3HexagonLayer
        ↓
11. Render hexagons with color mapping
        ↓
12. Cache data for 5 minutes
```

---

### API Contract

**Endpoint**: `GET /v1/hexmap`

**Request**:
```bash
curl "http://localhost:8000/v1/hexmap?resolution=4&time_window=24h&countries=US,BR,CO&threshold=0.2"
```

**Response** (example):
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
    "max_intensity": 0.92,
    "countries_included": ["US", "BR", "CO"],
    "avg_intensity": 0.34
  }
}
```

**Payload Size**:
- 1,000 hexes: ~50 KB (uncompressed), ~15 KB (gzipped)
- 5,000 hexes: ~250 KB (uncompressed), ~75 KB (gzipped)

---

## Implementation Phases

### Phase 1: MVP Hexagon Grid (Iteration 2)

**Timeline**: 5-7 days
**Complexity**: High

**Deliverables**:
- ✅ Backend `/v1/hexmap` endpoint
- ✅ Frontend deck.gl hexagon layer
- ✅ Zoom-based resolution switching
- ✅ Thermal color scale (blue → red)
- ✅ User toggle: "Classic" vs "Heatmap" mode

**Success Criteria**:
- 60 FPS with 5,000 hexagons (desktop)
- API response <2s (cache miss)
- Hexagons change smoothly on zoom

---

### Phase 2: Blob Effect & Smoothing (Iteration 3)

**Timeline**: 2-3 days
**Complexity**: Medium

**Deliverables**:
- ✅ Gaussian blur filter (CSS `blur(8px)`)
- ✅ K-ring smoothing (backend)
- ✅ 3D elevation effect (deck.gl `extruded: true`)
- ✅ Animated transitions

**Success Criteria**:
- Users describe visualization as "organic" and "blob-like"
- No performance degradation

---

### Phase 3: Advanced Features (Future)

**Timeline**: 3-4 days
**Complexity**: High

**Deliverables**:
- 🔲 Historical playback (time slider)
- 🔲 Animated intensity changes
- 🔲 Topic geocoding (NER + precise hex placement)
- 🔲 Flow arrows between high-intensity hexes

---

## Code Highlights

### Frontend: Hexagon Layer (TypeScript)

```typescript
import { H3HexagonLayer } from '@deck.gl/geo-layers'

const layers = [
  new H3HexagonLayer({
    id: 'hex-heatmap',
    data: hexData,
    getHexagon: (d) => d.h3_index,
    getFillColor: (d) => intensityToRGBA(d.intensity),
    getElevation: (d) => d.intensity * 5000,
    extruded: true,
    coverage: 0.95,
    transitions: {
      getFillColor: 500,
      getElevation: 500
    }
  })
]
```

### Backend: Country → Hexagons (Python)

```python
import h3
from shapely.geometry import shape

def country_to_hexes(country_code: str, intensity: float, resolution: int):
    # Get country polygon
    geom = country_geometries[country_code]

    # Convert to GeoJSON
    geojson = {"type": "Polygon", "coordinates": [list(geom.exterior.coords)]}

    # Polyfill with H3 hexagons
    hex_ids = h3.polyfill_geojson(geojson, resolution)

    # Return hexagons
    return [
        {"h3_index": hex_id, "intensity": intensity, "country": country_code}
        for hex_id in hex_ids
    ]
```

---

## Dependencies & Bundle Impact

### Frontend
```json
{
  "dependencies": {
    "h3-js": "^4.1.0",           // +50 KB
    "deck.gl": "^9.0.0",         // +400 KB
    "@deck.gl/react": "^9.0.0",
    "@deck.gl/geo-layers": "^9.0.0"
  }
}
```

**Total Bundle Impact**: +450 KB (gzipped: ~150 KB)
**Current Bundle**: ~800 KB → **New Bundle**: ~1.25 MB (acceptable)

### Backend
```
h3==3.7.6              # H3 spatial indexing
shapely==2.0.2         # Geometry operations
geopandas==0.14.1      # GeoJSON handling (optional)
```

---

## Performance Estimates

### Hexagon Counts by Resolution

| Scenario | Resolution | Hexagons | FPS (Desktop) | FPS (Mobile) | API Response |
|----------|------------|----------|---------------|--------------|--------------|
| Global view | 1-2 | ~600 | 60 | 60 | <1s |
| Continental | 3 | ~4,000 | 60 | 55 | <2s |
| Country zoom | 4 | ~28,000 | 60 | 40 | <3s |
| Regional zoom | 5 | ~200,000 | 45 | 20 | <5s ⚠️ |

**Iteration 2 Limit**: Resolution 4 (safe performance)
**Iteration 3+**: Add viewport culling for resolution 5-6

---

## Risk Assessment

### High-Priority Risks

| Risk | Mitigation |
|------|------------|
| **Poor performance (<30 FPS)** | Fallback to Turf.js, reduce max resolution to 3 |
| **Large bundle size (>2 MB)** | Code splitting, lazy load deck.gl |
| **H3 polyfill errors** | Validate geometries, graceful error handling |

### Medium-Priority Risks

| Risk | Mitigation |
|------|------------|
| **Color scale not intuitive** | A/B test scales, user preference setting |
| **Blob effect insufficient** | Add Gaussian blur, k-ring smoothing (Iteration 3) |
| **WebGL browser support** | Detect WebGL, fallback to 2D circles |

---

## Success Metrics

### Technical Metrics (Week 1)
- [ ] 60 FPS on desktop (Chrome, 5,000 hexes)
- [ ] 30 FPS on mobile (iOS Safari, 5,000 hexes)
- [ ] API 95th percentile response time <2s
- [ ] Cache hit rate >80%
- [ ] <5 bug reports

### User Metrics (Month 1)
- [ ] >70% of users try "Heatmap" mode
- [ ] >50% prefer "Heatmap" over "Classic"
- [ ] Positive feedback on "organic" feel in surveys
- [ ] <2% error rate on frontend

---

## File Deliverables

### Documentation
- ✅ `docs/decisions/ADR-0003-hexagonal-heatmap-architecture.md` (3,500 words)
- ✅ `docs/planning/iter2-hexmap-implementation.md` (implementation plan)
- ✅ `docs/hexmap-technical-summary.md` (this document)

### Proof-of-Concept Code
- ✅ `docs/examples/hex-poc-frontend.tsx` (React + deck.gl example)
- ✅ `docs/examples/hex-poc-backend.py` (FastAPI + H3 example)

### References
- ADR-0002: Heat Formula (intensity calculation)
- ADR-0001: Refresh Intervals (caching strategy)
- Existing: `frontend/src/components/map/MapContainer.tsx`
- Existing: `backend/app/api/v1/flows.py`

---

## Next Steps

### Immediate (Before Iteration 2)
1. Review ADR-0003 with stakeholders
2. Approve implementation plan
3. Allocate 5-7 days for development
4. Download countries.geojson dataset

### Iteration 2 Kickoff
1. Install dependencies (frontend + backend)
2. Create feature branch: `feat/frontend-map/iter2-hexmap`
3. Implement backend endpoint (2-3 days)
4. Implement frontend layer (2-3 days)
5. Integration testing (1 day)
6. Deploy to staging

### Post-Iteration 2
1. Collect user feedback
2. Measure performance in production
3. Plan Iteration 3 enhancements (blob smoothing)

---

## Key Resources

### Learning Materials
- [H3 Official Documentation](https://h3geo.org/)
- [deck.gl Get Started Guide](https://deck.gl/docs/get-started/getting-started)
- [Uber Engineering: H3 Blog](https://www.uber.com/blog/h3/)

### Tools & Datasets
- [H3 Resolution Table](https://h3geo.org/docs/core-library/restable/)
- [Countries GeoJSON](https://github.com/datasets/geo-countries)
- [H3 Demo (geojson.io)](https://observablehq.com/@nrabinowitz/h3-index-inspector)

### Inspiration
- Weather radar heatmaps (NOAA)
- Google Maps traffic visualization
- Uber surge pricing heatmaps

---

## Conclusion

The proposed hexagonal heatmap architecture using **H3 + deck.gl** provides a production-ready, scalable solution for visualizing information flow with organic, blob-like patterns.

**Why This Approach Wins**:
1. ✅ Battle-tested at scale (Uber, Mapbox)
2. ✅ High performance (60 FPS with 5,000+ hexes)
3. ✅ Smooth user experience (dynamic zoom, transitions)
4. ✅ Extensible (3D, smoothing, animations in future iterations)
5. ✅ Well-documented with strong ecosystem

**Alternative (Turf.js)** remains a valid MVP fallback if complexity proves too high.

**Ready for Implementation**: All architecture decisions documented, POC code provided, phased plan defined.

---

**Document Prepared By**: Technical Architecture Team
**Review Status**: Ready for stakeholder approval
**Next Review Date**: After Iteration 2 completion (est. 2025-01-22)

---

*Document Version: 1.0*
*Last Updated: 2025-01-13*
*Total Pages: 9*
