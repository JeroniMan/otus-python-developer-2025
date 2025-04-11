# Homework #1
# My Log Analyzer
    
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

## Usage

1. **Installation:**  
   Install dependencies using Poetry:
   ```bash
   poetry install