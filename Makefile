.PHONY: help setup up down logs test test-backend test-frontend lint format clean migrate seed status health

# Colors for pretty output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@echo "$(BLUE)Observatory Global - Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

setup: ## Initial project setup (copy .env, install deps)
	@echo "$(BLUE)Setting up Observatory Global...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env from .env.example$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env already exists, skipping$(NC)"; \
	fi
	@echo "$(GREEN)✓ Setup complete! Run 'make up' to start services$(NC)"

install-backend: ## Install Python dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	cd backend && poetry install
	@echo "$(GREEN)✓ Backend dependencies installed$(NC)"

install-frontend: ## Install Node.js dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

install: install-backend install-frontend ## Install all dependencies

##@ Docker Operations

up: ## Start all services (docker compose up)
	@echo "$(BLUE)Starting Observatory Global services...$(NC)"
	cd infra && docker compose up --build -d
	@echo "$(GREEN)✓ Services started!$(NC)"
	@echo "$(YELLOW)Backend:  http://localhost:8000$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:5173$(NC)"
	@echo "$(YELLOW)Redis:    localhost:6379$(NC)"
	@echo "$(YELLOW)Postgres: localhost:5432$(NC)"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	cd infra && docker compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

logs: ## Tail logs from all services
	cd infra && docker compose logs -f

logs-backend: ## Tail backend logs only
	cd infra && docker compose logs -f backend

logs-frontend: ## Tail frontend logs only
	cd infra && docker compose logs -f frontend

logs-redis: ## Tail Redis logs only
	cd infra && docker compose logs -f redis

logs-db: ## Tail Postgres logs only
	cd infra && docker compose logs -f db

ps: ## Show running services
	cd infra && docker compose ps

##@ Development

dev-backend: ## Run backend in dev mode (hot reload)
	cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend in dev mode (hot reload)
	cd frontend && npm run dev

shell-backend: ## Open shell in backend container
	cd infra && docker compose exec backend /bin/bash

shell-db: ## Open psql shell in database
	cd infra && docker compose exec db psql -U observatory -d observatory

shell-redis: ## Open redis-cli shell
	cd infra && docker compose exec redis redis-cli

##@ Testing

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests with coverage
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && poetry run pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Backend tests complete. Coverage report: backend/htmlcov/index.html$(NC)"

test-backend-fast: ## Run backend tests without coverage (faster)
	@echo "$(BLUE)Running backend tests (fast mode)...$(NC)"
	cd backend && poetry run pytest tests/ -v
	@echo "$(GREEN)✓ Backend tests complete$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm run test
	@echo "$(GREEN)✓ Frontend tests complete$(NC)"

test-watch: ## Run tests in watch mode
	cd backend && poetry run pytest-watch

##@ Code Quality

lint: lint-backend lint-frontend ## Run linters on all code

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(NC)"
	cd backend && poetry run ruff check app/ tests/
	cd backend && poetry run mypy app/
	@echo "$(GREEN)✓ Backend linting complete$(NC)"

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(NC)"
	cd frontend && npm run lint
	@echo "$(GREEN)✓ Frontend linting complete$(NC)"

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code with black
	@echo "$(BLUE)Formatting backend...$(NC)"
	cd backend && poetry run black app/ tests/
	cd backend && poetry run ruff check --fix app/ tests/
	@echo "$(GREEN)✓ Backend formatted$(NC)"

format-frontend: ## Format frontend code with prettier
	@echo "$(BLUE)Formatting frontend...$(NC)"
	cd frontend && npm run format
	@echo "$(GREEN)✓ Frontend formatted$(NC)"

type-check: ## Run type checking
	@echo "$(BLUE)Type checking...$(NC)"
	cd backend && poetry run mypy app/
	cd frontend && npm run type-check
	@echo "$(GREEN)✓ Type checking complete$(NC)"

##@ Database

migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	cd infra && docker compose exec backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add users table")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: Please provide MSG parameter$(NC)"; \
		echo "Usage: make migrate-create MSG=\"your migration message\""; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration: $(MSG)$(NC)"
	cd infra && docker compose exec backend alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✓ Migration created$(NC)"

migrate-down: ## Rollback last migration
	@echo "$(BLUE)Rolling back last migration...$(NC)"
	cd infra && docker compose exec backend alembic downgrade -1
	@echo "$(GREEN)✓ Rollback complete$(NC)"

migrate-history: ## Show migration history
	cd infra && docker compose exec backend alembic history

seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	cd infra && docker compose exec backend python scripts/seed_db.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

db-reset: ## Reset database (drop all tables and re-migrate)
	@echo "$(RED)⚠ This will delete all data. Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	@echo "$(BLUE)Resetting database...$(NC)"
	cd infra && docker compose exec db psql -U observatory -d observatory -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate
	$(MAKE) seed
	@echo "$(GREEN)✓ Database reset complete$(NC)"

##@ Monitoring & Health

status: ## Check status of all services
	@echo "$(BLUE)Checking service status...$(NC)"
	@echo ""
	@echo "$(YELLOW)Backend:$(NC)"
	@curl -s http://localhost:8000/health | jq '.' || echo "$(RED)✗ Backend not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend:$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 > /dev/null && echo "$(GREEN)✓ Frontend is up$(NC)" || echo "$(RED)✗ Frontend not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Redis:$(NC)"
	@cd infra && docker compose exec redis redis-cli ping > /dev/null && echo "$(GREEN)✓ Redis is up$(NC)" || echo "$(RED)✗ Redis not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Postgres:$(NC)"
	@cd infra && docker compose exec db pg_isready -U observatory > /dev/null && echo "$(GREEN)✓ Postgres is up$(NC)" || echo "$(RED)✗ Postgres not responding$(NC)"

health: ## Health check for API
	@curl -s http://localhost:8000/health | jq '.'

trends: ## Fetch trends for a country (usage: make trends COUNTRY=US)
	@if [ -z "$(COUNTRY)" ]; then \
		echo "Usage: make trends COUNTRY=US"; \
		exit 1; \
	fi
	@echo "$(BLUE)Fetching trends for $(COUNTRY)...$(NC)"
	@curl -s "http://localhost:8000/v1/trends/top?country=$(COUNTRY)&limit=10" | jq '.'

flows: ## Fetch information flows (usage: make flows WINDOW=24h)
	@WINDOW=$${WINDOW:-24h}; \
	echo "$(BLUE)Fetching flows for time window: $$WINDOW...$(NC)"; \
	curl -s "http://localhost:8000/v1/flows?time_window=$$WINDOW" | jq '.'

##@ Documentation

docs: ## Generate API documentation
	@echo "$(BLUE)Generating API docs...$(NC)"
	@echo "$(YELLOW)OpenAPI docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)ReDoc: http://localhost:8000/redoc$(NC)"

docs-adr: ## List all ADRs (Architecture Decision Records)
	@echo "$(BLUE)Architecture Decision Records:$(NC)"
	@ls -1 docs/decisions/*.md 2>/dev/null || echo "$(YELLOW)No ADRs found$(NC)"

##@ Cleanup

clean: ## Clean up temporary files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name node_modules -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-docker: ## Remove all Docker containers, volumes, and images
	@echo "$(RED)⚠ This will remove all containers, volumes, and images. Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	cd infra && docker compose down -v --rmi all
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

##@ Git Operations

git-status: ## Show git status and recent commits
	@echo "$(BLUE)Git Status:$(NC)"
	@git status
	@echo ""
	@echo "$(BLUE)Recent Commits:$(NC)"
	@git log --oneline -5

commit: ## Commit changes (usage: make commit MSG="feat: add flows API")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: Please provide MSG parameter$(NC)"; \
		echo "Usage: make commit MSG=\"feat: your commit message\""; \
		exit 1; \
	fi
	@echo "$(BLUE)Committing changes: $(MSG)$(NC)"
	@git add .
	@git commit -m "$(MSG)"
	@echo "$(GREEN)✓ Committed$(NC)"

push: ## Push to GitHub
	@echo "$(BLUE)Pushing to GitHub...$(NC)"
	@git push origin main
	@echo "$(GREEN)✓ Pushed to main$(NC)"

pull: ## Pull from GitHub
	@echo "$(BLUE)Pulling from GitHub...$(NC)"
	@git pull origin main
	@echo "$(GREEN)✓ Pulled from main$(NC)"

##@ Deployment

deploy-gcp: ## Deploy to Google Cloud Run
	@echo "$(BLUE)Deploying to Google Cloud Run...$(NC)"
	@echo "$(RED)Not implemented yet$(NC)"

build-prod: ## Build production images
	@echo "$(BLUE)Building production images...$(NC)"
	cd infra && docker compose -f docker-compose.prod.yml build
	@echo "$(GREEN)✓ Production images built$(NC)"

##@ Agents

agents-status: ## Show agent specs
	@echo "$(BLUE)Agent Specifications:$(NC)"
	@ls -1 .agents/*.md 2>/dev/null || echo "$(YELLOW)No agent specs found$(NC)"

daily-plan: ## Create daily plan document
	@DATE=$$(date +%Y-%m-%d); \
	echo "$(BLUE)Creating daily plan for $$DATE...$(NC)"; \
	touch "docs/state/daily-$$DATE.md"; \
	echo "# Daily Plan - $$DATE\n\n## Goals\n\n## Progress\n\n## Blockers\n" > "docs/state/daily-$$DATE.md"; \
	echo "$(GREEN)✓ Created docs/state/daily-$$DATE.md$(NC)"

snapshot: ## Create data snapshot for testing
	@DATE=$$(date +%Y-%m-%d); \
	echo "$(BLUE)Creating data snapshot for $$DATE...$(NC)"; \
	mkdir -p "data/snapshots/$$DATE"; \
	curl -s "http://localhost:8000/v1/flows?time_window=24h" > "data/snapshots/$$DATE/flows.json"; \
	echo "$(GREEN)✓ Snapshot saved to data/snapshots/$$DATE/$(NC)"

##@ Quick Actions

qa: lint test ## Run quick QA (lint + test)

ci: format lint test ## Run full CI pipeline locally

rebuild: clean down up ## Clean rebuild (remove cache and restart)

demo: ## Run demo scenario (fetch trends and flows)
	@echo "$(BLUE)Running demo scenario...$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Health Check:$(NC)"
	@$(MAKE) health
	@echo ""
	@echo "$(YELLOW)2. Trends for US:$(NC)"
	@$(MAKE) trends COUNTRY=US
	@echo ""
	@echo "$(YELLOW)3. Information Flows:$(NC)"
	@$(MAKE) flows WINDOW=24h
	@echo ""
	@echo "$(GREEN)✓ Demo complete$(NC)"
