.PHONY: help install test test-basic test-functions lint format clean docker-build docker-test

help:
	@echo "Byterun - Python interpreter in Python"
	@echo ""
	@echo "Available commands:"
	@echo "  make install        Install dependencies"
	@echo "  make test           Run all tests"
	@echo "  make test-basic     Run basic tests only"
	@echo "  make test-functions Run function tests only"
	@echo "  make lint           Run linters (black, isort, ruff, mypy)"
	@echo "  make format         Format code with black and isort"
	@echo "  make clean          Clean up generated files"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-test    Run tests in Docker"

install:
	pip install -e .
	pip install pytest black isort ruff mypy coverage

test:
	python -m pytest tests/ -v

test-basic:
	python -m pytest tests/test_basic.py -v

test-functions:
	python -m pytest tests/test_functions.py -v

test-coverage:
	python -m pytest tests/ --cov=byterun --cov-report=html --cov-report=term

lint:
	black --check byterun tests
	isort --check-only byterun tests
	ruff check byterun tests
	mypy byterun

format:
	black byterun tests
	isort byterun tests

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t byterun:latest .

docker-test:
	docker run --rm byterun:latest python -m pytest tests/ -v

# Development helpers
run-example:
	python examples/simple_example.py

debug:
	python -m pdb examples/simple_example.py

benchmark:
	python -m timeit -s "from byterun.pyvm import VirtualMachine; vm = VirtualMachine(); code = compile('x = 1 + 2', '<test>', 'exec')" "vm.run_code(code, {}, {})"