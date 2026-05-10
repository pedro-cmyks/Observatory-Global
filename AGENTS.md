# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the FastAPI service (APIs, services, NLP logic) and pytest suites under `tests/`. The active React + Vite client lives in `frontend-v2/` (`src/pages`, `src/components`, `src/lib`, `src/App.tsx`). The `frontend/` directory is DEPRECATED — do not touch it. Docker/Compose exists for local dev only; production runs on Vercel (frontend) + Fly.io (backend). ADRs, demos, and decision logs go in `docs/`; keep environment templates in `.env.example`. MCP server configuration lives in `.mcp.json` (supabase + stitch). Design assets exported from Google Stitch live in `stitch_atlas_landing_experience_redesign/`.

Key files added in session 6:
- `frontend-v2/src/components/InteractiveWorkspace.tsx` — force-graph canvas (react-force-graph-2d). MUST be lazy-loaded only.
- `frontend-v2/src/components/InvestigationWorkspace.tsx` — lazy shell + PanelErrorBoundary wrapper.
- `frontend-v2/src/lib/workspaceGraph.ts` — two-pass graph builder (pinned nodes + edges with per-item try/catch).
- `frontend-v2/src/contexts/WorkspaceContext.tsx` — workspace state (pinned items, graph useMemo, detail fetching).

Key files added in session 7:
- `frontend-v2/src/components/PublicAttentionPanel.tsx` — Google Trends + Wikipedia public-attention feed. Item clicks open investigation panel (no external navigation).
- `frontend-v2/src/components/TemporalNarrativeGraph.tsx` — timeline of narrative coverage + sentiment shift over time. In ThemeDetail. Workspace integration pending (#82).
- `frontend-v2/src/components/OnboardingCoachmark.tsx` — first-run onboarding overlay.
- `backend/app/services/ingest_rss.py` — RSS curated feed ingestion (Wave 1 + Wave 3).
- `backend/app/services/ingest_reliefweb.py` — ReliefWeb/OCHA humanitarian feeds (Wave 2, 19 crisis countries, geo_confidence=0.92).
- `backend/migrations/008_source_provenance.sql` — source_family, source_lang, geo_confidence, attribution_method, is_state_media fields.
- `backend/migrations/009_trends_v2_constraint.sql` — trends_v2 hour_bucket UNIQUE constraint.
- `backend/migrations/010_theme_country_hourly.sql` — theme_country_hourly_v2 pre-agg table.

Key files changed in session 8:
- `backend/app/services/ingest_loop.py` — NLP as non-blocking background task (`asyncio.create_task`), weekly 90-day retention cleanup for unprocessed signals.
- `backend/Dockerfile` — HF_HOME and TRANSFORMERS_CACHE env vars placed before pre-bake RUN; offline env vars placed after. Fixes OOM on Fly.io.
- `backend/enrichment/nlp_pipeline.py` — three-phase NLP pipeline (sentiment, NER, framing). Called by ingest_loop background task.
- `backend/migrations/011_nlp_columns.sql` — NLP columns on signals_v2 (APPLIED).
- `frontend-v2/src/App.tsx` — data coverage badge: fetches oldest_signal from /api/v2/stats, shows FROM [DATE] pill.
- `frontend-v2/src/App.css` — `.data-since-pill` CSS class.

## Build, Test, and Development Commands
Local backend: `cd backend && poetry run uvicorn app.main_v2:app --reload --port 8000`. Local frontend: `cd frontend-v2 && npm run dev`. Fly.io deploy: `fly deploy` from repo root. Lint via `poetry run ruff check`, `poetry run mypy app`, `npm run lint`. Run `npm run build` before every PR — TypeScript/Vite errors must be zero. DO NOT rely on `tsc --noEmit` alone: Vite's build uses `tsc -b` (project references mode), which is stricter and catches errors like TS6133 (unused imports) that `tsc --noEmit` silently ignores. A green `tsc --noEmit` does not guarantee a passing Vercel build. Pytest: `cd backend && poetry run pytest`. Migrations are raw `.sql` files run from the Supabase SQL editor dashboard (NOT via alembic, NOT via the connection pooler).

## Coding Style & Naming Conventions
Python targets 3.11, 4-space indentation, 100-char lines (Black/Ruff). Favor pydantic models in `app/models`, keep modules snake_case, and expose FastAPI routes under `/api/v2/...` (NOT `/v1/` — all active endpoints are v2). TypeScript uses 2-space indentation, PascalCase components, camelCase hooks/store setters, and colocated styles only when needed. Run Ruff, Mypy, ESLint, and `tsc` before committing; never commit generated OpenAPI artifacts or `node_modules`. Tooltip system: use `data-tip="text"` on any element — never use native `title=` attributes.

Additional frontend conventions (session 6):
- Theme names: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the `label` field from API responses — it may contain raw GDELT code strings.
- Graph library: use `react-force-graph-2d` only. The 3D variant (`react-force-graph`) imports AFRAME and crashes the app.
- Lazy-load heavy components: any component importing large visualization libraries must be wrapped in `React.lazy()` + `Suspense` to keep the main bundle lean.
- Error boundaries: wrap any panel that loads async data in `PanelErrorBoundary`. The `RootErrorBoundary` in `main.tsx` is the final fallback only.

Additional frontend conventions (session 7):
- Sentiment display: all API endpoints return sentiment in ÷10 normalized range. Frontend thresholds: ±0.1 neutral, beyond = positive/negative. Do NOT divide again on the frontend.
- Coverage confidence badges: when signal count n<10 render an orange "thin" badge; 10≤n<50 render a yellow "limited" badge; n≥50 no badge. Apply in any component displaying per-country/per-source metrics (CountryBrief, NarrativeThreads, ChokepointPanel pattern).
- PublicAttentionPanel item clicks: must open InvestigationWorkspace (internal), never navigate to external URL.
- Component count: 39 .tsx components in `frontend-v2/src/components/`.

Backend conventions (session 7):
- All new ingestion services must set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, and `is_state_media` on every inserted row.
- Concept endpoint hours>24 must query `theme_country_hourly_v2`, not `signals_v2`. Do not re-add the `effective_hours` cap.

Backend conventions (session 8):
- Migrations 007–011 are all applied. Next migration will be 012.
- NLP pipeline runs as a background task in `ingest_loop.py` — do not make it blocking.
- Dockerfile: `ENV HF_HOME=/app/hf_cache` and `ENV TRANSFORMERS_CACHE=/app/hf_cache` MUST appear before the pre-bake RUN step. `ENV TRANSFORMERS_OFFLINE=1` and `ENV HF_DATASETS_OFFLINE=1` MUST appear after. Do not reorder — this is the OOM fix.
- Data retention: unprocessed signals (nlp_processed_at IS NULL) are deleted after 90 days. NLP-processed signals are kept indefinitely.
- Branch: `v3-intel-layer` is production. `main` is abandoned — do not merge into it.

## Testing Guidelines
Backend tests live in `backend/tests/test_*.py` per `pyproject.toml`. New services need fixtures for flow/heat math and regression coverage for service clients; mock external providers through the client layer rather than hitting the network. Treat the coverage report from `make test-backend` as a gate and keep touched modules above the current baseline. Frontend work that touches the map or API should include Vitest/React Testing Library smoke tests or, at minimum, refreshed manual steps and screenshots in `docs/demos/`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`feat(flow): ...`, `docs: ...`, `revert: ...`) on focused branches such as `feat/frontend-map/...`. PRs should reuse the `PR_DESCRIPTION.md` structure: short summary, bullet list of file-level work, explicit test commands with results, and references to agent specs or ADRs. Attach screenshots or shell snippets for user-visible work, link relevant issues, and call out env or migration steps before requesting review.
