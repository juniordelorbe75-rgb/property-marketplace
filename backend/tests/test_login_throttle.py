import unittest
from unittest.mock import patch

from backend.auth.login_throttle import (
    MAX_ACCOUNT_FAILED_ATTEMPTS,
    MAX_CLIENT_FAILED_ATTEMPTS,
    clear_login_failures,
    login_retry_after,
    record_login_failure,
    reset_login_throttle,
)


class LoginThrottleTests(unittest.TestCase):
    def setUp(self):
        reset_login_throttle()

    def tearDown(self):
        reset_login_throttle()

    def test_distributed_attempts_are_bounded_per_account(self):
        with patch("backend.auth.login_throttle.monotonic", return_value=100.0):
            for attempt in range(MAX_ACCOUNT_FAILED_ATTEMPTS):
                record_login_failure(f"client-{attempt}", " Victim@Example.com ")

            self.assertEqual(
                login_retry_after("new-client", "victim@example.com"),
                15 * 60,
            )

    def test_password_spraying_is_bounded_per_client(self):
        with patch("backend.auth.login_throttle.monotonic", return_value=100.0):
            for attempt in range(MAX_CLIENT_FAILED_ATTEMPTS):
                record_login_failure("spraying-client", f"person-{attempt}@example.com")

            self.assertEqual(
                login_retry_after("spraying-client", "another@example.com"),
                15 * 60,
            )

    def test_success_clears_pair_and_account_but_not_client_protection(self):
        with patch("backend.auth.login_throttle.monotonic", return_value=100.0):
            for attempt in range(MAX_ACCOUNT_FAILED_ATTEMPTS):
                record_login_failure(f"client-{attempt}", "member@example.com")
            clear_login_failures("client-0", "member@example.com")
            self.assertIsNone(login_retry_after("new-client", "member@example.com"))

            for attempt in range(MAX_CLIENT_FAILED_ATTEMPTS):
                record_login_failure("shared-client", f"target-{attempt}@example.com")
            clear_login_failures("shared-client", "target-0@example.com")
            self.assertIsNotNone(
                login_retry_after("shared-client", "unrelated@example.com")
            )

    def test_expired_account_and_client_attempts_are_pruned(self):
        with patch("backend.auth.login_throttle.monotonic", return_value=100.0):
            for attempt in range(MAX_ACCOUNT_FAILED_ATTEMPTS):
                record_login_failure(f"client-{attempt}", "member@example.com")

        with patch("backend.auth.login_throttle.monotonic", return_value=1001.0):
            self.assertIsNone(login_retry_after("new-client", "member@example.com"))


if __name__ == "__main__":
    unittest.main()
