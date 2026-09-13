import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.external_listing import ListingSourceDB
from backend.feed_models import ListingFeedBatch
from backend.repositories.external_listing_repository import (
    get_public_external_listings,
    import_feed_batch,
    set_source_approval,
)


def build_batch():
    now = datetime.now(timezone.utc)
    common = {
        "listing_type": "sale",
        "status": "active",
        "currency": "USD",
        "country_code": "DO",
        "province": "Santiago",
        "municipality": "Santiago de los Caballeros",
        "sector": "Centro",
        "property_type": "Condo",
        "bedrooms": 2,
        "bathrooms": 2,
        "area_sqm": 100,
        "updated_at": now,
    }
    return ListingFeedBatch.model_validate({
        "source": {
            "source_key": "search-provider",
            "name": "Search Provider",
            "country_code": "DO",
            "license_name": "Publisher agreement",
            "license_url": "https://provider.example/agreement",
            "attribution": "Courtesy of Search Provider",
            "permits_commercial_display": True,
        },
        "retrieved_at": now,
        "records": [
            {
                **common,
                "external_id": "LOW",
                "source_url": "https://provider.example/low",
                "title": "Lower Price Pool Condo",
                "price": 150000,
                "amenities": ["Pool", "Gym"],
                "image_urls": ["https://provider.example/low.jpg"],
            },
            {
                **common,
                "external_id": "HIGH",
                "source_url": "https://provider.example/high",
                "title": "Higher Price Condo",
                "price": 300000,
                "amenities": ["Garage"],
                "image_urls": ["https://provider.example/high.jpg"],
            },
        ],
    })


class ExternalCatalogSearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        import_feed_batch(self.session, build_batch())
        source = self.session.scalar(select(ListingSourceDB))
        set_source_approval(
            self.session,
            source,
            approved=True,
            actor_user_id=1,
            permission_document_url="https://provider.example/signed-agreement",
        )
        import_feed_batch(self.session, build_batch())

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_amenity_filter_matches_partner_inventory(self):
        pool = get_public_external_listings(self.session, amenity="Pool")
        garage = get_public_external_listings(self.session, amenity="Garage")

        self.assertEqual([item.external_id for item in pool], ["LOW"])
        self.assertEqual([item.external_id for item in garage], ["HIGH"])

    def test_price_sorting_matches_native_search_options(self):
        low_first = get_public_external_listings(
            self.session,
            currency="USD",
            sort_by="price_low",
        )
        high_first = get_public_external_listings(
            self.session,
            currency="USD",
            sort_by="price_high",
        )

        self.assertEqual([item.external_id for item in low_first], ["LOW", "HIGH"])
        self.assertEqual([item.external_id for item in high_first], ["HIGH", "LOW"])


if __name__ == "__main__":
    unittest.main()
