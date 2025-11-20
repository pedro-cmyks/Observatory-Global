# CLAUDE.md - Project Guidelines and Agent Configuration

This file provides Claude Code with essential context about the Observatorio Global project, including agent configurations, tooling guidelines, and development workflows.

## Project Overview

Observatorio Global is a narrative intelligence system that tracks, analyzes, and visualizes how topics and narratives propagate across global media sources. The system aggregates signals from multiple data sources (GDELT, Reddit, Mastodon, etc.), normalizes them into a unified schema, and provides insights on geographic drift, sentiment analysis, and narrative mutations.

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
- **Source Family Analysis**: GDELT, Reddit, Mastodon, HN coverage patterns, biases, and reliability
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

**Purpose**: Implements and modifies the flows API, health endpoints, and trends endpoints in the Python/FastAPI backend.

**When to Call**:
- Implementing API endpoints (GET /v1/flows, /v1/health, /v1/trends)
- Implementing caching strategies with Redis
- Writing database migrations for PostgreSQL
- Calculating heat formulas and similarity scores
- Writing tests for backend functionality

**Interaction with Backend Tasks**:
- Implements endpoints following Pydantic model patterns
- Creates database migrations with proper indexes
- Implements caching with key patterns from DataSignalArchitect
- Writes unit and integration tests

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

**Purpose**: Implements interactive map visualizations using React and Mapbox GL.

**When to Call**:
- Adding circle markers/hotspots to maps
- Creating animated flow lines between countries
- Building map-related UI components (filters, sidebars)
- Handling real-time data updates with auto-refresh

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
```
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

### Purpose

Use Gemini CLI when:
- Analyzing large codebases or multiple files that exceed context limits
- Reviewing or comparing full directories
- Scanning for patterns across many files
- Verifying complex implementations scattered across the codebase
- Loading hundreds of files at once
- Performing static read-only analysis requiring massive context

### Syntax

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

### Purpose

Use Codex CLI when:
- Generating large code modules or full files
- Performing refactors across many files
- Generating test suites or documentation
- Scaffolding entire features or microservices
- Executing code or commands
- Running project automation tasks (formatters, linters, migrations)
- Transforming files requiring "write access"

### Syntax

Use `codex -p` for prompting:

```bash
codex -p "<prompt here>"
```

Codex also supports the `@file` and `@directory/` syntax for including context.

### Code Generation Examples

**Implement an endpoint:**
```bash
codex "Implement GET /v1/narratives/topic endpoint in backend/app/api/v1/narratives.py following the existing patterns"
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
claude "Design the /v1/narratives/topic endpoint with request/response schemas"

# 2. Gemini checks existing endpoint patterns
gemini -p "@backend/app/api/v1/ Show me the pattern used for existing endpoints including error handling"

# 3. Codex implements the endpoint
codex "Implement /v1/narratives/topic in backend/app/api/v1/narratives.py using the designed schema and existing patterns"
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
