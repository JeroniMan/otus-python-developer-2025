.PHONY: lint format test run clean build docker-run up down logs shell

# ===== General variables =====
IMAGE_NAME = log-analyzer
SERVICE_NAME = app

# ===== Code quality: linting and type checks =====
lint:
	# Run code linters and type checker
	poetry run flake8 --config=.flake8 src/
	poetry run mypy src/
	poetry run isort --check-only src/
	poetry run black --check src/

format:
	# Auto-format code with black and isort
	poetry run black .
	poetry run isort .

test:
	# Run unit tests with pytest
	poetry run pytest --maxfail=1 --disable-warnings -q

# ===== Run app locally with poetry =====
run:
	poetry run python -m log_analyzer.main

# ===== Docker commands =====
build:
	# Build Docker image
	docker build -t $(IMAGE_NAME) .

docker-run: build
	# Run the app directly in Docker
	docker run --rm $(IMAGE_NAME)

up:
	# Start the app using Docker Compose
	docker-compose up --build

down:
	# Stop and remove Docker Compose services
	docker-compose down

logs:
	# Show logs from the app service
	docker-compose logs -f $(SERVICE_NAME)

shell:
	# Open a shell in the running container
	docker-compose exec $(SERVICE_NAME) /bin/sh

# ===== Cleanup =====
clean:
	# Remove Python bytecode and cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete