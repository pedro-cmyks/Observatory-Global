# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the FastAPI service (APIs, services, NLP logic) and pytest suites under `tests/`. The active React + Vite client lives in `frontend-v2/` (`src/pages`, `src/components`, `src/lib`, `src/App.tsx`). The `frontend/` directory is DEPRECATED — do not touch it. Docker/Compose exists for local dev only; production runs on Vercel (frontend) + Fly.io (backend). ADRs, demos, and decision logs go in `docs/`; keep environment templates in `.env.example`. MCP server configuration lives in `.mcp.json` (supabase + stitch). Design assets exported from Google Stitch live in `stitch_atlas_landing_experience_redesign/`.

Key files added in session 6:
- `frontend-v2/src/components/InteractiveWorkspace.tsx` — force-graph canvas (react-force-graph-2d). MUST be lazy-loaded only.
- `frontend-v2/src/components/InvestigationWorkspace.tsx` — lazy shell + PanelErrorBoundary wrapper.
- `frontend-v2/src/lib/workspaceGraph.ts` — two-pass graph builder (pinned nodes + edges with per-item try/catch).
- `frontend-v2/src/contexts/WorkspaceContext.tsx` — workspace state (pinned items, graph useMemo, detail fetching).

## Build, Test, and Development Commands
Local backend: `cd backend && poetry run uvicorn app.main_v2:app --reload --port 8000`. Local frontend: `cd frontend-v2 && npm run dev`. Fly.io deploy: `fly deploy` from repo root. Lint via `poetry run ruff check`, `poetry run mypy app`, `npm run lint`. Run `npm run build` before every PR — TypeScript/Vite errors must be zero. DO NOT rely on `tsc --noEmit` alone: Vite's build uses `tsc -b` (project references mode), which is stricter and catches errors like TS6133 (unused imports) that `tsc --noEmit` silently ignores. A green `tsc --noEmit` does not guarantee a passing Vercel build. Pytest: `cd backend && poetry run pytest`. Migrations are raw `.sql` files run from the Supabase SQL editor dashboard (NOT via alembic, NOT via the connection pooler).

## Coding Style & Naming Conventions
Python targets 3.11, 4-space indentation, 100-char lines (Black/Ruff). Favor pydantic models in `app/models`, keep modules snake_case, and expose FastAPI routes under `/api/v2/...` (NOT `/v1/` — all active endpoints are v2). TypeScript uses 2-space indentation, PascalCase components, camelCase hooks/store setters, and colocated styles only when needed. Run Ruff, Mypy, ESLint, and `tsc` before committing; never commit generated OpenAPI artifacts or `node_modules`. Tooltip system: use `data-tip="text"` on any element — never use native `title=` attributes.

Additional frontend conventions (session 6):
- Theme names: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the `label` field from API responses — it may contain raw GDELT code strings.
- Graph library: use `react-force-graph-2d` only. The 3D variant (`react-force-graph`) imports AFRAME and crashes the app.
- Lazy-load heavy components: any component importing large visualization libraries must be wrapped in `React.lazy()` + `Suspense` to keep the main bundle lean.
- Error boundaries: wrap any panel that loads async data in `PanelErrorBoundary`. The `RootErrorBoundary` in `main.tsx` is the final fallback only.

## Testing Guidelines
Backend tests live in `backend/tests/test_*.py` per `pyproject.toml`. New services need fixtures for flow/heat math and regression coverage for service clients; mock external providers through the client layer rather than hitting the network. Treat the coverage report from `make test-backend` as a gate and keep touched modules above the current baseline. Frontend work that touches the map or API should include Vitest/React Testing Library smoke tests or, at minimum, refreshed manual steps and screenshots in `docs/demos/`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`feat(flow): ...`, `docs: ...`, `revert: ...`) on focused branches such as `feat/frontend-map/...`. PRs should reuse the `PR_DESCRIPTION.md` structure: short summary, bullet list of file-level work, explicit test commands with results, and references to agent specs or ADRs. Attach screenshots or shell snippets for user-visible work, link relevant issues, and call out env or migration steps before requesting review.
