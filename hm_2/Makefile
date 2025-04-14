.PHONY: lint

# ===== General variables =====
IMAGE_NAME = python-type-challenges
SERVICE_NAME = app

# ===== Code quality: linting and type checks =====
typing:
	# Run code linters and type checker
	poetry run flake8 --config=.flake8 .
	poetry run mypy .
	poetry run isort .
	poetry run black .