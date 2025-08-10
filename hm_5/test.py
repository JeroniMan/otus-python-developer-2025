import datetime
import functools
import hashlib
import json
import unittest
from unittest.mock import Mock, patch

import api
import scoring
from store import MockStore, Store


def cases(test_cases):
    """
    Decorator for running test with multiple test cases.
    Shows which case failed when test fails.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(self):
            for i, case in enumerate(test_cases):
                with self.subTest(case=i, data=case):
                    f(self, case)

        return wrapper

    return decorator


class TestFields(unittest.TestCase):
    """Unit tests for field validation."""

    def test_char_field_validation(self):
        field = api.CharField(required=True)
        field.name = "test_field"

        # Valid
        field.validate("test")

        # Invalid - None when required
        with self.assertRaises(api.ValidationError):
            field.validate(None)

        # Invalid - not a string
        with self.assertRaises(api.ValidationError):
            field.validate(123)

    def test_email_field_validation(self):
        field = api.EmailField()
        field.name = "email"

        # Valid
        field.validate("test@example.com")
        field.validate(None)  # nullable by default

        # Invalid - no @
        with self.assertRaises(api.ValidationError):
            field.validate("invalid_email")

    def test_phone_field_validation(self):
        field = api.PhoneField()
        field.name = "phone"

        # Valid
        field.validate("79175002040")
        field.validate(None)

        # Invalid - wrong length
        with self.assertRaises(api.ValidationError):
            field.validate("7917500")

        # Invalid - doesn't start with 7
        with self.assertRaises(api.ValidationError):
            field.validate("89175002040")

    def test_birthday_field_validation(self):
        field = api.BirthDayField()
        field.name = "birthday"

        # Valid
        field.validate("01.01.2000")
        field.validate(None)

        # Invalid - wrong format
        with self.assertRaises(api.ValidationError):
            field.validate("2000-01-01")

        # Invalid - too old
        with self.assertRaises(api.ValidationError):
            field.validate("01.01.1900")

    def test_gender_field_validation(self):
        field = api.GenderField()
        field.name = "gender"

        # Valid
        field.validate(0)
        field.validate(1)
        field.validate(2)
        field.validate(None)

        # Invalid
        with self.assertRaises(api.ValidationError):
            field.validate(3)
        with self.assertRaises(api.ValidationError):
            field.validate("male")

    def test_client_ids_field_validation(self):
        field = api.ClientIDsField(required=True)
        field.name = "client_ids"

        # Valid
        field.validate([1, 2, 3])

        # Invalid - empty when required
        with self.assertRaises(api.ValidationError):
            field.validate([])

        # Invalid - not a list
        with self.assertRaises(api.ValidationError):
            field.validate("123")

        # Invalid - non-integer elements
        with self.assertRaises(api.ValidationError):
            field.validate([1, "2", 3])


class TestRequests(unittest.TestCase):
    """Unit tests for request validation."""

    def test_online_score_request_valid(self):
        # Valid with phone-email pair
        request = api.OnlineScoreRequest({"phone": "79175002040", "email": "test@example.com"})
        self.assertTrue(request.validate())

        # Valid with first_name-last_name pair
        request = api.OnlineScoreRequest({"first_name": "John", "last_name": "Doe"})
        self.assertTrue(request.validate())

        # Valid with gender-birthday pair
        request = api.OnlineScoreRequest({"gender": 1, "birthday": "01.01.2000"})
        self.assertTrue(request.validate())

    def test_online_score_request_invalid(self):
        # Invalid - no valid pairs
        request = api.OnlineScoreRequest({"phone": "79175002040"})
        self.assertFalse(request.validate())
        self.assertIn("At least one pair must be non-empty", request._errors[0])

        # Invalid phone format
        request = api.OnlineScoreRequest({"phone": "123", "email": "test@example.com"})
        self.assertFalse(request.validate())

    def test_clients_interests_request_valid(self):
        request = api.ClientsInterestsRequest({"client_ids": [1, 2, 3]})
        self.assertTrue(request.validate())

        request = api.ClientsInterestsRequest({"client_ids": [1], "date": "01.01.2020"})
        self.assertTrue(request.validate())

    def test_clients_interests_request_invalid(self):
        # Missing required field
        request = api.ClientsInterestsRequest({})
        self.assertFalse(request.validate())

        # Invalid date format
        request = api.ClientsInterestsRequest({"client_ids": [1], "date": "2020-01-01"})
        self.assertFalse(request.validate())


class TestStore(unittest.TestCase):
    """Unit tests for store functionality."""

    def test_mock_store_cache_operations(self):
        store = MockStore()

        # Test cache set/get
        self.assertTrue(store.cache_set("key1", "value1"))
        self.assertEqual(store.cache_get("key1"), "value1")

        # Test cache miss
        self.assertIsNone(store.cache_get("nonexistent"))

        # Test cache failure mode
        store.fail_cache = True
        self.assertIsNone(store.cache_get("key1"))
        self.assertFalse(store.cache_set("key2", "value2"))

    def test_mock_store_persistent_operations(self):
        store = MockStore({"key1": "value1"})

        # Test get
        self.assertEqual(store.get("key1"), "value1")
        self.assertIsNone(store.get("nonexistent"))

        # Test set
        store.set("key2", "value2")
        self.assertEqual(store.get("key2"), "value2")

        # Test failure mode
        store.fail_storage = True
        with self.assertRaises(Exception):
            store.get("key1")
        with self.assertRaises(Exception):
            store.set("key3", "value3")

    @patch("store.redis.Redis")
    def test_real_store_retry_logic(self, mock_redis_class):
        """Test that Store retries on connection errors."""
        mock_client = Mock()
        mock_redis_class.return_value = mock_client

        # Import the actual ConnectionError from redis or use fallback
        try:
            from redis.exceptions import ConnectionError as RedisConnectionError
        except ImportError:
            import socket

            RedisConnectionError = socket.error

        # Simulate connection error then success
        mock_client.get.side_effect = [RedisConnectionError("Connection failed"), "value"]

        store = Store(connect_retries=2)
        result = store.cache_get("test_key")

        self.assertEqual(result, "value")
        self.assertEqual(mock_client.get.call_count, 2)


class TestScoring(unittest.TestCase):
    """Unit tests for scoring functions."""

    def test_get_score_calculation(self):
        store = MockStore()

        # Test score calculation
        score = scoring.get_score(store, phone="79175002040", email="test@example.com")
        self.assertEqual(score, 3.0)

        score = scoring.get_score(
            store,
            phone="79175002040",
            email="test@example.com",
            birthday=datetime.datetime(1990, 1, 1),
            gender=1,
            first_name="John",
            last_name="Doe",
        )
        self.assertEqual(score, 5.0)

    def test_get_score_with_cache(self):
        store = MockStore()

        # First call - calculates and caches
        score1 = scoring.get_score(store, phone="79175002040")
        self.assertEqual(score1, 1.5)
        self.assertEqual(len(store.cache_set_calls), 1)

        # Second call - should get from cache
        score2 = scoring.get_score(store, phone="79175002040")
        self.assertEqual(score2, 1.5)
        self.assertEqual(len(store.cache_get_calls), 2)

    def test_get_score_cache_failure(self):
        """Test that get_score works even when cache fails."""
        store = MockStore()
        store.fail_cache = True

        # Should still calculate score even with cache failure
        score = scoring.get_score(store, phone="79175002040", email="test@example.com")
        self.assertEqual(score, 3.0)

    def test_get_interests(self):
        store = MockStore({"i:1": json.dumps(["books", "music"])})

        interests = scoring.get_interests(store, "1")
        self.assertEqual(interests, ["books", "music"])

        # Empty interests
        interests = scoring.get_interests(store, "999")
        self.assertEqual(interests, [])

    def test_get_interests_storage_failure(self):
        """Test that get_interests raises exception when storage fails."""
        store = MockStore()
        store.fail_storage = True

        with self.assertRaises(Exception):
            scoring.get_interests(store, "1")


class TestAPI(unittest.TestCase):
    """Functional tests for API handlers."""

    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = MockStore()

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode("utf-8")
            ).hexdigest()
        else:
            msg = (request.get("account", "") + request.get("login", "") + api.SALT).encode("utf-8")
            request["token"] = hashlib.sha512(msg).hexdigest()

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases(
        [
            {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
            {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
            {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
        ]
    )
    def test_bad_auth(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases(
        [
            {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
            {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
            {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
        ]
    )
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases(
        [
            {},
            {"phone": "79175002040"},
            {"phone": "89175002040", "email": "stupnikov@otus.ru"},
            {"phone": "79175002040", "email": "stupnikovotus.ru"},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        ]
    )
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, f"Failed for arguments: {arguments}")
        self.assertTrue(len(response))

    @cases(
        [
            {"phone": "79175002040", "email": "stupnikov@otus.ru"},
            {"phone": 79175002040, "email": "stupnikov@otus.ru"},
            {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
            {"gender": 0, "birthday": "01.01.2000"},
            {"gender": 2, "birthday": "01.01.2000"},
            {"first_name": "a", "last_name": "b"},
        ]
    )
    def test_ok_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, f"Failed for arguments: {arguments}")
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases(
        [
            {},
            {"date": "20.07.2017"},
            {"client_ids": [], "date": "20.07.2017"},
            {"client_ids": {1: 2}, "date": "20.07.2017"},
            {"client_ids": ["1", "2"], "date": "20.07.2017"},
            {"client_ids": [1, 2], "date": "XXX"},
        ]
    )
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, f"Failed for arguments: {arguments}")
        self.assertTrue(len(response))

    @cases(
        [
            {"client_ids": [1, 2, 3], "date": datetime.datetime.today().strftime("%d.%m.%Y")},
            {"client_ids": [1, 2], "date": "19.07.2017"},
            {"client_ids": [0]},
        ]
    )
    def test_ok_interests_request(self, arguments):
        # Setup mock data
        for cid in arguments["client_ids"]:
            self.store.storage[f"i:{cid}"] = json.dumps(["books", "music"])

        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, f"Failed for arguments: {arguments}")
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(
            all(v and isinstance(v, list) and all(isinstance(i, (bytes, str)) for i in v) for v in response.values())
        )
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))

    def test_interests_storage_failure(self):
        """Test that interests handler returns error when storage fails."""
        self.store.fail_storage = True
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": {"client_ids": [1, 2]},
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INTERNAL_ERROR, code)


if __name__ == "__main__":
    unittest.main()
