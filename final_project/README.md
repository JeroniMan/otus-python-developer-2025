# Solana Indexer

A modular, Dockerized blockchain data processing pipeline for the Solana network, comprising three main components:
- **Collector**: Fetches blocks via RPC and writes raw JSON to GCS or local storage
- **Parser**: Reads raw JSON, transforms to Parquet, and uploads processed data
- **Validator**: Validates, partitions, and organizes processed Parquet files by epoch and block date

All services can run independently in Docker containers, orchestrated with Docker Compose.

## 📋 Prerequisites

- Docker & Docker Compose (v1.27+)
- UV package manager (for local development)
- Python 3.12+
- A `.env` file with required environment variables
- GCP Service Account JSON (if using GCS)

## 📁 Repository Structure

```
final_project/
├── indexer/
│   ├── collector.py      # Fetches blocks from Solana RPC
│   ├── parser.py         # Converts JSON to Parquet
│   ├── validator.py      # Organizes and partitions data
│   ├── utils.py          # Common utilities
│   ├── schema.py         # PyArrow schemas
│   ├── config.py         # Configuration loader
│   └── metrics.py        # Prometheus metrics
├── config/               # Configuration for monitoring stack
│   ├── grafana/
│   ├── loki/
│   └── prometheus/
├── tests/                # Test files
├── docker-compose.yml    # Service orchestration
├── Dockerfile           # Multi-stage Docker build
├── Makefile            # Common commands
├── pyproject.toml      # Project dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd final_project

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your configuration:

```bash
# Required for real data collection
RPC_URL=https://api.mainnet-beta.solana.com  # Or your preferred RPC endpoint
GCS_BUCKET_NAME=your-bucket-name
GCS_STATE_BUCKET_NAME=your-state-bucket
GCP_SERVICE_ACCOUNT_JSON=credentials/service-account.json

# For local testing without GCS
STORE_MODE=local  # Use 'gcs' for Google Cloud Storage

# Worker configuration
WORKER_COUNT=32
PARSER_COUNT=24
VALIDATOR_COUNT=3
START_SLOT=335474500  # Starting slot for collection
BATCH_SIZE=10
```

### 3. Add GCP Credentials (if using GCS)

```bash
mkdir -p credentials
# Place your service-account.json in credentials/ directory
```

### 4. Run with Docker

```bash
# Build all services
make build

# Start all services
make up

# View logs
make logs

# Stop services
make down
```

### 5. Run Individual Services

```bash
# Start only specific services
docker-compose up collector  # Only collector
docker-compose up parser     # Only parser
docker-compose up validator  # Only validator
```

## 🛠 Local Development

### Install Dependencies

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync --all-extras

# Run services locally
uv run python indexer/collector.py
uv run python indexer/parser.py
uv run python indexer/validator.py
```

### Code Quality

```bash
# Format code
uv run black indexer/
uv run isort indexer/

# Run linters
uv run flake8 indexer/
uv run mypy indexer/

# Run tests
uv run pytest tests/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## 📊 Component Details

### Collector (collector.py)
- Shards slot ranges across multiple worker threads
- Fetches blocks using `getBlock` RPC method
- Batches requests for efficiency
- Saves raw JSON to GCS or local storage
- Maintains state for fault tolerance

### Parser (parser.py)
- Monitors raw data directory for new files
- Extracts three entity types: blocks, transactions, rewards
- Converts to Parquet format with schema validation
- Uploads to `processed_data/` directory
- Manages processing queue with state persistence

### Validator (validator.py)
- Processes files in FIFO order based on creation timestamp
- Partitions data by:
  - Epoch (432,000 slots)
  - Block date (YYYY-MM-DD)
  - Block hour (HH:00:00)
- Splits files that span multiple partitions
- Maintains processed files state

## 📈 Monitoring

The stack includes comprehensive monitoring:

- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Visualization (port 3000)
- **Loki**: Log aggregation (port 3100)
- **Custom metrics**: Collection progress, queue sizes, worker gaps

Access monitoring dashboards:
- Grafana: http://localhost:3000 (admin/secret)
- Prometheus: http://localhost:9090

## 🔧 Configuration

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `RPC_URL` | Solana RPC endpoint | Required |
| `GCS_BUCKET_NAME` | Main storage bucket | Required |
| `GCS_STATE_BUCKET_NAME` | State storage bucket | Required |
| `GCP_SERVICE_ACCOUNT_JSON` | Path to GCP credentials | Required for GCS |
| `WORKER_COUNT` | Number of collector workers | 32 |
| `PARSER_COUNT` | Number of parser workers | 24 |
| `VALIDATOR_COUNT` | Number of validator workers | 3 |
| `START_SLOT` | Starting slot number | 335474500 |
| `BATCH_SIZE` | RPC batch size | 10 |
| `STORE_MODE` | Storage mode (gcs/local) | gcs |

### Makefile Commands

```bash
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make logs           # View service logs
make restart-collector  # Restart collector
make restart-parser     # Restart parser
make restart-validator  # Restart validator
make ps             # List running containers
```

## 🧪 Testing

Basic import tests are included to verify module structure:

```bash
# Run tests
uv run pytest tests/ -v
```

For production deployment, additional tests should be implemented for:
- RPC connection handling
- Data transformation accuracy
- State recovery mechanisms
- Error handling scenarios

## 📝 Notes

- **For demonstration purposes**: This is a simplified version of a production indexer
- **Requires real RPC**: To process actual data, you need access to a Solana RPC node
- **Storage costs**: Be aware of GCS storage and egress costs when running at scale
- **Rate limiting**: Consider RPC rate limits when configuring worker counts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linters and tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details