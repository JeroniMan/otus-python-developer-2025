# Makefile for Django Polls Application

.PHONY: help install run test lint format clean migrate shell docker-build docker-run

# Variables
PYTHON := python
MANAGE := $(PYTHON) mysite/manage.py
PROJECT_DIR := mysite
APP_NAME := polls

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Django Polls Application - Available Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies using Poetry
	@echo "$(GREEN)Installing dependencies...$(NC)"
	poetry install
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

install-pip: ## Install dependencies using pip
	@echo "$(GREEN)Installing dependencies with pip...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

migrate: ## Run database migrations
	@echo "$(GREEN)Running migrations...$(NC)"
	$(MANAGE) makemigrations
	$(MANAGE) migrate
	@echo "$(GREEN)Migrations completed!$(NC)"

run: ## Run development server
	@echo "$(GREEN)Starting Django development server...$(NC)"
	$(MANAGE) runserver

runplus: ## Run development server with Django Extensions
	@echo "$(GREEN)Starting Django development server with extensions...$(NC)"
	$(MANAGE) runserver_plus

test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	cd $(PROJECT_DIR) && $(PYTHON) manage.py test polls -v 2

test-coverage: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	cd $(PROJECT_DIR) && coverage run --source='.' manage.py test polls
	cd $(PROJECT_DIR) && coverage report
	cd $(PROJECT_DIR) && coverage html
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

pytest: ## Run tests with pytest
	@echo "$(GREEN)Running tests with pytest...$(NC)"
	pytest $(PROJECT_DIR) -v

pytest-coverage: ## Run pytest with coverage
	@echo "$(GREEN)Running pytest with coverage...$(NC)"
	pytest $(PROJECT_DIR) --cov=$(PROJECT_DIR) --cov-report=html --cov-report=term

lint: ## Run linting checks
	@echo "$(YELLOW)Running Black...$(NC)"
	black --check $(PROJECT_DIR)
	@echo "$(YELLOW)Running isort...$(NC)"
	isort --check-only $(PROJECT_DIR)
	@echo "$(YELLOW)Running flake8...$(NC)"
	flake8 $(PROJECT_DIR) --exclude=migrations,settings.py,venv,.venv
	@echo "$(YELLOW)Running mypy...$(NC)"
	mypy $(PROJECT_DIR) --exclude migrations
	@echo "$(GREEN)All linting checks passed!$(NC)"

format: ## Format code with Black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	black $(PROJECT_DIR)
	isort $(PROJECT_DIR)
	@echo "$(GREEN)Code formatted successfully!$(NC)"

security: ## Run security checks
	@echo "$(YELLOW)Running security checks...$(NC)"
	bandit -r $(PROJECT_DIR) -x '*/migrations/*,*/tests/*'
	safety check
	@echo "$(GREEN)Security checks completed!$(NC)"

shell: ## Open Django shell
	@echo "$(GREEN)Opening Django shell...$(NC)"
	$(MANAGE) shell

shell-plus: ## Open Django shell with extensions
	@echo "$(GREEN)Opening Django shell plus...$(NC)"
	$(MANAGE) shell_plus

dbshell: ## Open database shell
	@echo "$(GREEN)Opening database shell...$(NC)"
	$(MANAGE) dbshell

superuser: ## Create superuser
	@echo "$(GREEN)Creating superuser...$(NC)"
	$(MANAGE) createsuperuser

collectstatic: ## Collect static files
	@echo "$(GREEN)Collecting static files...$(NC)"
	$(MANAGE) collectstatic --noinput
	@echo "$(GREEN)Static files collected!$(NC)"

clean: ## Clean up generated files
	@echo "$(RED)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup completed!$(NC)"

reset-db: ## Reset database (WARNING: Deletes all data!)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	rm -f $(PROJECT_DIR)/db.sqlite3
	$(MAKE) migrate
	@echo "$(GREEN)Database reset completed!$(NC)"

fixtures-load: ## Load fixture data
	@echo "$(GREEN)Loading fixtures...$(NC)"
	$(MANAGE) loaddata initial_data
	@echo "$(GREEN)Fixtures loaded!$(NC)"

fixtures-dump: ## Dump current data to fixtures
	@echo "$(GREEN)Dumping data to fixtures...$(NC)"
	$(MANAGE) dumpdata polls --indent=2 > $(PROJECT_DIR)/polls/fixtures/initial_data.json
	@echo "$(GREEN)Data dumped to fixtures!$(NC)"

# Docker commands
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t django-polls:latest .
	@echo "$(GREEN)Docker image built successfully!$(NC)"

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run -p 8000:8000 --rm django-polls:latest

docker-compose-up: ## Start services with docker-compose
	@echo "$(GREEN)Starting services with docker-compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"

docker-compose-down: ## Stop services with docker-compose
	@echo "$(RED)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(NC)"

docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f

# CI/CD commands
ci: lint test security ## Run all CI checks
	@echo "$(GREEN)All CI checks passed!$(NC)"

pre-commit: format lint test ## Run pre-commit checks
	@echo "$(GREEN)Pre-commit checks completed!$(NC)"

# Development shortcuts
dev: install migrate run ## Setup and run development environment

refresh: clean install migrate ## Clean and reinstall everything
	@echo "$(GREEN)Environment refreshed!$(NC)"

.DEFAULT_GOAL := help