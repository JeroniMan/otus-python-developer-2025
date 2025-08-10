FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY *.py ./

# Expose port
EXPOSE 8080

# Default command
CMD ["uv", "run", "python", "api.py", "-p", "8080"]