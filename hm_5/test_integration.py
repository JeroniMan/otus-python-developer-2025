"""
Integration tests with real Redis instance.
Run with: pytest test_integration.py -v --redis
"""

import json
import time

import pytest
import redis

from store import Store


@pytest.fixture(scope="module")
def redis_store():
    """Create a Store connected to Redis for integration tests."""
    try:
        # Try to connect to Redis
        store = Store(host="localhost", port=6379, db=15)  # Use DB 15 for tests
        # Test connection
        client = store._get_client()
        client.ping()
        # Clear test database
        client.flushdb()
        yield store
        # Cleanup after tests
        client.flushdb()
    except redis.ConnectionError:
        pytest.skip("Redis is not available for integration tests")


@pytest.mark.integration
class TestStoreIntegration:
    """Integration tests for Store with real Redis."""

    def test_cache_operations(self, redis_store):
        """Test cache set/get with real Redis."""
        # Set value in cache
        assert redis_store.cache_set("test_key", "test_value", 10)

        # Get value from cache
        value = redis_store.cache_get("test_key")
        assert value == "test_value"

        # Test non-existent key
        assert redis_store.cache_get("non_existent") is None

    def test_cache_expiration(self, redis_store):
        """Test that cache entries expire."""
        # Set with 1 second expiration
        redis_store.cache_set("expire_key", "expire_value", 1)
        assert redis_store.cache_get("expire_key") == "expire_value"

        # Wait for expiration
        time.sleep(2)
        assert redis_store.cache_get("expire_key") is None

    def test_persistent_operations(self, redis_store):
        """Test persistent storage operations."""
        # Set and get string
        redis_store.set("persist_key", "persist_value")
        assert redis_store.get("persist_key") == "persist_value"

        # Set and get JSON
        data = {"name": "John", "age": 30}
        redis_store.set("json_key", data)
        retrieved = redis_store.get("json_key")
        assert json.loads(retrieved) == data

        # Test non-existent key
        assert redis_store.get("non_existent") is None

    def test_retry_on_connection_error(self, redis_store):
        """Test that store retries on connection errors."""
        # Temporarily break the connection
        original_port = redis_store.port
        redis_store.port = 9999  # Wrong port
        redis_store._client = None  # Force reconnection

        # Should return None for cache operations
        assert redis_store.cache_get("any_key") is None
        assert redis_store.cache_set("any_key", "value") is False

        # Should raise for persistent operations after retries
        with pytest.raises(Exception):
            redis_store.get("any_key")

        # Restore connection
        redis_store.port = original_port
        redis_store._client = None

    def test_concurrent_operations(self, redis_store):
        """Test concurrent operations on the store."""
        import threading

        results = []

        def worker(i):
            key = f"concurrent_{i}"
            redis_store.cache_set(key, i, 60)
            value = redis_store.cache_get(key)
            results.append(value == str(i))

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert all(results), "Some concurrent operations failed"

    def test_large_values(self, redis_store):
        """Test storing large values."""
        large_data = "x" * 10000  # 10KB string
        redis_store.set("large_key", large_data)
        retrieved = redis_store.get("large_key")
        assert retrieved == large_data

    def test_special_characters(self, redis_store):
        """Test keys and values with special characters."""
        special_key = "key:with:colons:and-dashes"
        special_value = "value with \"quotes\" and 'apostrophes' and 中文"

        redis_store.set(special_key, special_value)
        assert redis_store.get(special_key) == special_value


@pytest.mark.integration
class TestScoringIntegration:
    """Integration tests for scoring functions with real Redis."""

    def test_score_caching(self, redis_store):
        """Test that scores are properly cached."""
        import scoring

        # Clear any existing cache
        client = redis_store._get_client()
        client.flushdb()

        # Calculate score
        score1 = scoring.get_score(
            redis_store, phone="79175002040", email="test@test.com", first_name="John", last_name="Doe"
        )

        # Check that it was cached
        # The key is constructed in scoring.py
        import hashlib

        key_parts = ["John", "Doe", "79175002040", ""]
        key = "cache:uid:" + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()

        cached_value = client.get(key)
        assert cached_value is not None
        assert float(cached_value) == score1

        # Get from cache
        score2 = scoring.get_score(
            redis_store, phone="79175002040", email="test@test.com", first_name="John", last_name="Doe"
        )
        assert score1 == score2

    def test_interests_storage(self, redis_store):
        """Test storing and retrieving interests."""
        import scoring

        # Store interests
        interests_data = ["books", "travel", "music"]
        redis_store.set("i:123", interests_data)

        # Retrieve interests
        interests = scoring.get_interests(redis_store, "123")
        assert interests == interests_data

        # Non-existent user
        interests = scoring.get_interests(redis_store, "999")
        assert interests == []


# Run with: pytest test_integration.py -v -m integration
# or: python -m pytest test_integration.py::TestStoreIntegration -v
