.PHONY: install format lint test run clean

# Install dependencies
install:
	uv sync --all-extras

# Format code
format:
	uv run black .
	uv run isort .

# Run linters
lint:
	uv run black --check .
	uv run flake8 .
	uv run mypy . --ignore-missing-imports
	uv run isort --check-only .

# Run tests
test:
	uv run python test.py

# Run server
run:
	uv run python api.py

# Run server with logging
run-log:
	uv run python api.py -l api.log

# Clean cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f api.log