import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.external_listing import ExternalListingDB, ListingSourceDB
from backend.integrations.reppingdr_sync import sync_reppingdr
from backend.repositories.external_listing_repository import set_source_approval


class ReppingDRSyncTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.source = ListingSourceDB(
            source_key="reppingdr", name="ReppingDR", country_code="DO",
            license_name="Written agreement",
            license_url="https://agreements.example/reppingdr",
            attribution="Courtesy of ReppingDR",
        )
        self.session.add(self.source)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_sync_refuses_unapproved_source_before_network_access(self):
        called = False

        def fetcher(_url, _key):
            nonlocal called
            called = True
            return {}

        with self.assertRaises(PermissionError):
            sync_reppingdr(self.session, self.source, fetch_json=fetcher, api_key="secret")
        self.assertFalse(called)

    def test_sync_paginates_and_imports_full_snapshot(self):
        set_source_approval(
            self.session, self.source, approved=True, actor_user_id=7,
            permission_document_url="https://agreements.example/reppingdr-signed",
        )
        calls = []

        def fetcher(url, key):
            calls.append((url, key))
            if url.endswith("/zones"):
                return {"zones": [{
                    "id": "punta-cana", "name": "Punta Cana",
                    "nameEs": "Punta Cana", "province": "La Altagracia",
                }]}
            page = "2" if "page=2" in url else "1"
            return {
                "properties": [{
                    "id": f"property-{page}", "title": f"Property {page}",
                    "slug": f"property-{page}", "price": 100000 + int(page),
                    "currency": "USD", "type": "condo", "status": "available",
                    "zone": "punta-cana",
                }],
                "hasMore": page == "1",
            }

        result = sync_reppingdr(
            self.session, self.source, fetch_json=fetcher, api_key="server-secret"
        )
        listings = self.session.scalars(
            select(ExternalListingDB).order_by(ExternalListingDB.external_id)
        ).all()

        self.assertEqual(result, {"created": 2, "updated": 0, "withdrawn": 0})
        self.assertEqual([item.external_id for item in listings], ["property-1", "property-2"])
        self.assertTrue(all(item.is_public for item in listings))
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(key == "server-secret" for _url, key in calls))

    def test_sync_does_not_withdraw_inventory_on_unexpected_empty_response(self):
        set_source_approval(
            self.session, self.source, approved=True, actor_user_id=7,
            permission_document_url="https://agreements.example/reppingdr-signed",
        )

        def initial_fetcher(url, _key):
            if url.endswith("/zones"):
                return {"zones": [{
                    "id": "punta-cana", "name": "Punta Cana",
                    "nameEs": "Punta Cana", "province": "La Altagracia",
                }]}
            return {
                "properties": [{
                    "id": "property-1", "title": "Property 1",
                    "slug": "property-1", "price": 100001,
                    "currency": "USD", "type": "condo", "status": "available",
                    "zone": "punta-cana",
                }],
                "hasMore": False,
            }

        sync_reppingdr(self.session, self.source, fetch_json=initial_fetcher, api_key="secret")

        def empty_fetcher(url, _key):
            if url.endswith("/zones"):
                return {"zones": [{
                    "id": "punta-cana", "name": "Punta Cana",
                    "nameEs": "Punta Cana", "province": "La Altagracia",
                }]}
            return {"properties": [], "hasMore": False}

        with self.assertRaisesRegex(ValueError, "explicit confirmation"):
            sync_reppingdr(self.session, self.source, fetch_json=empty_fetcher, api_key="secret")

        stored = self.session.scalar(select(ExternalListingDB))
        self.assertEqual(stored.status, "active")
        self.assertTrue(stored.is_public)


if __name__ == "__main__":
    unittest.main()
