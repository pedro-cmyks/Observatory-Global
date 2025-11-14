# Orchestrator Agent

## Role
Senior technical orchestrator. Prioritizes, slices work, integrates outputs, and performs baseline QA.

## Mission
**Current Focus:** Iteration 3 - Narrative Intelligence Layer
Maintain visible, verifiable increments across parallel workstreams with clear handoffs and zero heroics.

## Primary Responsibilities
- Convert iteration goals into small issues with acceptance criteria and test notes
- Sequence work across agents, manage dependencies, and reduce idle time
- Coordinate parallel workstreams (visualization, data architecture, frontend, backend)
- Enforce PR hygiene: small diffs, passing tests, clear logs, and updated .env.example
- Produce daily plan and end-of-day status, tagging risks and mitigations
- Manage handoffs between usage windows with complete context preservation

## Inputs
- Open issues
- CI logs
- Outputs from other agents
- Stakeholder notes

## Outputs
- Daily plan
- Integrated checklists
- QA comments on PRs
- ADR stubs when ambiguity appears

## Definition of Done
The increment:
- Compiles successfully
- All tests pass
- Logs are useful and structured
- Environment variables are documented in .env.example
- An ADR exists if a non-trivial choice was made

## Operating Rules
1. **Do not block on perfection** - ship visibility first
2. **If in doubt, write a 1-2 paragraph ADR** before implementing
3. **Label and track** data, performance, and API quota risks
4. **Small, frequent PRs** over large batches
5. **Continuous integration** - keep main stable at all times

## Communication Protocol
- Daily standup summary in docs/state/daily-YYYY-MM-DD.md
- Tag blocking issues immediately
- Document decisions in real-time
- Keep stakeholder updated on risks and progress

---

## Current Iteration 3 Status (2025-01-14)

### Active Agents & Responsibilities

| Agent | Current Task | Priority | Status |
|-------|--------------|----------|--------|
| **DataSignalArchitect** | Issue #14: GDELT signals schema | High | Blocked - awaiting next window |
| **DataSignalArchitect** | Issue #16: Update placeholders | High | Blocked - awaiting next window |
| **Frontend Visualization** | Issue #13: Fix heatmap rendering | **URGENT** | Active - debugging required |
| **Frontend Architect** | Issue #15: Dual-layer viz spec | High | Blocked - awaiting next window |
| **Backend Team** | Issue #17: Migration checklist | Medium | Documentation complete |

### GitHub Issues Created

- **#13:** [HIGH PRIORITY] Heatmap layer not rendering hexagons
  - **Blocker:** Validation of dual-layer architecture
  - **Assignment:** Frontend Visualization Specialist
  - **Next Steps:** Follow debugging guide in `/docs/VISUALIZATION_UX_FLOW.md`

- **#14:** Design GDELT-based signals schema
  - **Deliverables:** PostgreSQL DDL, migration scripts, indexing strategy
  - **Assignment:** DataSignalArchitect
  - **Timeline:** Week 1 of next window

- **#15:** Design dual-layer visualization architecture
  - **Deliverables:** Component spec, animation plan, performance strategy
  - **Assignment:** Frontend Architect + Visualization Specialist
  - **Timeline:** Week 2 of next window

- **#16:** Update placeholders to match GDELT structure
  - **Deliverables:** Real GDELT-shaped placeholder data
  - **Assignment:** DataSignalArchitect
  - **Timeline:** Week 1 of next window (parallel with #14)

- **#17:** Migration checklist (placeholder → real GDELT)
  - **Deliverables:** 4-week implementation plan
  - **Assignment:** Backend Team + DataSignalArchitect
  - **Timeline:** Weeks 3-4 of next window

### Key Documents Created

1. **`/docs/GDELT_SCHEMA_ANALYSIS.md`** (400+ lines)
   - Comprehensive GDELT 2.0 GKG field analysis
   - Tier 1 & Tier 2 field breakdown
   - Implementation recommendations
   - 5-week roadmap

2. **`/docs/ITERATION_3_PLANNING.md`**
   - Executive summary
   - Complete architecture overview
   - All 5 GitHub issues explained
   - Success metrics & risk mitigation

3. **`/docs/VISUALIZATION_UX_FLOW.md`**
   - Layer architecture & z-index ordering
   - User interaction flows (6 complete scenarios)
   - Component hierarchy & data flow
   - Animation specifications (pulsing, particles, gradients, glow)
   - Comprehensive debugging guide for heatmap issue
   - Performance requirements & targets

4. **`/docs/GITHUB_CLI_SETUP.md`**
   - Required PAT scopes for project management
   - Setup instructions (3 options)
   - Verification steps
   - Automation examples

### Priority for Next Window

**Immediate (Before work begins):**
1. ✅ Heatmap rendering fix (Issue #13) - **MUST BE RESOLVED**
2. Verify fix deployed and working

**Week 1 Parallel Start:**
1. DataSignalArchitect → Issue #14 (schema design)
2. DataSignalArchitect → Issue #16 (placeholder updates)
3. Frontend Architect → Issue #15 (visualization spec)

**Week 2-3:**
- Continue parallel work
- Begin Issue #17 implementation (real GDELT parser)

### Known Issues & Blockers

**Critical:**
- Heatmap not rendering despite:
  - API returning correct data
  - @deck.gl/react package installed
  - Component mounting correctly
- **Root Cause:** Under investigation - likely deck.gl/Mapbox viewState sync issue
- **Impact:** Blocks validation of dual-layer architecture

**Non-Blocking:**
- GitHub CLI lacks `project` scope (manual project creation required)
- Solution documented in `/docs/GITHUB_CLI_SETUP.md`

### Handoff Instructions for Next Window

**For Visualization Specialist (Issue #13):**
1. Read `/docs/VISUALIZATION_UX_FLOW.md` § "Debugging Guide"
2. Follow 6-step debugging procedure
3. Add debug logging to `HexagonHeatmapLayer.tsx`
4. Test minimal H3HexagonLayer configuration
5. Verify WebGL context availability
6. Check H3 index validity with `h3-js`
7. Document findings in Issue #13 comments

**For DataSignalArchitect (Issues #14, #16):**
1. Read `/docs/GDELT_SCHEMA_ANALYSIS.md` (complete reference)
2. Design PostgreSQL schema based on Tier 1 fields
3. Create migration scripts (Alembic)
4. Update placeholder generators with real GDELT structure
5. Test placeholders with existing endpoints
6. Ensure backward compatibility

**For Frontend Architect (Issue #15):**
1. Read `/docs/VISUALIZATION_UX_FLOW.md` (complete spec)
2. Design enhanced flow detection algorithm (multi-signal)
3. Specify animation implementations (code examples)
4. Create performance optimization plan
5. Define component interfaces

### Technical Debt & Risks

**Moderate Risk:**
- Bundle size approaching 3 MB limit (current: 2.6 MB)
  - Mitigation: Code splitting, lazy loading
- GDELT data volume (1-2M articles/day)
  - Mitigation: Server-side aggregation, streaming parser
- 280+ GDELT themes complexity
  - Mitigation: Show top 50, support search across all

**Low Risk:**
- Classic + Heatmap simultaneous rendering performance
  - Mitigation: RequestAnimationFrame optimization, layer toggles
- Docker cache causing stale builds
  - Mitigation: Use `--no-cache` flag when dependencies change

### Success Metrics for Next Window

**Visualization:**
- [ ] Heatmap hexagons render correctly
- [ ] Gaussian blur effect visible
- [ ] Globe wrapping works properly
- [ ] Performance: 60 FPS maintained

**Architecture:**
- [ ] PostgreSQL schema designed and reviewed
- [ ] Placeholders match GDELT structure exactly
- [ ] Dual-layer spec complete and approved
- [ ] All tests passing with new placeholders

**Documentation:**
- [ ] All handoff documents complete
- [ ] Debugging findings documented
- [ ] ADRs created for significant decisions
- [ ] Next window roadmap clear

### Coordination Notes

**Dependencies:**
- Issue #15 (dual-layer viz) depends on Issue #13 (heatmap fix) for validation
- Issue #16 (placeholders) should align with Issue #14 (schema design)
- Issue #17 (migration) builds on Issues #14 & #16 completion

**No Dependencies (Can Parallelize):**
- Issues #14 & #16 (both DataSignalArchitect, compatible work)
- Issue #13 (visualization) independent from data architecture

**Recommended Sequence:**
```
Window Start
    ↓
[URGENT] Fix Issue #13 (heatmap)
    ↓
┌─────────────┬─────────────┬──────────────┐
│  Issue #14  │  Issue #16  │  Issue #15   │
│  (schema)   │(placeholders)│  (dual-viz)  │
│             │             │              │
│ DataSignal  │ DataSignal  │  Frontend    │
│  Architect  │  Architect  │  Architect   │
└─────────────┴─────────────┴──────────────┘
              ↓
        Week 2-3: Issue #17 (migration)
              ↓
        Week 4-5: Production hardening
```

---

**Last Updated:** 2025-01-14 17:30 EST
**Next Review:** Start of next usage window
**Context Preserved:** ✅ Complete handoff documentation created
