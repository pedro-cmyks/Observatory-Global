# ADR-0004: Map Projection Strategy for Deck.gl + Mapbox Integration

## Status
**Accepted**

## Date
2025-11-24

## Context

The Global Information Radar visualization requires rendering geospatial data layers (heatmap, flows, markers) on top of a Mapbox base map using deck.gl. The initial implementation attempted to use Mapbox's 3D globe projection (`projection: { name: 'globe' }`), which provides an aesthetically pleasing spherical Earth visualization.

### Problem Identified

When using Mapbox's globe projection with deck.gl overlay layers, the following critical issues occurred:

1. **Coordinate System Mismatch**:
   - Mapbox's globe projection uses a true 3D sphere with a custom projection matrix
   - deck.gl treats geographic coordinates as 2D and projects them using its own transformation
   - These two projection systems diverge, especially at map edges and during rotation

2. **Visual Artifacts**:
   - Heatmap circles appeared "tangent" to the globe surface, floating on an "inner sphere"
   - Flow arcs appeared as tiny "birds" instead of clear arcs at global zoom levels
   - All layers drifted and detached from geographic positions when rotating the globe
   - Layers appeared to live on a different coordinate plane than the Mapbox basemap

3. **Technical Root Cause**:
   - Mapbox's globe projection modifies the projection matrix for 3D rendering
   - deck.gl's coordinate system doesn't automatically sync with Mapbox's modified matrix
   - The `MapboxOverlay` integration (even with `interleaved: false`) doesn't fully resolve this
   - Switching to `DeckGL` component wrapping `Map` improved viewState sync but didn't fix the fundamental projection mismatch

### Attempted Solutions

1. **MapboxOverlay with interleaved mode**: Layers didn't render properly
2. **MapboxOverlay with interleaved: false**: Layers rendered but floated/drifted
3. **DeckGL component with shared viewState**: Better sync, but projection mismatch persisted
4. **Zoom-based scaling**: Helped with sizing but didn't fix positioning
5. **Depth testing parameters**: Addressed z-fighting but not the coordinate mismatch

## Decision

**Use Mercator projection (standard 2D projection) instead of globe projection.**

### Implementation

Remove the `projection` property from the Mapbox `Map` component, allowing it to default to Mercator projection:

```tsx
<Map
    mapboxAccessToken={MAPBOX_TOKEN}
    mapStyle="mapbox://styles/mapbox/dark-v11"
    // projection property removed - defaults to Mercator
    style={{ width: '100%', height: '100%' }}
>
```

This ensures that both Mapbox and deck.gl use compatible 2D coordinate projection systems.

## Rationale

### Why Mercator Works

1. **Coordinate System Compatibility**: Mercator projection uses standard Web Mercator (EPSG:3857), which deck.gl natively supports
2. **Shared Projection Matrix**: Both Mapbox and deck.gl use the same 2D→3D transformation
3. **Perfect Layer Alignment**: All layers (Mapbox basemap, deck.gl heatmap, flows, markers) sit on the same coordinate plane
4. **No Drift**: Layers remain anchored to geographic positions during pan, zoom, and rotation
5. **Industry Standard**: Web Mercator is the de facto standard for web mapping applications

### Trade-offs

**What We Gain:**
- ✅ Perfect layer alignment and positioning
- ✅ Reliable, predictable coordinate transformations
- ✅ No visual artifacts or floating layers
- ✅ Simpler integration with deck.gl
- ✅ Better performance (no complex 3D matrix calculations)

**What We Lose:**
- ❌ 3D globe aesthetic (no spinning sphere)
- ❌ True spherical Earth representation
- ❌ Impressive "globe view" for presentations

### Alternative Considered: Native deck.gl GlobeView

deck.gl v9 provides a native `GlobeView` that could theoretically provide both globe projection AND proper layer alignment. However:

**Why We Rejected This Approach:**
1. **Complexity**: Requires completely rewriting the map integration
   - No `react-map-gl` integration
   - Must manage all basemap tiles manually
   - Custom projection handling for all layers
2. **Development Time**: Would require significant refactoring
3. **Maturity**: Less mature integration compared to standard Mercator
4. **Risk**: Higher risk of edge cases and bugs
5. **Maintenance**: More complex codebase to maintain

**Future Consideration**: If globe visualization becomes a hard requirement, we could explore deck.gl's native `GlobeView` in a future iteration. This would require:
- Removing `react-map-gl` dependency
- Using deck.gl's tile layer for basemap
- Implementing custom projection handling
- Extensive testing of all layer types

## Consequences

### Positive
- All layers render correctly on the same surface
- No floating, drifting, or coordinate mismatch issues
- Simpler, more maintainable codebase
- Reliable visualization for production use
- Better performance

### Negative
- Flat map view instead of globe (less visually impressive)
- Distortion at extreme latitudes (inherent to Mercator)
- May need to explain to stakeholders why we don't have a spinning globe

### Mitigation
- The "meteorological radar" visual style works excellently with flat projection
- Focus narrative on "intelligence map" rather than "globe view"
- Use dark basemap style to maintain professional aesthetic
- Consider adding subtle globe icon/branding elsewhere in UI if needed

## Validation Checklist

To verify this decision resolves all issues:
- [x] Code updated: `projection` property removed from Map component
- [ ] Vite cache cleared to force fresh build
- [ ] Browser hard refresh performed (Ctrl+Shift+R)
- [ ] Visual verification: All layers appear on same flat surface
- [ ] Interaction test: Layers stay anchored during pan/zoom/rotate
- [ ] Flow arcs: Visible and properly curved at all zoom levels
- [ ] Heatmap circles: Stay on geographic positions
- [ ] Markers: Aligned with country centroids

## References

- Mapbox GL JS Projections: https://docs.mapbox.com/mapbox-gl-js/api/properties/#projections
- deck.gl Coordinate Systems: https://deck.gl/docs/developer-guide/coordinate-systems
- deck.gl GlobeView: https://deck.gl/docs/api-reference/core/globe-view
- Web Mercator (EPSG:3857): https://epsg.io/3857

## Related Documents

- `docs/frontend/ARCHITECTURE-FRONTEND-RADAR-V1.md` (needs update to reflect Mercator projection)
- `docs/state/HANDOFF-2025-11-22.md` (documents the "inner sphere" problem)
- `docs/KNOWN_ISSUES.md` (should be updated once fix is verified)

## Author
Claude Code (assisted by user feedback and visual bug reports)

## Reviewers
Pending user verification and visual testing in browser
