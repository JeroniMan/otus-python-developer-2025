.PHONY: build up down logs restart-collector restart-parser restart-validator ps

# Build all services
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# View logs for all services
logs:
	docker-compose logs -f

# Restart individual services	restart-collector:
	docker-compose restart collector

restart-parser:
	docker-compose restart parser

restart-validator:
	docker-compose restart validator

# List running containers
ps:
	docker-compose ps