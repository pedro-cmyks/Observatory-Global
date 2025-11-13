# Iteration 2: Hexagonal Heatmap Implementation Plan

**Status**: Planned
**Target Dates**: 2025-01-15 to 2025-01-22 (1 week)
**Complexity**: High
**Dependencies**: Iteration 1 (complete)

---

## Overview

Transform Observatory Global's visualization from country-centric circles to a dynamic hexagonal heatmap that shows information flow as organic, blob-like patterns across geographic space.

**Before (Current)**:
```
🔵 Country circle at centroid
    ↓ Straight arc
🔵 Country circle at centroid
```

**After (Iteration 2)**:
```
🔷🔶🔷    Hexagonal tiles
🔶🔴🔶    with smooth color gradients
🔷🔶🔷    creating blob-like patterns
```

---

## Success Criteria

### Must Have (Iteration 2)
- ✅ Replace country circles with hexagonal grid
- ✅ Hexagons colored by information flow intensity
- ✅ Dynamic resolution based on map zoom (H3 levels 1-4)
- ✅ Renders 5,000+ hexagons at 60 FPS on desktop
- ✅ Backend API endpoint `/v1/hexmap` returns hex data
- ✅ User can toggle between "Classic" (circles) and "Heatmap" (hexagons)

### Should Have (Iteration 2)
- ✅ Smooth color transitions (thermal scale: blue → red)
- ✅ Hover tooltip showing hex intensity and country
- ✅ Threshold filter (only show hexes above X intensity)

### Nice to Have (Iteration 3)
- 🔲 3D elevation effect (hex height = intensity)
- 🔲 Gaussian blur for organic blob appearance
- 🔲 K-ring smoothing (spreads intensity to neighbors)
- 🔲 Animated transitions when changing time window

---

## Phase Breakdown

### Phase 2.1: Setup & Dependencies (Day 1)

**Goal**: Add required libraries and data files.

**Tasks**:
1. **Frontend Dependencies**
   ```bash
   cd frontend
   npm install h3-js deck.gl @deck.gl/react @deck.gl/geo-layers @deck.gl/core
   ```

2. **Backend Dependencies**
   ```bash
   cd backend
   pip install h3==3.7.6 shapely==2.0.2 geopandas==0.14.1
   ```

3. **Download Country GeoJSON**
   ```bash
   cd data
   curl -o countries.geojson https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson
   ```

4. **Verify Bundle Size Impact**
   - Check frontend build size (should be <1.5 MB gzipped)
   - If too large, enable code splitting for deck.gl

**Estimated Time**: 2 hours
**Assigned To**: DevOps / Infrastructure Agent
**Success Metric**: `npm run build` succeeds, backend starts without errors

---

### Phase 2.2: Backend Hexmap API (Days 2-3)

**Goal**: Create `/v1/hexmap` endpoint that converts country intensities to hexagons.

**Tasks**:

1. **Create Pydantic Models** (`backend/app/models/hexmap.py`)
   - `Hexagon`: Single hex with h3_index, intensity, country
   - `HexmapResponse`: Complete API response
   - `HexmapMetadata`: Statistics (total hexes, max intensity, etc.)

2. **Implement HexGenerator Service** (`backend/app/services/hex_generator.py`)
   - `country_to_hexes()`: Polyfill country with H3 hexagons
   - `aggregate_hexes()`: Combine overlapping hexagons (border regions)
   - `_load_country_geometries()`: Load countries.geojson on startup

3. **Create API Endpoint** (`backend/app/api/v1/hexmap.py`)
   ```python
   @router.get("/hexmap")
   async def get_hexmap(
       resolution: int = 4,
       time_window: str = "24h",
       countries: Optional[str] = None,
       threshold: float = 0.1
   )
   ```

4. **Add Caching**
   - Cache key: `hexmap:res{resolution}:window{time_window}`
   - TTL: 5 minutes (same as flows)
   - Eviction: LRU (max 50 MB cache)

5. **Write Unit Tests** (`backend/tests/test_hex_generator.py`)
   - Test polyfill for single country
   - Test aggregation of overlapping hexes
   - Test threshold filtering
   - Test resolution validation

**Files Created**:
- `backend/app/models/hexmap.py` (~80 lines)
- `backend/app/services/hex_generator.py` (~200 lines)
- `backend/app/api/v1/hexmap.py` (~120 lines)
- `backend/tests/test_hex_generator.py` (~150 lines)

**Estimated Time**: 8-10 hours
**Assigned To**: Backend Flow Agent
**Success Metric**:
- Endpoint returns 1,000-5,000 hexagons for 10 countries at resolution 3
- Response time <2s (cache miss), <200ms (cache hit)
- All tests pass

---

### Phase 2.3: Frontend Hexagon Layer (Days 4-5)

**Goal**: Render hexagons using deck.gl on top of Mapbox.

**Tasks**:

1. **Create HexagonHeatmapLayer Component** (`frontend/src/components/map/HexagonHeatmapLayer.tsx`)
   - Initialize deck.gl H3HexagonLayer
   - Map intensity to color (thermal scale)
   - Handle hover interactions
   - Apply smooth transitions

2. **Add Zoom Controller** (`frontend/src/components/map/HexZoomController.tsx`)
   - Listen to map zoom events
   - Calculate target H3 resolution
   - Fetch new data when resolution changes

3. **Update Zustand Store** (`frontend/src/store/mapStore.ts`)
   - Add `hexData: Hexagon[]` state
   - Add `currentResolution: number` state
   - Add `fetchHexData(resolution)` action
   - Add `viewMode: 'classic' | 'heatmap'` toggle

4. **Create View Toggle Control** (`frontend/src/components/map/ViewModeToggle.tsx`)
   - Radio buttons: "Classic" vs "Heatmap"
   - Smooth transition between modes

5. **Add Color Legend** (`frontend/src/components/map/HexLegend.tsx`)
   - Gradient bar showing intensity scale
   - Labels: "Cold" (blue) → "Hot" (red)

6. **Update MapContainer** (`frontend/src/components/map/MapContainer.tsx`)
   - Conditionally render HexagonHeatmapLayer or HotspotLayer
   - Add deck.gl overlay to Mapbox

**Files Created**:
- `frontend/src/components/map/HexagonHeatmapLayer.tsx` (~180 lines)
- `frontend/src/components/map/HexZoomController.tsx` (~60 lines)
- `frontend/src/components/map/ViewModeToggle.tsx` (~40 lines)
- `frontend/src/components/map/HexLegend.tsx` (~50 lines)

**Files Modified**:
- `frontend/src/store/mapStore.ts` (+80 lines)
- `frontend/src/components/map/MapContainer.tsx` (+20 lines)

**Estimated Time**: 10-12 hours
**Assigned To**: Frontend Map Agent
**Success Metric**:
- Hexagons render at 60 FPS (5,000 hexes, desktop)
- Zoom changes resolution dynamically (no lag)
- Colors match intensity values
- Hover tooltip shows hex data

---

### Phase 2.4: Integration & Testing (Day 6)

**Goal**: Connect frontend to backend, test end-to-end.

**Tasks**:

1. **API Integration**
   - Update `frontend/src/lib/api.ts` with `/v1/hexmap` endpoint
   - Test with real backend data

2. **Performance Testing**
   - Measure FPS with 1k, 5k, 10k hexagons
   - Profile render times (Chrome DevTools)
   - Optimize if needed (viewport culling, LOD)

3. **Cross-Browser Testing**
   - Test on Chrome, Firefox, Safari, Edge
   - Verify WebGL support detection

4. **Mobile Testing**
   - Test on iOS Safari, Android Chrome
   - Verify touch interactions (pan, zoom)
   - Check performance (target: 30 FPS on mobile)

5. **Visual QA**
   - Compare against mockups/design
   - Verify color accuracy
   - Check tooltip positioning
   - Test all zoom levels (1-12)

6. **User Acceptance Testing**
   - Internal demo with stakeholders
   - Collect feedback on "blob" feel
   - Iterate on color scale if needed

**Estimated Time**: 6-8 hours
**Assigned To**: Full team
**Success Metric**:
- End-to-end flow works (backend → frontend)
- Performance meets targets (60 FPS desktop, 30 FPS mobile)
- No visual bugs
- Positive feedback from stakeholders

---

### Phase 2.5: Documentation & Deployment (Day 7)

**Goal**: Document architecture, deploy to staging.

**Tasks**:

1. **Update Documentation**
   - Add hexmap section to `backend/README.md`
   - Document API endpoint in OpenAPI spec
   - Update frontend component docs

2. **Create Demo Video**
   - Record 2-minute screen capture
   - Show: zoom levels, color scale, hover tooltip, mode toggle
   - Save to `docs/demos/iter2-hexmap-demo.mp4`

3. **Write ADR Review**
   - Update `docs/decisions/ADR-0003-hexagonal-heatmap-architecture.md`
   - Mark status as "Accepted"
   - Add lessons learned

4. **Deploy to Staging**
   ```bash
   # Backend
   cd backend
   docker build -t observatory-backend:iter2 .
   docker push gcr.io/project/observatory-backend:iter2

   # Frontend
   cd frontend
   npm run build
   gsutil -m rsync -r dist gs://observatory-frontend-staging
   ```

5. **Monitor Performance**
   - Set up CloudWatch/Stackdriver metrics
   - Track API response times
   - Monitor cache hit rates

**Estimated Time**: 4-6 hours
**Assigned To**: DevOps + Documentation Agent
**Success Metric**:
- Staging deployment successful
- Demo video approved
- Documentation complete

---

## Risk Mitigation

### High-Impact Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **deck.gl bundle too large** | Medium | High | Code splitting, lazy loading deck.gl |
| **Poor performance (<30 FPS)** | Low | Critical | Fallback to Turf.js approach, reduce hex count |
| **H3 polyfill errors (country geometries)** | Medium | Medium | Validate geometries, handle exceptions gracefully |
| **Color scale not intuitive** | Medium | Low | A/B test multiple scales, user preference setting |

### Low-Impact Risks

| Risk | Mitigation |
|------|------------|
| Browser WebGL support issues | Detect WebGL, fallback to 2D circles |
| Country GeoJSON download fails | Bundle GeoJSON with backend image |
| Cache invalidation bugs | Add manual cache clear button |

---

## Rollback Plan

If hexmap implementation fails or performs poorly:

1. **Immediate Rollback**: Disable "Heatmap" toggle, default to "Classic" mode
2. **Keep Backend Endpoint**: Leave `/v1/hexmap` for future iterations
3. **Document Blockers**: Create GitHub issues for unresolved problems
4. **Iteration 3 Pivot**: Focus on other features (e.g., historical playback)

**Rollback Trigger Conditions**:
- Performance <20 FPS on desktop
- Critical bugs in production
- Negative user feedback (>50% prefer classic mode)

---

## Dependencies

### External Libraries
- `h3-js` (frontend): MIT license, 50 KB
- `deck.gl`: MIT license, 400 KB
- `h3` (Python): Apache 2.0, active maintenance
- `shapely`: BSD license, geospatial standard

### Data Files
- `countries.geojson`: Public domain, 5 MB
- Alternative: Simplified geometries (1 MB) for faster loading

### Backend Services
- Existing `/v1/flows` endpoint (provides country intensities)
- Redis cache (optional but recommended)

---

## Performance Targets

### Backend API
| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| Response time (cache hit) | <200ms | <500ms |
| Response time (cache miss) | <2s | <5s |
| Payload size (10 countries, res 3) | <200 KB (gzipped) | <500 KB |
| Cache hit rate | >80% | >60% |

### Frontend Rendering
| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| FPS (5k hexes, desktop) | 60 FPS | 30 FPS |
| FPS (5k hexes, mobile) | 30 FPS | 15 FPS |
| Initial render time | <1s | <3s |
| Zoom transition smoothness | No jank | Acceptable jank |

---

## Testing Checklist

### Unit Tests
- [ ] Backend: `test_hex_generator.py` (10+ tests)
- [ ] Backend: `test_hexmap_endpoint.py` (5+ tests)
- [ ] Frontend: `HexagonHeatmapLayer.test.tsx` (optional for Iteration 2)

### Integration Tests
- [ ] Backend → Frontend data flow
- [ ] Zoom → Resolution change → API call
- [ ] Toggle Classic ↔ Heatmap mode

### Performance Tests
- [ ] FPS benchmark (1k, 5k, 10k hexes)
- [ ] API response time (cache hit/miss)
- [ ] Bundle size check (<1.5 MB total)

### Visual Tests
- [ ] Screenshot comparison (before/after)
- [ ] Color scale accuracy
- [ ] Tooltip positioning
- [ ] Mobile responsiveness

---

## Estimated Effort

| Phase | Hours | Days (8h/day) |
|-------|-------|---------------|
| 2.1 Setup & Dependencies | 2 | 0.25 |
| 2.2 Backend Hexmap API | 10 | 1.25 |
| 2.3 Frontend Hexagon Layer | 12 | 1.5 |
| 2.4 Integration & Testing | 8 | 1 |
| 2.5 Documentation & Deployment | 5 | 0.625 |
| **Total** | **37 hours** | **~5 days** |

**Buffer**: +2 days for unexpected issues = **7 days total**

---

## Success Metrics (Post-Launch)

**Week 1 After Deployment**:
- [ ] >70% of users try "Heatmap" mode
- [ ] <5 bug reports related to hexmap
- [ ] Average FPS >45 on desktop (via analytics)
- [ ] <1% error rate on `/v1/hexmap` endpoint

**Month 1 After Deployment**:
- [ ] >50% of sessions use "Heatmap" as default
- [ ] Positive feedback on "organic" feel in user surveys
- [ ] <2s average API response time (95th percentile)

---

## Next Steps (Iteration 3)

**Features to Add**:
1. **3D Elevation**: Hex height = intensity (deck.gl `extruded: true`)
2. **Gaussian Blur**: Apply CSS filter for smooth blobs
3. **K-Ring Smoothing**: Backend spreads intensity to neighbor hexes
4. **Animated Transitions**: Pulse effect for high-activity hexes
5. **Historical Playback**: Time slider showing intensity changes over 24h

**Estimated Effort**: 3-4 days

---

## Resources

### Documentation
- [H3 Documentation](https://h3geo.org/)
- [deck.gl Tutorials](https://deck.gl/docs/get-started/using-with-react)
- [ADR-0003: Hexagonal Heatmap Architecture](../decisions/ADR-0003-hexagonal-heatmap-architecture.md)

### Code Examples
- [POC Frontend](../examples/hex-poc-frontend.tsx)
- [POC Backend](../examples/hex-poc-backend.py)

### Design References
- [Uber H3 Blog Post](https://www.uber.com/blog/h3/)
- [Weather Radar Heatmaps](https://www.weather.gov/radar) (inspiration)
- [Traffic Heatmaps (Google Maps)](https://maps.google.com) (inspiration)

---

**Approval Status**: Pending review
**Reviewed By**: [Pending]
**Approved Date**: [Pending]

---

*Document Version: 1.0*
*Last Updated: 2025-01-13*
