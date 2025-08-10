.PHONY: install format lint test test-unit test-integration test-coverage run run-redis clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  install           - Install dependencies"
	@echo "  format            - Format code with black and isort"
	@echo "  lint              - Run linters"
	@echo "  test              - Run all tests"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests (requires Redis)"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  run               - Run API server"
	@echo "  run-redis         - Run Redis in Docker"
	@echo "  clean             - Clean cache files"

# Install dependencies
install:
	uv sync --all-extras

# Format code
format:
	uv run black .
	uv run isort .

# Run linters
lint:
	uv run black --check .
	uv run flake8 . --exclude=test*.py,.venv/*
	uv run mypy . --ignore-missing-imports
	uv run isort --check-only .

# Run all tests
test:
	uv run python -m pytest test.py -v

# Run unit tests only
test-unit:
	uv run python -m pytest test.py -v -m "not integration"

# Run integration tests (requires Redis)
test-integration:
	uv run python -m pytest test_integration.py -v -m integration

# Run tests with coverage
test-coverage:
	uv run pytest test.py --cov=. --cov-report=term-missing --cov-report=html

# Run server
run:
	uv run python api.py

# Run server with logging
run-log:
	uv run python api.py -l api.log

# Run Redis in Docker for testing
run-redis:
	docker run -d --name redis-test -p 6379:6379 redis:7-alpine || docker start redis-test

# Stop Redis container
stop-redis:
	docker stop redis-test || true

# Clean cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -f api.log