import json
import logging
import socket
import time
from typing import Any, Optional, Union

try:
    import redis
    from redis.exceptions import ConnectionError, TimeoutError
except ImportError:
    # Fallback for tests without redis installed
    ConnectionError = socket.error
    TimeoutError = socket.timeout
    redis = None

logger = logging.getLogger(__name__)


class RetryableStore:
    """Base class for store with retry logic."""

    def __init__(self, host="localhost", port=6379, db=0, socket_timeout=3, connect_retries=3, retry_delay=0.1):
        self.host = host
        self.port = port
        self.db = db
        self.socket_timeout = socket_timeout
        self.connect_retries = connect_retries
        self.retry_delay = retry_delay
        self._client = None

    def _get_client(self):
        """Get or create Redis client."""
        if redis is None:
            raise ImportError("Redis library is not installed. Install with: pip install redis")
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_timeout,
                decode_responses=True,
            )
        return self._client

    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        for attempt in range(self.connect_retries):
            try:
                client = self._get_client()
                return func(client, *args, **kwargs)
            except (ConnectionError, TimeoutError, socket.error, socket.timeout) as e:
                last_exception = e
                logger.warning(f"Store operation failed (attempt {attempt + 1}/{self.connect_retries}): {e}")
                if attempt < self.connect_retries - 1:
                    time.sleep(self.retry_delay)
                    # Reset client to force reconnection
                    self._client = None
            except Exception as e:
                logger.error(f"Unexpected error in store operation: {e}")
                raise

        raise last_exception


class Store(RetryableStore):
    """Store implementation with separate cache and persistent storage logic."""

    def cache_get(self, key: str) -> Optional[Any]:
        """
        Get value from cache. Returns None if not found or on error.
        This method is fault-tolerant - it returns None on any error.
        """
        try:
            return self._execute_with_retry(lambda client: client.get(f"cache:{key}"))
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    def cache_set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set value in cache with expiration.
        This method is fault-tolerant - it returns False on any error.
        """
        try:

            def _set_with_expire(client, k, v, ex):
                # Convert value to string if needed
                if not isinstance(v, (str, bytes)):
                    v = str(v)
                return client.setex(f"cache:{k}", ex, v)

            self._execute_with_retry(_set_with_expire, key, value, expire)
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        Get value from persistent storage.
        This method must return value or raise exception if store is unavailable.
        """
        return self._execute_with_retry(lambda client: client.get(f"persistent:{key}"))

    def set(self, key: str, value: Union[str, dict, list]) -> None:
        """
        Set value in persistent storage.
        This method must succeed or raise exception.
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self._execute_with_retry(lambda client: client.set(f"persistent:{key}", value))


class MockStore:
    """Mock store for testing without Redis."""

    def __init__(self, initial_data=None):
        self.cache = {}
        self.storage = initial_data or {}
        self.cache_get_calls = []
        self.cache_set_calls = []
        self.get_calls = []
        self.set_calls = []
        self.fail_cache = False
        self.fail_storage = False

    def cache_get(self, key: str) -> Optional[Any]:
        """Mock cache get - always returns None on failure."""
        self.cache_get_calls.append(key)
        if self.fail_cache:
            return None
        return self.cache.get(key)

    def cache_set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Mock cache set - returns False on failure."""
        self.cache_set_calls.append((key, value, expire))
        if self.fail_cache:
            return False
        self.cache[key] = value
        return True

    def get(self, key: str) -> Optional[str]:
        """Mock storage get - raises exception on failure."""
        self.get_calls.append(key)
        if self.fail_storage:
            raise ConnectionError("Mock storage unavailable")
        value = self.storage.get(key)
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    def set(self, key: str, value: Union[str, dict, list]) -> None:
        """Mock storage set - raises exception on failure."""
        self.set_calls.append((key, value))
        if self.fail_storage:
            raise ConnectionError("Mock storage unavailable")
        self.storage[key] = value
