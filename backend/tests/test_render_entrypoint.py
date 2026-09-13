import os
import unittest
from unittest.mock import patch

from backend.render_entrypoint import _render_database_url, configure_environment


class RenderEntrypointTests(unittest.TestCase):
    def test_database_url_uses_psycopg_and_encrypted_transport(self):
        self.assertEqual(
            _render_database_url("postgresql://user:pass@db/habitard"),
            "postgresql+psycopg://user:pass@db/habitard?sslmode=require",
        )

    def test_preserves_existing_database_options(self):
        self.assertEqual(
            _render_database_url("postgresql+psycopg://user:pass@db/habitard?sslmode=verify-full"),
            "postgresql+psycopg://user:pass@db/habitard?sslmode=verify-full",
        )

    def test_configures_render_proxy_and_public_origin(self):
        with patch.dict(
            os.environ,
            {"RENDER_EXTERNAL_HOSTNAME": "HabitaRD-Marketplace.onrender.com"},
            clear=True,
        ):
            configure_environment()

            self.assertEqual(os.environ["TRUSTED_HOSTS"], "habitard-marketplace.onrender.com")
            self.assertEqual(
                os.environ["OAUTH_REDIRECT_BASE_URL"],
                "https://habitard-marketplace.onrender.com",
            )
            self.assertEqual(os.environ["FORWARDED_ALLOW_IPS"], "*")


if __name__ == "__main__":
    unittest.main()
