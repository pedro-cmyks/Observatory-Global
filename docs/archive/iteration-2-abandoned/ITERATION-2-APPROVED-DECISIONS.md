# Iteration 2 - Approved Decisions & Implementation Kickoff

**Status**: ✅ APPROVED - Implementation Starting
**Date**: 2025-11-13
**Decision Maker**: Pedro (Product Owner)
**Timeline**: 12 working days (adjusted to 7-9 days for Phase 1)

---

## User Decisions Summary

### Q1: Hex Heatmap Scope → **Option B (Blob Smoothing)**
**Decision**: Implement hex grid with dynamic blobs and smoothing
- NOT just basic discrete hexes (Option A)
- NOT full 3D elevation yet (Option C)
- **Vision**: Heat should feel "organic and alive, not discrete or blocky"

**Implementation Details**:
- H3 hexagonal grid with intensity colors
- Gaussian blur filter for organic blob effect
- K-ring smoothing (backend aggregation)
- Smooth transitions and interpolation
- Timeline: 7-9 days (vs 5-7 for basic)

---

### Q2: Data Sources → **Option B (HN + Mastodon)**
**Decision**: Integrate Hacker News + Mastodon first
- Both free, no authentication required
- Real-time signals (0-2 second latency)
- High-quality global coverage
- Defer RSS to Iteration 3

**Implementation Details**:
- Hacker News Firebase API (12-16 hours)
- Mastodon multi-instance streaming (12-16 hours)
- Total effort: 20-24 hours
- Sources after Iteration 2: Wikipedia, GDELT, Trends, HN, Mastodon (5 total)

---

### Q3: BERTopic Depth → **Option B+ (Full BERTopic)**
**Decision**: Full BERTopic with simple stance detection
- User specified "Full BERTopic, simple stance detection"
- Move beyond basic sentence-transformers
- Implement UMAP + HDBSCAN clustering
- Add lightweight stance markers

**Implementation Details**:
- sentence-transformers for embeddings
- UMAP dimensionality reduction
- HDBSCAN hierarchical clustering
- TextBlob or VADER for stance/sentiment
- Timeline: 8-10 hours (full implementation)

---

### Q4: PostgreSQL Timing → **Option B (Week 2-3)**
**Decision**: Implement PostgreSQL in parallel during Week 2-3
- Don't block early visualization work
- BackendFlow and DataGeoIntel coordinate in Week 2
- Allows frontend to progress independently

**Implementation Details**:
- Week 1: Focus on GDELT + hexmap
- Week 2: Enable PostgreSQL, run migration
- Week 2-3: Wire persistence to API endpoints
- No blocking dependencies

---

### Q5: Frontend Connection → **Option A (Day 1)**
**Decision**: Connect frontend to backend immediately (Day 1)
- Remove mock data ASAP
- UI evolves in sync with backend
- Real feedback loop from start

**Implementation Details**:
- Uncomment API call in mapStore.ts (5 minutes)
- Test with current backend endpoints
- Validate integration works
- **Priority**: Do this FIRST before other work

---

### Q6: Flow Animations → **Option C (Pulsing Only)**
**Decision**: Implement pulsing arcs only (not full timeline replay)
- Quick win that makes flows feel "alive"
- Defer timeline replay to Iteration 3
- Focus on stable data flow model first

**Implementation Details**:
- CSS-based pulsing animation
- Pulse speed based on heat intensity
- Smooth transitions (no performance impact)
- Timeline: 2-3 hours

---

## Vision Alignment: "Waze for Information"

**User's Long-Term Vision**:
> "A dynamic, geo-semantic 'Waze for information'"

**Iteration 2 Moves Toward This By**:
1. **Dynamic**: Blob smoothing makes heat feel organic and alive
2. **Geo-semantic**: Hexagonal spatial distribution + BERTopic narrative clustering
3. **Real-time**: HN + Mastodon provide 0-2 second latency signals
4. **Navigation-like**: Pulsing flows show information "traffic" in motion

---

## Adjusted Timeline (Based on Decisions)

### Week 1: Foundation & Critical Path (Days 1-5)

**Day 1 - IMMEDIATE**:
- ✅ **Connect Frontend to Backend** (Frontend Map - 1 hour)
  - Uncomment API call in mapStore.ts
  - Remove mock data
  - Test with real /v1/flows endpoint
  - Validate all existing features work

**Day 1-2 - PostgreSQL Setup**:
- 🔧 **Enable PostgreSQL** (Backend Flow - 2 hours)
  - Uncomment postgres service in docker-compose.yml
  - Start PostgreSQL container
  - Run migration 002_comprehensive_flow_schema.sql
  - Verify tables created correctly

**Day 2-3 - GDELT Critical Path**:
- 📡 **Implement GDELT Real Data** (DataGeoIntel - 8-10 hours)
  - Download and parse GDELT CSV files
  - Extract themes, locations, tones
  - Integrate with NLP pipeline
  - Achieve 100% real data (no fallbacks)
  - Write comprehensive tests

**Day 3-4 - Hexmap Backend**:
- 🗺️ **Implement /v1/hexmap Endpoint** (Backend Flow - 10-12 hours)
  - Install H3 Python library
  - Generate hex grids with intensity
  - K-ring smoothing for blob effect (backend aggregation)
  - Redis caching (5-min TTL)
  - API response <2s target

**Day 5 - Integration Check**:
- ✅ Validate frontend connects to hexmap API
- ✅ Test end-to-end data flow
- ✅ Performance benchmarking

---

### Week 2: Visualization & Data Expansion (Days 6-9)

**Day 6-7 - Hexmap Frontend with Blob Effect**:
- 🎨 **Implement Hexagon Layer** (Frontend Map - 12-14 hours)
  - Install deck.gl, H3-js
  - Create HexagonHeatmapLayer component
  - Implement Gaussian blur filter (CSS)
  - Zoom-based resolution switching
  - View mode toggle (Classic/Heatmap)
  - 60 FPS performance validation

**Day 8 - Hacker News Integration**:
- 📰 **HN Firebase Client** (DataGeoIntel - 12-16 hours)
  - Connect to HN Firebase API
  - Fetch top stories + comments
  - Extract topics and sentiment
  - Real-time polling (30s)

**Day 9 - Mastodon Integration**:
- 🐘 **Mastodon Streaming** (DataGeoIntel - 12-16 hours)
  - Connect to 3-5 Mastodon instances
  - WebSocket streaming
  - Language detection and filtering
  - Deduplication across instances

**Day 9-10 - BERTopic Upgrade**:
- 🧠 **Full BERTopic Implementation** (Backend Flow - 8-10 hours)
  - sentence-transformers embeddings
  - UMAP dimensionality reduction
  - HDBSCAN clustering
  - Stance detection (TextBlob/VADER)
  - Store stance in PostgreSQL

---

### Week 3: Integration & Polish (Days 10-12)

**Day 10-11 - PostgreSQL Wiring**:
- 💾 **Persistence Layer** (Backend Flow - 8-10 hours)
  - Modify /v1/trends to persist snapshots
  - Modify /v1/flows to persist hotspots/flows
  - Implement read-through cache (Redis → PostgreSQL)
  - Integration testing

**Day 11 - Pulsing Animations**:
- ✨ **Flow Arc Pulsing** (Frontend Map - 4-6 hours)
  - CSS-based pulse effect
  - Pulse speed based on heat
  - Smooth transitions
  - Toggle animation on/off

**Day 12 - Final Polish**:
- 📝 **Documentation & Demo** (All Agents)
  - Add narrative content preview (Frontend)
  - Create ADR-0005, ADR-0006 (Orchestrator)
  - Update README and API docs
  - Demo preparation
  - Screenshots/GIFs

---

## Branch Strategy

### Feature Branches (7 PRs)

**PR #1**: Frontend connection + PostgreSQL setup
- Branch: `feat/iter2-immediate/frontend-backend-connection`
- Agent: Frontend Map + Orchestrator
- Effort: 3 hours
- Merge target: Day 1

**PR #2**: GDELT real data implementation
- Branch: `feat/iter2-datageointel/gdelt-real-data`
- Agent: DataGeoIntel
- Effort: 8-10 hours
- Merge target: Day 3

**PR #3**: Hexmap backend API
- Branch: `feat/iter2-backendflow/hexmap-api`
- Agent: Backend Flow
- Effort: 10-12 hours
- Merge target: Day 4

**PR #4**: Hexmap frontend with blob effect
- Branch: `feat/iter2-frontendmap/hexmap-visualization`
- Agent: Frontend Map
- Effort: 12-14 hours
- Merge target: Day 7

**PR #5**: HN + Mastodon integration
- Branch: `feat/iter2-datageointel/hn-mastodon`
- Agent: DataGeoIntel
- Effort: 20-24 hours
- Merge target: Day 9

**PR #6**: BERTopic + PostgreSQL wiring
- Branch: `feat/iter2-backendflow/bertopic-persistence`
- Agent: Backend Flow
- Effort: 16-20 hours
- Merge target: Day 11

**PR #7**: Pulsing animations + polish
- Branch: `feat/iter2-final/animations-polish`
- Agent: Frontend Map + Orchestrator
- Effort: 6-8 hours
- Merge target: Day 12

---

## Success Criteria (Aligned with Vision)

### Technical Metrics
- [ ] Data completeness: 90%+ real data (5 sources)
- [ ] Hexmap performance: 60 FPS with 5,000+ hexagons
- [ ] Blob effect: Subjectively "organic and alive"
- [ ] API response: <2s for /v1/hexmap
- [ ] Frontend-backend: 100% real data (0% mock)
- [ ] PostgreSQL: Successfully storing time-series data

### User Experience Metrics
- [ ] Heat distribution feels spatial (not just country dots)
- [ ] Flows pulse with intensity (feels dynamic)
- [ ] Narrative content visible in sidebar
- [ ] Can toggle between Classic and Heatmap modes
- [ ] Page load time <3s

### "Waze for Information" Indicators
- [ ] User can "see" information traffic patterns
- [ ] Geographic heat distribution is intuitive
- [ ] Real-time updates feel responsive (<2s latency)
- [ ] Narrative clustering reveals story connections
- [ ] System feels "alive" and continuously updating

---

## Risk Mitigation

### Critical Risks Addressed

**Risk: Blob effect doesn't feel organic**
- Mitigation: Implement both Gaussian blur (CSS) AND k-ring smoothing (backend)
- Fallback: Adjust blur radius and k-ring parameters iteratively
- User validation: Subjective feedback required

**Risk: BERTopic performance**
- Mitigation: Async background processing, cache embeddings
- Fallback: Keep TF-IDF as fallback if latency >5s
- Monitor: API response times daily

**Risk: Multi-source integration complexity**
- Mitigation: Implement HN first (simpler), then Mastodon
- Fallback: Can launch with HN-only if Mastodon blocks
- Timeline buffer: 2 days built into Week 2

---

## Daily Standup Format (Async)

Each agent will update a daily progress file:

**File**: `docs/progress/iter2-day-{N}.md`

**Format**:
```markdown
# Iteration 2 - Day {N} Progress

## DataGeoIntel Agent
- ✅ Completed: [task]
- 🚧 In Progress: [task]
- ⏸️ Blocked: [blocker if any]
- 📊 Metrics: [data quality, API success rate]

## Backend Flow Agent
- ✅ Completed: [task]
- 🚧 In Progress: [task]
- ⏸️ Blocked: [blocker if any]
- 📊 Metrics: [API latency, cache hit ratio]

## Frontend Map Agent
- ✅ Completed: [task]
- 🚧 In Progress: [task]
- ⏸️ Blocked: [blocker if any]
- 📊 Metrics: [FPS, bundle size]

## Orchestrator Notes
- Integration status: [green/yellow/red]
- Risks surfaced: [any new risks]
- Decisions needed: [user input required?]
```

---

## Immediate Next Steps (Starting Now)

### 1. Frontend Connection (IMMEDIATE - 1 hour)
**Agent**: Frontend Map
**Task**: Connect frontend to backend, remove mock data
**Branch**: `feat/iter2-immediate/frontend-backend-connection`

**Steps**:
1. Create feature branch
2. Edit `frontend/src/store/mapStore.ts`:
   - Uncomment API call (lines 87-97)
   - Remove mock data import
3. Test with real `/v1/flows` endpoint
4. Commit and create PR
5. Merge to main

### 2. Enable PostgreSQL (2 hours)
**Agent**: Backend Flow (with Orchestrator)
**Task**: Uncomment PostgreSQL, run migration
**Branch**: Same as #1 (can combine)

**Steps**:
1. Edit `infra/docker-compose.yml`: Uncomment postgres service
2. Start PostgreSQL: `docker compose up -d postgres`
3. Run migration: `python -m app.db.migrate`
4. Verify tables: `docker compose exec postgres psql -U observatory -c '\dt'`
5. Commit and include in PR #1

### 3. Create Remaining Feature Branches (15 min)
**Agent**: Orchestrator
**Task**: Set up branch structure for all PRs

**Branches to create**:
- `feat/iter2-datageointel/gdelt-real-data`
- `feat/iter2-backendflow/hexmap-api`
- `feat/iter2-frontendmap/hexmap-visualization`
- `feat/iter2-datageointel/hn-mastodon`
- `feat/iter2-backendflow/bertopic-persistence`
- `feat/iter2-final/animations-polish`

---

## Approval Confirmation

✅ **User Approval**: Confirmed
✅ **Decisions Documented**: This file
✅ **Agent Tasks**: Defined in ITERATION-2-MASTER-PLAN.md
✅ **Branch Strategy**: Defined above
✅ **Success Criteria**: Aligned with "Waze for Information" vision

**Status**: 🚀 **READY TO START IMPLEMENTATION**

---

## Communication

**Daily Updates**: `docs/progress/iter2-day-{N}.md`
**PR Template**: Include acceptance criteria from master plan
**Demo Day**: Friday of each week (Days 5, 10, 12)
**User Check-ins**: As needed via async updates

---

**Let's build a live intelligence map! 🗺️✨**

---

*Approved by: Pedro*
*Documented by: Orchestrator Agent*
*Date: 2025-11-13*
*Version: 1.0 (Approved)*
