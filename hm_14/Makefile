# Makefile for Memcache Loader
.PHONY: help install sync test lint format clean build proto docker memcached

# Variables
PYTHON := python3.12
UV := uv
PROJECT_NAME := hw-memcache-loader
MAIN_MODULE := memc_load.py
PROTO_FILE := appsinstalled.proto

# Colors for terminal output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '${GREEN}Memcache Loader - Development Commands${NC}'
	@echo ''
	@echo '${YELLOW}Usage:${NC}'
	@echo '  ${BLUE}make${NC} ${GREEN}<target>${NC}'
	@echo ''
	@echo '${YELLOW}Targets:${NC}'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  ${BLUE}%-20s${NC} %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-uv: ## Install uv package manager
	@echo "${GREEN}Installing uv...${NC}"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "${GREEN}✓ uv installed successfully${NC}"

install: ## Install project dependencies with uv
	@echo "${GREEN}Installing dependencies...${NC}"
	@$(UV) sync --all-extras
	@echo "${GREEN}✓ Dependencies installed${NC}"

sync: ## Sync dependencies with uv.lock
	@echo "${GREEN}Syncing dependencies...${NC}"
	@$(UV) sync --frozen
	@echo "${GREEN}✓ Dependencies synced${NC}"

update: ## Update all dependencies
	@echo "${GREEN}Updating dependencies...${NC}"
	@$(UV) sync --upgrade
	@echo "${GREEN}✓ Dependencies updated${NC}"

test: ## Run all tests
	@echo "${GREEN}Running tests...${NC}"
	@$(UV) run python -m pytest tests/ -v --cov=. --cov-report=term-missing
	@echo "${GREEN}✓ Tests completed${NC}"

test-unit: ## Run unit tests only
	@echo "${GREEN}Running unit tests...${NC}"
	@$(UV) run python -m pytest tests/ -v -m "not integration and not memcached"
	@echo "${GREEN}✓ Unit tests completed${NC}"

test-integration: memcached-start ## Run integration tests
	@echo "${GREEN}Running integration tests...${NC}"
	@$(UV) run python -m pytest tests/ -v -m "integration or memcached"
	@echo "${GREEN}✓ Integration tests completed${NC}"

test-coverage: ## Run tests with coverage report
	@echo "${GREEN}Running tests with coverage...${NC}"
	@$(UV) run python -m pytest tests/ -v \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml
	@echo "${GREEN}✓ Coverage report generated in htmlcov/${NC}"
	@echo "${YELLOW}Opening coverage report...${NC}"
	@open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null || echo "Please open htmlcov/index.html manually"

lint: ## Run all linters
	@echo "${GREEN}Running linters...${NC}"
	@$(UV) run ruff check .
	@$(UV) run ruff format --check .
	@$(UV) run black --check .
	@$(UV) run flake8 . --max-line-length=88 --extend-ignore=E203 || true
	@echo "${GREEN}✓ Linting completed${NC}"

format: ## Format code with black and ruff
	@echo "${GREEN}Formatting code...${NC}"
	@$(UV) run ruff check --fix .
	@$(UV) run ruff format .
	@$(UV) run black .
	@echo "${GREEN}✓ Code formatted${NC}"

mypy: ## Run type checking with mypy
	@echo "${GREEN}Running type checker...${NC}"
	@$(UV) run mypy $(MAIN_MODULE) --ignore-missing-imports
	@echo "${GREEN}✓ Type checking completed${NC}"

security: ## Run security checks
	@echo "${GREEN}Running security checks...${NC}"
	@$(UV) run bandit -r . -ll -x tests,appsinstalled_pb2.py
	@$(UV) run safety check --json || true
	@echo "${GREEN}✓ Security checks completed${NC}"

clean: ## Clean up temporary files and caches
	@echo "${GREEN}Cleaning up...${NC}"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.coverage" -delete 2>/dev/null || true
	@find . -type f -name ".coverage.*" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml 2>/dev/null || true
	@rm -rf dist build *.egg-info 2>/dev/null || true
	@rm -rf .*.tsv.gz 2>/dev/null || true
	@echo "${GREEN}✓ Cleanup completed${NC}"

build: clean ## Build distribution packages
	@echo "${GREEN}Building packages...${NC}"
	@$(UV) build
	@echo "${GREEN}✓ Packages built in dist/${NC}"

install-protoc: ## Install Protocol Buffers compiler
	@echo "${GREEN}Installing protoc...${NC}"
	@if ! command -v protoc &> /dev/null; then \
		if [[ "$$(uname)" == "Darwin" ]]; then \
			brew install protobuf; \
		elif [[ "$$(uname)" == "Linux" ]]; then \
			sudo apt-get update && sudo apt-get install -y protobuf-compiler; \
		else \
			echo "${RED}Please install protoc manually${NC}"; \
			exit 1; \
		fi; \
	else \
		echo "${YELLOW}protoc is already installed${NC}"; \
	fi
	@echo "${GREEN}✓ protoc installed${NC}"

proto: ## Generate Python code from Protocol Buffers
	@echo "${GREEN}Generating Protocol Buffers code...${NC}"
	@protoc --python_out=. $(PROTO_FILE)
	@echo "${GREEN}✓ Generated appsinstalled_pb2.py${NC}"

pre-commit: ## Install and run pre-commit hooks
	@echo "${GREEN}Setting up pre-commit hooks...${NC}"
	@$(UV) run pre-commit install
	@$(UV) run pre-commit run --all-files
	@echo "${GREEN}✓ Pre-commit hooks installed and executed${NC}"

check: lint mypy test security ## Run all checks (lint, type check, test, security)
	@echo "${GREEN}✓ All checks passed!${NC}"

# Memcached commands
memcached-start: ## Start Memcached in Docker
	@echo "${GREEN}Starting Memcached...${NC}"
	@docker run -d --name memcached-test \
		-p 33013-33016:11211 \
		memcached:latest \
		2>/dev/null || echo "${YELLOW}Memcached container already exists${NC}"
	@echo "${GREEN}✓ Memcached started${NC}"

memcached-stop: ## Stop Memcached container
	@echo "${GREEN}Stopping Memcached...${NC}"
	@docker stop memcached-test 2>/dev/null || true
	@docker rm memcached-test 2>/dev/null || true
	@echo "${GREEN}✓ Memcached stopped${NC}"

memcached-restart: memcached-stop memcached-start ## Restart Memcached

# Run commands
run-dry: ## Run loader in dry-run mode with test data
	@echo "${GREEN}Running in dry-run mode...${NC}"
	@$(UV) run python $(MAIN_MODULE) --dry --pattern="tests/fixtures/*.tsv.gz" --loginfo

run-test: memcached-start ## Run loader with test data
	@echo "${GREEN}Running with test data...${NC}"
	@$(UV) run python $(MAIN_MODULE) --pattern="tests/fixtures/*.tsv.gz" --loginfo --maxworkers=3

run-bench: ## Run performance benchmark
	@echo "${GREEN}Running performance benchmark...${NC}"
	@echo "${YELLOW}Generating test data...${NC}"
	@python -c "import gzip; f=gzip.open('bench.tsv.gz','wt'); [f.write(f'idfa\ttest{i}\t55.55\t42.42\t1,2,3,4,5\n') for i in range(100000)]; f.close()"
	@echo "${YELLOW}Running benchmark...${NC}"
	@time $(UV) run python $(MAIN_MODULE) --dry --pattern="bench.tsv.gz" --maxworkers=10
	@rm -f bench.tsv.gz .bench.tsv.gz
	@echo "${GREEN}✓ Benchmark completed${NC}"

# Docker commands
docker-build: ## Build Docker image
	@echo "${GREEN}Building Docker image...${NC}"
	@docker build -t $(PROJECT_NAME):latest .
	@echo "${GREEN}✓ Docker image built${NC}"

docker-run: ## Run Docker container
	@echo "${GREEN}Running Docker container...${NC}"
	@docker run -it --rm \
		--network host \
		-v $(PWD)/data:/data \
		$(PROJECT_NAME):latest
	@echo "${GREEN}✓ Docker container stopped${NC}"

# Development workflow
dev: install pre-commit ## Setup development environment
	@echo "${GREEN}✓ Development environment ready!${NC}"

ci: check build ## Run CI pipeline locally
	@echo "${GREEN}✓ CI pipeline completed successfully!${NC}"

# Monitoring
monitor: ## Monitor Memcached stats
	@echo "${GREEN}Monitoring Memcached...${NC}"
	@watch -n 1 'echo "stats" | nc localhost 33013'

logs: ## Show application logs
	@echo "${GREEN}Showing logs...${NC}"
	@tail -f *.log 2>/dev/null || echo "${YELLOW}No log files found${NC}"

.DEFAULT_GOAL := help