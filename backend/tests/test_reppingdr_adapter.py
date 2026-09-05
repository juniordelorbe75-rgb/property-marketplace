import unittest
from datetime import datetime, timezone

from backend.integrations.reppingdr import build_reppingdr_batch


class ReppingDRAdapterTests(unittest.TestCase):
    def setUp(self):
        self.retrieved_at = datetime.now(timezone.utc)
        self.properties = {"properties": [{
            "id": "abc123",
            "publicId": "RDR-00142",
            "title": "Two-bedroom condo",
            "slug": "two-bedroom-condo-punta-cana",
            "price": 185000,
            "currency": "USD",
            "type": "condo",
            "status": "available",
            "bedrooms": 2,
            "bathrooms": 2,
            "sqm": 95,
            "zone": "punta-cana",
            "images": ["https://storage.example/abc123/1.jpg"],
            "amenities": ["pool", "gym", "pool"],
            "aiDescription": "A well-located property.",
        }]}
        self.zones = {"zones": [{
            "id": "punta-cana",
            "name": "Punta Cana",
            "nameEs": "Punta Cana",
            "province": "La Altagracia",
        }]}

    def test_refuses_to_transform_data_without_written_permission(self):
        with self.assertRaises(PermissionError):
            build_reppingdr_batch(
                self.properties, self.zones, self.retrieved_at,
                "https://agreements.example/reppingdr", permission_approved=False,
            )

    def test_maps_documented_api_fields_into_feed_contract(self):
        batch = build_reppingdr_batch(
            self.properties, self.zones, self.retrieved_at,
            "https://agreements.example/reppingdr", permission_approved=True,
        )
        record = batch.records[0]
        self.assertEqual(record.external_id, "abc123")
        self.assertEqual(record.status, "active")
        self.assertEqual(record.province, "La Altagracia")
        self.assertEqual(record.municipality, "Punta Cana")
        self.assertEqual(record.amenities, ["pool", "gym"])
        self.assertEqual(record.source_url, "https://www.reppingdr.com/properties/two-bedroom-condo-punta-cana")


if __name__ == "__main__":
    unittest.main()
