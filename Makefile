.PHONY: help test test-cov lint format typecheck clean install install-dev

# Default target
help:
	@echo "Available targets:"
	@echo "  help        Show this help message"
	@echo "  install     Install the package"
	@echo "  install-dev Install in development mode with dev dependencies"
	@echo "  test        Run all tests"
	@echo "  test-cov    Run tests with coverage report"
	@echo "  lint        Run linting (ruff)"
	@echo "  format      Format code (black)"
	@echo "  typecheck   Run type checking (mypy)"
	@echo "  clean       Clean build artifacts and cache"
	@echo "  build       Build the package"
	@echo "  docs        Generate documentation"

# Installation
install:
	pip install .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=oca --cov-report=term-missing --cov-report=html

test-unit:
	python -m pytest tests/unit/ -v

test-integration:
	python -m pytest tests/integration/ -v

# Code quality (when tools are available)
lint:
	@echo "Checking code with basic linting..."
	python -m py_compile oca/*.py oca/*/*.py

format:
	@echo "Would format code with black (not installed)"
	@echo "Run: pip install black && black oca tests"

typecheck:
	@echo "Would run type checking with mypy (not installed)"
	@echo "Run: pip install mypy && mypy oca"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build
build:
	python -m build

# Development shortcuts
dev-setup: install-dev
	@echo "Development environment set up!"

ci: test-cov lint
	@echo "CI checks complete!"

# Demo commands
demo:
	@echo "=== OCA Demo ==="
	@echo "Showing all available commands:"
	oca --help
	@echo ""
	@echo "Testing commands in dry-run mode:"
	@echo "1. Initialize project:"
	oca --dry-run init
	@echo ""
	@echo "2. Explain code:"
	oca --dry-run explain "What does this code do?"
	@echo ""
	@echo "3. Fix issue:"
	oca --dry-run fix "Fix the TypeError"
	@echo ""
	@echo "Demo complete!"