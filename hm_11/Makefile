# Makefile
.PHONY: help install sync test lint format clean build docs

# Variables
PYTHON := python3.12
UV := uv
PROJECT_NAME := homework-11
SOURCE_DIR := dmia
TEST_DIR := tests

# Colors for terminal output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '${GREEN}Usage:${NC}'
	@echo '  ${YELLOW}make${NC} ${GREEN}<target>${NC}'
	@echo ''
	@echo '${GREEN}Targets:${NC}'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${YELLOW}%-15s${NC} %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-uv: ## Install uv package manager
	@echo "${GREEN}Installing uv...${NC}"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "${GREEN}✓ uv installed successfully${NC}"

install: ## Install project with all dependencies using uv
	@echo "${GREEN}Installing dependencies...${NC}"
	@$(UV) sync --all-extras
	@echo "${GREEN}✓ Dependencies installed${NC}"

sync: ## Sync dependencies with uv.lock
	@echo "${GREEN}Syncing dependencies...${NC}"
	@$(UV) sync --frozen
	@echo "${GREEN}✓ Dependencies synced${NC}"

update: ## Update dependencies
	@echo "${GREEN}Updating dependencies...${NC}"
	@$(UV) sync --upgrade
	@echo "${GREEN}✓ Dependencies updated${NC}"

test: ## Run tests with pytest
	@echo "${GREEN}Running tests...${NC}"
	@$(UV) run pytest $(TEST_DIR) -v --cov=$(SOURCE_DIR) --cov-report=term-missing
	@echo "${GREEN}✓ Tests completed${NC}"

test-coverage: ## Run tests with coverage report
	@echo "${GREEN}Running tests with coverage...${NC}"
	@$(UV) run pytest $(TEST_DIR) -v \
		--cov=$(SOURCE_DIR) \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml
	@echo "${GREEN}✓ Coverage report generated in htmlcov/${NC}"

lint: ## Run linting with ruff
	@echo "${GREEN}Running linters...${NC}"
	@$(UV) run ruff check $(SOURCE_DIR) $(TEST_DIR)
	@$(UV) run ruff format --check $(SOURCE_DIR) $(TEST_DIR)
	@echo "${GREEN}✓ Linting completed${NC}"

format: ## Format code with black and ruff
	@echo "${GREEN}Formatting code...${NC}"
	@$(UV) run ruff check --fix $(SOURCE_DIR) $(TEST_DIR)
	@$(UV) run ruff format $(SOURCE_DIR) $(TEST_DIR)
	@$(UV) run black $(SOURCE_DIR) $(TEST_DIR)
	@echo "${GREEN}✓ Code formatted${NC}"

mypy: ## Run type checking with mypy
	@echo "${GREEN}Running type checker...${NC}"
	@$(UV) run mypy $(SOURCE_DIR) --ignore-missing-imports
	@echo "${GREEN}✓ Type checking completed${NC}"

security: ## Run security checks with bandit and safety
	@echo "${GREEN}Running security checks...${NC}"
	@$(UV) run bandit -r $(SOURCE_DIR) -ll
	@$(UV) run safety check --json || true
	@echo "${GREEN}✓ Security checks completed${NC}"

clean: ## Clean up temporary files and caches
	@echo "${GREEN}Cleaning up...${NC}"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.coverage" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml 2>/dev/null || true
	@rm -rf dist build *.egg-info 2>/dev/null || true
	@echo "${GREEN}✓ Cleanup completed${NC}"

build: clean ## Build distribution packages
	@echo "${GREEN}Building packages...${NC}"
	@$(UV) build
	@echo "${GREEN}✓ Packages built in dist/${NC}"

docs: ## Build documentation
	@echo "${GREEN}Building documentation...${NC}"
	@$(UV) run mkdocs build
	@echo "${GREEN}✓ Documentation built in site/${NC}"

docs-serve: ## Serve documentation locally
	@echo "${GREEN}Serving documentation...${NC}"
	@$(UV) run mkdocs serve

notebook: ## Start Jupyter Lab
	@echo "${GREEN}Starting Jupyter Lab...${NC}"
	@$(UV) run jupyter lab

pre-commit: ## Install and run pre-commit hooks
	@echo "${GREEN}Setting up pre-commit hooks...${NC}"
	@$(UV) run pre-commit install
	@$(UV) run pre-commit run --all-files
	@echo "${GREEN}✓ Pre-commit hooks installed and executed${NC}"

check: lint mypy test security ## Run all checks (lint, type check, test, security)
	@echo "${GREEN}✓ All checks passed!${NC}"

dev: install pre-commit ## Setup development environment
	@echo "${GREEN}✓ Development environment ready!${NC}"

ci: check build ## Run CI pipeline locally
	@echo "${GREEN}✓ CI pipeline completed successfully!${NC}"

# Docker targets (optional)
docker-build: ## Build Docker image
	@echo "${GREEN}Building Docker image...${NC}"
	@docker build -t $(PROJECT_NAME):latest .
	@echo "${GREEN}✓ Docker image built${NC}"

docker-run: ## Run Docker container
	@echo "${GREEN}Running Docker container...${NC}"
	@docker run -it --rm -v $(PWD):/app $(PROJECT_NAME):latest
	@echo "${GREEN}✓ Docker container stopped${NC}"

.DEFAULT_GOAL := help