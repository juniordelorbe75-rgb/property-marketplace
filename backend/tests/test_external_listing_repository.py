import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.external_listing import ExternalListingDB, ListingFeedAuditDB, ListingSourceDB
from backend.feed_models import ListingFeedBatch
from backend.repositories.external_listing_repository import (
    count_public_external_listings,
    get_public_external_listings,
    import_feed_batch,
    set_source_approval,
    withdraw_stale_listings,
)
from backend.routes.catalog import admin_sources


def feed_batch(records=None):
    now = datetime.now(timezone.utc)
    return ListingFeedBatch.model_validate({
        "source": {
            "source_key": "provider-one",
            "name": "Provider One",
            "country_code": "DO",
            "license_name": "Publisher agreement",
            "license_url": "https://provider.example/agreement",
            "attribution": "Courtesy of Provider One",
            "permits_commercial_display": True,
        },
        "retrieved_at": now,
        "records": records if records is not None else [{
            "external_id": "A-100",
            "source_url": "https://provider.example/A-100",
            "title": "Punta Cana Condo",
            "listing_type": "sale",
            "status": "active",
            "price": 250000,
            "currency": "USD",
            "country_code": "DO",
            "province": "La Altagracia",
            "municipality": "Higüey",
            "sector": "Punta Cana",
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 2,
            "area_sqm": 95,
            "image_urls": ["https://provider.example/A-100.jpg"],
            "updated_at": now,
        }],
    })


class ExternalListingRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_import_is_private_until_source_is_approved(self):
        result = import_feed_batch(self.session, feed_batch())
        self.assertEqual(result, {"created": 1, "updated": 0, "withdrawn": 0})
        self.assertEqual(get_public_external_listings(self.session), [])

    def test_approved_refresh_publishes_and_missing_record_withdraws(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )

        refresh = import_feed_batch(self.session, feed_batch())
        public = get_public_external_listings(self.session)
        withdrawal = import_feed_batch(
            self.session,
            feed_batch(records=[]),
            allow_empty_snapshot=True,
        )
        stored = self.session.scalar(select(ExternalListingDB))

        self.assertEqual(refresh["updated"], 1)
        self.assertEqual([item.external_id for item in public], ["A-100"])
        self.assertEqual(withdrawal["withdrawn"], 1)
        self.assertEqual(stored.status, "withdrawn")
        self.assertFalse(stored.is_public)

    def test_same_source_identity_never_creates_a_duplicate(self):
        import_feed_batch(self.session, feed_batch())
        result = import_feed_batch(self.session, feed_batch())
        self.assertEqual(result["created"], 0)
        self.assertEqual(self.session.query(ExternalListingDB).count(), 1)

    def test_duplicate_snapshot_is_rejected_without_partial_changes(self):
        batch = feed_batch()
        duplicate = batch.records[0].model_copy(update={"title": "Conflicting copy"})
        batch.records.append(duplicate)

        with self.assertRaisesRegex(ValueError, "duplicate"):
            import_feed_batch(self.session, batch)

        self.assertEqual(self.session.query(ExternalListingDB).count(), 0)
        self.assertEqual(self.session.query(ListingFeedAuditDB).count(), 0)

    def test_unexpected_empty_snapshot_preserves_existing_catalog(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session,
            source,
            approved=True,
            actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, feed_batch())

        with self.assertRaisesRegex(ValueError, "explicit confirmation"):
            import_feed_batch(self.session, feed_batch(records=[]))

        stored = self.session.scalar(select(ExternalListingDB))
        self.assertEqual(stored.status, "active")
        self.assertTrue(stored.is_public)

    def test_older_snapshot_cannot_overwrite_newer_provider_data(self):
        latest = feed_batch()
        import_feed_batch(self.session, latest)
        older = feed_batch()
        older.retrieved_at = latest.retrieved_at.replace(year=latest.retrieved_at.year - 1)
        older.records[0].title = "Stale title"

        with self.assertRaisesRegex(ValueError, "older"):
            import_feed_batch(self.session, older)

        stored = self.session.scalar(select(ExternalListingDB))
        self.assertEqual(stored.title, "Punta Cana Condo")

    def test_public_catalog_filters_authorized_inventory(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, feed_batch())

        matches = get_public_external_listings(
            self.session,
            location="Altagracia",
            currency="USD",
            bedrooms=2,
            min_price=200000,
            max_price=300000,
        )
        misses = get_public_external_listings(self.session, location="Santiago")

        self.assertEqual([item.external_id for item in matches], ["A-100"])
        self.assertEqual(misses, [])
        self.assertEqual(count_public_external_listings(self.session, location="Punta Cana"), 1)

    def test_approval_and_imports_create_audit_events(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, feed_batch())

        events = self.session.scalars(
            select(ListingFeedAuditDB).order_by(ListingFeedAuditDB.id)
        ).all()
        self.assertEqual(
            [event.event_type for event in events],
            ["feed_imported", "source_approved", "feed_imported"],
        )
        self.assertEqual(events[1].actor_user_id, 42)

    def test_admin_source_oversight_reports_inventory_and_latest_event(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, feed_batch())

        overview = admin_sources(_admin_user_id=42, session=self.session)

        self.assertEqual(len(overview), 1)
        self.assertEqual(overview[0]["total_listings"], 1)
        self.assertEqual(overview[0]["public_listings"], 1)
        self.assertEqual(overview[0]["latest_event_type"], "feed_imported")
        self.assertIsNotNone(overview[0]["latest_event_at"])

    def test_revoking_permission_immediately_unpublishes_inventory(self):
        import_feed_batch(self.session, feed_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, feed_batch())
        self.assertEqual(len(get_public_external_listings(self.session)), 1)

        set_source_approval(self.session, source, approved=False, actor_user_id=42)
        self.assertEqual(get_public_external_listings(self.session), [])

    def test_stale_feed_is_unpublished_without_deleting_audit_history(self):
        old_batch = feed_batch()
        old_batch.retrieved_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        for record in old_batch.records:
            record.updated_at = old_batch.retrieved_at
        import_feed_batch(self.session, old_batch)
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session, source, approved=True, actor_user_id=42,
            permission_document_url="https://provider.example/signed-agreement",
            stale_after_hours=24,
        )
        import_feed_batch(self.session, old_batch)

        withdrawn = withdraw_stale_listings(
            self.session, datetime(2020, 1, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(withdrawn, 1)
        self.assertEqual(get_public_external_listings(self.session), [])


if __name__ == "__main__":
    unittest.main()
