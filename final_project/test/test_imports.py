"""Basic import tests to verify modules can be loaded."""

import pytest


def test_collector_imports():
    """Test that collector module can be imported."""
    import indexer.collector
    assert hasattr(indexer.collector, 'SolanaCollector')
    assert hasattr(indexer.collector, 'PersistentSlotQueueManager')


def test_parser_imports():
    """Test that parser module can be imported."""
    import indexer.parser
    assert hasattr(indexer.parser, 'SolanaParser')
    assert hasattr(indexer.parser, 'ParseQueueManager')


def test_validator_imports():
    """Test that validator module can be imported."""
    import indexer.validator
    assert hasattr(indexer.validator, 'Validator')


def test_utils_imports():
    """Test that utils module can be imported."""
    import indexer.utils
    assert hasattr(indexer.utils, 'get_gcs_client')
    assert hasattr(indexer.utils, 'upload_json_to_gcs')
    assert hasattr(indexer.utils, 'upload_parquet_to_gcs')


def test_schema_imports():
    """Test that schema module can be imported."""
    import indexer.schema
    assert hasattr(indexer.schema, 'create_block_schema')
    assert hasattr(indexer.schema, 'create_transaction_schema')
    assert hasattr(indexer.schema, 'create_rewards_schema')


def test_config_imports():
    """Test that config module can be imported."""
    import indexer.config
    assert hasattr(indexer.config, 'RPC_URL')
    assert hasattr(indexer.config, 'GCS_BUCKET_NAME')
    assert hasattr(indexer.config, 'WORKER_COUNT')


def test_metrics_imports():
    """Test that metrics module can be imported."""
    import indexer.metrics
    assert hasattr(indexer.metrics, 'current_collector_progress')
    assert hasattr(indexer.metrics, 'raw_files_queue')


@pytest.mark.parametrize("module_name", [
    'indexer.collector',
    'indexer.parser',
    'indexer.validator',
    'indexer.utils',
    'indexer.schema',
    'indexer.config',
    'indexer.metrics'
])
def test_module_imports_no_errors(module_name):
    """Test that all modules can be imported without errors."""
    try:
        __import__(module_name)
    except ImportError as e:
        pytest.fail(f"Failed to import {module_name}: {e}")


def test_env_example_exists():
    """Test that .env.example file exists."""
    import os
    assert os.path.exists('.env.example'), ".env.example file is missing"


def test_dockerfile_exists():
    """Test that Dockerfile exists."""
    import os
    assert os.path.exists('Dockerfile'), "Dockerfile is missing"


def test_docker_compose_exists():
    """Test that docker-compose.yml exists."""
    import os
    assert os.path.exists('docker-compose.yml'), "docker-compose.yml is missing"