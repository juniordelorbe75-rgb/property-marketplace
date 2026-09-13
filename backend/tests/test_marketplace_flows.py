"""Favorites and inquiry flow tests for the current marketplace services."""

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
from backend.models import PropertyCreate, PropertyUpdate, UserCreate
from backend.services.favorite_service import (
    create_favorite,
    delete_favorite,
    get_my_favorites,
)
from backend.services.inquiry_service import (
    cancel_inquiry,
    create_inquiry,
    reply_to_inquiry,
    update_inquiry_status,
)
from backend.services.property_services import create_property, update_property
from backend.services.user_service import create_user


class MarketplaceTestCase(unittest.TestCase):
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
        self.other_buyer = self.make_user("Other Buyer", "other@example.com")
        self.property = self.make_property(self.seller.id)

    def tearDown(self):
        self.email_patcher.stop()
        self.session.close()
        self.engine.dispose()

    def make_user(self, name, email):
        return create_user(
            self.session,
            UserCreate(name=name, email=email, password="password-123"),
        )

    def make_property(self, owner_id, *, title="Test Home", status="available"):
        return create_property(
            self.session,
            PropertyCreate(
                title=title,
                image_url="https://example.com/home.jpg",
                price=250000,
                currency="USD",
                location="Santo Domingo",
                property_type="House",
                bedrooms=3,
                bathrooms=2,
                status=status,
            ),
            owner_id,
        )


class FavoritesTests(MarketplaceTestCase):
    def test_buyer_can_favorite_and_unfavorite_property(self):
        favorite = create_favorite(
            self.session,
            self.property.id,
            self.buyer.id,
        )
        self.assertIsNotNone(favorite.id)
        self.assertEqual(favorite.property_id, self.property.id)
        self.assertEqual(favorite.user_id, self.buyer.id)

        deleted = delete_favorite(
            self.session,
            self.property.id,
            self.buyer.id,
        )
        self.assertEqual(deleted.id, favorite.id)
        self.assertIsNone(self.session.get(FavoriteDB, favorite.id))

    def test_owner_cannot_favorite_own_property(self):
        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, self.property.id, self.seller.id)
        self.assertEqual(raised.exception.status_code, 400)

    def test_duplicate_favorite_is_rejected(self):
        create_favorite(self.session, self.property.id, self.buyer.id)
        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, self.property.id, self.buyer.id)
        self.assertEqual(raised.exception.status_code, 400)

    def test_nonexistent_property_cannot_be_favorited(self):
        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, 999999, self.buyer.id)
        self.assertEqual(raised.exception.status_code, 404)

    def test_favorites_are_isolated_by_user(self):
        create_favorite(self.session, self.property.id, self.buyer.id)
        second_property = self.make_property(
            self.seller.id,
            title="Second Home",
        )
        create_favorite(self.session, second_property.id, self.other_buyer.id)

        buyer_ids = {
            item.property_id
            for item in get_my_favorites(self.session, self.buyer.id)
        }
        other_ids = {
            item.property_id
            for item in get_my_favorites(self.session, self.other_buyer.id)
        }
        self.assertEqual(buyer_ids, {self.property.id})
        self.assertEqual(other_ids, {second_property.id})

    def test_multiple_buyers_can_favorite_same_property(self):
        first = create_favorite(self.session, self.property.id, self.buyer.id)
        second = create_favorite(
            self.session,
            self.property.id,
            self.other_buyer.id,
        )
        self.assertNotEqual(first.id, second.id)


class InquiryTests(MarketplaceTestCase):
    def create_test_inquiry(self, message="Is this still available?"):
        return create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            message,
        )

    def test_buyer_can_create_inquiry(self):
        inquiry = self.create_test_inquiry()
        self.assertIsNotNone(inquiry.id)
        self.assertEqual(inquiry.property_id, self.property.id)
        self.assertEqual(inquiry.buyer_id, self.buyer.id)
        self.assertEqual(inquiry.seller_id, self.seller.id)
        self.assertEqual(inquiry.status, "pending")

    def test_owner_cannot_inquire_about_own_property(self):
        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                self.property.id,
                self.seller.id,
                "Question",
            )
        self.assertEqual(raised.exception.status_code, 400)

    def test_inquiry_about_unavailable_property_is_rejected(self):
        update_property(
            self.session,
            self.property.id,
            PropertyUpdate(
                title=self.property.title,
                description=self.property.description,
                image_url=self.property.image_url,
                image_urls=self.property.image_urls,
                price=self.property.price,
                currency=self.property.currency,
                listing_type=self.property.listing_type,
                amenities=self.property.amenities,
                location=self.property.location,
                country_code=self.property.country_code,
                province=self.property.province,
                municipality=self.property.municipality,
                sector=self.property.sector,
                property_type=self.property.property_type,
                bedrooms=self.property.bedrooms,
                bathrooms=self.property.bathrooms,
                square_feet=self.property.square_feet,
                status="unavailable",
            ),
            self.seller.id,
        )

        with self.assertRaises(HTTPException) as raised:
            self.create_test_inquiry()
        self.assertEqual(raised.exception.status_code, 400)

    def test_duplicate_pending_inquiry_is_rejected(self):
        self.create_test_inquiry("First")
        with self.assertRaises(HTTPException) as raised:
            self.create_test_inquiry("Second")
        self.assertEqual(raised.exception.status_code, 409)

    def test_nonexistent_property_inquiry_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                999999,
                self.buyer.id,
                "Question",
            )
        self.assertEqual(raised.exception.status_code, 404)

    def test_seller_can_accept_or_reject_pending_inquiry(self):
        accepted = self.create_test_inquiry("Viewing?")
        result = update_inquiry_status(
            self.session,
            accepted.id,
            self.seller.id,
            "accepted",
        )
        self.assertEqual(result.status, "accepted")

        second_property = self.make_property(self.seller.id, title="Another Home")
        rejected = create_inquiry(
            self.session,
            second_property.id,
            self.buyer.id,
            "Price?",
        )
        result = update_inquiry_status(
            self.session,
            rejected.id,
            self.seller.id,
            "rejected",
        )
        self.assertEqual(result.status, "rejected")

    def test_buyer_cannot_change_inquiry_status(self):
        inquiry = self.create_test_inquiry()
        with self.assertRaises(HTTPException) as raised:
            update_inquiry_status(
                self.session,
                inquiry.id,
                self.buyer.id,
                "accepted",
            )
        self.assertEqual(raised.exception.status_code, 403)

    def test_buyer_can_cancel_pending_inquiry(self):
        inquiry = self.create_test_inquiry()
        result = cancel_inquiry(
            self.session,
            inquiry.id,
            self.buyer.id,
        )
        self.assertEqual(result.status, "cancelled")

        with self.assertRaises(HTTPException):
            reply_to_inquiry(
                self.session,
                inquiry.id,
                self.seller.id,
                "Late response",
            )

    def test_seller_can_reply_and_buyer_cannot_use_seller_reply(self):
        inquiry = self.create_test_inquiry()
        replied = reply_to_inquiry(
            self.session,
            inquiry.id,
            self.seller.id,
            "Yes, it is available.",
        )
        self.assertEqual(replied.reply, "Yes, it is available.")

        with self.assertRaises(HTTPException) as raised:
            reply_to_inquiry(
                self.session,
                inquiry.id,
                self.buyer.id,
                "Buyer cannot use seller reply endpoint",
            )
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
