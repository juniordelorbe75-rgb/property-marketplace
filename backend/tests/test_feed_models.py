import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.feed_models import ListingFeedBatch


def valid_batch():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "source": {
            "source_key": "licensed-broker",
            "name": "Licensed Broker Feed",
            "country_code": "do",
            "license_name": "Commercial display agreement",
            "license_url": "https://broker.example/license",
            "attribution": "Listing courtesy of Licensed Broker",
            "permits_commercial_display": True,
        },
        "retrieved_at": now,
        "records": [{
            "external_id": "listing-42",
            "source_url": "https://broker.example/listings/42",
            "title": "Apartment in Piantini",
            "listing_type": "sale",
            "status": "active",
            "price": 18500000,
            "currency": "dop",
            "country_code": "do",
            "province": "distrito nacional",
            "municipality": " Santo  Domingo ",
            "sector": "Piantini",
            "property_type": "Apartment",
            "bedrooms": 3,
            "bathrooms": 2.5,
            "area_sqm": 180,
            "image_urls": ["https://broker.example/images/42.jpg"],
            "updated_at": now,
        }],
    }


class ListingFeedContractTests(unittest.TestCase):
    def test_accepts_normalized_licensed_dominican_feed(self):
        batch = ListingFeedBatch.model_validate(valid_batch())
        listing = batch.records[0]
        self.assertEqual(batch.source.country_code, "DO")
        self.assertEqual(listing.currency, "DOP")
        self.assertEqual(listing.province, "Distrito Nacional")
        self.assertEqual(listing.municipality, "Santo Domingo")

    def test_rejects_source_without_commercial_display_rights(self):
        payload = valid_batch()
        payload["source"]["permits_commercial_display"] = False
        with self.assertRaises(ValidationError):
            ListingFeedBatch.model_validate(payload)

    def test_rejects_duplicate_source_identity(self):
        payload = valid_batch()
        payload["records"].append(dict(payload["records"][0]))
        with self.assertRaises(ValidationError):
            ListingFeedBatch.model_validate(payload)

    def test_rejects_insecure_listing_or_image_urls(self):
        payload = valid_batch()
        payload["records"][0]["source_url"] = "http://broker.example/listings/42"
        with self.assertRaises(ValidationError):
            ListingFeedBatch.model_validate(payload)
