import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.external_listing import ExternalListingDB, ListingSourceDB
from backend.feed_models import ListingFeedBatch
from backend.repositories.external_listing_repository import (
    count_public_external_listings,
    get_public_external_listings,
    import_feed_batch,
    set_source_approval,
)


def feed_batch():
    now = datetime.now(timezone.utc)
    return ListingFeedBatch.model_validate({
        "source": {
            "source_key": "permission-runtime-provider",
            "name": "Permission Runtime Provider",
            "country_code": "DO",
            "license_name": "Publisher agreement",
            "license_url": "https://provider.example/agreement",
            "attribution": "Courtesy of Permission Runtime Provider",
            "permits_commercial_display": True,
        },
        "retrieved_at": now,
        "records": [{
            "external_id": "P-100",
            "source_url": "https://provider.example/P-100",
            "title": "Authorized Condo",
            "listing_type": "sale",
            "status": "active",
            "price": 200000,
            "currency": "USD",
            "country_code": "DO",
            "province": "Santiago",
            "municipality": "Santiago de los Caballeros",
            "sector": "Centro",
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 2,
            "area_sqm": 90,
            "image_urls": ["https://provider.example/P-100.jpg"],
            "updated_at": now,
        }],
    })


class ExternalPermissionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_expired_permission_is_hidden_even_before_cleanup_job_runs(self):
        batch = feed_batch()
        import_feed_batch(self.session, batch)
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session,
            source,
            approved=True,
            actor_user_id=1,
            permission_document_url="https://provider.example/signed-agreement",
            permission_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        import_feed_batch(self.session, feed_batch())

        self.assertEqual(len(get_public_external_listings(self.session)), 1)
        self.assertEqual(count_public_external_listings(self.session), 1)

        source.permission_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.session.commit()

        stored = self.session.scalar(select(ExternalListingDB))
        self.assertTrue(stored.is_public)
        self.assertEqual(get_public_external_listings(self.session), [])
        self.assertEqual(count_public_external_listings(self.session), 0)


if __name__ == "__main__":
    unittest.main()
