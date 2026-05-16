# Atlas — Session Log

## 2026-05-16 (session 18 — Video UX review + productization roadmap)

### Session type: UX research, issue triage, roadmap planning

### What happened
Reviewed the three owner walkthrough videos through local transcripts and extracted visual frames:

- Landing walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.40.47.txt`
- Brief walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.53.02.txt`
- App walkthrough: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-16 at 09.25.31.txt`
- App YouTube captions: `docs/research/ux-video-evaluation/transcripts/youtube-app-x8qlx2cijEE-es-auto.txt`

Added:

- `docs/research/ux-video-evaluation/2026-05-16-atlas-video-review.md`
- `docs/superpowers/specs/2026-05-16-atlas-productization-design.md`
- `docs/roadmap/2026-05-16-productization-roadmap.md`

### Key conclusion
The correct flow remains `Landing -> Brief -> App`, but Atlas needs a productization pass before more advanced features. The next product theme is:

**Make Atlas teachable, persistent, and exportable.**

### Issue work
Reopened with new video evidence:

- #56 Day/Night overlay + Settings utility
- #69 Spanish-language routing + multilingual query expansion
- #104 Google Trends missing/stale data
- #124 Saved watches / persistent alerts
- #128 Workspace viewport + Trail/Pinned graph clarity

Created:

- #135 Landing live stats + clickable docs/use-case cards
- #136 Landing -> Brief -> App prefetch/loading states
- #137 Methodology/editorial explanation
- #138 Investigation context persistence
- #139 Time range beyond 24h + Live/Pause semantics
- #140 Visual use-case manual with real Atlas screenshots
- #141 Reading Mode / investigation newspaper from pinned evidence
- #142 Public Attention scoping and actionability
- #143 Map layer explanation and decluttering

Expanded:

- #133 Workspace dossier should become the evidence foundation for Reading Mode.
- #134 Use cases should be visual and product-grounded, not text-only.

### Next
Start with P0 trust/continuity issues: #136, #137, #138, #128, #104/#142, and #69. After that, build the visual manual (#140/#134/#135), then Workspace Dossier and Reading Mode (#133/#141).

---

## 2026-05-14 (session 17 — Remaining closable issues closed)

### Session type: Issue closure + branch synchronization

### What happened
Started from the session 16 handoff and verified GitHub open issues. Found that local `v3-intel-layer` was 10 commits ahead of `origin/v3-intel-layer`; ran `npm run build`, committed the remaining-issues plan, and pushed `origin/v3-intel-layer` to match local before new work.

**Closed issues:**
- `220b91f` **#82** Temporal Narrative Graph selected bucket can now be pinned as a `temporal_snapshot` workspace node, with graph relationships to theme, countries, sources, people, and related themes.
- `7fb5eaa` **#61** Added shared `CompareDashboard` shell; ThemeCompare and PersonCompare now use one reusable 50/50 comparison overlay.
- `ea6c2ce` **#105** Safely ported only `backend/app/services/ingest_rss.py` from candidate branch; RSS registry now has 50 curated feeds across LATAM, MENA, Sub-Saharan Africa, and Southeast Asia.
- `2d3b2aa` **#70** Added frontend-only theme hierarchy: 7 clusters, 79 mapped codes, grouped EntityPanel related themes, and NarrativeThreads cluster labels.

**Blocked issues documented:**
- **#46** ACLED remains open with `blocked` label; needs real ACLED API access and credentials.
- **#106** Octopus mascot remains open with `blocked` label; needs designer SVG assets before implementation.

### Validation
- `cd frontend-v2 && npm run test` → 26 passed.
- `cd frontend-v2 && npm run build` → passed; existing large chunk warning only.
- `python3 -m py_compile backend/app/services/ingest_rss.py` → passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_health.py -q` → 2 passed.
- Production Fly `/health` → 200 healthy after `82e2e77`.
- Production Fly and Vercel `/api/v2/narratives?hours=24&limit=3` → 200 JSON after `6e8e0df`.
- Production Vercel `/api/v2/stats` → 200 JSON.

### Production hotfixes
- `82e2e77` restored missing `datetime/timezone/asyncio` imports in `backend/app/routers/stats.py`; fixed `/health` 500 after deploy.
- `6e8e0df` restored missing runtime imports across split routers; fixed `/api/v2/narratives` 500 and prevented similar `app.state.redis`, `json`, and `datetime/timezone` failures in adjacent endpoints.

### Next
Production is deployed and smoke-tested on `v3-intel-layer`. Remaining open GitHub issues are blocked externally: #46 needs ACLED credentials, #106 needs designer SVG assets. Keep production on `v3-intel-layer` unless a separate branch-migration decision is made.

---

## 2026-05-14 (session 16 — Tier 5 sweep: 10 issues closed)

### Session type: Issue closure + feature work

### What happened
Continued from session 15. Triaged all 12 remaining open issues by effort, picked path of least resistance, closed 10 in one session.

**Verified already-implemented (3):**
- `#80` — Session graph: trackVisit, Trail tab, promote-to-pin all shipped in session 12
- `#79` — Public Attention AEIL: pin support, workspace node type, graph relationships, navigate-back all implemented
- `#114` — Workspace audit: wrote `docs/research/workspace-expert-audit.md` (synthetic expert walkthrough, drug-trafficking topic, 28-min session, 9 gaps documented, 4 new issues recommended)

**Bug fixes (3):**
- `2f97f19` **#129** Onboarding tour writes `localStorage` on mount → navigating away before Skip/Done no longer re-triggers tour
- `5e2499b` **#130** SourceIntegrityPanel: `filter.theme` routed through `getThemeLabel()`, raw GDELT codes gone
- `f5e4383` **#132** Workspace graph: compact dot + type initial when nodeCount ≥ 20 and globalScale < 1.2; full labels return on zoom

**Features (4):**
- `09d24be` **#131** Custom investigative concepts: `useCustomConcepts` hook (localStorage), `CustomConceptModal` (label + description + debounced theme search picker), SearchBar shows "My Concepts" section + "Save as concept" CTA
- `1888800` **#111** StreamLevel added to FocusContext GlobalFilter; SignalStream writes it on every tab click; AnomalyPanel shows THREAD/STREAM context badge; SourceIntegrityPanel shows level pill
- `37aaf0b` **#124** Saved watches: `useSavedWatches` hook, WATCH button (gold, toolbar, only when filter active), name dialog, watches section in /brief with Open-in-Atlas deep-link
- `3f42949` **#109** Evolution Graph: degree-1 nodes render at 55% radius + hide label below zoom 1.4; "⊞ Workspace" button pins theme + opens WorkspaceBoard

**Untracked audit fixes:**
- `21fa9d0` NarrativeThreads country pips → clickable buttons (setCountry + fly + onCountrySelect); thread click auto-opens CountryBrief for top country

**Documentation:**
- `#106` scoped in issue comment: needs designer SVG assets (3 poses, 3 costume overlays) before dev starts
- `1b2b35c` `docs/research/workspace-expert-audit.md` added

### Build status
`npm run build` passed (11s). 6 open issues remain — all L/research/blocked.

### Open issues after session
#82 (temporal+workspace), #61 (compare engine), #105 (RSS), #70 (theme clustering), #46 (ACLED, blocked), #106 (needs designer)

### Next
#82 is the highest-value remaining item — temporal narrative graph integration with WorkspaceBoard. Requires rethinking the bucket model.

---

## 2026-05-14 (session 15 — Issue blitz: Tiers 1–4 closed)

### Session type: Systematic issue closure

### What happened
Reviewed all 26 open issues, categorized into 4 tiers by impact/effort, and closed 14 in one session.

**Tier 1 — Already implemented, code-verified and closed (7):**
#108, #119, #120, #121, #122, #123, #127

**Tier 2 — Bug fixes (2):**
- `9a0cb5d` **#128** Workspace: Trail and Pinned are now separate graph modes; header fixed; charge strength auto-scales
- `9a0cb5d` **#110** Top Sources LIMIT 10 → 20 in backend theme endpoint

**Tier 3 — UX polish (3):**
- `c265c77` **#126** TemporalNarrativeGraph hover dims unconnected nodes/links (refs pattern for frame stability)
- `cbd58b2` **#112** Related Topics compare button: VS → icon + tooltip + CSS class + overflow fix
- `9eadc3f` **#113** Signal Stream entry: green flash + left border glow animation (650ms, live-arrival feel)

**Tier 4 — Tech debt (2):**
- `547db58` **#107** PanelSkeleton shimmer component; stale-while-revalidate in ThemeDetail; skeletons in NarrativeDrift + FocusSummaryPanel
- `bf037cf` **#125** Backend split: main_v2.py 4958→120 lines, 12 APIRouter files, app/db.py, app/utils.py

### New issues opened during session
- **#129** Guided tour re-triggers every visit (bug — should be localStorage-gated)
- **#130** Raw GDELT code `CRISISLEX_CRISISLEXREC` visible in Source Integrity panel
- **#131** Custom investigative concepts (feat)
- **#132** Workspace graph label overlap at 26+ nodes

### Build status
`npm run build` passed (15s). All 43 backend routes import-verified with `.venv` Python.

### Next
#129 (guided tour bug) + #130 (raw code bug) — both small, high-visibility.

---

## 2026-05-14 (session 14 — UX Panel Evaluation Ronda 2)

### Session Type: Documentation & UX Research (no code shipped)

### Context
Between sessions 12 and 14, significant work was done by Claude Code (sessions 10–13), shipping 14 of the 16 issues identified in our first evaluation. This session re-evaluates Atlas against the same 5-persona panel to measure progress.

### UX Panel Evaluation Ronda 2 (5-persona re-audit)
Re-evaluated against production (observatory-global.vercel.app):

| Evaluator | Sesión 12 | Sesión 14 | Delta |
|-----------|:---------:|:---------:|:-----:|
| **Investor (VC)** | 7/10 | 8/10 | **+1** |
| **CTO** | 7.5/10 | 8.5/10 | **+1** |
| **Journalist** | 7/10 | 8/10 | **+1** |
| **Product (UX)** | 7/10 | 8.5/10 | **+1.5** |
| **Intelligence Analyst** | 8/10 | 8.5/10 | **+0.5** |
| **PROMEDIO** | **7.3** | **8.3** | **+1.0** |

### Issues Verified as Resolved (from Session 12 → closed by Claude Code)
#108, #112, #113, #119, #120, #121, #122, #123, #125, #126, #127, #128, #107

### New Issues Created (from Ronda 2 findings)
- **#129** — Guided tour re-triggers on every console visit ← bug, should only show first time
- **#130** — Raw theme code `CRISISLEX_CRISISLEXREC` visible in Source Integrity ← `getThemeLabel()` rule violation
- **#131** — Allow users to create custom investigative concepts ← owner-endorsed scope expansion
- **#132** — Workspace graph label overlap with 26+ nodes ← follow-up to #128

### Owner Notes
- Custom investigative concepts (#131) endorsed as an important scope problem — the 6 fixed concepts demonstrate the engine's power but limit the analytical lens.

---

## 2026-05-12 (session 12 — UX audit, panel evaluation, documentation)

### Session Type: Documentation & UX Research (no code shipped)

### Added
- **Ephemeral Session Trail (#63)** — `WorkspaceContext` now tracks up to 20 visited items per session. `workspaceGraph.ts` generates chronological `session-trail` links. `InteractiveWorkspace` renders session nodes with dashed borders and includes a "Show Session Trail" toggle. `App.tsx` auto-tracks visits to countries, themes, sources, persons, and public attention items.
- **CompareSearchModal integration** — rescued from Claude Code worktree (`competent-maxwell-4eb03c`) and integrated into EntityPanel.
- **Z-score heat map logic** — backend `/api/v2/nodes` now uses statistical z-score instead of absolute counts for anomaly heat representation.
- **Google Trends expansion** — coverage expanded from 30 to 84 countries (commit `7594cb3`).

### UX Panel Evaluation (5-persona audit)
Conducted a rigorous multi-persona UX audit against production (observatory-global.vercel.app):

| Evaluator | Verdict | Key Finding |
|-----------|---------|-------------|
| **Investor (VC)** | 7/10 | `/brief` is the killer feature — lead with it. No clear ICP yet. |
| **CTO** | 7.5/10 | `main_v2.py` monolith (4,100 lines) is tech debt #1. Error boundaries are excellent. |
| **Journalist** | 7/10 | Source Family badges are powerful. Signal Stream is noise — needs editorial default. |
| **Product (UX)** | 7/10 | Dashboard default is overwhelming. "CF CF" country name bug found in production. |
| **Intelligence Analyst** | 8/10 | 4-source cross-correlation is unique. English-language bias needs disclaimer. |

**Overall: 7.3/10** — "Atlas doesn't need more features. It needs to decide who its #1 user is."

### Issues Created (from audit findings)
- **#119** — Brief country filter should include ALL countries (not just highlighted) ← owner-reported
- **#120** — Default Signal Stream to NOTABLE/CRITICAL, not ALL ← relates to #111, #113
- **#121** — Add coverage bias disclaimer to dashboard ← relates to #105, #91, #70
- **#122** — Country Brief shows "CF CF" instead of full name ← bug
- **#123** — Make Workspace tab more discoverable ← relates to #114, #80
- **#124** — Saved searches / persistent alerts for investigative patterns ← relates to #61, #80
- **#125** — Refactor main_v2.py into APIRouter modules ← relates to #107, #73
- **#126** — TemporalNarrativeGraph hover-to-focus (dim unselected) ← relates to #82, #109
- **#127** — Filter entertainment from Public Attention panel ← relates to #78, #85

### Cross-reference with existing open issues
| Existing Issue | Audit Finding |
|---------------|--------------|
| #111 (Stream filter accessibility) | Confirmed: ALL default is wrong. → #120 created |
| #113 (Stream show volume) | Confirmed: volume metric exists but doesn't help curation |
| #114 (WorkspaceBoard UX research) | Confirmed: workspace is hard to find → #123 created |
| #109 (Evolution Graph interactions) | Confirmed: spaghetti effect → #126 created |
| #107 (perf audit) | Confirmed: would benefit from router split → #125 created |
| #105 (RSS feed expansion) | Confirmed: bias is structural, not just volume → #121 created |
| #82 (Temporal graph integration) | Confirmed: needs hover-to-focus → #126 created |

### Owner Notes
- Monetization: owner prefers Wikipedia-style donation model (free for the world). Not pursuing SaaS.
- Philosophy: Atlas exists to help users escape algorithmic echo chambers and see beyond their local information bubble.

---

## 2026-04-24 (session 2)

### Added
- **EntityPanel component** — right panel for person/keyword search results. Shows: trust indicators (source diversity, countries, global sentiment), coverage by country (bar chart colored by sentiment), related themes (clickable chips → ThemeDetail), top sources with sentiment, recent headlines. Opens automatically when `focus.type === 'person'`.
- **Keyword search fully connected** — SearchBar now triggers map fly + correct panel for all result types:
  - Country result → fly + CountryBrief
  - Theme result → fly to top country + ThemeDetail + arcs
  - Person result → fly to top country + EntityPanel (person-filtered map)
- **FocusContext: person as first-class focus type** — added `person: string | null` to `GlobalFilter`, `setPerson()` method, `focus.type` now returns `'person'`. Previously `setFocus('person',...)` called `clearFilter()` silently.
- **Search endpoint enriched** — themes and persons now return `total_signals` + `top_countries [{code, name, count}]` (needed for map fly). TAX_* and WORLDLANGUAGES_* themes excluded from results. Redis cache 2 min.
- **Search dropdown redesigned** — country tag (blue), person tag (violet), signal count + top country codes in meta. ESC closes, × button clears.

### Fixed
- `setFocus('person', ...)` was silently calling `clearFilter()` — EntityPanel never rendered
- Country click inside EntityPanel now calls `clearFocus()` first so CountryBrief can take over
- Theme search was matching GDELT taxonomy codes (TAX_WORLDFISH_TRUMPETER for "trump") — filtered

### Known issues / Roadmap
- AI insight: account needs Anthropic credits (key is loaded, auth works)
- Person click inside CountryBrief/ThemeDetail pill → still no action (separate from search)
- Aircraft: still amber dots, needs intelligence-value filter (military/diplomatic callsigns)
- Maritime vessels: AISStream Phase 3C, not started
- Globe 3D: deferred

### Next session
- Sort/rank for article coverage in ThemeDetail (currently timestamp, consider relevance)
- Hosting: move off local Mac → Fly.io (backend) + Vercel (frontend)
- Aircraft intel layer: filter by military/diplomatic callsigns (ADSBExchange)
- Maritime layer design + implementation

---

## 2026-04-24

### Added
- **Country territory click** — Mapbox fill layer (`country-heat-fill`) click handler replaces node dot clicks. Clicking anywhere on a country's geography fires `handleCountryClick`. Includes `ISO_TO_GDELT` mapping for code mismatches (ID→RI, RS→RB, XK→KV, etc.)
- **Node dots removed** — `nodes-core` ScatterplotLayer deleted. Territory click handles selection. Anomaly pulse rings (red circles for crisis countries) preserved.
- **NODES toggle button removed** — was controlling the now-deleted dots layer.
- **AI insight error codes** — backend now returns `insight_no_credits` (vs `insight_unavailable`) when the Anthropic API rejects due to low balance. ThemeDetail shows actionable message: "Anthropic account has no credits (top up at console.anthropic.com)"
- **Insight model fix** — model name corrected from `claude-haiku-4-5` → `claude-haiku-4-5-20251001`
- **CorrelationMatrix parse error fix** — removed IIFE pattern `(() => { ... })()` inside JSX ternary (Babel parser incompatible). Refactored normalization into a plain variable block before the return.

### Known issues / Roadmap
- **AI insight**: `ANTHROPIC_API_KEY` is loaded and auth works, but account has no API credits — add funds at console.anthropic.com to activate
- People Mentioned: pills shown but person click → no action yet
- Keyword/company search: SearchBar exists but free-text search not connected to backend
- Aircraft icon: still amber dot, real plane SVG shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred

### Next session
- Signal stream sort order — review how articles are ordered inside ThemeDetail recent coverage (currently by timestamp, consider by relevance/sentiment)
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Aircraft icon → real plane SVG shape

---

## 2026-04-23 (session 2)

### Added
- `COUNTRY_COORDS` static coordinate table in App.tsx — map fly now works for countries without active signals (Slovenia, Tanzania, Albania, etc.)
- `CountryThemePanel` component — right panel showing a country's specific coverage of a theme (timeline, sources, articles, related topics). Positioned at right:0, z-index 500
- ThemeDetail `hasRightPanel` prop — shifts overlay left (padding-right: 420px) so it doesn't cover CountryThemePanel
- ThemeDetail `onCountryCardClick` prop — "How It's Covered" cards now update the right CountryThemePanel instead of drilling in center
- ThemeDetail `originCountry` — origin country appears first in "How It's Covered" grid with blue highlight
- `rightPanelThemeCountry` state in App.tsx — manages which country+theme to show in right panel
- Backend: `load_dotenv()` added to main_v2.py to auto-load root `.env` (fixes ANTHROPIC_API_KEY not found)
- Better insight error message: "AI analysis not configured — add ANTHROPIC_API_KEY to .env and restart the backend"
- Welcome card switched from `localStorage` to `sessionStorage` — shows on every new session, not once ever
- AnomalyPanel now calls `setFocus('country', code)` + `setMapFlyCountry(code)` — map flies on anomaly click
- CountryBrief: `useCrisis()` anomaly lookup — shows `▲ Nx above 7-day baseline` badge + spike indicator on top theme
- CountryBrief: `WORLDLANGUAGES_` and `TAX_WORLDLANGUAGES_` themes filtered from top themes (GDELT language metadata, not actual topics)
- Help mode toggle (`?` button in toolbar) — cursor changes, `[data-help]` hover tooltips enabled globally
- `data-help` attributes on ThemeDetail section headers

### Fixed
- AnomalyAlert click had no map fly (used `setCountry` not `setFocus`)
- CountryBrief theme click opened ThemeDetail without country context or map fly
- ThemeDetail showed "Coverage analysis unavailable" without explanation
- Welcome card never showed again after first dismiss
- ThemeDetail auto-drilled into country (reverted) — now always shows global view
- "Language: Slovenian" no longer appears in top themes (GDELT language tag, not topic)

### Known issues / Roadmap
- ANTHROPIC_API_KEY: backend must be restarted after adding key to .env
- People Mentioned: pills shown but person click → no action yet (search/filter by person not implemented)
- Keyword/company search: SearchBar exists but free-text topic search not yet connected to backend
- Aircraft icon: still amber dot, real plane shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred to later phase
- OpenSky free tier: ~1 req/60s rate limit

### Next session
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane SVG shape
- UX: first-minute experience / onboarding improvements

---

## 2026-04-23

### Added
- AI Coverage Insight endpoint: `GET /api/v2/theme/{theme_code}/insight` (Claude Haiku, Redis-cached 15 min, Ollama fallback)
- `anthropic>=0.40.0` added to backend/pyproject.toml
- `.env.example` updated with `ANTHROPIC_API_KEY`, `INSIGHT_PROVIDER`, `OLLAMA_HOST`, `OLLAMA_MODEL`
- ThemeDetail: async insight block, person pills, 2-col related grid, source-filter for Recent Coverage
- FocusContext: `mapFlyCountry` state + `setMapFlyCountry()` for cross-component fly-to hints
- App.tsx: 4 new effects — map fly from Correlation Matrix, fly from NarrativeThreads hint, open ThemeDetail on filter.theme change, close CountryBrief on external country clear
- ESC handler and close callbacks now call `clearFocus()` consistently
- ArcLayer now renders on theme focus; `filter.theme` added to layers useMemo deps

### Fixed
- CountryBrief re-open bug (close was being overridden by focus sync)
- NarrativeThreads theme click only showed pill — ThemeDetail never opened
- Country click in Correlation Matrix did not animate map

### Activate insight feature
Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`. Without it the endpoint returns `insight: null` gracefully.

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape

---

## 2026-04-20

### Added
- Aircraft layer: OpenSky integration, amber dots, PLANE toggle
- Graceful degradation for API rate limits (no fake data)
- ThemeDetail framing section promoted to top
- Correlation Matrix → CountryBrief click navigation
- Source Integrity: real domain names from backend (extract_domain)
- GDELT theme label improvements (regex cleanup in themeLabels.ts)
- README rewritten for Atlas public launch
- CONTRIBUTING.md added

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape
