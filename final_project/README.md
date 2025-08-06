# Solana Indexer

A modular, Dockerized blockchain data processing pipeline for the Solana network, comprising three main components:
- Collector: Fetches blocks via RPC and writes raw JSON to GCS or local storage. 
- Parser: Reads raw JSON, transforms to Parquet, and uploads processed data.
- Validator: Validates, partitions, and organizes processed Parquet files by epoch and block date.

All services can run independently in Docker containers, orchestrated with Docker Compose.


## Prerequisites
- Docker & Docker Compose (v1.27+)
- Poetry (only for local development; containers install dependencies)
- A .env file with required environment variables (see below)
- GCP Service Account JSON (if using GCS)

## Repository Structure
```
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── poetry.lock
├── indexer/
│   ├── collector.py
│   ├── parser.py
│   ├── validator.py
│   └── utils.py
└── README.md
```

## Environment Variables

Copy .env.example to .env and set values:


## Docker & Compose

1. Build images: `make build`
2. Start all services: `make up`
3. View logs: `make logs`
4. Stop: `make down`
5. Each service can also be restarted individually:
- `make restart-collector`
- `make restart-parser`
- `make restart-validator`



## Component Responsibilities

### Collector (collector.py)
	•	Shards slots across WORKER_COUNT threads
	•	Fetches blocks via getBlock RPC
	•	Batches and uploads raw JSON (to GCS or local)
	•	Persists per-worker state for restart

### Parser (parser.py)
	•	Reads raw JSON blobs
	•	Converts to Parquet (schema validation)
	•	Uploads to processed_data/ in GCS

### Validator (validator.py)
	•	Polls processed_data/ for new Parquet files
	•	Groups by iteration and entity
	•	Uses filename metadata to decide whether to move or split
	•	Organizes output under <entity>/creation_date=…/epoch=…/block_date=…/
	•	Uploads per-iteration state JSON

### Conventions & Best Practices
	•	Poetry for dependency management via pyproject.toml.
	•	Makefile for common tasks.
	•	Docker Compose for orchestration; services are independent and restartable.
	•	Environment-driven configuration; no hard-coded secrets.
	•	Logging at INFO/DEBUG levels for observability.


### Happy indexing!