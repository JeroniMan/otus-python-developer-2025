.PHONY: help install run test docker-build docker-up docker-down clean

help:
	@echo "Доступные команды:"
	@echo "  install      - Установка зависимостей"
	@echo "  run          - Запуск краулера"
	@echo "  test         - Запуск тестов"
	@echo "  docker-build - Сборка Docker образа"
	@echo "  docker-up    - Запуск через Docker Compose"
	@echo "  docker-down  - Остановка Docker контейнеров"
	@echo "  clean        - Очистка временных файлов"

install:
	pip install -r requirements.txt

run:
	python main.py

test:
	pytest tests/ -v

docker-build:
	docker build -t hn-crawler:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage