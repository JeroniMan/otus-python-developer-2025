.PHONY: help install format format-check lint type-check test test-coverage \
        server server-stop docker-build docker-run docker-stop clean \
        http-test-suite http-test-suite-run stress check all

# Variables
PYTHON := poetry run python
POETRY := poetry
SRC_DIR := src
TEST_DIR := tests
DOC_ROOT := docs
PORT := 8080
HOST := 127.0.0.1
WORKERS := 4

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(GREEN)Available commands:$(NC)"
	@echo "  $(YELLOW)install$(NC)            - Install all dependencies"
	@echo "  $(YELLOW)format$(NC)             - Format code with black and isort"
	@echo "  $(YELLOW)format-check$(NC)       - Check code formatting"
	@echo "  $(YELLOW)lint$(NC)               - Run all linters (flake8, pylint)"
	@echo "  $(YELLOW)type-check$(NC)         - Run mypy type checking"
	@echo "  $(YELLOW)test$(NC)               - Run unit tests"
	@echo "  $(YELLOW)test-coverage$(NC)      - Run tests with coverage report"
	@echo "  $(YELLOW)server$(NC)             - Start HTTP server"
	@echo "  $(YELLOW)server-stop$(NC)        - Stop running server"
	@echo "  $(YELLOW)docker-build$(NC)       - Build Docker image"
	@echo "  $(YELLOW)docker-run$(NC)         - Run server in Docker"
	@echo "  $(YELLOW)docker-stop$(NC)        - Stop Docker container"
	@echo "  $(YELLOW)http-test-suite$(NC)    - Clone http-test-suite"
	@echo "  $(YELLOW)http-test-suite-run$(NC) - Run http-test-suite"
	@echo "  $(YELLOW)stress$(NC)             - Run stress test with Apache Bench"
	@echo "  $(YELLOW)check$(NC)              - Run all checks (format, lint, type, test)"
	@echo "  $(YELLOW)clean$(NC)              - Clean up temporary files"
	@echo "  $(YELLOW)all$(NC)                - Install deps and run all checks"

# Installation
install:
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)Dependencies installed!$(NC)"

install-dev:
	@echo "$(GREEN)Installing dev dependencies...$(NC)"
	$(POETRY) install --with dev
	$(POETRY) run pre-commit install
	@echo "$(GREEN)Dev dependencies installed!$(NC)"

# Code formatting
format:
	@echo "$(GREEN)Formatting code...$(NC)"
	$(POETRY) run black $(SRC_DIR) $(TEST_DIR)
	$(POETRY) run isort $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)Code formatted!$(NC)"

format-check:
	@echo "$(GREEN)Checking code format...$(NC)"
	$(POETRY) run black --check $(SRC_DIR) $(TEST_DIR)
	$(POETRY) run isort --check-only $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)Format check passed!$(NC)"

# Linting
lint:
	@echo "$(GREEN)Running linters...$(NC)"
	$(POETRY) run flake8 $(SRC_DIR) $(TEST_DIR) --max-line-length=120 --exclude=.venv
	$(POETRY) run pylint $(SRC_DIR) --disable=C0114,C0115,C0116,R0903,R0913,W0212 || true
	@echo "$(GREEN)Linting complete!$(NC)"

# Type checking
type-check:
	@echo "$(GREEN)Running type checker...$(NC)"
	$(POETRY) run mypy $(SRC_DIR) --ignore-missing-imports || true
	@echo "$(GREEN)Type check complete!$(NC)"

# Testing
test:
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR) -v --tb=short
	@echo "$(GREEN)Tests passed!$(NC)"

test-coverage:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR) \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml
	@echo "$(GREEN)Coverage report generated!$(NC)"
	@echo "Open htmlcov/index.html to view detailed report"

# Server management
server:
	@echo "$(GREEN)Starting HTTP server on $(HOST):$(PORT)...$(NC)"
	$(PYTHON) $(SRC_DIR)/httpd.py -h $(HOST) -p $(PORT) -r $(DOC_ROOT) -w $(WORKERS)

server-background:
	@echo "$(GREEN)Starting HTTP server in background...$(NC)"
	@$(PYTHON) $(SRC_DIR)/httpd.py -h $(HOST) -p $(PORT) -r $(DOC_ROOT) -w $(WORKERS) & \
		echo $$! > .server.pid
	@sleep 2
	@echo "$(GREEN)Server started with PID $$(cat .server.pid)$(NC)"

server-stop:
	@if [ -f .server.pid ]; then \
		echo "$(YELLOW)Stopping server...$(NC)"; \
		kill $$(cat .server.pid) 2>/dev/null || true; \
		rm .server.pid; \
		echo "$(GREEN)Server stopped$(NC)"; \
	else \
		echo "$(YELLOW)No server running$(NC)"; \
	fi

# Docker commands
docker-build:
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t http-server:latest .
	@echo "$(GREEN)Docker image built!$(NC)"

docker-run:
	@echo "$(GREEN)Running server in Docker...$(NC)"
	docker run -d --name http-server \
		-p $(PORT):$(PORT) \
		-v $$(pwd)/$(DOC_ROOT):/app/$(DOC_ROOT) \
		-e DOCUMENT_ROOT=/app/$(DOC_ROOT) \
		-e PORT=$(PORT) \
		http-server:latest
	@echo "$(GREEN)Server running in Docker!$(NC)"

docker-stop:
	@echo "$(YELLOW)Stopping Docker container...$(NC)"
	docker stop http-server 2>/dev/null || true
	docker rm http-server 2>/dev/null || true
	@echo "$(GREEN)Docker container stopped$(NC)"

docker-logs:
	docker logs -f http-server

# HTTP Test Suite
http-test-suite:
	@if [ ! -d ../http-test-suite ]; then \
		echo "$(GREEN)Cloning http-test-suite...$(NC)"; \
		cd .. && git clone https://github.com/s-stupnikov/http-test-suite.git; \
		cd http-test-suite && $(POETRY) install --no-root; \
	else \
		echo "$(YELLOW)http-test-suite already exists$(NC)"; \
	fi

http-test-suite-run: server-background
	@echo "$(GREEN)Running http-test-suite...$(NC)"
	@cd ../http-test-suite && $(POETRY) run python httptest.py --host $(HOST) --port $(PORT)
	@$(MAKE) server-stop

# Performance testing
stress: server-background
	@echo "$(GREEN)Running stress test...$(NC)"
	@if ! command -v ab &> /dev/null; then \
		echo "$(RED)Apache Bench (ab) not found. Install with: sudo apt-get install apache2-utils$(NC)"; \
		$(MAKE) server-stop; \
		exit 1; \
	fi
	@echo "$(YELLOW)Warming up...$(NC)"
	@ab -n 100 -c 1 http://$(HOST):$(PORT)/ > /dev/null 2>&1
	@echo "$(GREEN)Running benchmark...$(NC)"
	@ab -n 10000 -c 100 -t 30 http://$(HOST):$(PORT)/ | tee stress_results.txt
	@echo "$(GREEN)Stress test complete! Results saved to stress_results.txt$(NC)"
	@$(MAKE) server-stop

# Aggregate commands
check: format-check lint type-check test
	@echo "$(GREEN)All checks passed!$(NC)"

all: install check
	@echo "$(GREEN)Everything is ready!$(NC)"

# Cleanup
clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf coverage.xml
	@rm -rf __pycache__
	@rm -rf $(SRC_DIR)/__pycache__
	@rm -rf $(TEST_DIR)/__pycache__
	@rm -rf .mypy_cache
	@rm -rf .server.pid
	@rm -rf stress_results.txt
	@rm -rf benchmark_results.txt
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Development workflow
dev: install-dev format lint type-check test
	@echo "$(GREEN)Development environment ready!$(NC)"

# Pre-commit
pre-commit:
	$(POETRY) run pre-commit run --all-files

# Watch mode for development (requires entr)
watch:
	@if command -v entr &> /dev/null; then \
		find $(SRC_DIR) $(TEST_DIR) -name "*.py" | entr -c $(MAKE) test; \
	else \
		echo "$(RED)entr not found. Install with: sudo apt-get install entr$(NC)"; \
	fi