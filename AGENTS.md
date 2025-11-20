# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the FastAPI service (APIs, services, NLP logic) and pytest suites under `tests/`, plus shared agent specs in `.agents/`. The React + Vite client lives in `frontend/` (`src/pages`, `src/components`, `src/store`), Docker + Cloud Code manifests sit in `infra/`, and data exports or fixtures land in `data/`. ADRs, demos, and decision logs go in `docs/`; keep environment templates in `.env.example` and surface reusable scripts through the root `Makefile`.

## Build, Test, and Development Commands
`make up` builds and starts the Compose stack from `infra/`; `make down` stops it. Local loops use `make dev-backend` (Poetry + Uvicorn reload) and `make dev-frontend` (Vite dev server). Lint via `make lint` or component-specific commands (`poetry run ruff check`, `poetry run mypy app`, `npm run lint`). `make test-backend` runs pytest with HTML coverage in `backend/htmlcov/index.html`, while `make test-backend-fast` skips coverage. Always run `npm run build` before PRs so TypeScript/Vite errors surface early.

## Coding Style & Naming Conventions
Python targets 3.11, 4-space indentation, 100-char lines (Black/Ruff). Favor pydantic models in `app/models`, keep modules snake_case, and expose FastAPI routes under `/v1/...`. TypeScript uses 2-space indentation, PascalCase components, camelCase hooks/store setters, and colocated styles only when needed. Run Ruff, Mypy, ESLint, and `tsc` before committing; never commit generated OpenAPI artifacts or `node_modules`.

## Testing Guidelines
Backend tests live in `backend/tests/test_*.py` per `pyproject.toml`. New services need fixtures for flow/heat math and regression coverage for service clients; mock external providers through the client layer rather than hitting the network. Treat the coverage report from `make test-backend` as a gate and keep touched modules above the current baseline. Frontend work that touches the map or API should include Vitest/React Testing Library smoke tests or, at minimum, refreshed manual steps and screenshots in `docs/demos/`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`feat(flow): ...`, `docs: ...`, `revert: ...`) on focused branches such as `feat/frontend-map/...`. PRs should reuse the `PR_DESCRIPTION.md` structure: short summary, bullet list of file-level work, explicit test commands with results, and references to agent specs or ADRs. Attach screenshots or shell snippets for user-visible work, link relevant issues, and call out env or migration steps before requesting review.
