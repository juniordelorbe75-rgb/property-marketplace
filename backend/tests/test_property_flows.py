"""
Property management flow tests covering creation, updates, deletion, and search.
Tests verify ownership enforcement, version control, and cascade cleanup.
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
from backend.db_models.property import PropertyDB
from backend.db_models.favorite import FavoriteDB
from backend.db_models.inquiry import InquiryDB
from backend.db_models.user import UserDB
from backend.models import PropertyCreate, PropertyUpdate, UserCreate
from backend.services.user_service import create_user
from backend.services.property_services import (
    create_property,
    update_property,
    delete_property,
    get_property_by_id,
)


class PropertyCreationTests(unittest.TestCase):
    """Test property creation with validation and ownership."""

    def setUp(self):
        """Create isolated in-memory SQLite database."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
        # Create a test user (seller)
        self.seller = create_user(
            self.session,
            UserCreate(
                name="Test Seller",
                email="seller@example.com",
                password="password-123",
            ),
        )

    def tearDown(self):
        """Clean up session and database."""
        self.session.close()
        self.engine.dispose()

    # ============================================================================
    # Property Creation Tests
    # ============================================================================

    def test_property_creation_sets_owner(self):
        """Property creation should set the current user as owner."""
        prop = create_property(
            self.session,
            PropertyCreate(
                title="Test House",
                image_url="https://example.com/house.jpg",
                price=250000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
            ),
            self.seller.id,
        )

        self.assertEqual(prop.owner_id, self.seller.id)
        self.assertEqual(prop.title, "Test House")
        self.assertEqual(prop.status, "available")

    def test_property_creation_rejects_invalid_price(self):
        """Property creation should reject zero or negative prices."""
        invalid_prices = [0, -100, -1]

        for invalid_price in invalid_prices:
            with self.subTest(price=invalid_price):
                with self.assertRaises(ValueError):
                    PropertyCreate(
                        title="Invalid Price Home",
                        image_url="https://example.com/home.jpg",
                        price=invalid_price,
                        location="Miami, Florida",
                        property_type="House",
                        bedrooms=2,
                    )

    def test_property_creation_rejects_empty_title(self):
        """Property creation should reject empty or whitespace-only titles."""
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="   ",  # Whitespace only
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=2,
            )

    def test_property_creation_rejects_empty_location(self):
        """Property creation should reject empty or whitespace-only locations."""
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Valid Title",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="   ",  # Whitespace only
                property_type="House",
                bedrooms=2,
            )

    def test_property_creation_normalizes_location(self):
        """Property creation should normalize location text (trim, case)."""
        prop = create_property(
            self.session,
            PropertyCreate(
                title="Location Test",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="  miami, florida  ",  # Extra spaces
                property_type="House",
                bedrooms=2,
            ),
            self.seller.id,
        )

        self.assertEqual(prop.location, "Miami, Florida")

    def test_property_creation_rejects_invalid_property_type(self):
        """Property creation should reject invalid property types."""
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Invalid Type Home",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Miami, Florida",
                property_type="Castle",  # Not a valid type
                bedrooms=2,
            )

    def test_property_creation_rejects_negative_bedrooms(self):
        """Property creation should reject negative bedroom counts."""
        with self.assertRaises(ValueError):
            PropertyCreate(
                title="Negative Beds Home",
                image_url="https://example.com/home.jpg",
                price=100000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=-1,
            )

    def test_property_creation_supports_optional_fields(self):
        """Property creation should accept optional fields like description, bathrooms."""
        prop = create_property(
            self.session,
            PropertyCreate(
                title="Full Details Home",
                image_url="https://example.com/home.jpg",
                price=350000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=4,
                bathrooms=2,
                square_feet=2500,
                description="A beautiful home with a pool",
                amenities=["Pool", "Garage", "Garden"],
            ),
            self.seller.id,
        )

        self.assertEqual(prop.bathrooms, 2)
        self.assertEqual(prop.square_feet, 2500)
        self.assertEqual(prop.description, "A beautiful home with a pool")
        self.assertIn("Pool", prop.amenities)

    def test_property_creation_assigns_version_one(self):
        """Property creation should assign version 1."""
        prop = create_property(
            self.session,
            PropertyCreate(
                title="Versioned Home",
                image_url="https://example.com/home.jpg",
                price=200000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
            ),
            self.seller.id,
        )

        self.assertEqual(prop.version, 1)


class PropertyUpdateTests(unittest.TestCase):
    """Test property updates with version control and ownership enforcement."""

    def setUp(self):
        """Create isolated database with test seller and property."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
        # Create test seller and buyer
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
        
        # Create a test property
        self.property = create_property(
            self.session,
            PropertyCreate(
                title="Original Home",
                image_url="https://example.com/home.jpg",
                price=200000,
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

    def test_property_update_requires_ownership(self):
        """Only the owner can update a property."""
        update = PropertyUpdate(
            title="Unauthorized Update",
            image_url="https://example.com/home.jpg",
            price=250000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=3,
            status="available",
            currency="USD",
        )

        with self.assertRaises(HTTPException) as raised:
            update_property(
                self.session,
                self.property.id,
                update,
                self.buyer.id,  # Different user
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_property_update_increments_version(self):
        """Property update should increment version number."""
        original_version = self.property.version
        
        update = PropertyUpdate(
            title="Updated Home",
            image_url="https://example.com/updated.jpg",
            price=275000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=3,
            status="available",
            currency="USD",
        )

        updated = update_property(
            self.session,
            self.property.id,
            update,
            self.seller.id,
        )

        self.assertEqual(updated.version, original_version + 1)

    def test_property_update_validates_new_values(self):
        """Property update should validate all new values."""
        with self.assertRaises(ValueError):
            PropertyUpdate(
                title="Valid Title",
                image_url="https://example.com/home.jpg",
                price=0,  # Invalid: zero price
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
                status="available",
                currency="USD",
            )

    def test_property_update_changes_status(self):
        """Property status can be updated between available/unavailable."""
        update = PropertyUpdate(
            title="Original Home",
            image_url="https://example.com/home.jpg",
            price=200000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=3,
            status="unavailable",  # Changed status
            currency="USD",
        )

        updated = update_property(
            self.session,
            self.property.id,
            update,
            self.seller.id,
        )

        self.assertEqual(updated.status, "unavailable")


class PropertyDeletionTests(unittest.TestCase):
    """Test property deletion with cascade cleanup of favorites and inquiries."""

    def setUp(self):
        """Create database with seller, buyer, property, favorite, and inquiry."""
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
                title="Property to Delete",
                image_url="https://example.com/home.jpg",
                price=200000,
                location="Miami, Florida",
                property_type="House",
                bedrooms=3,
            ),
            self.seller.id,
        )
        
        # Create favorite (buyer favorites the property)
        from backend.services.favorite_service import create_favorite
        self.favorite = create_favorite(self.session, self.property.id, self.buyer.id)
        
        # Create inquiry (buyer inquires about property)
        from backend.services.inquiry_service import create_inquiry
        self.inquiry = create_inquiry(
            self.session,
            self.property.id,
            self.buyer.id,
            "Is this property still available?",
        )

    def tearDown(self):
        """Clean up session and database."""
        self.session.close()
        self.engine.dispose()

    def test_property_deletion_requires_ownership(self):
        """Only owner can delete a property."""
        with self.assertRaises(HTTPException) as raised:
            delete_property(self.session, self.property.id, self.buyer.id)

        self.assertEqual(raised.exception.status_code, 403)

    def test_property_deletion_removes_favorites(self):
        """Deleting property should cascade-delete associated favorites."""
        # Verify favorite exists
        self.assertIsNotNone(self.session.get(FavoriteDB, self.favorite.id))

        # Delete property
        delete_property(self.session, self.property.id, self.seller.id)

        # Favorite should be gone
        self.assertIsNone(self.session.get(FavoriteDB, self.favorite.id))

    def test_property_deletion_removes_inquiries(self):
        """Deleting property should cascade-delete associated inquiries."""
        # Verify inquiry exists
        self.assertIsNotNone(self.session.get(InquiryDB, self.inquiry.id))

        # Delete property
        delete_property(self.session, self.property.id, self.seller.id)

        # Inquiry should be gone
        self.assertIsNone(self.session.get(InquiryDB, self.inquiry.id))

    def test_property_deletion_is_permanent(self):
        """Deleted property cannot be accessed."""
        delete_property(self.session, self.property.id, self.seller.id)

        with self.assertRaises(HTTPException) as raised:
            get_property_by_id(self.session, self.property.id)

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
