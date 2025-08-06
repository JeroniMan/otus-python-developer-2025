"""
Test suite for Solana Indexer components
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class TestImports:
    """Test that all modules can be imported"""

    def test_collector_imports(self):
        """Test that collector module can be imported."""
        import indexer.collector
        assert hasattr(indexer.collector, 'SolanaCollector')
        assert hasattr(indexer.collector, 'PersistentSlotQueueManager')
        assert hasattr(indexer.collector, 'SlotTask')

    def test_parser_imports(self):
        """Test that parser module can be imported."""
        import indexer.parser
        assert hasattr(indexer.parser, 'SolanaParser')
        assert hasattr(indexer.parser, 'ParseQueueManager')
        assert hasattr(indexer.parser, 'ParseTask')

    def test_validator_imports(self):
        """Test that validator module can be imported."""
        import indexer.validator
        assert hasattr(indexer.validator, 'Validator')

    def test_utils_imports(self):
        """Test that utils module can be imported."""
        import indexer.utils
        assert hasattr(indexer.utils, 'get_gcs_client')
        assert hasattr(indexer.utils, 'upload_json_to_gcs')
        assert hasattr(indexer.utils, 'calculate_files_queue')

    def test_schema_imports(self):
        """Test that schema module can be imported."""
        import indexer.schema
        assert hasattr(indexer.schema, 'create_block_schema')
        assert hasattr(indexer.schema, 'create_rewards_schema')
        assert hasattr(indexer.schema, 'create_transaction_schema')


class TestSlotTask:
    """Test SlotTask dataclass"""

    def test_slot_task_creation(self):
        from indexer.collector import SlotTask

        task = SlotTask(slot=12345)
        assert task.slot == 12345
        assert task.retry_count == 0
        assert task.assigned_at is None
        assert task.worker_id is None

    def test_slot_task_with_params(self):
        from indexer.collector import SlotTask

        task = SlotTask(slot=12345, retry_count=2, worker_id=1)
        assert task.slot == 12345
        assert task.retry_count == 2
        assert task.worker_id == 1


class TestParseTask:
    """Test ParseTask dataclass"""

    def test_parse_task_creation(self):
        from indexer.parser import ParseTask

        task = ParseTask(blob_name="tests.json")
        assert task.blob_name == "tests.json"
        assert task.file_size == 0
        assert task.created_at is None
        assert task.retry_count == 0


class TestUtilFunctions:
    """Test utility functions"""

    @patch('indexer.utils.storage.Client')
    def test_calculate_files_queue_empty(self, mock_storage):
        """Test calculate_files_queue with no files"""
        from indexer.utils import calculate_files_queue

        # Mock empty bucket
        mock_bucket = Mock()
        mock_bucket.list_blobs.return_value = []
        mock_storage.return_value.bucket.return_value = mock_bucket

        count, min_progress = calculate_files_queue('raw_data/')
        assert count == 0
        assert min_progress == 0

    @patch('indexer.utils.storage.Client')
    def test_calculate_files_queue_with_files(self, mock_storage):
        """Test calculate_files_queue with matching files"""
        from indexer.utils import calculate_files_queue

        # Mock files
        mock_blob1 = Mock()
        mock_blob1.name = 'raw_data/slots_100_200_1234_5678_1000_0.json.gzip'
        mock_blob2 = Mock()
        mock_blob2.name = 'raw_data/slots_201_300_5679_6789_2000_1.json.gzip'

        mock_bucket = Mock()
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_storage.return_value.bucket.return_value = mock_bucket

        with patch('indexer.utils.get_gcs_client', return_value=mock_storage.return_value):
            count, min_progress = calculate_files_queue('raw_data/')

        assert count == 2
        assert min_progress == 1000  # minimum timestamp


class TestValidator:
    """Test Validator class"""

    def test_calculate_epoch(self):
        """Test epoch calculation"""
        from indexer.validator import Validator

        assert Validator.calculate_epoch(0) == 0
        assert Validator.calculate_epoch(431999) == 0
        assert Validator.calculate_epoch(432000) == 1
        assert Validator.calculate_epoch(864000) == 2

    def test_calculate_block_date(self):
        """Test block date calculation"""
        from indexer.validator import Validator

        # Test zero timestamp
        assert Validator.calculate_block_date(0) == "1970-01-01"

        # Test specific timestamp
        assert Validator.calculate_block_date(1609459200) == "2021-01-01"

    def test_calculate_block_hour(self):
        """Test block hour calculation"""
        from indexer.validator import Validator

        # Test zero timestamp
        assert Validator.calculate_block_hour(0) == "1970-01-01 00:00:00"

        # Test specific timestamp
        assert Validator.calculate_block_hour(1609459200) == "2021-01-01 00:00:00"


class TestSchemas:
    """Test PyArrow schemas"""

    def test_block_schema_fields(self):
        """Test block schema has required fields"""
        from indexer.schema import create_block_schema

        schema = create_block_schema()
        field_names = [field.name for field in schema]

        required_fields = ['slot', 'blockhash', 'blockTime', 'blockHeight']
        for field in required_fields:
            assert field in field_names

    def test_transaction_schema_fields(self):
        """Test transaction schema has required fields"""
        from indexer.schema import create_transaction_schema

        schema = create_transaction_schema()
        field_names = [field.name for field in schema]

        required_fields = ['slot', 'transaction_id', 'blockTime', 'transaction_index']
        for field in required_fields:
            assert field in field_names

    def test_rewards_schema_fields(self):
        """Test rewards schema has required fields"""
        from indexer.schema import create_rewards_schema

        schema = create_rewards_schema()
        field_names = [field.name for field in schema]

        required_fields = ['slot', 'pubkey', 'lamports', 'rewardType']
        for field in required_fields:
            assert field in field_names


class TestFilePatterns:
    """Test file name patterns"""

    def test_raw_file_pattern(self):
        """Test raw file pattern matching"""
        import re

        pattern = re.compile(
            r"raw_data/slots_"
            r"(?P<first_slot>\d+)_"
            r"(?P<last_slot>\d+)_"
            r"(?P<first_time>\d+)_"
            r"(?P<last_time>\d+)_"
            r"(?P<timestamp>\d+)_"
            r"(?P<worker_id>\d+)"
            r"\.json(\.gzip)?$"
        )

        # Test valid filenames
        valid_names = [
            "raw_data/slots_100_200_1234_5678_1000_0.json",
            "raw_data/slots_100_200_1234_5678_1000_0.json.gzip",
        ]

        for name in valid_names:
            match = pattern.match(name)
            assert match is not None
            assert match.group('first_slot') == '100'
            assert match.group('last_slot') == '200'
            assert match.group('worker_id') == '0'

        # Test invalid filenames
        invalid_names = [
            "raw_data/slot_100_200.json",  # missing 's' in slots
            "raw_data/slots_100.json",  # missing fields
            "processed_data/slots_100_200_1234_5678_1000_0.json",  # wrong directory
        ]

        for name in invalid_names:
            match = pattern.match(name)
            assert match is None


class TestQueueManager:
    """Test PersistentSlotQueueManager"""

    @patch('indexer.collector.storage.Client')
    @patch('indexer.collector.requests.Session')
    def test_queue_manager_init(self, mock_session, mock_storage):
        """Test queue manager initialization"""
        from indexer.collector import PersistentSlotQueueManager

        manager = PersistentSlotQueueManager(
            start_slot=1000,
            rpc_url='https://test.rpc.url',
            state_bucket='tests-bucket',
            storage_client=mock_storage.return_value
        )

        assert manager.start_slot == 1000
        assert manager.current_slot == 1000
        assert manager.slot_queue.empty()
        assert len(manager.processing_slots) == 0
        assert len(manager.completed_slots) == 0


# Configuration for pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])