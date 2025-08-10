.PHONY: install format lint test test-coverage run demo clean help

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies with UV"
	@echo "  make format         - Format code with black and isort"
	@echo "  make lint           - Run linters (pylint, mypy)"
	@echo "  make test           - Run tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make run            - Run the application"
	@echo "  make demo           - Run demo script"
	@echo "  make clean          - Clean up generated files"

install:
	uv sync --all-extras

format:
	uv run black domain infrastructure tests
	uv run isort domain infrastructure tests

lint:
	uv run pylint domain infrastructure
	uv run mypy domain infrastructure

test:
	uv run pytest tests/ -v

test-coverage:
	uv run pytest tests/ --cov=domain --cov=infrastructure --cov-report=html --cov-report=term

run:
	uv run python main.py

demo:
	uv run python demo.py

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov .coverage
	rm -f warehouse.db
	rm -rf .venv uv.lock