# 🧾 HM_1 — Log Analyzer

A Python application to parse nginx logs, generate aggregated statistics on URLs, and output an HTML report.

## Features

- **Log Parsing:** Extract URL and request time from nginx logs using regex.
- **Report Generation:** Create an HTML report with the top URLs (by total request time).
- **Structured Logging:** Uses `structlog` to write JSON logs.
- **Error Handling:** Aborts when parse error ratio exceeds a threshold.
- **CLI:** Configurable via a JSON config file; file paths, thresholds, and report size are all customizable.
- **Testing:** Includes pytest-based tests.
- **CI/CD:** Configured for CI with standard checks (lint, mypy, tests, etc.).
- **Docker:** A Dockerfile is provided to build a container that can process logs via mounted volumes.

---

## 📦 Project Structure

```
hm_1/
├── pyproject.toml          # Project metadata and dependencies
├── src/
│   └── log_analyzer.py     # Main application logic
├── tests/                  # Unit tests (optional)
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Service orchestration
├── .pre-commit-config.yaml # Pre-commit hook configuration
├── Makefile                # Developer shortcuts
```

---

## 🚀 Quick Start

### ✅ Install dependencies

```bash
poetry install
```

### ▶️ Run the app

```bash
poetry run python src/log_analyzer.py
```

Or using the `Makefile`:

```bash
make run
```

---

## 🧪 Run Tests

```bash
make test
```

---

## 🧹 Code Quality

Check format, imports, types, and lints:

```bash
make lint
```

Auto-format code:

```bash
make format
```

---

## 🐳 Docker Support

### 🛠 Build and Run

```bash
make build        # Build Docker image
make docker-run   # Run container directly
make up           # Run via docker-compose
make down         # Stop services
```

### 🔄 Live volumes

Docker Compose mounts local folders:
- `./logs → /app/logs`
- `./reports → /app/reports`

---

## ✅ Pre-commit Hooks

Install once:

```bash
poetry run pre-commit install
```

Run manually:

```bash
make pre-commit
```

---

## 📌 Requirements

- Python 3.12+
- Poetry
- Docker (for container-based usage)

---

## 📂 CI/CD

GitHub Actions runs:

- on push to `main`
- only when changes are made in `hm_1/`
- using `poetry install`, `black`, `flake8`, `isort`, `mypy`, `pytest`

---

## 🧑‍💻 Author

**German Kovalev**  
[GitHub](https://github.com/JeroniMan)

---

## 📝 License

MIT — feel free to use, modify, and distribute.
