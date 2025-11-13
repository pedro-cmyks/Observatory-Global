# Observatory Global - Iteration 2 Master Plan

**Status**: Ready for Review & Approval
**Target Timeline**: 10-12 working days
**Start Date**: TBD (pending approval)
**Agent Coordination**: Orchestrator + 3 specialist agents

---

## Executive Summary

Iteration 2 transforms the MVP from a proof-of-concept into a **live intelligence map** with:
- Real data from 5+ sources (GDELT + 3 new free sources)
- Hexagonal heatmap visualization showing information flow across space
- BERTopic-based narrative clustering with stance detection
- PostgreSQL persistence for historical analysis
- Animated flow arcs with pulsing intensity

**Key Outcomes**:
1. Move from 57% real data → **90%+ real data**
2. Replace country centroids → **Dynamic hex-tile heatmap**
3. Simple TF-IDF → **BERTopic narrative clustering**
4. Ephemeral data → **PostgreSQL time-series persistence**
5. Mock frontend → **Fully connected live visualization**

---

## Part 1: Current State Assessment

### What's Working (Foundation Strengths)
✅ Backend API architecture (FastAPI, versioned endpoints)
✅ Flow detection algorithm (TF-IDF + exponential decay)
✅ Frontend UI components (8 React components, Zustand state)
✅ Wikipedia data source (100% real data)
✅ Documentation quality (ADRs, agent specs, comprehensive docs)
✅ Docker containerization (backend, frontend, Redis running)

### Critical Gaps Identified
❌ GDELT implementation (0% real data - **blocker**)
❌ Frontend disconnected from backend (using mock data)
❌ PostgreSQL schema ready but not wired
❌ No Redis caching active (performance issue)
❌ Google Trends has simulated counts (70% real data)
❌ Single-point country centroids (not spatial heat distribution)
❌ No narrative content analysis (just topic labels)

### Data Completeness Score: 57%
- Wikipedia: 100% (real pageviews)
- Google Trends: 70% (real topics, fake counts)
- GDELT: 0% (placeholder only)

---

## Part 2: Agent Research Findings Summary

### 2A. Hexagonal Heatmap Architecture (ADR-0003)

**Recommended Solution**: H3 (Uber) + deck.gl

**Technical Stack**:
- Frontend: Mapbox GL + deck.gl H3HexagonLayer
- Backend: FastAPI `/v1/hexmap` endpoint with H3 Python
- Data: countries.geojson (5 MB, public domain)

**Performance Targets**:
- 60 FPS with 5,000 hexagons (desktop)
- <2s API response time
- Dynamic zoom resolution (4 levels: global → country)

**Phased Approach**:
- **Phase 2.1** (Iteration 2): MVP hex grid with intensity coloring
- **Phase 2.2** (Iteration 3): Blob smoothing with Gaussian blur + k-ring
- **Phase 2.3** (Iteration 4): 3D elevation, animated transitions

**Files Delivered**:
- Architecture document: `docs/decisions/ADR-0003-hexagonal-heatmap-architecture.md`
- Implementation plan: `docs/planning/iter2-hexmap-implementation.md`
- Frontend POC: `docs/examples/hex-poc-frontend.tsx`
- Backend POC: `docs/examples/hex-poc-backend.py`
- Quick reference: `docs/examples/hexmap-quick-reference.md`

---

### 2B. PostgreSQL Schema Design

**6 Core Tables**:
1. **countries**: Reference table (250 rows)
2. **topics**: Normalized topic labels (~10K-100K rows)
3. **topic_snapshots**: Time-series core, weekly partitions (~38K rows/day for 10 countries)
4. **hotspots**: Pre-computed country intensity (~960 rows/day)
5. **flows**: Information flows between countries (~1,296 rows/day)
6. **stance_history**: Narrative evolution tracking (~1,920 rows/day)

**Retention Strategy** (4-tier hybrid):
- Hot (0-30 days): Full 15-min granularity
- Warm (30-90 days): Hourly aggregation (4x reduction)
- Cold (90 days - 1 year): Daily aggregation, S3 Parquet export
- Delete (>1 year): Purge, keep monthly summaries

**Storage Estimates**:
- 10 countries: 14 MB/day, 6.8 GB/year
- 50 countries: 70 MB/day, 27 GB/year
- AWS RDS cost: $60-110/month

**Migration Timeline**: 5 weeks (parallel with Iteration 2)

**Files Delivered**:
- Schema design: `docs/database-schema-design.md`
- Migration SQL: `backend/app/db/migrations/002_comprehensive_flow_schema.sql`
- Migration runner: `backend/app/db/migrate.py`
- Quick reference: `docs/database-schema-quickref.md`

---

### 2C. New Data Sources Feasibility

**Top 3 Recommendations** (all free, no auth required):

**#1: Hacker News Firebase API** (Score: 9.5/10)
- Auth: NONE
- Rate limit: Unlimited
- Real-time: Yes (0-5 seconds)
- Coverage: Tech/startup narratives globally
- Implementation: 12-16 hours

**#2: Mastodon Public API** (Score: 9.0/10)
- Auth: OPTIONAL (not required for public timeline)
- Rate limit: 300 req/5min per instance
- Real-time: Yes (WebSocket streaming, 0-2 seconds)
- Coverage: Global, decentralized, 10K-50K daily posts
- Implementation: 12-16 hours

**#3: RSS News Aggregation** (Score: 8.5/10)
- Auth: Varies (most free)
- Rate limit: Aggregator-friendly
- Real-time: 15-60 minute polling
- Coverage: 20-30 major outlets (BBC, Reuters, AP, Al Jazeera, etc.)
- Implementation: 4-6 hours

**3-Layer Architecture**:
```
Layer 1: EMERGING (HN + Mastodon) → 0-2 min latency
Layer 2: VALIDATION (RSS News) → 15-60 min latency
Layer 3: EXISTING (Wikipedia, GDELT, Trends) → baseline
```

**Files Delivered**:
- Implementation guide: `infra/DATA_SOURCES_IMPLEMENTATION.md`
- Feasibility study: `infra/DATA_SOURCES_FEASIBILITY.md`
- Quick start: `infra/QUICK_START.txt`
- Comparison matrix: `infra/COMPARISON_MATRIX.txt`

---

## Part 3: Clarifying Questions for User

Before finalizing agent tasks, please clarify:

### Question 1: Hex Heatmap MVP Scope
The hex architecture is designed in phases. For Iteration 2, should we:
- **Option A**: Basic hex grid with intensity colors only (5-7 days)
- **Option B**: Basic grid + Gaussian blur for "blob" effect (7-9 days)
- **Option C**: Full implementation with 3D elevation and animations (10-12 days)

**Recommendation**: Option A for Iteration 2, Option B for Iteration 3

### Question 2: Data Source Priority
We have 3 new sources ready to integrate. Should we:
- **Option A**: Implement all 3 in parallel (HN + Mastodon + RSS) - 25-30 hours
- **Option B**: Implement HN + Mastodon first (highest value) - 20-24 hours
- **Option C**: Implement HN only (quickest win) - 12-16 hours

**Recommendation**: Option B (HN + Mastodon) for Iteration 2, RSS for Iteration 3

### Question 3: BERTopic Integration Depth
BERTopic can replace TF-IDF for topic modeling. Should we:
- **Option A**: Full BERTopic with UMAP + HDBSCAN clustering (8-10 hours)
- **Option B**: Basic sentence-transformers embeddings + simple clustering (4-6 hours)
- **Option C**: Defer to Iteration 3, focus on data sources first

**Recommendation**: Option B for Iteration 2 (foundation for Option A in Iteration 3)

### Question 4: PostgreSQL Wiring Timeline
PostgreSQL schema is ready. Should we:
- **Option A**: Wire PostgreSQL in Week 1 (blocks other work)
- **Option B**: Wire PostgreSQL in Week 2-3 (parallel with features)
- **Option C**: Wire PostgreSQL in Week 4 (after features complete)

**Recommendation**: Option B (parallel implementation, lower risk)

### Question 5: Frontend Connection Priority
Frontend is using mock data. Should we:
- **Option A**: Connect frontend ASAP (Day 1, 5 minutes)
- **Option B**: Connect after hex heatmap is ready (Week 2)
- **Option C**: Connect after all backend features are complete (Week 3)

**Recommendation**: Option A (immediate feedback, validates integration)

### Question 6: Flow Arc Animation
You requested animated arcs with pulsing. Should we:
- **Option A**: Implement animated arcs in Iteration 2 (add 2-3 days)
- **Option B**: Keep static arcs in Iteration 2, animate in Iteration 3
- **Option C**: Implement pulsing only (no full animation path yet)

**Recommendation**: Option C (pulsing gives "alive" feel, full animation for Iteration 3)

---

## Part 4: Proposed Agent Tasks (Pending Answers)

### 4A. DataGeoIntel Agent Tasks

**Task 2.1a: Implement GDELT Real Data Fetching**
- **Priority**: CRITICAL (blocks production)
- **Effort**: 8-10 hours
- **Acceptance Criteria**:
  - Download and parse GDELT CSV files (every 15 minutes)
  - Extract relevant fields (themes, locations, tones)
  - Integrate with existing NLP pipeline
  - Achieve 100% real data (no fallbacks)
  - Handle 429 errors gracefully
- **Files Modified**: `backend/app/services/gdelt_client.py`
- **Tests Required**: `tests/test_gdelt_client.py` (10+ unit tests)

**Task 2.1b: Integrate Hacker News Data Source**
- **Priority**: HIGH
- **Effort**: 12-16 hours
- **Acceptance Criteria**:
  - Connect to HN Firebase API
  - Fetch top stories + comments
  - Extract topics and sentiment
  - Store in normalized format
  - Real-time updates (30s polling)
- **Files Created**: `backend/app/services/hn_client.py`
- **Tests Required**: `tests/test_hn_client.py`

**Task 2.1c: Integrate Mastodon Public Timeline**
- **Priority**: HIGH
- **Effort**: 12-16 hours
- **Acceptance Criteria**:
  - Connect to Mastodon public timeline (3-5 instances)
  - WebSocket streaming for real-time posts
  - Language detection and filtering
  - Deduplicate across instances
  - Handle rate limits per instance
- **Files Created**: `backend/app/services/mastodon_client.py`
- **Tests Required**: `tests/test_mastodon_client.py`

**Task 2.1d: Data Quality Monitoring**
- **Priority**: MEDIUM
- **Effort**: 4-6 hours
- **Acceptance Criteria**:
  - Create `/v1/data-health` endpoint
  - Report success rate per source
  - Track latency and volume
  - Alert on degraded sources
- **Files Created**: `backend/app/api/v1/data_health.py`

---

### 4B. Backend Flow Agent Tasks

**Task 2.2a: Implement Hexmap API Endpoint**
- **Priority**: CRITICAL
- **Effort**: 10-12 hours
- **Acceptance Criteria**:
  - Create `/v1/hexmap` endpoint
  - Generate hex grid using H3 library
  - Aggregate intensity per hex
  - Return GeoJSON with intensity values
  - API response <2s (5,000 hexes)
  - Implement Redis caching (5-min TTL)
- **Files Created**:
  - `backend/app/api/v1/hexmap.py`
  - `backend/app/services/hex_generator.py`
  - `backend/app/models/hexmap.py`
- **Tests Required**: `tests/test_hex_generator.py` (15+ tests)

**Task 2.2b: Upgrade to BERTopic for Topic Modeling**
- **Priority**: HIGH
- **Effort**: 6-8 hours
- **Acceptance Criteria**:
  - Replace TF-IDF with sentence-transformers
  - Implement basic clustering (sklearn KMeans or HDBSCAN)
  - Maintain backward compatibility with existing API
  - Improve topic quality (subjective evaluation)
  - Latency <5s for 100 topics
- **Files Modified**: `backend/app/services/nlp.py`
- **Dependencies**: `sentence-transformers`, `transformers`

**Task 2.2c: Add Stance Detection**
- **Priority**: MEDIUM
- **Effort**: 4-6 hours
- **Acceptance Criteria**:
  - Classify sentiment (positive/negative/neutral)
  - Detect stance (pro/against/neutral) for topics
  - Return confidence scores
  - Store in `stance_history` table
- **Files Modified**: `backend/app/services/nlp.py`
- **Dependencies**: `vaderSentiment` or `textblob`

**Task 2.2d: Wire PostgreSQL Persistence**
- **Priority**: HIGH
- **Effort**: 8-10 hours
- **Acceptance Criteria**:
  - Enable PostgreSQL in docker-compose
  - Run migration 002 successfully
  - Modify `/v1/trends` to persist snapshots
  - Modify `/v1/flows` to persist hotspots/flows
  - Implement read-through cache (Redis → PostgreSQL)
  - No API performance degradation
- **Files Modified**:
  - `backend/app/api/v1/trends.py`
  - `backend/app/api/v1/flows.py`
  - `backend/app/db/database.py` (new)
- **Tests Required**: Integration tests for persistence

**Task 2.2e: Implement Redis Caching Layer**
- **Priority**: MEDIUM
- **Effort**: 3-4 hours
- **Acceptance Criteria**:
  - Cache `/v1/flows` responses (15-min TTL)
  - Cache `/v1/hexmap` responses (5-min TTL)
  - Cache hit ratio >95%
  - Response time <200ms for cache hits
- **Files Modified**: `backend/app/core/cache.py` (new)

---

### 4C. Frontend Map Agent Tasks

**Task 2.3a: Implement Hexagon Heatmap Layer**
- **Priority**: CRITICAL
- **Effort**: 12-14 hours
- **Acceptance Criteria**:
  - Install deck.gl and H3-js libraries
  - Create HexagonHeatmapLayer component
  - Connect to `/v1/hexmap` API
  - Render hexagons with intensity colors
  - Zoom-based resolution switching (4 levels)
  - 60 FPS performance with 5,000 hexes
  - Toggle between "Classic" and "Heatmap" modes
- **Files Created**:
  - `frontend/src/components/map/HexagonHeatmapLayer.tsx`
  - `frontend/src/components/map/HexZoomController.tsx`
  - `frontend/src/components/map/ViewModeToggle.tsx`
  - `frontend/src/components/map/HexLegend.tsx`
- **Dependencies**: `deck.gl`, `@deck.gl/react`, `h3-js`

**Task 2.3b: Connect Frontend to Backend API**
- **Priority**: CRITICAL
- **Effort**: 1 hour (5 minutes to uncomment + testing)
- **Acceptance Criteria**:
  - Uncomment API call in mapStore.ts (line 87-97)
  - Remove mock data usage
  - Verify real data displays correctly
  - Handle loading states
  - Handle API errors gracefully
- **Files Modified**: `frontend/src/store/mapStore.ts`

**Task 2.3c: Add Flow Arc Pulsing Animation**
- **Priority**: MEDIUM
- **Effort**: 4-6 hours
- **Acceptance Criteria**:
  - Animate flow arcs with pulsing effect
  - Pulse speed based on heat intensity
  - Smooth CSS transitions (no jank)
  - Toggle animation on/off
  - Performance: no FPS drop
- **Files Modified**: `frontend/src/components/map/FlowLayer.tsx`

**Task 2.3d: Add Narrative Content Preview**
- **Priority**: MEDIUM
- **Effort**: 6-8 hours
- **Acceptance Criteria**:
  - Show sample headlines/snippets in sidebar
  - Display sentiment indicators
  - Show stance markers (pro/against/neutral)
  - Click topic → see full narrative details
  - Smooth scrolling and loading
- **Files Modified**: `frontend/src/components/map/CountrySidebar.tsx`

**Task 2.3e: Add Data Source Indicators**
- **Priority**: LOW
- **Effort**: 2-3 hours
- **Acceptance Criteria**:
  - Show which sources contributed to each topic
  - Visual badges (Wikipedia, GDELT, HN, Mastodon, etc.)
  - Hover → see source details
- **Files Modified**: `frontend/src/components/map/CountrySidebar.tsx`

---

### 4D. Orchestrator Tasks

**Task 2.4a: Create Iteration 2 ADRs**
- **Priority**: HIGH
- **Effort**: 4-6 hours
- **ADRs to Create**:
  - ADR-0004: Data Source Integration Strategy
  - ADR-0005: BERTopic vs TF-IDF Trade-offs
  - ADR-0006: PostgreSQL Retention Policy
  - ADR-0007: Frontend Visualization Mode Toggle
- **Files Created**: `docs/decisions/ADR-000{4,5,6,7}-*.md`

**Task 2.4b: Coordinate PR Strategy**
- **Priority**: HIGH
- **Effort**: Ongoing
- **PR Plan**:
  - PR #4: GDELT implementation + tests
  - PR #5: Hexmap backend + tests
  - PR #6: Hexmap frontend + integration
  - PR #7: HN + Mastodon data sources
  - PR #8: BERTopic + stance detection
  - PR #9: PostgreSQL wiring + migration
  - PR #10: Frontend-backend connection + polish

**Task 2.4c: Update Documentation**
- **Priority**: MEDIUM
- **Effort**: 6-8 hours
- **Updates Required**:
  - Update README with new features
  - Update backend API docs (new endpoints)
  - Create Iteration 2 retrospective
  - Update architecture diagrams
  - Create demo screenshots/GIFs

---

## Part 5: Execution Timeline (12 Days)

### Week 1: Foundation & Critical Path

**Day 1-2: Setup & GDELT** (DataGeoIntel)
- Enable PostgreSQL in docker-compose
- Run migration 002
- Implement GDELT real data fetching
- Write tests and validate 100% real data

**Day 3-4: Hexmap Backend** (Backend Flow)
- Implement `/v1/hexmap` endpoint
- Install H3 Python library
- Generate hex grids with intensity
- Add Redis caching
- Write comprehensive tests

**Day 5: Frontend Connection** (Frontend Map)
- Connect frontend to backend API (5 min)
- Test with real data
- Fix any integration issues
- Validate all existing features work

---

### Week 2: Visualization & Data Expansion

**Day 6-7: Hexmap Frontend** (Frontend Map)
- Install deck.gl and H3-js
- Implement HexagonHeatmapLayer component
- Add zoom-based resolution switching
- Create view mode toggle (Classic/Heatmap)
- Performance testing (60 FPS target)

**Day 8-9: New Data Sources** (DataGeoIntel)
- Implement Hacker News client
- Implement Mastodon client
- Test real-time data ingestion
- Validate data quality

**Day 10: BERTopic Integration** (Backend Flow)
- Replace TF-IDF with sentence-transformers
- Implement basic clustering
- Add stance detection
- Test narrative quality improvements

---

### Week 3: Polish & Integration

**Day 11: PostgreSQL Wiring** (Backend Flow)
- Modify `/v1/trends` to persist snapshots
- Modify `/v1/flows` to persist hotspots/flows
- Implement read-through cache
- Integration testing

**Day 12: Final Polish** (All Agents)
- Add narrative content preview (Frontend)
- Add flow arc pulsing (Frontend)
- Create ADRs (Orchestrator)
- Update documentation
- Demo preparation

---

## Part 6: Success Criteria

### Technical Metrics
- [ ] Data completeness: 90%+ real data (vs 57% current)
- [ ] API response time: <2s for `/v1/hexmap`
- [ ] Frontend FPS: 60 FPS with 5,000 hexagons
- [ ] Cache hit ratio: >95%
- [ ] PostgreSQL migration: successful with 0 data loss
- [ ] Test coverage: >80% for new code

### User Experience Metrics
- [ ] Hex heatmap visible and smooth
- [ ] Real-time data updates (no mock data)
- [ ] Narrative content visible in sidebar
- [ ] Flow arcs show pulsing animation
- [ ] Toggle between Classic and Heatmap modes works
- [ ] Page load time <3s

### Data Quality Metrics
- [ ] GDELT: 100% real data (0 fallbacks)
- [ ] Hacker News: >100 stories/day ingested
- [ ] Mastodon: >500 posts/day ingested
- [ ] Topic quality: subjectively improved (user feedback)
- [ ] Stance detection: >70% accuracy (manual validation)

---

## Part 7: Risk Assessment & Mitigation

### High Risk Items

**Risk 1: H3/deck.gl Performance Issues**
- **Likelihood**: Medium
- **Impact**: High (blocks visualization)
- **Mitigation**: Fallback to Turf.js documented in ADR-0003
- **Contingency**: Use simple circle markers with interpolation

**Risk 2: BERTopic Latency**
- **Likelihood**: Medium
- **Impact**: Medium (slower API responses)
- **Mitigation**: Implement async background processing
- **Contingency**: Keep TF-IDF as fallback option

**Risk 3: PostgreSQL Migration Complexity**
- **Likelihood**: Low
- **Impact**: High (data loss risk)
- **Mitigation**: Comprehensive testing on dev environment first
- **Contingency**: Rollback plan documented in migration README

### Medium Risk Items

**Risk 4: Mastodon Rate Limits**
- **Likelihood**: Medium
- **Impact**: Low (reduced data volume)
- **Mitigation**: Multi-instance strategy (3-5 instances)
- **Contingency**: Reduce polling frequency

**Risk 5: Frontend Bundle Size**
- **Likelihood**: High
- **Impact**: Low (slower initial load)
- **Mitigation**: Code splitting, lazy loading
- **Target**: <2 MB total bundle

---

## Part 8: Dependencies & Prerequisites

### Backend Dependencies
```python
# New dependencies for Iteration 2
h3==3.7.6                # Hexagonal spatial indexing
sentence-transformers    # BERTopic embeddings
transformers             # BERT models
hdbscan                  # Clustering
vaderSentiment          # Sentiment analysis
mastodon.py             # Mastodon API client
psycopg2-binary         # PostgreSQL driver
SQLAlchemy==2.0+        # ORM (optional, for convenience)
```

### Frontend Dependencies
```json
{
  "deck.gl": "^9.0.0",
  "@deck.gl/react": "^9.0.0",
  "@deck.gl/geo-layers": "^9.0.0",
  "h3-js": "^4.1.0"
}
```

### Infrastructure
- PostgreSQL 15+ (already in docker-compose, need to uncomment)
- Redis (already running)
- 16GB RAM recommended (for BERT models)
- GPU optional but recommended for BERTopic

---

## Part 9: Estimated Effort Summary

| Agent | Tasks | Effort (hours) | Effort (days) |
|-------|-------|----------------|---------------|
| **DataGeoIntel** | 4 tasks | 36-48h | 4.5-6 days |
| **Backend Flow** | 5 tasks | 31-40h | 3.9-5 days |
| **Frontend Map** | 5 tasks | 25-32h | 3.1-4 days |
| **Orchestrator** | 3 tasks | 10-14h | 1.3-1.8 days |
| **TOTAL** | 17 tasks | **102-134h** | **12.8-16.8 days** |

**Realistic Timeline**: 12 working days with parallel execution

**Critical Path**: GDELT → Hexmap Backend → Hexmap Frontend → Integration

---

## Part 10: Approval Checklist

Before proceeding, please review and approve:

- [ ] **Scope**: Balanced expansion (data + visualization + analysis)
- [ ] **Timeline**: 12 working days acceptable
- [ ] **Agent Tasks**: Tasks are clear and achievable
- [ ] **Success Criteria**: Metrics are measurable
- [ ] **Risk Mitigation**: Fallback plans are documented
- [ ] **Questions Answered**: All 6 clarifying questions addressed

**Once approved, agents will proceed with:**
1. Creating detailed task issues
2. Branching strategy (feat/iter2-{agent}-{task})
3. Small PRs (7 PRs total)
4. Daily standups (async via docs)
5. Weekly demos (Friday)

---

## Part 11: Post-Iteration 2 Preview (Iteration 3)

**Expected Capabilities After Iteration 2**:
- Live intelligence map with 90%+ real data
- Hexagonal heatmap showing spatial information flow
- 5 data sources (Wikipedia, GDELT, Trends, HN, Mastodon)
- BERTopic narrative clustering with stance
- PostgreSQL time-series persistence
- Animated pulsing flow arcs

**Iteration 3 Will Add**:
- Blob smoothing (Gaussian blur, k-ring)
- Full arc animations (not just pulsing)
- Timeline replay mode (historical playback)
- Entity-level flow tracking
- RSS news integration (Layer 2 validation)
- Advanced narrative graphs

---

**Status**: ⏸️ **Awaiting User Approval & Clarifications**

**Next Steps**:
1. User answers 6 clarifying questions
2. User approves overall plan
3. Orchestrator creates task issues and branches
4. Agents begin parallel execution

---

*Prepared by: Orchestrator Agent*
*Date: 2025-11-13*
*Version: 1.0*
