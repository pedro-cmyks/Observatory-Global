# ADR-0004: Iteration 2 Strategic Direction

**Status**: Proposed
**Date**: 2025-11-13
**Decision Makers**: Orchestrator + All Agents
**Stakeholder**: Pedro (Product Owner)

---

## Context

Iteration 1 delivered a functional MVP with:
- Backend API with flow detection algorithm
- Frontend visualization with 8 components
- 57% real data (Wikipedia 100%, Trends 70%, GDELT 0%)
- Ephemeral in-memory data (no persistence)
- Country centroid markers (not spatial heat distribution)

**User Vision**: Transform MVP into a "live intelligence map" that reveals:
- What information is moving (narrative content)
- How it's moving (flow patterns)
- Through which regions (spatial heat distribution)
- With what narrative content (stance, sentiment, entities)

---

## Decision

Iteration 2 will pursue a **balanced expansion** across four dimensions:

### 1. Data Realism (57% → 90%+)
- Implement GDELT real data fetching (0% → 100%)
- Add Hacker News real-time source (tech narratives)
- Add Mastodon decentralized source (emerging narratives)
- Create 3-layer architecture: Emerging → Validation → Baseline

### 2. Visualization Enhancement (Centroids → Hex Tiles)
- Replace country centroid markers with hexagonal heatmap
- Use H3 (Uber) + deck.gl for spatial heat distribution
- Implement zoom-based resolution switching (global → country)
- Add view mode toggle (Classic vs Heatmap)

### 3. Narrative Analysis (TF-IDF → BERTopic)
- Upgrade from TF-IDF to sentence-transformers embeddings
- Implement basic BERTopic clustering (foundation for deep analysis)
- Add stance detection (pro/against/neutral)
- Show sample headlines/snippets in UI

### 4. Data Persistence (Ephemeral → PostgreSQL)
- Wire PostgreSQL for time-series storage
- Implement 4-tier retention policy (hot/warm/cold/delete)
- Store topic snapshots, hotspots, flows, stance history
- Enable historical analysis and trend detection

---

## Rationale

### Why Balanced (not Depth-First)?

**Rejected Alternative 1: Data-Only Focus**
- Pro: Achieves 100% real data quickly
- Con: User sees no visual improvement, feels like backend work

**Rejected Alternative 2: Visualization-Only Focus**
- Pro: Impressive visual upgrades
- Con: Still showing fake data, not trustworthy

**Chosen: Balanced Expansion**
- Pro: User sees improvement in all dimensions
- Pro: Each dimension reinforces others (real data makes better visualizations)
- Pro: Delivers on vision holistically
- Con: Takes longer per dimension (mitigated by parallel agent execution)

### Why These Specific Data Sources?

**Hacker News** (Rank #1):
- Zero auth required, unlimited rate limit
- Captures tech/startup narratives globally
- Real-time (0-5 second latency)
- High signal-to-noise ratio

**Mastodon** (Rank #2):
- Decentralized, no corporate control
- WebSocket streaming (0-2 second latency)
- Captures emerging narratives before mainstream media
- Multi-instance strategy avoids single point of failure

**RSS News** (Deferred to Iteration 3):
- Provides validation layer (mainstream confirmation)
- Less urgent than emerging narrative detection
- Easier to implement later

### Why H3 Hexagons (not Voronoi, Grid, or Custom)?

**H3 Advantages**:
- Production-proven at Uber scale (millions of hexagons)
- Hierarchical (16 zoom levels)
- Deterministic IDs (perfect for caching)
- Native deck.gl integration (H3HexagonLayer)
- 60 FPS with 100K+ hexagons (GPU-accelerated)

**Alternatives Rejected**:
- Voronoi: Non-uniform, hard to cache
- Square grid: Visual artifacts at edges
- Custom WebGL: Overkill, high maintenance

### Why BERTopic (not GPT, LDA, or NMF)?

**BERTopic Advantages**:
- Contextual embeddings (understands semantics)
- No predefined topic count (discovers natural clusters)
- Hierarchical topics (parent-child relationships)
- Open-source, runs locally (no API costs)

**Alternatives Rejected**:
- GPT-4: Expensive ($0.03/1K tokens), API latency
- LDA: Bag-of-words (loses word order context)
- NMF: Requires predefined topic count

### Why PostgreSQL (not MongoDB, DynamoDB, or InfluxDB)?

**PostgreSQL Advantages**:
- ACID guarantees (data integrity)
- Rich indexing (B-tree, GIN, GiST for geo)
- Mature partitioning (time-series optimization)
- TimescaleDB extension (10x compression)
- PostGIS extension (future spatial queries)

**Alternatives Rejected**:
- MongoDB: Weaker consistency guarantees
- DynamoDB: Lock-in, higher costs at scale
- InfluxDB: Limited query flexibility

---

## Consequences

### Positive

**For Users**:
- Trustworthy data (90%+ real, no more fake counts)
- Spatial heat distribution (sees "where" information is concentrated)
- Narrative content (sees "what" people are talking about)
- Historical context (can analyze trends over time)

**For Development**:
- Solid foundation for Iteration 3 (blob smoothing, timeline replay)
- Parallel agent execution (reduces total timeline)
- Modular architecture (can swap components independently)
- Comprehensive testing (high confidence in stability)

**For Operations**:
- PostgreSQL enables backup/restore
- Monitoring via pg_stat_statements
- Performance tuning via indexes and caching
- Scalable to 50+ countries

### Negative

**Increased Complexity**:
- More dependencies (H3, deck.gl, sentence-transformers, psycopg2)
- Frontend bundle size +600 KB (deck.gl)
- Backend memory usage +2 GB (BERT models)
- Infrastructure cost +$60-110/month (PostgreSQL RDS)

**Migration Risk**:
- PostgreSQL migration could fail (mitigated by comprehensive testing)
- Performance degradation possible (mitigated by caching + indexing)

**Learning Curve**:
- Team needs to learn H3, deck.gl, BERTopic
- Increased onboarding time for new developers

---

## Implementation Strategy

### Phased Approach

**Phase 1: Critical Path** (Days 1-5)
1. Enable PostgreSQL and run migration
2. Implement GDELT real data fetching
3. Implement hexmap backend API
4. Connect frontend to backend (remove mock data)
5. Implement hexmap frontend visualization

**Phase 2: Data Expansion** (Days 6-9)
6. Integrate Hacker News data source
7. Integrate Mastodon data source
8. Upgrade to BERTopic clustering
9. Add stance detection

**Phase 3: Integration & Polish** (Days 10-12)
10. Wire PostgreSQL persistence
11. Add narrative content preview
12. Add flow arc pulsing
13. Documentation and demo

### Parallel Execution

Three agents work simultaneously:
- **DataGeoIntel**: Data sources (GDELT, HN, Mastodon)
- **Backend Flow**: APIs and algorithms (hexmap, BERTopic, PostgreSQL)
- **Frontend Map**: Visualization (hex layer, pulsing, content preview)

**Orchestrator** coordinates via daily async standups and PR reviews.

---

## Success Metrics

### Quantitative
- [ ] Data completeness: 90%+ real data
- [ ] Hexmap performance: 60 FPS with 5,000 hexagons
- [ ] API response time: <2s for `/v1/hexmap`
- [ ] Cache hit ratio: >95%
- [ ] Test coverage: >80% for new code

### Qualitative
- [ ] User describes visualization as "alive" and "organic"
- [ ] User trusts the data (no more skepticism about fake counts)
- [ ] User can identify narrative patterns by visual inspection
- [ ] User wants to explore historical trends (validates persistence value)

---

## Related ADRs

- **ADR-0001**: Refresh Intervals (15-minute cycle)
- **ADR-0002**: Heat Formula (exponential decay)
- **ADR-0003**: Hexagonal Heatmap Architecture
- **ADR-0005**: BERTopic vs TF-IDF Trade-offs (TBD)
- **ADR-0006**: PostgreSQL Retention Policy (TBD)

---

## References

- Iteration 2 Master Plan: `docs/planning/ITERATION-2-MASTER-PLAN.md`
- H3 Documentation: https://h3geo.org/
- BERTopic Paper: https://arxiv.org/abs/2203.05794
- Mastodon API: https://docs.joinmastodon.org/api/
- Hacker News API: https://github.com/HackerNews/API

---

**Status**: ⏸️ Awaiting User Approval
**Next Review**: After user answers clarifying questions
