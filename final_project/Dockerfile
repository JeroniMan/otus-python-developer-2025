# 1) Builder stage: install uv, build-deps, and Python dependencies
FROM python:3.12-slim AS builder

# Install build-time system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      libtool \
      autoconf \
      automake \
      python3-dev \
      libffi-dev \
      libgmp-dev \
      libsodium-dev \
      cmake \
      git \
 && rm -rf /var/lib/apt/lists/*

# Install uv (pin version via ARG)
ARG UV_VERSION=0.6.14
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH" \
    UV_COMPILE_BYTECODE=1

# Copy lockfiles first to leverage Docker cache
COPY pyproject.toml README.md ./

# Sync (install) your Python dependencies
RUN uv sync

# 2) Final stage: runtime only
FROM python:3.12-slim

# Install only the runtime libraries your extensions need
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libffi-dev \
      libgmp10 \
      libsodium23 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bring in uv and the venv/site-packages from the builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12

ENV PATH="/root/.local/bin:$PATH" \
    UV_COMPILE_BYTECODE=1

# Copy your application code
COPY . .
