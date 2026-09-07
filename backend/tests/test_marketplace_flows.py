"""
Favorites and inquiries flow tests covering buyer-seller interactions.
Tests verify ownership isolation, duplicate prevention, and state transitions.
"""

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
from backend.db_models.user import UserDB
from backend.models import PropertyCreate, UserCreate
from backend.services.user_service import create_user
from backend.services.property_services import create_property
from backend.services.favorite_service import (
    create_favorite,
    delete_favorite,
    get_favorites_by_user,
)
from backend.services.inquiry_service import (
    create_inquiry,
    cancel_inquiry,
    update_inquiry_status,
    reply_to_inquiry,
)


class FavoritesTests(unittest.TestCase):
    """Test favorite creation, deletion, and isolation."""

    def setUp(self):
        """Create isolated database with seller and buyers."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
        # Create users
        self.seller = create_user(
            self.session,
            UserCreate(
                name="Test Seller",
                email="seller@example.com",
                password="password-123",
            ),
        )
        self.buyer1 = create_user(
            self.session,
            UserCreate(
                name="Buyer One",
                email="buyer1@example.com",
                password="password-123",
            ),
        )
        self.buyer2 = create_user(
            self.session,
            UserCreate(
                name="Buyer Two",
                email="buyer2@example.com",
                password="password-123",
            ),
        )
        
        # Create property
        self.property = create_property(
            self.session,
            PropertyCreate(
                title="Favorite Test Home",
                image_url="https://example.com/home.jpg",
                price=250000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
            ),
            self.seller.id,
        )

    def tearDown(self):
        """Clean up session and database."""
        self.session.close()
        self.engine.dispose()

    # ============================================================================
    # Favorite Creation Tests
    # ============================================================================

    def test_buyer_can_favorite_property(self):
        """Buyer should be able to favorite a property."""
        favorite = create_favorite(
            self.session,
            self.property.id,
            self.buyer1.id,
        )

        self.assertIsNotNone(favorite.id)
        self.assertEqual(favorite.property_id, self.property.id)
        self.assertEqual(favorite.user_id, self.buyer1.id)

    def test_owner_cannot_favorite_own_property(self):
        """Seller should not be able to favorite their own property."""
        with self.assertRaises(HTTPException) as raised:
            create_favorite(
                self.session,
                self.property.id,
                self.seller.id,  # Owner trying to favorite own property
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_favorite_duplicate_is_rejected(self):
        """Second favorite of same property should be rejected."""
        create_favorite(self.session, self.property.id, self.buyer1.id)

        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, self.property.id, self.buyer1.id)

        self.assertEqual(raised.exception.status_code, 400)

    def test_favorite_nonexistent_property_fails(self):
        """Favoriting nonexistent property should fail."""
        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, 9999, self.buyer1.id)

        self.assertEqual(raised.exception.status_code, 404)

    # ============================================================================
    # Favorite Deletion Tests
    # ============================================================================

    def test_buyer_can_unfavorite_property(self):
        """Buyer should be able to delete their favorite."""
        favorite = create_favorite(
            self.session,
            self.property.id,
            self.buyer1.id,
        )

        deleted = delete_favorite(
            self.session,
            self.property.id,
            self.buyer1.id,
        )

        self.assertEqual(deleted.id, favorite.id)
        # Verify it's gone
        self.assertIsNone(self.session.get(FavoriteDB, favorite.id))

    def test_unfavorite_nonexistent_fails(self):
        """Unfavoriting property that's not favorited should fail."""
        with self.assertRaises(HTTPException) as raised:
            delete_favorite(self.session, self.property.id, self.buyer1.id)

        self.assertEqual(raised.exception.status_code, 404)

    # ============================================================================
    # Favorite Isolation Tests
    # ============================================================================

    def test_multiple_buyers_can_favorite_same_property(self):
        """Multiple buyers should be able to favorite same property."""
        fav1 = create_favorite(self.session, self.property.id, self.buyer1.id)
        fav2 = create_favorite(self.session, self.property.id, self.buyer2.id)

        self.assertNotEqual(fav1.id, fav2.id)
        self.assertEqual(fav1.property_id, fav2.property_id)

    def test_buyer_favorites_are_isolated(self):
        """Each buyer should only see their own favorites."""
        create_favorite(self.session, self.property.id, self.buyer1.id)

        # Create another property
        prop2 = create_property(
            self.session,
            PropertyCreate(
                title="Second Home",
                image_url="https://example.com/home2.jpg",
                price=300000,
                location="Orlando, Florida",
                property_type="House",
                bedrooms=4,
            ),
            self.seller.id,
        )
        create_favorite(self.session, prop2.id, self.buyer2.id)

        # Buyer1's favorites (should only have prop1)
        buyer1_favorites = get_favorites_by_user(self.session, self.buyer1.id)
        buyer1_ids = [f.property_id for f in buyer1_favorites]
        self.assertIn(self.property.id, buyer1_ids)
        self.assertNotIn(prop2.id, buyer1_ids)

        # Buyer2's favorites (should only have prop2)
        buyer2_favorites = get_favorites_by_user(self.session, self.buyer2.id)
        buyer2_ids = [f.property_id for f in buyer2_favorites]
        self.assertIn(prop2.id, buyer2_ids)
        self.assertNotIn(self.property.id, buyer2_ids)


class InquiriesTests(unittest.TestCase):
    """Test inquiry creation, status transitions, and messaging."""

    def setUp(self):
        """Create isolated database with seller, buyer, and property."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
        # Create users
        self.seller = create_user(
            self.session,
            UserCreate(
                name="Test Seller",
                email="seller@example.com",
                password="password-123",
            ),
        )
        self.buyer = create_user(
            self.session,
            UserCreate(
                name="Test Buyer",
                email="buyer@example.com",
                password="password-123",
            ),
        )
        
        # Create property
        self.property = create_property(
            self.session,
            PropertyCreate(
                title="Inquiry Test Home",
                image_url="https://example.com/home.jpg",
                price=250000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
                status="available",
            ),
            self.seller.id,
        )

    def tearDown(self):
        """Clean up session and database."""
        self.session.close()
        self.engine.dispose()

    # ============================================================================
    # Inquiry Creation Tests
    # ============================================================================

    def test_buyer_can_create_inquiry(self):
        """Buyer should be able to create inquiry about property."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Is this property still available?",
        )

        self.assertIsNotNone(inquiry.id)
        self.assertEqual(inquiry.property_id, self.property.id)
        self.assertEqual(inquiry.buyer_id, self.buyer.id)
        self.assertEqual(inquiry.seller_id, self.seller.id)
        self.assertEqual(inquiry.status, "pending")

    def test_owner_cannot_inquire_about_own_property(self):
        """Seller should not be able to inquire about own property."""
        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                self.property.id,
                self.seller.id,  # Owner trying to inquire
                "Is this available?",
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_inquiry_about_unavailable_property_fails(self):
        """Inquiry about unavailable property should fail."""
        # Mark property as unavailable
        from backend.services.property_services import update_property
        from backend.models import PropertyUpdate

        update_property(
            self.session,
            self.property.id,
            PropertyUpdate(
                title=self.property.title,
                image_url=self.property.image_url,
                price=self.property.price,
                location=self.property.location,
                property_type=self.property.property_type,
                bedrooms=self.property.bedrooms,
                status="unavailable",
                currency="USD",
            ),
            self.seller.id,
        )

        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                self.property.id,
                self.buyer.id,
                "Is this available?",
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_duplicate_pending_inquiry_is_rejected(self):
        """Second inquiry about same property should fail if first is pending."""
        create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "First inquiry",
        )

        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                self.property.id,
                self.buyer.id,
                "Duplicate inquiry",
            )

        self.assertEqual(raised.exception.status_code, 409)

    def test_inquiry_nonexistent_property_fails(self):
        """Inquiry about nonexistent property should fail."""
        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                9999,  # Nonexistent
                self.buyer.id,
                "Question?",
            )

        self.assertEqual(raised.exception.status_code, 404)

    # ============================================================================
    # Inquiry Status Transition Tests
    # ============================================================================

    def test_seller_can_accept_inquiry(self):
        """Seller should be able to accept inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Can I schedule a viewing?",
        )

        accepted = update_inquiry_status(
            self.session,
            inquiry.id,
            self.seller.id,
            "accepted",
        )

        self.assertEqual(accepted.status, "accepted")

    def test_seller_can_reject_inquiry(self):
        """Seller should be able to reject inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Are you flexible on price?",
        )

        rejected = update_inquiry_status(
            self.session,
            inquiry.id,
            self.seller.id,
            "rejected",
        )

        self.assertEqual(rejected.status, "rejected")

    def test_buyer_cannot_change_inquiry_status(self):
        """Buyer should not be able to change inquiry status."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Is this available?",
        )

        with self.assertRaises(HTTPException) as raised:
            update_inquiry_status(
                self.session,
                inquiry.id,
                self.buyer.id,  # Buyer trying to change status
                "accepted",
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_inquiry_status_transition_is_permanent(self):
        """Rejected/accepted inquiry should not revert to pending."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Question?",
        )

        update_inquiry_status(
            self.session,
            inquiry.id,
            self.seller.id,
            "rejected",
        )

        # Try to change back to pending
        with self.assertRaises(HTTPException) as raised:
            update_inquiry_status(
                self.session,
                inquiry.id,
                self.seller.id,
                "pending",
            )

        self.assertEqual(raised.exception.status_code, 400)

    # ============================================================================
    # Inquiry Cancellation Tests
    # ============================================================================

    def test_buyer_can_cancel_pending_inquiry(self):
        """Buyer should be able to cancel pending inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Initial inquiry",
        )

        cancelled = cancel_inquiry(
            self.session,
            inquiry.id,
            self.buyer.id,
        )

        self.assertEqual(cancelled.status, "cancelled")

    def test_seller_cannot_cancel_inquiry(self):
        """Seller should not be able to cancel inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Question?",
        )

        with self.assertRaises(HTTPException) as raised:
            cancel_inquiry(
                self.session,
                inquiry.id,
                self.seller.id,  # Seller trying to cancel
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_cancelled_inquiry_cannot_be_reopened(self):
        """Cancelled inquiry should not accept replies or status changes."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Question?",
        )

        cancel_inquiry(self.session, inquiry.id, self.buyer.id)

        # Try to reply to cancelled inquiry
        with self.assertRaises(HTTPException):
            reply_to_inquiry(
                self.session,
                inquiry.id,
                self.seller.id,
                "Response",
            )

    # ============================================================================
    # Inquiry Reply Tests
    # ============================================================================

    def test_seller_can_reply_to_inquiry(self):
        """Seller should be able to reply to inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Is this available?",
        )

        replied = reply_to_inquiry(
            self.session,
            inquiry.id,
            self.seller.id,
            "Yes, it is available for viewing this weekend.",
        )

        self.assertEqual(replied.reply, "Yes, it is available for viewing this weekend.")

    def test_buyer_cannot_reply_to_inquiry(self):
        """Buyer should not be able to reply to own inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Question?",
        )

        with self.assertRaises(HTTPException) as raised:
            reply_to_inquiry(
                self.session,
                inquiry.id,
                self.buyer.id,  # Buyer trying to reply
                "I should not be able to reply",
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_reply_to_rejected_inquiry_fails(self):
        """Seller should not be able to reply to rejected inquiry."""
        inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Question?",
        )

        update_inquiry_status(
            self.session,
            inquiry.id,
            self.seller.id,
            "rejected",
        )

        # Try to reply to rejected
        with self.assertRaises(HTTPException) as raised:
            reply_to_inquiry(
                self.session,
                inquiry.id,
                self.seller.id,
                "Late response",
            )

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
