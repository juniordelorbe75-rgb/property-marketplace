import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")
os.environ.setdefault("PROPERTY_IMAGE_STORAGE", "local")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.db_models.base import Base
from backend.db_models.user import UserDB
from backend.models import PropertyCreate, PropertyUpdate
from backend.services.property_services import create_property, update_property


class PropertyImageOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.owner = UserDB(
            name="Owner",
            email="image-owner@example.com",
            password=hash_password("password-123"),
            email_verified=True,
            role="buyer",
        )
        self.other = UserDB(
            name="Other User",
            email="other-image-owner@example.com",
            password=hash_password("password-123"),
            email_verified=True,
            role="buyer",
        )
        self.session.add_all([self.owner, self.other])
        self.session.commit()
        self.session.refresh(self.owner)
        self.session.refresh(self.other)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def payload(self, image_url):
        return PropertyCreate(
            title="Image Ownership Home",
            image_url=image_url,
            price=250000,
            currency="USD",
            location="Santiago",
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            status="available",
        )

    def test_owner_can_attach_own_managed_upload(self):
        image_url = f"/uploads/property-images/{self.owner.id}_abc123.jpg"
        listing = create_property(self.session, self.payload(image_url), self.owner.id)
        self.assertEqual(listing.image_url, image_url)

    def test_user_cannot_attach_another_accounts_managed_upload(self):
        image_url = f"/uploads/property-images/{self.other.id}_abc123.jpg"
        with self.assertRaises(HTTPException) as raised:
            create_property(self.session, self.payload(image_url), self.owner.id)
        self.assertEqual(raised.exception.status_code, 403)

    def test_malformed_managed_upload_name_is_rejected(self):
        image_url = "/uploads/property-images/not-owned.jpg"
        with self.assertRaises(HTTPException) as raised:
            create_property(self.session, self.payload(image_url), self.owner.id)
        self.assertEqual(raised.exception.status_code, 403)

    def test_external_image_url_is_not_treated_as_managed_upload(self):
        image_url = "https://images.example.com/listing.jpg"
        listing = create_property(self.session, self.payload(image_url), self.owner.id)
        self.assertEqual(listing.image_url, image_url)

    def test_update_cannot_add_another_accounts_managed_upload(self):
        own_image = f"/uploads/property-images/{self.owner.id}_original.jpg"
        listing = create_property(self.session, self.payload(own_image), self.owner.id)
        stolen_image = f"/uploads/property-images/{self.other.id}_stolen.jpg"

        update = PropertyUpdate(
            title=listing.title,
            description=listing.description,
            image_url=own_image,
            image_urls=[own_image, stolen_image],
            price=listing.price,
            currency=listing.currency,
            listing_type=listing.listing_type,
            amenities=listing.amenities,
            location=listing.location,
            country_code=listing.country_code,
            province=listing.province,
            municipality=listing.municipality,
            sector=listing.sector,
            property_type=listing.property_type,
            bedrooms=listing.bedrooms,
            bathrooms=listing.bathrooms,
            square_feet=listing.square_feet,
            status=listing.status,
        )

        with self.assertRaises(HTTPException) as raised:
            update_property(self.session, listing.id, update, self.owner.id)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
