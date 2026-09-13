import unittest

from backend.render_entrypoint import _render_database_url


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


if __name__ == "__main__":
    unittest.main()
