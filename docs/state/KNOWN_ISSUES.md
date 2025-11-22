# Known Issues - Radar Rebuild (2025-11-22)

**Status:** Post-Docker Cleanup
**Last Updated:** 2025-11-22

## Critical Issues

### 1. Map Blank/Loading Issues
**Status:** RESOLVED (Docker Build Fixed)
**Impact:** High
**Description:**
- Map was showing blank screen or infinite loading
- Root cause: TypeScript build errors preventing frontend compilation
- Also caused by lack of `.dockerignore` files leading to slow builds

**Resolution:**
- Fixed TypeScript errors in:
  - `useNodeLayer.ts` (return types for `getPosition`, `onHover`, `onClick`)
  - `useGaussianRadarLayer.ts` (onHover return type)
  - `MapContainer.tsx` (implicit any types)
  - `DataStatusBar.tsx` (removed obsolete hexmapData references)
- Deleted unused `FlowLayer.tsx`
- Added `.dockerignore` files for frontend and backend
- Stack now builds and runs cleanly

### 2. Flow Animation Not Working
**Status:** BLOCKED
**Impact:** Medium (visual enhancement, not core functionality)
**Description:**
- Flow lines are currently static (no animation)
- Previous attempts to animate flows have failed:
  - **TripsLayer Approach:** Caused blank screen/crashes
  - **Shader-based Approach:** Also caused blank screen (WebGL errors with `varying` keyword)

**Attempted Solutions:**
1. `TripsLayer` from `@deck.gl/geo-layers`
   - Generated great circle paths using `@turf/turf`
   - Assigned timestamps for animation
   - Result: Blank screen, likely due to data format mismatch or layer conflicts

2. Custom `AnimatedArcLayer` with GLSL shaders
   - Extended `ArcLayer` with custom vertex/fragment shaders
   - Used `time` uniform for pulsing effect
   - Result: Shader compilation error (`varying` is reserved in WebGL 2.0/GLSL 300 es)

**Next Steps:**
- Option A: Use CSS-based overlays or DOM animations (safer, less performant)
- Option B: Simplify shader approach (avoid `varying`, use `out`/`in` for GLSL 300)
- Option C: Investigate `PathLayer` with `widthScale` animation
- **Recommendation:** Defer until core stability is confirmed for a few days

### 3. Data Display Issues
**Status:** NEEDS INVESTIGATION
**Impact:** Unknown (reported by user)
**Description:**
- User mentioned "new map and information issue"
- Specifics not yet documented
- Possible areas:
  - Country sidebar not showing correct data
  - Tooltip information missing/incorrect
  - Flow intensity/heat values not displaying
  - Data status bar showing errors

**Actions Needed:**
1. User to provide specific details about what's not working
2. Check browser console for errors
3. Verify backend API responses (`/v1/flows`)
4. Check data transformation in frontend stores

## Minor Issues

### 4. Code Cleanup Needed
**Status:** OPEN
**Impact:** Low (technical debt)
**Description:**
- Removed multiple deprecated files during cleanup
- Some old handoff documents archived
- Backend has unused `hexmap_generator.py` (deleted)

**Actions:**
- Continue monitoring for unused code
- Consider adding ESLint/TSLint rules to catch dead code

### 5. Docker Build Performance
**Status:** IMPROVED
**Impact:** Low (developer experience)
**Description:**
- Initial builds were very slow (5+ minutes) due to including `node_modules` in build context
- Now resolved with `.dockerignore` files
- Build time reduced to ~2 minutes

## Environment State

**Working Components:**
- ✅ Backend API (http://localhost:8000)
- ✅ Frontend Server (http://localhost:5173)
- ✅ PostgreSQL
- ✅ Redis
- ✅ Docker Compose orchestration

**Non-Working Components:**
- ❌ Flow animation (static only)
- ❓ Data display (needs user clarification)

## Clean Restart Procedure

If issues arise, follow this procedure:

```bash
# From repo root
make down                    # Stop all services
docker container prune -f    # Remove stopped containers
make up                      # Rebuild and restart (takes ~2 mins)
```

Then verify:
1. Backend health: `curl http://localhost:8000/health`
2. Frontend loads: Open http://localhost:5173
3. Map displays with static flow lines

## Next Session Priorities

1. **Investigate "information issue"** - Get specifics from user
2. **Verify data display** - Check all UI components showing correct data
3. **Plan animation strategy** - After stability confirmed, choose safest approach
4. **Consider performance testing** - Ensure stable under load before adding features
