.PHONY: help setup test lint format clean dev install-common

help:
	@echo "RGrid Monorepo - Available targets:"
	@echo ""
	@echo "  setup          - Install all dependencies and set up development environment"
	@echo "  install-common - Install shared common package in editable mode"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linters (ruff, mypy)"
	@echo "  format         - Format code with black and ruff"
	@echo "  clean          - Remove build artifacts and cache files"
	@echo "  dev            - Start local development environment"
	@echo ""

setup: install-common
	@echo "Installing API dependencies..."
	cd api && pip install -e .
	@echo "Installing CLI dependencies..."
	cd cli && pip install -e .
	@echo "Installing orchestrator dependencies..."
	cd orchestrator && pip install -e .
	@echo "Installing runner dependencies..."
	cd runner && pip install -e .
	@echo "Installing dev dependencies..."
	pip install pytest pytest-asyncio pytest-cov black ruff mypy pre-commit
	@echo "Setting up pre-commit hooks..."
	pre-commit install
	@echo "Setup complete!"

install-common:
	@echo "Installing common package..."
	cd common && pip install -e .

test:
	@echo "Running tests..."
	pytest tests/ -v --cov=api --cov=cli --cov=orchestrator --cov=runner --cov=common

lint:
	@echo "Running ruff..."
	ruff check api/ cli/ orchestrator/ runner/ common/
	@echo "Running mypy..."
	mypy api/ cli/ orchestrator/ runner/ common/

format:
	@echo "Formatting with black..."
	black api/ cli/ orchestrator/ runner/ common/ tests/
	@echo "Sorting imports with ruff..."
	ruff check --select I --fix api/ cli/ orchestrator/ runner/ common/ tests/

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	@echo "Clean complete!"

dev:
	@echo "Starting local development environment..."
	docker-compose -f infra/docker-compose.yml up
