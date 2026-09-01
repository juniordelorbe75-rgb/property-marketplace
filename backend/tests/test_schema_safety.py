import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from sqlalchemy import create_engine, inspect, text

import backend.db as database
from backend.db_models.base import Base


class SchemaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_startup_restores_performance_indexes_idempotently(self):
        expected = {
            "properties": {
                "ix_properties_created_id",
                "ix_properties_price_id",
                "ix_properties_currency_price_id",
                "ix_properties_status_listing_created",
                "ix_properties_owner_created",
                "uq_properties_owner_creation_key",
            },
            "inquiries": {
                "ix_inquiries_buyer_updated",
                "ix_inquiries_buyer_status_updated",
                "ix_inquiries_seller_status_updated",
                "ix_inquiries_property_id",
                "uq_inquiries_buyer_creation_key",
            },
            "inquiry_messages": {
                "ix_inquiry_messages_inquiry_created",
                "uq_inquiry_messages_sender_creation_key",
            },
            "favorites": {"ix_favorites_property_id"},
        }
        with self.engine.begin() as connection:
            for index_names in expected.values():
                for index_name in index_names:
                    connection.execute(text(f"DROP INDEX {index_name}"))

        with patch.object(database, "engine", self.engine):
            database.ensure_schema_safety()
            database.ensure_schema_safety()

        inspector = inspect(self.engine)
        self.assertIn(
            "token_generation",
            {column["name"] for column in inspector.get_columns("users")},
        )
        self.assertIn(
            "version",
            {column["name"] for column in inspector.get_columns("properties")},
        )
        self.assertIn(
            "updated_at",
            {column["name"] for column in inspector.get_columns("properties")},
        )
        self.assertIn(
            "currency",
            {column["name"] for column in inspector.get_columns("properties")},
        )
        self.assertIn(
            "creation_key",
            {column["name"] for column in inspector.get_columns("inquiry_messages")},
        )
        inquiry_columns = {
            column["name"] for column in inspector.get_columns("inquiries")
        }
        self.assertIn("buyer_last_read_at", inquiry_columns)
        self.assertIn("seller_last_read_at", inquiry_columns)
        for table_name, expected_names in expected.items():
            actual_names = {
                index["name"] for index in inspector.get_indexes(table_name)
            }
            self.assertTrue(expected_names.issubset(actual_names))


if __name__ == "__main__":
    unittest.main()
