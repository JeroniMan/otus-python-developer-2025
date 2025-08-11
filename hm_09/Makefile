.PHONY: help install run test lint format docker-build docker-run clean

help:
	@echo "Доступные команды:"
	@echo "  install      - Установка зависимостей через uv"
	@echo "  run          - Запуск сервера разработки"
	@echo "  test         - Запуск тестов"
	@echo "  lint         - Проверка кода с ruff"
	@echo "  format       - Форматирование кода"
	@echo "  docker-build - Сборка Docker образа"
	@echo "  docker-run   - Запуск в Docker"
	@echo "  clean        - Очистка временных файлов"

install:
	uv sync

run:
	uv run uvicorn app.app:app --reload --host 127.0.0.1 --port 8000

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run mypy app/

format:
	uv run ruff format .
	uv run ruff check --fix .

docker-build:
	docker build -t hm9-api:latest .

docker-run:
	docker run -p 8000:8000 hm9-api:latest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage
	rm -rf .ruff_cache
	rm -rf .mypy_cache