# CLAUDE.md - Project Guidelines and Agent Configuration

Last updated: 2026-05-19 (session 15 close — 4 new ingest sources live; NLP worker 4GB with xlm-v1 multilingual confirmed; migrations 019+020 applied; 2.28M signals)

This file provides Claude Code with essential context about the Observatorio Global project, including agent configurations, tooling guidelines, and development workflows.

## Project Overview

Observatorio Global is a narrative intelligence system that tracks, analyzes, and visualizes how topics and narratives propagate across global media sources. The system aggregates signals from GDELT 2.0, Google Trends, and Wikipedia, normalizes them into a unified schema, and provides insights on geographic drift, sentiment analysis, and narrative mutations.

## Current Session Context (2026-05-19, session 15 close)

- Active branch: `v3-intel-layer`; production branch. Do not merge into `main`.
- PR #144 open against main: https://github.com/pedro-cmyks/Observatory-Global/pull/144
- Production: Vercel (frontend auto-deploy), Fly.io `atlas-api-pedro` (backend), Fly.io `nlp_worker` (4GB)
- Total signals: 2,279,950. Ingest lag 4.1 min. 3849 rows/15min.
- Atlas product framing: **public narrative intelligence console**, not a GDELT wrapper.
- Preferred user path: `/brief` for readable orientation, then `/app` for full analyst investigation.

### Session 15 closed with two parallel tracks:

**Track A (Claude) — Multi-source ingestion**:
- 4 new ingest services live: NewsData.io (multilingual), MediaStack (ES/PT), NewsAPI.org (EN crisis queries), Reddit public API (social commentary)
- Fly secrets set: `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`
- Volume projection: ~99.7K signals/day total (GDELT ~72K + new ~27.6K)
- `backend/.env.example` documents all env vars

**Track B (Codex) — NLP worker stabilization + Topic Intelligence**:
- Commit `e4e8f92`
- `nlp_worker` raised to `shared-cpu-2x:4096MB`, standby stopped
- Migrations `019_atlas_topic_intelligence.sql` + `020_nlp_progress_indexes.sql` applied
- **Multilingual NLP CONFIRMED**: logs show `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]`. Cycle 231.5s, error=no
- `NLP_SAMPLE_REFRESH_EVERY=0`, `NLP_SAMPLE_CLEANUP_LIMIT=50` set in prod
- 27 tests pass on NLP pipeline + worker + topic intelligence schema

### Next session priorities:
1. ~~Verify multilingual NLP~~ DONE (xlm-v1 confirmed by Codex)
2. Add `signal_class` + `narrative_cluster_id` to signals_v2 (migration 021)
3. Voice Mix component in CountryBrief (stacked bar: local-lang / international / social)
4. NewsAPI refactor: 6 evergreen + 2 dynamic from GDELT spikes + 36 req/day analyst reserve
5. Validate HuggingFace tokenizer warning on `twitter-xlm-roberta-base-sentiment`
6. Resolve `country_heat_v2` refresh timeout

### Reference docs:
- `docs/STATUS.md` — current state, validation results
- `docs/superpowers/plans/2026-05-18-multisource-intelligence-hardening.md` — original plan

### Key patterns (established across sessions 13–14)

- `resolveCountryName(code, name)` — always use for country display, never raw `c.name` from API
- `getThemeLabel(code)` — always use, never raw GDELT theme codes in UI
- `data-tip` attribute only — never native `title=` for tooltips
- `themeSignals[theme][0]` — do NOT use as headline anchor; misclassification risk
- `d?.trending ?? []` — correct field for trends API response (`trending`, not `trends`)
- `detail_hours = min(hours, 48)` — Phase 2 narrative detail cap in `narratives.py`
- Two ForceGraph2D instances with `visibility: hidden` toggle — preserves simulation state
- `briefingPrefetch.ts` sessionStorage cache (4-min TTL) — read before fetch in BriefNewspaper
- `parseCompoundQuery(q)` in SearchBar — extracts countryCode from "topic Country" queries
- `useSavedWatches` localStorage key: `atlas_saved_watches_v1`; `markSeen(id, count)` records delta baseline
- ACLED is optional connector — no `ACLED_API_KEY` → empty layer, no errors
- `createTerminatorLayer()` returns `PolygonLayer[]` (5 bands) — spread with `...terminatorLayers`
- `fetchItemSignals(item)` in `exportFormatters.ts` — shared by dossier export and ReadingMode
- New ingest services follow `ingest_rss.py` pattern: every row sets `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, `is_state_media`
- Reddit signals: `source_family="social"`, `attribution_method="reddit_public"` — commentary layer, NOT independent corroboration; needs `signal_class="commentary"` before #149 scoring
- `geo_confidence` defaults: NewsData 0.7, MediaStack 0.65, NewsAPI 0.65, Reddit 0.5, GDELT GKG 0.9, RSS 0.6
- NLP env flags in prod: `NLP_SAMPLE_REFRESH_EVERY=0`, `NLP_SAMPLE_CLEANUP_LIMIT=50` — do NOT change without testing
- NLP worker confirmed multilingual: logs `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]`. Throughput 25 rows/cycle stable — do NOT raise without observing DB pressure
- `npm run build` (not `tsc --noEmit`) is the canonical build check — Vite uses `tsc -b` (stricter)

## Specialized Agents

The project uses a multi-agent architecture where each agent has specific expertise. The **Orchestrator** coordinates these agents based on task requirements.

### Agent Summary

| Agent | Purpose | When to Call |
|-------|---------|--------------|
| orchestrator | Coordinates multi-agent workstreams | Starting sessions, planning iterations, QA reviews, managing blockers |
| backend-flow-engineer | Implements API endpoints and backend logic | Flows API, health endpoints, trends endpoints, caching, migrations |
| data-geointel-analyst | Handles geointelligence data sources | GDELT/Trends/Wikipedia clients, topic normalization, scoring algorithms |
| data-signal-architect | Designs signal processing systems | Schema design, Redis caching, signal validation, mobile optimization |
| narrative-geopolitics-analyst | Analyzes narrative propagation | Drift detection, mutation patterns, source analysis, visualization design |
| frontend-map-engineer | Implements map visualizations | Mapbox components, geospatial displays, real-time updates |

---

## Agent Details

### Orchestrator

**Purpose**: Senior technical orchestrator for multi-agent coordination, work prioritization, and incremental delivery.

**When to Call**:
- Starting a new session and need to pick up where work left off
- Planning the next iteration after receiving outputs from multiple agents
- Multiple PRs need QA coordination
- Blocking issues affect multiple workstreams
- Breaking down high-level goals into trackable issues

**Key Responsibilities**:
- Convert iteration goals into small, focused GitHub issues
- Manage handoffs between agents with complete context
- Enforce PR hygiene standards
- Produce daily planning artifacts
- Track and label risks by category

**Interaction with Backend Tasks**:
- Creates issues for backend agents with clear acceptance criteria
- Sequences backend work to minimize idle time
- Coordinates data pipeline outputs with API endpoint implementations
- Ensures database migrations are properly sequenced

---

### Data Signal Architect

**Purpose**: Expert in large-scale signal processing, time-series data architectures, anomaly detection, and cross-source data normalization. Specializes in PostgreSQL schema design and Redis caching strategies for lightweight, mobile-ready systems.

**When to Call**:
- Designing signals schemas for multi-source narrative tracking
- Implementing time-bucketing strategies (15-min vs 1-hour)
- Reviewing or optimizing Redis caching implementations
- Validating incoming signals and detecting synthetic data
- Integrating new data sources into existing pipelines
- Optimizing queries for mobile deployment

**Core Expertise**:
- **Signals Schema Design**: Temporal, geographic, and topic dimensions with proper constraints and indexes
- **Time-Bucketing Strategy**: 15-minute buckets for real-time, 1-hour for trend analysis
- **PostgreSQL Optimization**: Efficient data types, index strategies, constraint definitions
- **Redis Caching**: Key patterns, expiration policies, memory budgets (500MB max)
- **Signal Validation**: Source verification, volume sanity, sentiment bounds, URL validation
- **Mobile Optimization**: <100ms queries, <50KB responses, gzip compression

**Interaction with Backend Tasks**:
- Provides schema DDL for database migrations
- Defines caching key patterns for backend services
- Validates signal processing logic against data quality requirements
- Recommends index strategies for API endpoint queries
- Reviews backend implementations for performance and efficiency

**Execution Guidelines**:
- Always include complete DDL with constraints and indexes
- Provide storage and performance estimates
- Include example queries demonstrating index usage
- Document edge cases and error handling
- Target 100ms query latency and 1000 signals/minute throughput

---

### Narrative Geopolitics Analyst

**Purpose**: Expert in global information ecosystems, disinformation analysis, narrative framing, and comparative media analysis. Provides domain insight on how narratives propagate, mutate, and polarize across regions and platforms.

**When to Call**:
- Analyzing how topics are framed differently across countries
- Defining narrative mutation patterns (framing shifts, emphasis changes, attribution flips)
- Implementing drift detection algorithms (geographic, temporal, cross-platform)
- Specifying API schemas for narrative intelligence endpoints
- Interpreting signals from different source families
- Designing visualizations for narrative data
- Adding geopolitical context flags to the system

**Core Expertise**:
- **Narrative Mutation Types**: Framing shifts, emphasis mutations, omissions, amplifications, minimizations, attribution flips
- **Drift Detection**: Geographic drift scores, temporal sentiment trajectories, cross-platform divergence
- **Source Family Analysis**: GDELT, Google Trends, and Wikipedia coverage patterns, biases, and reliability
- **Geopolitical Context**: State media flags, echo chamber detection, information deserts, polarization thresholds
- **Visualization Design**: Geographic heatmaps, cluster views, temporal timelines, narrative flow diagrams

**Interaction with Backend Tasks**:
- Defines API response schemas with required metadata fields
- Provides Python implementations for drift detection algorithms
- Specifies validation rules for narrative signals
- Recommends data structures for stance and cluster tracking
- Defines confidence scoring methodologies

**Execution Guidelines**:
- Provide at least 3 concrete examples for each concept
- Include quantitative metrics with specific formulas and thresholds
- Supply Python code with type hints when algorithms are requested
- Include complete JSON schemas for API responses
- Provide user-facing plain language explanations
- Document testing recommendations and success criteria

**Collaboration**:
- Works with **DataGeoIntel** to ensure source normalization aligns with narrative needs
- Validates with **DataSignalArchitect** that signals schema includes stance and cluster fields
- Coordinates with **BackendFlow** for efficient narrative query endpoints
- Provides UX guidance to **FrontendMap** for visualization implementations

---

### Backend Flow Engineer

**Purpose**: Implements and modifies the flows API, health endpoints, trends endpoints, and intelligence enrichment endpoints in the Python/FastAPI backend.

**When to Call**:
- Implementing API endpoints (all under `/api/v2/...`; crisis endpoints under `/api/v3/...`)
- Implementing caching strategies with Redis
- Writing database migrations for PostgreSQL (raw `.sql` files in `backend/migrations/`)
- Calculating heat formulas and similarity scores
- Writing tests for backend functionality
- Adding new data source integrations (ACLED, OpenSky, AISStream)

**Interaction with Backend Tasks**:
- Implements endpoints following Pydantic model patterns in `app/models/`
- Creates database migrations run via Supabase SQL editor (NOT alembic)
- Implements caching with key patterns from DataSignalArchitect
- Writes unit and integration tests in `backend/tests/`

---

### Data GeoIntel Analyst

**Purpose**: Works on geointelligence data analysis tasks involving GDELT, Google Trends, and Wikipedia data sources.

**When to Call**:
- Validating or implementing data source clients
- Creating topic normalization logic for cross-country comparisons
- Implementing intensity scoring algorithms
- Writing ADRs for time windows or decay formulas
- Creating dataset snapshots with manifests
- Documenting API quotas and error recovery strategies

**Interaction with Backend Tasks**:
- Provides client implementations for data sources
- Defines normalization pipelines for topic extraction
- Implements scoring formulas (heat, intensity, similarity)

---

### Frontend Map Engineer

**Purpose**: Implements interactive map visualizations using React, MapLibre GL, and DeckGL v9.

**When to Call**:
- Adding circle markers/hotspots to maps (ScatterplotLayer)
- Creating animated flow lines between countries (ArcLayer)
- Building map-related UI components (filters, sidebars, chokepoint panels)
- Handling real-time data updates with auto-refresh (aircraft 15s poll, vessels 30s poll)
- Implementing custom DeckGL layers (e.g. TerminatorLayer)

**Critical Rules for Frontend:**
- Use **Vanilla CSS** for all dashboard components. CSS custom properties come from `ThemeContext`.
- **Tailwind CSS** is installed but used **exclusively for `Landing.tsx`** (the public marketing page). Do NOT add Tailwind classes to dashboard components.
- Use `data-tip="text"` for tooltips on any element — NEVER use native `title=` attributes.
- Components live in `frontend-v2/src/components/`. Current count: **36 .tsx components**.
- Always run `npm run build` (not just `tsc --noEmit`) before pushing — Vite's `tsc -b` is stricter.
- `InteractiveWorkspace.tsx` (the force-graph canvas) is lazy-loaded via `React.lazy()` inside `InvestigationWorkspace.tsx` — do NOT import it directly or it will blow the main bundle.
- Theme labels: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT trust the `label` field returned by the API — the API field may be raw GDELT codes.

---

## AI Model Coordination: Claude, Gemini, and Codex

This project uses three AI models in coordination, each with distinct strengths. Understanding when to use each model maximizes efficiency and output quality.

### Claude's Role: Orchestration and Reasoning

Claude serves as the **orchestrator and system-level reasoning engine**.

**Primary Responsibilities:**

- High-level design, architecture, and planning
- Multi-agent coordination and task sequencing
- Narrative analysis and data interpretation
- Schema design and technical decisions
- Complex reasoning requiring deep context
- Documentation and specification writing
- **Automatic delegation** to Gemini and Codex when appropriate

**When to Use Claude:**

- Starting a session and planning work
- Designing database schemas or API architectures
- Analyzing narrative patterns or drift detection algorithms
- Making technical decisions with tradeoffs
- Coordinating multiple workstreams
- Writing ADRs or architectural documents

**Automatic Delegation Rules:**

Claude should automatically:

1. **Delegate to Gemini** when large multi-file context is needed
2. **Delegate to Codex** when code generation or execution is required
3. **Keep reasoning centralized** within Claude
4. **Combine outputs** from Gemini + Codex into coherent plans

**Orchestration Workflow:**

```text
1. Claude analyzes the goal
2. If large multi-file context needed → Claude triggers Gemini CLI
3. Claude receives Gemini's output and reasons about it
4. If code generation/execution needed → Claude triggers Codex CLI
5. Claude merges all results and produces high-level reasoning
```

**Example Commands:**

```bash
# Claude Code CLI for orchestration
claude "Review the handoff document and create today's plan"
claude "Design the PostgreSQL schema for GDELT signals"
claude "Analyze how drift detection should work across geographic regions"
```

---

## Using Gemini CLI for Large Codebase Analysis

Gemini CLI leverages Google Gemini's massive context window for analyzing large codebases or multiple files that would exceed Claude's context limits.

### Gemini Purpose

Use Gemini CLI when:

- Analyzing large codebases or multiple files that exceed context limits
- Reviewing or comparing full directories
- Scanning for patterns across many files
- Verifying complex implementations scattered across the codebase
- Loading hundreds of files at once
- Performing static read-only analysis requiring massive context

### Gemini Syntax

Use `gemini -p` for non-interactive mode with prompts:

```bash
gemini -p "<prompt here>"
```

### File and Directory Inclusion

Use the `@` syntax to include files and directories. Paths are relative to your current working directory:

#### Basic Examples

**Single file analysis:**

```bash
gemini -p "@src/main.py Explain this file's purpose and structure"
```

**Multiple files:**

```bash
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"
```

**Entire directory:**

```bash
gemini -p "@src/ Summarize the architecture of this codebase"
```

**Multiple directories:**

```bash
gemini -p "@src/ @tests/ Analyze test coverage for the source code"
```

**Current directory and subdirectories:**

```bash
gemini -p "@./ Give me an overview of this entire project"
```

**All files automatically:**

```bash
gemini --all_files -p "Analyze the project structure and dependencies"
```

### Implementation Verification Examples

**Check if a feature is implemented:**

```bash
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"
```

**Verify authentication implementation:**

```bash
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"
```

**Check for specific patterns:**

```bash
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"
```

**Verify error handling:**

```bash
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"
```

**Check for rate limiting:**

```bash
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"
```

**Verify caching strategy:**

```bash
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"
```

**Check for specific security measures:**

```bash
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"
```

**Verify test coverage for features:**

```bash
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"
```

### When to Use Gemini

- Analyzing entire codebases or large directories
- Comparing multiple large files
- Understanding project-wide patterns or architecture
- Context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented
- Checking for coding patterns across the entire codebase

### When NOT to Use Gemini

- **Generating new code** (use Codex instead)
- **Executing commands** (use Codex instead)
- **Small context tasks** that fit in Claude's window
- **Code refactoring or implementation** (use Codex instead)

### Important Notes

- Paths in `@` syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results

---

## Using Codex CLI for Code Generation and Execution

Codex CLI is optimized for heavy code generation, refactoring, and execution tasks. It specializes in writing and modifying code with high quality output.

### Codex Purpose

Use Codex CLI when:

- Generating large code modules or full files
- Performing refactors across many files
- Generating test suites or documentation
- Scaffolding entire features or microservices
- Executing code or commands
- Running project automation tasks (formatters, linters, migrations)
- Transforming files requiring "write access"

### Codex Syntax

Use `codex -p` for prompting:

```bash
codex -p "<prompt here>"
```

Codex also supports the `@file` and `@directory/` syntax for including context.

### Code Generation Examples

**Implement an endpoint:**

```bash
codex "Implement GET /api/v2/narratives/topic endpoint in backend/app/main_v2.py following the existing endpoint patterns"
```

**Write tests:**

```bash
codex "Write unit tests for the gdelt_parser.py parse_v2_tone function"
```

**Create TypeScript types:**

```bash
codex "Create TypeScript interfaces in frontend/src/lib/types.ts matching the GDELTSignal Pydantic model"
```

**Refactor for performance:**

```bash
codex "Refactor the flow_detector.py to use numpy vectorization instead of nested loops"
```

**Fix a specific bug:**

```bash
codex "Fix the heatmap rendering issue in HexagonHeatmapLayer.tsx where hexagons are not appearing"
```

### File Context Examples

**Generate tests with context:**

```bash
codex -p "@backend/ Generate a complete test suite for all services"
```

**Refactor with file context:**

```bash
codex -p "@src/ Refactor all API handlers to use dependency injection"
```

**Create new module:**

```bash
codex -p "@app/ Create a new logging module and integrate it"
```

**Full CRUD generation:**

```bash
codex -p "@./ Build a full CRUD module for the User entity"
```

### Execution Examples

Run commands directly through Codex:

```bash
codex run tests
codex run "npm install"
codex run "pytest -q"
codex -p "@scripts/ Execute the migration scripts and show output"
```

### When to Use Codex

- Implementing new API endpoints
- Writing tests for services
- Creating React components
- Refactoring modules for performance
- Generating Pydantic models or TypeScript interfaces
- Fixing bugs in specific files
- Running project commands

### When NOT to Use Codex

- **Analyzing very large contexts** (use Gemini instead)
- **Deep reasoning or cross-file orchestration** (Claude handles this)
- **Verifying architecture or patterns** (use Gemini instead)
- **Planning and decision-making** (use Claude instead)

---

## Combined Workflow

The three models work together in a coordinated pipeline:

```
┌─────────────────────────────────────────────────────┐
│                    WORKFLOW                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. CLAUDE THINKS                                   │
│     ├─ Review context and plan                      │
│     ├─ Design architecture                          │
│     └─ Coordinate agents                            │
│                    ↓                                │
│  2. GEMINI INSPECTS                                 │
│     ├─ Analyze codebase                             │
│     ├─ Verify implementations                       │
│     └─ Check patterns                               │
│                    ↓                                │
│  3. CODEX IMPLEMENTS                                │
│     ├─ Write code                                   │
│     ├─ Create tests                                 │
│     └─ Apply fixes                                  │
│                                                     │
│  ═══════════════════════════════════════════════   │
│  All models can run in PARALLEL for independent    │
│  tasks to maximize efficiency                       │
└─────────────────────────────────────────────────────┘
```

**Example Combined Workflow:**

```bash
# Step 1: Claude plans the work
claude "Design the schema for storing narrative clusters with drift scores"

# Step 2: Gemini checks existing patterns
gemini -p "@backend/app/models/ @backend/app/db/ Analyze existing database patterns and constraints"

# Step 3: Codex implements
codex "Create the narrative_clusters table migration following the patterns identified"

# Parallel execution for independent tasks
claude "Design visualization spec" &
gemini -p "@frontend/ Check component structure" &
codex "Implement the tooltip component" &
wait
```

---

## Quick Reference: When to Pick Each Model

| Task Type | Model | Reason |
|-----------|-------|--------|
| Planning and coordination | **Claude** | Complex reasoning, context management |
| Architecture design | **Claude** | Tradeoff analysis, system thinking |
| Codebase-wide analysis | **Gemini** | Large context window |
| "Does X exist in the code?" | **Gemini** | Full repo search |
| Security/pattern audit | **Gemini** | Cross-file analysis |
| Implement endpoint | **Codex** | Code generation |
| Write tests | **Codex** | Implementation |
| Refactor module | **Codex** | Code transformation |
| Fix specific bug | **Codex** | Targeted edits |
| Schema design | **Claude** | Domain expertise |
| TypeScript types | **Codex** | Type generation |
| Execute commands | **Codex** | Command execution |

---

## Concrete Examples by Task

**Task: Add a new API endpoint for narrative topics**

```bash
# 1. Claude designs the API schema
claude "Design the /api/v2/narratives/topic endpoint with request/response schemas"

# 2. Gemini checks existing endpoint patterns
gemini -p "@backend/app/main_v2.py Show me the pattern used for existing endpoints including error handling"

# 3. Codex implements the endpoint
codex "Implement /api/v2/narratives/topic in backend/app/main_v2.py using the designed schema and existing patterns"
```

**Task: Optimize database queries**

```bash
# 1. Gemini identifies slow queries
gemini -p "@backend/app/services/ @backend/app/api/ Find all database queries and identify which ones might be slow"

# 2. Claude designs optimization strategy
claude "Design index strategy for the identified slow queries"

# 3. Codex implements the indexes
codex "Add the recommended indexes to the migration file"
```

**Task: Debug a rendering issue**

```bash
# 1. Gemini finds related code
gemini -p "@frontend/src/components/map/ Show all code related to hexagon rendering"

# 2. Claude analyzes the issue
claude "Analyze why hexagons might not be rendering based on the code"

# 3. Codex fixes the bug
codex "Fix the hexagon rendering issue in HexagonHeatmapLayer.tsx"
```

**Task: Add test coverage**

```bash
# 1. Gemini identifies untested code
gemini -p "@backend/app/services/ @backend/tests/ Which services have less than 80% test coverage?"

# 2. Codex writes the tests
codex "Write comprehensive tests for gdelt_parser.py covering all edge cases"
```

---

## Development Workflow

### Starting a Session

1. Call the **Orchestrator** to review handoff documentation
2. Assess current blockers and prioritize work for the window
3. Create daily plan with agent assignments

### Working on Tasks

1. Use the appropriate specialized agent for each task type
2. Maintain small, focused PRs (<300 lines)
3. Update todos as work progresses
4. Document decisions in ADRs when ambiguity appears

### Ending a Session

1. Complete handoff documentation
2. Update state documents
3. Tag any unresolved blockers
4. Push changes to GitHub

---

## Quality Standards

### PR Hygiene

- Small, focused diffs
- All tests passing
- Structured, useful logs
- Updated .env.example for new environment variables
- Clear commit messages following conventional commits

### Definition of Done

- [ ] Compiles successfully with no errors
- [ ] All tests pass
- [ ] Logs are structured and useful
- [ ] Environment variables documented
- [ ] ADR exists for non-trivial decisions
- [ ] Documentation updated
- [ ] Handoff notes complete

---

## Current Technical State (as of session 13 — 2026-05-17)

### Session 13 Additions (P0 productization pass — PR #144)

**Briefing prefetch (#136)**
- `frontend-v2/src/lib/briefingPrefetch.ts` — sessionStorage cache with 4-min TTL for briefing + insight API responses.
- `Landing.tsx` prefetches on mount. `BriefNewspaper.tsx` reads cache before fetch — no spinner when entering `/brief` from Landing.

**Editor's Analysis restored (#137)**
- `BriefNewspaper.tsx`: `buildGlobalFallback(d)` — 4 rotating variants (theme-lead, geography-lead, sentiment-lead, volume-first).
- `buildCountryFallback(detail)` — 3 country variants.
- `Math.random()` per render for angle rotation — intentional, not seeded.
- Removed all `themeSignals[theme][0]` headline anchors — signals misclassification risk.
- All country names via `resolveCountryName(code, name)` — never raw `c.name`.

**Investigation context preservation (#138)**
- `App.tsx`: `prevStreamCtx` union extended with `country` type.
- Back from source → CountryBrief; Back from country → thread if theme was active.

**Public Attention scoped to active country (#142)**
- `AnomalyPanel.tsx`: re-fetches Wiki on `activeCountry` change; Trends + Wiki merged into single PUBLIC ATTENTION section.
- `[S]` (green) badge for searches, `[W]` (indigo) badge for wiki articles.
- Staleness indicator: `trendsStaleHours` state, shows badge when >25h old.
- Deduplication: `Array.from(new Map(raw.map(a => [a.title, a])).values())`.
- `CountryBrief`: `onAttentionItemClick?: (query: string) => void` prop; `App.tsx` wires it.
- API field fix: `d?.trending ?? []` (was `d?.trends`).

**Google Trends stale data mitigation (#104)**
- `backend/app/services/ingest_trends.py`: shuffle country list each run (`import random`), batch size 5→3, delay 1s→2s, retry pass for failed countries.
- `frontend-v2/src/lib/publicAttention.ts`: `getTrendingSearchesUrl` uses `Math.max(hours, 72)` floor.
- AnomalyPanel shows "searches from Nh ago" badge when stale.

**Narrative Threads timeout cap (#139)**
- `backend/app/routers/narratives.py`: `detail_hours = min(hours, 48)` for Phase 2 (signals_v2 unnest scan); Phase 1 (theme_hourly_v2) still uses full `hours`.
- `effective_hours: detail_hours` added to result dict.
- `NarrativeThreads.tsx`: stores `effectiveHours` state; shows notice "Thread details show last Xh · counts reflect full Yh window" when capped.

**Trail / Pinned graph separation (#128)**
- `InteractiveWorkspace.tsx`: replaced single `graphRef`/`filteredGraph`/physics effect with separate `trailGraphRef` + `pinnedGraphRef`, `trailGraph` + `pinnedGraph` memos, two physics effects.
- Both ForceGraph2D instances always mounted; CSS `visibility: hidden` keeps simulation alive when inactive.
- Trail: linear-spread physics (charge -320/-420, distance 150); Pinned: dense-web physics (charge -380/-560/-760, distance 125-160).
- `InvestigationWorkspace.css`: `.workspace-graph-slot { position: absolute; inset: 0 }` + `.workspace-graph-slot.hidden { visibility: hidden; pointer-events: none }`.

**Backend deployment**
- Fly.io `atlas-api-pedro` deployed with `ingest_trends.py` + `narratives.py` changes (machine version 113, region iad, 1 passing health check as of 2026-05-17T13:57:17Z).

---

## Current Technical State (as of session 9 — 2026-05-11)

### Session 9 Additions

**Geo-validation (Wave 4 Phase 4)**
- `signals_v2.source_origin_country CHAR(2)` — outlet home country (≠ story subject country). Migration 012 applied, 12,944 US signals backfilled.
- `_extract_source_country(url)` in `ingest_v2.py` — 70+ known domains + ccTLD fallback.
- `foreignSourcePct` in country endpoint — null when <50 known-origin signals; shown as warning badge in `CountryBrief` when >60%.

**Source framing split (EntityPanel)**
- Replaces linear source list with Positive/Negative columns + narrative spread bar when sources span both extremes (threshold: `|avg_sentiment| > 0.2`, require ≥2 split sources).

**NER geo-filter**
- `_is_valid_person()` + `_GEO_NAME_BLOCKLIST` (40 entries) + `_GEO_FIRST_WORDS` in `main_v2.py` — filters GDELT-misclassified place names from People Mentioned.

**ESLint clean (#62)**
- `npm run lint` exits 0. `react-hooks/set-state-in-effect` and `purity` off; `no-explicit-any` downgraded to warning; before-declaration ordering fixed in `App.tsx`.

**Tolerant search (#51 closed)**
- `concept_suggestions` chip row added to `SearchBar.tsx`. All acceptance criteria met.

**Onboarding (session 9)**
- Removed redundant `welcome-card` and `map-hint` overlays from `App.tsx`. `OnboardingCoachmark` is the sole onboarding (localStorage, 3-step).

**Command bar stale-while-revalidate**
- `FocusDataContext` preserves nodes/meta during refetch when API returns empty. `App.tsx` command bar fades to 50% opacity during `isRefetching`.

**BRIEF Global Focus (session 9)**
- `Briefing.tsx` — theme→country pill rows showing signal counts per country per topic. Backend already had `theme_country_rows` query + Redis cache.

**Source blocklist expansion**
- 50+ domains added to `backend/app/config/source_blocklist.py`: consumer tech, sports leagues, entertainment, local US TV.

**Investigative concept vocabulary**
- 6 new `CONCEPT_MAP` entries: `blood-diamonds`, `electoral-fraud`, `narcotrafficking`, `forced-displacement`, `water-crisis`, `land-grabbing`.

## Current Technical State (as of session 8 — 2026-05-10)

### Critical Build Rule

Always run `npm run build` (not just `tsc --noEmit`) before pushing frontend changes. Vite uses `tsc -b` (project references), which is stricter. A passing `tsc --noEmit` does NOT guarantee a passing Vercel build.

### No Pending Fly.io Deploys

All backend changes are live. Fly.io app: `atlas-api-pedro`. Migrations 007–011 applied.

### Frontend Component Count

68 .tsx components in `frontend-v2/src/components/` as of 2026-05-10. Do not add Tailwind to any of them.
Session 7 additions: `OnboardingCoachmark`, `PublicAttentionPanel`, `TemporalNarrativeGraph`.

### NLP Pipeline (session 8, live on Fly.io)

- `backend/enrichment/nlp_pipeline.py` — three-phase pipeline: sentiment (RoBERTa), NER (spaCy), framing (NLI distilroberta).
- `ingest_loop.py` fires `asyncio.create_task(_nlp_background(limit=100))` after each GDELT cycle. Non-blocking. Skip if previous task still running.
- Dockerfile: `ENV HF_HOME=/app/hf_cache` and `ENV TRANSFORMERS_CACHE=/app/hf_cache` BEFORE pre-bake RUN. `ENV TRANSFORMERS_OFFLINE=1` AFTER pre-bake RUN. This is the OOM fix — do not reorder.
- NLP rate on Fly: ~200 signals/hour. Peak memory: ~720–738MB on 985MB machine.
- API: `COALESCE(nlp_sentiment, sentiment)` — RoBERTa replaces GDELT tone when available.

### Data Hygiene (session 8)

- Deleted 1,116,136 signals from Apr 27 – May 3 (no NLP, freed ~1GB).
- Retention policy: unprocessed signals deleted after 90 days, NLP-processed kept indefinitely.
- Automated cleanup in `ingest_loop.py` every 672nd cycle (~7 days).
- DB state: ~1.23M total signals, ~34K NLP-processed (2.8%), range May 3 – present.

### Data Coverage Badge (session 8)

- `App.tsx` fetches `oldest_signal` from `/api/v2/stats` on mount.
- Displays `FROM [DATE]` pill next to LIVE DATA in command bar.
- CSS class `.data-since-pill` in `App.css`.

### Branch Status

- `v3-intel-layer` IS production — Vercel and Fly.io both deploy from it.
- `main` is stale/abandoned. Do not merge into it.

### Investigation Workspace (session 6, still current)

- `InteractiveWorkspace.tsx` — react-force-graph-2d canvas. Lazy-loaded (chunk: ~187KB). Use react-force-graph-2d ONLY — the 3D version (react-force-graph) pulls AFRAME and crashes the app.
- `InvestigationWorkspace.tsx` + `InvestigationWorkspace.css` — shell. Wraps `InteractiveWorkspace` via `React.lazy()` + `Suspense` + `PanelErrorBoundary`. Rendered by App.tsx.
- `workspaceGraph.ts` — two-pass graph builder. Pinned nodes always succeed; edges per-item try/catch.

### Error Isolation Architecture (established session 6)

Three-layer error boundary hierarchy:
1. `RootErrorBoundary` in `main.tsx`
2. `PanelErrorBoundary` in `App.tsx` — wraps `InvestigationWorkspace` and other panels
3. `MapErrorBoundary` — wraps DeckGL map layer

### Theme Label Rule (session 6, still current)

All components rendering GDELT theme names must call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the API `label` field — it can return raw GDELT codes.

### Stream Panel Behavior (session 5, still current)

Default stream slot is `DiscoveryPanel` (blank state). State machine: `isPerson → isCompound → isCountry → isTheme → isChokepoint → DiscoveryPanel`.

### Sentiment Scale (unified session 7)

All endpoints return sentiment ÷10 (frontend expects ±1 range, ±0.1 thresholds). GDELT V2Tone raw is ~-20 to +20. Exception: ThemeDetail uses `getSentimentBarWidth()` which normalizes -10 to +10 internally. Do not change ThemeDetail.

### Coverage Confidence Badges (session 7)

Applied in CountryBrief, NarrativeThreads, ChokepointPanel: n<10 → `thin` (orange), 10≤n<50 → `limited` (yellow). CSS classes: `coverage-badge--thin`, `coverage-badge--limited` in respective CSS files.

### Concept Endpoint Fast Path (session 7)

`GET /api/v2/concept/{slug}?hours=N`: for `hours > 24` queries `theme_country_hourly_v2` (pre-agg, PK: hour+theme+country). For `hours ≤ 24` queries `signals_v2` directly. `effective_hours` always equals requested `hours`.

### Source Ingestion Stack (session 7)

- `ingest_rss.py` — Wave 1 general feeds + Wave 3 state media (RT/Sputnik/Global Times/IRNA) + non-English (France24 AR/BBC Arabic/El País/DW). `is_state_media=True` for state sources.
- `ingest_reliefweb.py` — Wave 2: 19 crisis country feeds via ReliefWeb OCHA. `geo_confidence=0.92`, `source_family='ngo'`. Direct URL pattern: `/updates/rss.xml?legacy-river=country/{iso3}` (not country path — that redirects and gets blocked).

### API Endpoints

- `GET /api/v2/search/unified?q=&hours=` — preferred search. Merges taxonomy, concepts, regions, DB. Cached 2 min.
- All v2 and v3 endpoints live. No pending deploys.

### FocusContext

- `GlobalFilter` includes `concept: ConceptFilter | null` and `region: RegionFilter | null`
- `setConcept()` expands to multiple GDELT themes; `setRegion()` expands to multiple countries

### Backend: gdelt_taxonomy.py

- `REGION_MAP` — 6 regions with ISO codes and multilingual aliases (EN/ES/FR/PT/DE/AR)
- `match_region()` — fuzzy region matching

### GitHub Issues Status

Open as of 2026-05-11 (6 issues): #46, #61, #70, #79, #80, #82, #83.
Closed session 7: #63, #73, #78, #81, #84–#93.
Closed session 8: #92 (Wave 4 NLP ADR).
Closed session 9: #51 (tolerant search), #62 (ESLint debt), #77 (source framing viz), #92 (NLP ADR), #99 (geo validation Wave 4 Phase 4), #100 (NER geo-filter).
Next priority: #83 (Signal Intelligence Panel), #61 (comparative engine UI), #70 (theme clustering), mac backfill completion.
