# TickStock Development Commands
# Provides convenient commands for development, testing, and deployment

.PHONY: help test test-unit test-integration test-performance test-all test-quick test-coverage
.PHONY: lint format clean install dev-install requirements
.PHONY: run-dev run-prod setup-dev setup-db
.PHONY: docker-build docker-run docker-stop

# Default target
help:
	@echo "TickStock Development Commands"
	@echo "============================="
	@echo ""
	@echo "Testing:"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-all         Run all tests with coverage"
	@echo "  test-quick       Run fast tests only (no slow/api/db)"
	@echo "  test-coverage    Generate detailed coverage report"
	@echo "  test-smoke       Run smoke tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run linting (ruff)"
	@echo "  format          Format code (black)"
	@echo "  type-check      Run type checking (mypy)"
	@echo "  quality         Run all quality checks"
	@echo ""
	@echo "Development:"
	@echo "  install         Install production dependencies"
	@echo "  dev-install     Install development dependencies"
	@echo "  requirements    Update requirements files"
	@echo "  clean           Clean temporary files"
	@echo ""
	@echo "Application:"
	@echo "  run-dev         Run development server"
	@echo "  run-prod        Run production server"
	@echo "  setup-dev       Set up development environment"
	@echo "  setup-db        Set up database"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build    Build Docker image"
	@echo "  docker-run      Run in Docker container"
	@echo "  docker-stop     Stop Docker containers"

# Testing targets
test-unit:
	@echo "🧪 Running unit tests..."
	python -m pytest tests/unit/ -v --cov=src --cov-report=term-missing -m unit

test-integration:
	@echo "🔗 Running integration tests..."
	python -m pytest tests/integration/ -v -m integration

test-performance:
	@echo "⚡ Running performance tests..."
	python -m pytest tests/ -v -m performance

test-all:
	@echo "🚀 Running all tests with coverage..."
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=70

test-quick:
	@echo "⚡ Running quick tests..."
	python -m pytest tests/ -v -m "not slow and not api and not database" -x --tb=short

test-coverage:
	@echo "📊 Generating coverage report..."
	python -m pytest tests/unit/ --cov=src --cov-report=html:htmlcov --cov-report=term-missing --cov-fail-under=70
	@echo "Coverage report generated in htmlcov/index.html"

test-smoke:
	@echo "💨 Running smoke tests..."
	python -m pytest tests/ -v -m smoke --tb=short

# Code quality targets
lint:
	@echo "🔍 Running linting..."
	ruff check src/ tests/ scripts/
	@echo "✅ Linting complete"

format:
	@echo "🎨 Formatting code..."
	black src/ tests/ scripts/
	@echo "✅ Formatting complete"

type-check:
	@echo "🔍 Running type checks..."
	mypy src/ --ignore-missing-imports
	@echo "✅ Type checking complete"

quality: lint type-check
	@echo "✅ All quality checks passed"

# Dependency management
install:
	@echo "📦 Installing production dependencies..."
	pip install -r requirements/prod.txt

dev-install:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements/dev.txt
	pip install -e .

requirements:
	@echo "📝 Updating requirements..."
	pip-compile requirements/base.in
	pip-compile requirements/dev.in
	pip-compile requirements/prod.in

# Development setup
setup-dev: dev-install
	@echo "🛠️  Setting up development environment..."
	pre-commit install
	@echo "✅ Development environment ready"

setup-db:
	@echo "🗄️  Setting up database..."
	python scripts/setup_database.py
	@echo "✅ Database setup complete"

# Application running
run-dev:
	@echo "🚀 Starting development server..."
	python src/app.py --env=dev

run-prod:
	@echo "🚀 Starting production server..."
	python src/app.py --env=prod

# Docker targets
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t tickstock:latest -f docker/Dockerfile .

docker-run:
	@echo "🐳 Running Docker container..."
	docker-compose -f docker/docker-compose.yml up -d

docker-stop:
	@echo "🐳 Stopping Docker containers..."
	docker-compose -f docker/docker-compose.yml down

# Cleanup
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/
	@echo "✅ Cleanup complete"

# Git hooks
pre-commit:
	@echo "🔍 Running pre-commit checks..."
	python -m pytest tests/unit/ -x --tb=short -q
	ruff check src/ tests/
	@echo "✅ Pre-commit checks passed"

# CI/CD simulation
ci-test:
	@echo "🤖 Running CI test pipeline..."
	make lint
	make type-check
	make test-unit
	make test-integration
	@echo "✅ CI pipeline completed successfully"

# Development utilities
watch-tests:
	@echo "👀 Watching for changes and running tests..."
	ptw tests/ src/ -- -v --tb=short

profile-tests:
	@echo "📊 Profiling test performance..."
	python -m pytest tests/unit/ --durations=10

# Database utilities
migrate:
	@echo "📊 Running database migrations..."
	python -m flask db upgrade

migrate-create:
	@echo "📊 Creating new migration..."
	python -m flask db migrate -m "$(message)"

# Monitoring
logs:
	@echo "📋 Showing application logs..."
	tail -f logs/*.log

health-check:
	@echo "🏥 Running health check..."
	python scripts/health_check.py