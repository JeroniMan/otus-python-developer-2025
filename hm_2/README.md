# Python Type Challenges - Homework Repository

This repository contains solutions for the **Python Type Challenges** as part of the course/homework. The challenges involve working with Python's typing system to ensure correctness and proper type-checking in code.


## Project Overview

This project includes solutions to various Python type challenges, covering:
- Type hinting with `TypedDict`, `Literal`, `TypeVar`, etc.
- Type checking using tools like `mypy` and `pyright`
- Ensuring type safety in Python code

The repository uses **Poetry** for dependency management and packaging, and **GitHub Actions** for Continuous Integration (CI).

## Getting Started

### Requirements

To run the project locally, make sure you have the following installed:
- Python 3.12 (as specified in `.python-version`)
- Poetry for dependency management

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/ci-project.git
    cd ci-project
    ```

2. Install dependencies with Poetry:

    ```bash
    poetry install
    ```

3. To run the checks locally, use the following commands:
   - **Formatting**: `poetry run black .`
   - **Linting**: `poetry run flake8 .`
   - **Type Checking**: `poetry run mypy .`
   - **Import Order**: `poetry run isort --check-only .`

## CI Pipeline

The CI pipeline runs on every push to the `main` branch and every pull request to the `main` branch. The checks are triggered for any changes in the `hm_2/` directory.
    
## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes.
4. Run the checks locally (`black`, `flake8`, `mypy`, `isort`).
5. Push your changes and create a pull request.

## License

This project is licensed under the MIT License.