import unittest
from unittest.mock import patch

from backend.auth.request_throttle import consume_rate_limit, reset_request_throttles, retry_after_detail


class RequestThrottleTests(unittest.TestCase):
    def setUp(self):
        reset_request_throttles()

    def tearDown(self):
        reset_request_throttles()

    def test_blocks_only_after_limit_and_reports_retry_time(self):
        with patch("backend.auth.request_throttle.monotonic", return_value=100.0):
            self.assertIsNone(consume_rate_limit("register", "client-a", limit=2, window_seconds=60))
            self.assertIsNone(consume_rate_limit("register", "client-a", limit=2, window_seconds=60))
            self.assertEqual(consume_rate_limit("register", "client-a", limit=2, window_seconds=60), 60)

    def test_actions_and_clients_have_independent_limits(self):
        self.assertIsNone(consume_rate_limit("register", "client-a", limit=1, window_seconds=60))
        self.assertEqual(consume_rate_limit("register", "client-a", limit=1, window_seconds=60), 60)
        self.assertIsNone(consume_rate_limit("upload", "client-a", limit=1, window_seconds=60))
        self.assertIsNone(consume_rate_limit("register", "client-b", limit=1, window_seconds=60))

    def test_expired_attempts_do_not_count(self):
        with patch("backend.auth.request_throttle.monotonic", return_value=100.0):
            self.assertIsNone(consume_rate_limit("register", "client-a", limit=1, window_seconds=60))

    def test_retry_message_uses_a_human_friendly_rounded_wait(self):
        self.assertEqual(
            retry_after_detail("Too many attempts.", 61),
            "Too many attempts. Try again in about 2 minutes.",
        )
        self.assertEqual(
            retry_after_detail("Too many attempts.", 1),
            "Too many attempts. Try again in about 1 minute.",
        )
        with patch("backend.auth.request_throttle.monotonic", return_value=161.0):
            self.assertIsNone(consume_rate_limit("register", "client-a", limit=1, window_seconds=60))


if __name__ == "__main__":
    unittest.main()
