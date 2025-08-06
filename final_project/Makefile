.PHONY: help build up down logs restart test lint format clean

# Default
.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Docker commands
build: ## Build all containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs (all services)
	docker-compose logs -f

ps: ## Show container status
	docker-compose ps

restart: down up ## Restart all services

# Service management
restart-collector: ## Restart collector
	docker-compose restart collector

restart-parser: ## Restart parser
	docker-compose restart parser

restart-validator: ## Restart validator
	docker-compose restart validator

restart-metrics: ## Restart metrics
	docker-compose restart metrics

# Development
install: ## Install dependencies
	uv sync --all-extras

test: ## Run tests
	uv run pytest tests/ -v

lint: ## Run linters
	uv run flake8 indexer/
	uv run mypy indexer/ --ignore-missing-imports

format: ## Format code
	uv run black indexer/ tests/
	uv run isort indexer/ tests/

# Local run
run-collector: ## Run collector locally
	uv run python indexer/collector.py

run-parser: ## Run parser locally
	uv run python indexer/parser.py

run-validator: ## Run validator locally
	uv run python indexer/validator.py

run-metrics: ## Run metrics locally
	uv run python indexer/metrics.py

# Cleanup
clean: ## Clean cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +