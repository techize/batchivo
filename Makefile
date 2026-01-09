# Nozzly - Development Makefile

.PHONY: help
help: ## Show this help message
	@echo "Nozzly - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

## Development

.PHONY: dev
dev: ## Start full development stack
	@echo "Starting Docker Compose stack..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	sleep 5
	@echo ""
	@echo "✓ Infrastructure started"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Backend:  cd backend && poetry run uvicorn app.main:app --reload"
	@echo "  2. Frontend: cd frontend && pnpm dev"
	@echo ""
	@echo "Access:"
	@echo "  Frontend:   http://localhost:5173"
	@echo "  Backend:    http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo "  Authentik:  http://localhost:9000"
	@echo "  Grafana:    http://localhost:3000"

.PHONY: dev-backend
dev-backend: ## Start backend development server
	cd backend && poetry run uvicorn app.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Start frontend development server
	cd frontend && pnpm dev

.PHONY: dev-worker
dev-worker: ## Start Celery worker for background jobs
	cd backend && poetry run celery -A app.background.celery_app worker --loglevel=info

.PHONY: stop
stop: ## Stop all Docker Compose services
	docker-compose stop

.PHONY: down
down: ## Stop and remove Docker Compose services
	docker-compose down

.PHONY: clean
clean: ## Stop services and remove volumes (fresh start)
	docker-compose down -v
	@echo "✓ All services stopped and volumes removed"

.PHONY: logs
logs: ## View logs from all Docker services
	docker-compose logs -f

.PHONY: logs-backend
logs-backend: ## View backend logs only
	docker-compose logs -f backend

.PHONY: logs-postgres
logs-postgres: ## View PostgreSQL logs
	docker-compose logs -f postgres

## Setup

.PHONY: install
install: install-backend install-frontend ## Install all dependencies

.PHONY: install-backend
install-backend: ## Install backend dependencies
	cd backend && poetry install

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies
	cd frontend && pnpm install

.PHONY: setup
setup: install migrate seed ## Complete project setup (install, migrate, seed)
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Run 'make dev' to start development environment"

## Database

.PHONY: migrate
migrate: ## Run database migrations
	cd backend && poetry run alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Rollback last migration
	cd backend && poetry run alembic downgrade -1

.PHONY: migrate-create
migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required"; \
		echo "Usage: make migrate-create MESSAGE='Add spools table'"; \
		exit 1; \
	fi
	cd backend && poetry run alembic revision --autogenerate -m "$(MESSAGE)"

.PHONY: seed
seed: ## Seed database with reference data
	cd backend && poetry run python scripts/seed_data.py

.PHONY: db-shell
db-shell: ## Connect to PostgreSQL shell
	docker-compose exec postgres psql -U nozzly -d nozzly

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  WARNING: This will destroy all data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	docker-compose down -v
	docker-compose up -d postgres redis
	sleep 3
	$(MAKE) migrate seed
	@echo "✓ Database reset complete"

## Testing

.PHONY: test
test: test-backend test-frontend ## Run all tests

.PHONY: test-backend
test-backend: ## Run backend tests
	cd backend && poetry run pytest

.PHONY: test-frontend
test-frontend: ## Run frontend tests
	cd frontend && pnpm test

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	cd backend && poetry run pytest --cov=app --cov-report=html
	cd frontend && pnpm test:coverage
	@echo ""
	@echo "Coverage reports:"
	@echo "  Backend:  backend/htmlcov/index.html"
	@echo "  Frontend: frontend/coverage/index.html"

.PHONY: test-watch
test-watch: ## Run frontend tests in watch mode
	cd frontend && pnpm test:watch

## Code Quality

.PHONY: lint
lint: lint-backend lint-frontend ## Run all linters

.PHONY: lint-backend
lint-backend: ## Run backend linters
	cd backend && poetry run ruff check .
	cd backend && poetry run mypy .

.PHONY: lint-frontend
lint-frontend: ## Run frontend linters
	cd frontend && pnpm lint

.PHONY: format
format: format-backend format-frontend ## Format all code

.PHONY: format-backend
format-backend: ## Format backend code
	cd backend && poetry run black .
	cd backend && poetry run ruff check --fix .

.PHONY: format-frontend
format-frontend: ## Format frontend code
	cd frontend && pnpm format

.PHONY: check
check: lint test ## Run linters and tests (pre-commit check)
	@echo "✓ All checks passed!"

## Build

.PHONY: build
build: build-backend build-frontend ## Build Docker images

.PHONY: build-backend
build-backend: ## Build backend Docker image
	docker build -t nozzly-backend:latest ./backend

.PHONY: build-frontend
build-frontend: ## Build frontend Docker image
	docker build -t nozzly-frontend:latest ./frontend

## Deployment (k3s)

.PHONY: deploy-dev
deploy-dev: ## Deploy to k3s (dev namespace)
	kubectl apply -f infrastructure/k8s/namespace.yaml
	kubectl apply -f infrastructure/k8s/ -n nozzly-dev

.PHONY: deploy-prod
deploy-prod: ## Deploy to k3s (production namespace)
	@echo "⚠️  Deploying to PRODUCTION"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	kubectl apply -f infrastructure/k8s/namespace.yaml
	kubectl apply -f infrastructure/k8s/ -n nozzly

.PHONY: k8s-status
k8s-status: ## Check k8s deployment status
	kubectl get pods -n nozzly
	kubectl get services -n nozzly

.PHONY: k8s-logs
k8s-logs: ## View k8s backend logs
	kubectl logs -f -l app=nozzly-backend -n nozzly

## Documentation

.PHONY: docs
docs: ## Open documentation in browser
	@echo "Opening documentation..."
	@which open > /dev/null && open README.md || xdg-open README.md || echo "Please open README.md manually"

.PHONY: api-docs
api-docs: ## Open API documentation in browser
	@echo "Starting backend server (if not running)..."
	@echo "Opening API docs at http://localhost:8000/docs"
	@which open > /dev/null && open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

## Utilities

.PHONY: ps
ps: ## Show running Docker containers
	docker-compose ps

.PHONY: shell-backend
shell-backend: ## Open Python shell in backend environment
	cd backend && poetry run python

.PHONY: shell-redis
shell-redis: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

.PHONY: upgrade-deps
upgrade-deps: ## Upgrade all dependencies
	cd backend && poetry update
	cd frontend && pnpm update

.PHONY: security-check
security-check: ## Run security checks
	cd backend && poetry run pip-audit
	cd frontend && pnpm audit

.PHONY: grafana
grafana: ## Open Grafana in browser
	@which open > /dev/null && open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Open http://localhost:3000 in your browser"

.PHONY: prometheus
prometheus: ## Open Prometheus in browser
	@which open > /dev/null && open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Open http://localhost:9090 in your browser"

.PHONY: authentik
authentik: ## Open Authentik in browser
	@which open > /dev/null && open http://localhost:9000 || xdg-open http://localhost:9000 || echo "Open http://localhost:9000 in your browser"

## Observability

.PHONY: traces
traces: ## View traces in Grafana
	@echo "Opening Grafana Explore (Tempo)..."
	@which open > /dev/null && open "http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22tempo%22%7D" || echo "Open http://localhost:3000/explore in your browser and select Tempo"

.PHONY: metrics
metrics: ## View metrics in Grafana
	@echo "Opening Grafana Explore (Prometheus)..."
	@which open > /dev/null && open "http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22prometheus%22%7D" || echo "Open http://localhost:3000/explore in your browser and select Prometheus"

## Git Helpers

.PHONY: git-setup
git-setup: ## Configure git hooks and settings
	@echo "Configuring git hooks..."
	@echo "Pre-commit hook: make check" > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ Git hooks configured"

## Default target
.DEFAULT_GOAL := help
