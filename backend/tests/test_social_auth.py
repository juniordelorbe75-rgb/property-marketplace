import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.auth import social
from backend.routes.auth import _safe_return_to


class SocialAuthTests(unittest.TestCase):
    def setUp(self):
        social._flows.clear()
        social._codes.clear()

    def test_all_providers_are_advertised_with_configuration_status(self):
        values = {
            "GOOGLE_CLIENT_ID": "google-id",
            "GOOGLE_CLIENT_SECRET": "google-secret",
        }
        with patch.dict(os.environ, values, clear=True):
            self.assertEqual(
                social.provider_options(),
                [
                    {"id": "google", "name": "Google", "enabled": True},
                    {"id": "facebook", "name": "Facebook", "enabled": False},
                    {"id": "yahoo", "name": "Yahoo", "enabled": False},
                ],
            )

    def test_flow_state_and_login_code_are_single_use(self):
        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "secret",
        }, clear=True):
            url, returned_state = social.begin_flow("google", "/favorites")
        state = next(iter(social._flows))
        self.assertEqual(returned_state, state)
        self.assertIn("accounts.google.com", url)
        self.assertEqual(social.consume_flow("google", state), "/favorites")
        with self.assertRaises(HTTPException):
            social.consume_flow("google", state)

        code = social.create_login_code(42)
        self.assertEqual(social.consume_login_code(code), 42)
        with self.assertRaises(HTTPException):
            social.consume_login_code(code)

    def test_return_paths_cannot_leave_the_marketplace(self):
        self.assertEqual(_safe_return_to("/properties/12"), "/properties/12")
        self.assertEqual(_safe_return_to("https://evil.example"), "/")
        self.assertEqual(_safe_return_to("//evil.example"), "/")


if __name__ == "__main__":
    unittest.main()
