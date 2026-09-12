"""Property management flow tests covering creation, updates, deletion, and search."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.favorite import FavoriteDB
from backend.db_models.inquiry import InquiryDB
from backend.models import PropertyCreate, PropertyUpdate, UserCreate
from backend.repositories import property_repository
from backend.services.favorite_service import create_favorite
from backend.services.inquiry_service import create_inquiry
from backend.services.property_services import (
    create_property,
    delete_property,
    get_property_by_id,
    update_property,
)
from backend.services.user_service import create_user


class PropertyTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.email_patcher = patch("backend.services.email_verification_service._send")
        self.email_patcher.start()
        self.seller = self.make_user("Seller", "seller@example.com")
        self.buyer = self.make_user("Buyer", "buyer@example.com")

    def tearDown(self):
        self.email_patcher.stop()
        self.session.close()
        self.engine.dispose()

    def make_user(self, name, email):
        return create_user(
            self.session,
            UserCreate(name=name, email=email, password="password-123"),
        )

    def make_property(
        self,
        *,
        owner_id=None,
        title="Test House",
        status="available",
        location="Santo Domingo",
        price=250000,
    ):
        return create_property(
            self.session,
            PropertyCreate(
                title=title,
                image_url="https://example.com/house.jpg",
                price=price,
                currency="USD",
                location=location,
                property_type="House",
                bedrooms=3,
                bathrooms=2,
                status=status,
            ),
            owner_id or self.seller.id,
        )

    def update_payload(self, property_item, **overrides):
        values = {
            "title": property_item.title,
            "description": property_item.description,
            "image_url": property_item.image_url,
            "image_urls": property_item.image_urls,
            "price": property_item.price,
            "currency": property_item.currency,
            "listing_type": property_item.listing_type,
            "amenities": property_item.amenities,
            "location": property_item.location,
            "country_code": property_item.country_code,
            "province": property_item.province,
            "municipality": property_item.municipality,
            "sector": property_item.sector,
            "property_type": property_item.property_type,
            "bedrooms": property_item.bedrooms,
            "bathrooms": property_item.bathrooms,
            "square_feet": property_item.square_feet,
            "status": property_item.status,
        }
        values.update(overrides)
        return PropertyUpdate(**values)


class PropertyCreationTests(PropertyTestCase):
    def test_property_creation_sets_owner_and_version(self):
        prop = self.make_property()
        self.assertEqual(prop.owner_id, self.seller.id)
        self.assertEqual(prop.title, "Test House")
        self.assertEqual(prop.status, "available")
        self.assertEqual(prop.version, 1)

    def test_property_creation_rejects_invalid_price(self):
        for invalid_price in (0, -100, -1):
            with self.subTest(price=invalid_price), self.assertRaises(ValueError):
                PropertyCreate(
                    title="Invalid Price Home",
                    image_url="https://example.com/home.jpg",
                    price=invalid_price,
                    location="Santiago",
                    property_type="House",
                    bedrooms=2,
                )

    def test_property_creation_rejects_blank_title_and_location(self):
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="   ",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Santiago",
                property_type="House",
                bedrooms=2,
            )
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Valid Title",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="   ",
                property_type="House",
                bedrooms=2,
            )

    def test_property_creation_trims_location_without_forcing_case(self):
        prop = self.make_property(location="  santo domingo  ")
        self.assertEqual(prop.location, "santo domingo")

    def test_property_creation_rejects_invalid_property_type_and_bedrooms(self):
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Invalid Type Home",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Santiago",
                property_type="Castle",
                bedrooms=2,
            )
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Negative Beds Home",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Santiago",
                property_type="House",
                bedrooms=-1,
            )

    def test_property_creation_supports_optional_fields(self):
        prop = create_property(
            self.session,
            PropertyCreate(
                title="Full Details Home",
                image_url="https://example.com/home.jpg",
                price=350000,
                location="Santiago",
                property_type="House",
                bedrooms=4,
                bathrooms=2,
                square_feet=2500,
                description="A beautiful home with a pool",
                amenities=["Pool", "Garage", "Yard"],
            ),
            self.seller.id,
        )
        self.assertEqual(prop.bathrooms, 2)
        self.assertEqual(prop.square_feet, 2500)
        self.assertEqual(prop.description, "A beautiful home with a pool")
        self.assertEqual(prop.amenities, ["Pool", "Garage", "Yard"])


class PropertyUpdateTests(PropertyTestCase):
    def setUp(self):
        super().setUp()
        self.property = self.make_property(title="Original Home")

    def test_property_update_requires_ownership(self):
        with self.assertRaises(HTTPException) as raised:
            update_property(
                self.session,
                self.property.id,
                self.update_payload(self.property, title="Unauthorized Update"),
                self.buyer.id,
            )
        self.assertEqual(raised.exception.status_code, 403)

    def test_property_update_increments_version(self):
        original_version = self.property.version
        updated = update_property(
            self.session,
            self.property.id,
            self.update_payload(
                self.property,
                title="Updated Home",
                image_url="https://example.com/updated.jpg",
                image_urls=["https://example.com/updated.jpg"],
                price=275000,
            ),
            self.seller.id,
        )
        self.assertEqual(updated.version, original_version + 1)

    def test_property_update_validates_new_values(self):
        with self.assertRaises(ValueError):
            self.update_payload(self.property, price=0)

    def test_property_update_changes_status(self):
        updated = update_property(
            self.session,
            self.property.id,
            self.update_payload(self.property, status="unavailable"),
            self.seller.id,
        )
        self.assertEqual(updated.status, "unavailable")


class PropertySearchTests(PropertyTestCase):
    def test_available_filter_does_not_match_unavailable(self):
        available = self.make_property(title="Available Home", status="available")
        unavailable = self.make_property(title="Unavailable Home", status="unavailable")

        results = property_repository.search_properties(
            self.session,
            status="available",
        )
        ids = {item.id for item in results}
        self.assertIn(available.id, ids)
        self.assertNotIn(unavailable.id, ids)

        results = property_repository.search_properties(
            self.session,
            status="unavailable",
        )
        ids = {item.id for item in results}
        self.assertIn(unavailable.id, ids)
        self.assertNotIn(available.id, ids)


class PropertyDeletionTests(PropertyTestCase):
    def setUp(self):
        super().setUp()
        self.property = self.make_property(title="Property to Delete")
        self.favorite = create_favorite(
            self.session,
            self.property.id,
            self.buyer.id,
        )
        self.inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Is this property still available?",
        )

    def test_property_deletion_requires_ownership(self):
        with self.assertRaises(HTTPException) as raised:
            delete_property(self.session, self.property.id, self.buyer.id)
        self.assertEqual(raised.exception.status_code, 403)

    def test_property_deletion_cascades_favorites_and_inquiries(self):
        delete_property(self.session, self.property.id, self.seller.id)
        self.assertIsNone(self.session.get(FavoriteDB, self.favorite.id))
        self.assertIsNone(self.session.get(InquiryDB, self.inquiry.id))

    def test_deleted_property_cannot_be_accessed(self):
        delete_property(self.session, self.property.id, self.seller.id)
        with self.assertRaises(HTTPException) as raised:
            get_property_by_id(self.session, self.property.id)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
