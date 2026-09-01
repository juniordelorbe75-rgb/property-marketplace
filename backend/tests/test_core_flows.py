import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")


from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.auth.security import verify_password
from backend.auth.token import ALGORITHM, SECRET_KEY, verify_access_token
from backend.auth.dependencies import get_current_user_id
from backend.db_models.base import Base
from backend.db_models.favorite import FavoriteDB  # noqa: F401
from backend.db_models.inquiry import InquiryDB  # noqa: F401
from backend.db_models.property import PropertyDB  # noqa: F401
from backend.db_models.user import UserDB  # noqa: F401
from backend.models import PropertyCreate, PropertyUpdate, UserCreate
from backend.services.favorite_service import create_favorite, delete_favorite
from backend.services.inquiry_service import (
    cancel_inquiry,
    create_inquiry,
    reply_to_inquiry,
    update_inquiry_status,
)
from backend.services.property_services import (
    create_property,
    delete_property,
    update_property,
)
from backend.services.user_service import (
    create_user,
    delete_current_user,
    login_user,
)


class CoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def create_test_user(self):
        return create_user(
            self.session,
            UserCreate(
                name="  Test Seller  ",
                email="  SELLER@example.com  ",
                password="secure-password",
            ),
        )

    def create_buyer(self):
        return create_user(
            self.session,
            UserCreate(
                name="Test Buyer",
                email="buyer@example.com",
                password="buyer-password",
            ),
        )

    def create_test_property(self, owner_id):
        return create_property(
            self.session,
            PropertyCreate(
                title="Starter Home",
                image_url="https://images.example.com/starter-home.jpg",
                price=250000,
                location="miami, florida",
                property_type="House",
                bedrooms=3,
            ),
            owner_id,
        )

    def test_registration_normalizes_and_hashes_user_data(self):
        user = self.create_test_user()

        self.assertEqual(user.name, "Test Seller")
        self.assertEqual(user.email, "seller@example.com")
        self.assertEqual(user.role, "buyer")
        self.assertNotEqual(user.password, "secure-password")
        self.assertTrue(verify_password("secure-password", user.password))

    def test_login_returns_a_token_for_the_registered_user(self):
        user = self.create_test_user()

        result = login_user(
            self.session,
            "SELLER@example.com",
            "secure-password",
        )

        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(
            verify_access_token(result["access_token"]),
            str(user.id),
        )

    def test_login_rejects_incorrect_password(self):
        self.create_test_user()

        with self.assertRaises(HTTPException) as raised:
            login_user(
                self.session,
                "seller@example.com",
                "incorrect-password",
            )

        self.assertEqual(raised.exception.status_code, 401)

    def test_duplicate_registration_is_rejected_cleanly(self):
        self.create_test_user()

        with self.assertRaises(HTTPException) as raised:
            self.create_test_user()

        self.assertEqual(raised.exception.status_code, 400)

    def test_database_email_conflict_rolls_back_the_session(self):
        existing_user = self.create_test_user()

        with patch(
            "backend.services.user_service.user_repository.get_user_by_email",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as raised:
                create_user(
                    self.session,
                    UserCreate(
                        name="Conflicting User",
                        email=existing_user.email,
                        password="another-password",
                    ),
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIsNotNone(self.session.get(UserDB, existing_user.id))
        self.assertEqual(
            len(self.session.scalars(select(UserDB)).all()),
            1,
        )

    def test_malformed_and_expired_tokens_are_rejected(self):
        expired_token = jwt.encode(
            {
                "sub": "1",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        self.assertIsNone(verify_access_token("not-a-valid-token"))
        self.assertIsNone(verify_access_token(expired_token))

    def test_token_is_rejected_after_account_is_deleted(self):
        user = self.create_test_user()
        login = login_user(
            self.session,
            user.email,
            "secure-password",
        )
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=login["access_token"],
        )

        self.assertEqual(
            get_current_user_id(credentials, self.session),
            user.id,
        )

        delete_current_user(self.session, user.id)

        with self.assertRaises(HTTPException) as raised:
            get_current_user_id(credentials, self.session)

        self.assertEqual(raised.exception.status_code, 401)

    def test_authenticated_user_can_create_a_property(self):
        user = self.create_test_user()
        property_item = self.create_test_property(user.id)

        self.assertIsNotNone(property_item.id)
        self.assertEqual(property_item.owner_id, user.id)
        self.assertEqual(property_item.title, "Starter Home")
        self.assertEqual(property_item.status, "available")

    def test_buyer_can_also_create_a_property(self):
        buyer = self.create_buyer()

        property_item = self.create_test_property(buyer.id)

        self.assertEqual(property_item.owner_id, buyer.id)

    def test_favorite_cannot_be_created_twice(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)

        favorite = create_favorite(
            self.session,
            property_item.id,
            buyer.id,
        )

        self.assertEqual(favorite.user_id, buyer.id)
        self.assertEqual(favorite.property_id, property_item.id)

        with self.assertRaises(HTTPException) as raised:
            create_favorite(
                self.session,
                property_item.id,
                buyer.id,
            )

        self.assertEqual(raised.exception.status_code, 400)

        deleted = delete_favorite(
            self.session,
            property_item.id,
            buyer.id,
        )
        self.assertEqual(deleted.id, favorite.id)

    def test_database_favorite_conflict_rolls_back_the_session(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        favorite = create_favorite(
            self.session,
            property_item.id,
            buyer.id,
        )

        with patch(
            "backend.services.favorite_service.favorite_repository.get_favorites_by_user",
            return_value=[],
        ):
            with self.assertRaises(HTTPException) as raised:
                create_favorite(
                    self.session,
                    property_item.id,
                    buyer.id,
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIsNotNone(self.session.get(FavoriteDB, favorite.id))
        self.assertEqual(
            len(self.session.scalars(select(FavoriteDB)).all()),
            1,
        )

    def test_favorite_and_inquiry_commit_failures_roll_back(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        database_error = OperationalError(
            "COMMIT",
            {},
            Exception("database disconnected"),
        )

        for operation in (
            lambda: create_favorite(
                self.session,
                property_item.id,
                buyer.id,
            ),
            lambda: create_inquiry(
                self.session,
                property_item.id,
                buyer.id,
                "Will this commit?",
            ),
        ):
            with self.subTest(operation=operation):
                with patch.object(
                    self.session,
                    "commit",
                    side_effect=database_error,
                ), patch.object(
                    self.session,
                    "rollback",
                    wraps=self.session.rollback,
                ) as rollback:
                    with self.assertRaises(OperationalError):
                        operation()
                rollback.assert_called_once()

        self.assertEqual(self.session.scalars(select(FavoriteDB)).all(), [])
        self.assertEqual(self.session.scalars(select(InquiryDB)).all(), [])

    def test_account_delete_commit_failure_rolls_back_without_image_cleanup(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)
        property_item.image_urls = ["/uploads/property-images/account-kept.png"]
        self.session.commit()
        database_error = OperationalError(
            "COMMIT",
            {},
            Exception("database disconnected"),
        )

        with patch.object(
            self.session,
            "commit",
            side_effect=database_error,
        ), patch.object(
            self.session,
            "rollback",
            wraps=self.session.rollback,
        ) as rollback, patch(
            "backend.services.user_service.delete_uploaded_property_image"
        ) as delete_image:
            with self.assertRaises(OperationalError):
                delete_current_user(self.session, seller.id)

        rollback.assert_called_once()
        delete_image.assert_not_called()
        self.assertIsNotNone(self.session.get(UserDB, seller.id))
        self.assertIsNotNone(self.session.get(PropertyDB, property_item.id))

    def test_favoriting_missing_property_returns_not_found(self):
        buyer = self.create_buyer()

        with self.assertRaises(HTTPException) as raised:
            create_favorite(self.session, 9999, buyer.id)

        self.assertEqual(raised.exception.status_code, 404)

    def test_owner_cannot_favorite_their_own_property(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)

        with self.assertRaises(HTTPException) as raised:
            create_favorite(
                self.session,
                property_item.id,
                seller.id,
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_only_owner_can_update_a_property(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        update = PropertyUpdate(
            title="Updated Home",
            currency="USD",
            image_url="https://images.example.com/updated-home.jpg",
            price=275000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=4,
            status="available",
        )

        with self.assertRaises(HTTPException) as raised:
            update_property(
                self.session,
                property_item.id,
                update,
                buyer.id,
            )

        self.assertEqual(raised.exception.status_code, 403)

        updated = update_property(
            self.session,
            property_item.id,
            update,
            seller.id,
        )
        self.assertEqual(updated.title, "Updated Home")

    def test_property_commit_failure_rolls_back_without_image_cleanup(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)
        property_item.image_urls = ["/uploads/property-images/existing.png"]
        self.session.commit()
        update = PropertyUpdate(
            title="Commit Failure Home",
            currency="USD",
            image_urls=["/uploads/property-images/replacement.png"],
            price=275000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=4,
            status="available",
        )
        database_error = OperationalError(
            "COMMIT",
            {},
            Exception("database disconnected"),
        )

        with patch.object(
            self.session,
            "commit",
            side_effect=database_error,
        ), patch.object(
            self.session,
            "rollback",
            wraps=self.session.rollback,
        ) as rollback, patch(
            "backend.services.property_services.delete_uploaded_property_image"
        ) as delete_image:
            with self.assertRaises(OperationalError):
                update_property(
                    self.session,
                    property_item.id,
                    update,
                    seller.id,
                )

        rollback.assert_called_once()
        delete_image.assert_not_called()
        persisted = self.session.get(PropertyDB, property_item.id)
        self.assertEqual(persisted.title, "Starter Home")
        self.assertEqual(
            persisted.image_urls,
            ["/uploads/property-images/existing.png"],
        )

    def test_property_create_and_delete_commit_failures_roll_back(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)
        database_error = OperationalError(
            "COMMIT",
            {},
            Exception("database disconnected"),
        )

        with patch.object(
            self.session,
            "commit",
            side_effect=database_error,
        ), patch.object(
            self.session,
            "rollback",
            wraps=self.session.rollback,
        ) as rollback:
            with self.assertRaises(OperationalError):
                create_property(
                    self.session,
                    PropertyCreate(
                        title="Failed Create Home",
                        image_url="https://images.example.com/failed-home.jpg",
                        price=200000,
                        location="Tampa, Florida",
                        property_type="House",
                        bedrooms=2,
                    ),
                    seller.id,
                )
            with self.assertRaises(OperationalError):
                delete_property(
                    self.session,
                    property_item.id,
                    seller.id,
                )

        self.assertEqual(rollback.call_count, 2)
        self.assertIsNotNone(self.session.get(PropertyDB, property_item.id))

    def test_replacing_or_deleting_property_cleans_up_uploaded_image(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)
        property_item.image_urls = [
            "/uploads/property-images/old-image.png",
            "/uploads/property-images/kept-image.png",
        ]
        self.session.commit()
        update = PropertyUpdate(
            title="Updated Image Home",
            currency="USD",
            image_url="/uploads/property-images/new-image.png",
            image_urls=[
                "/uploads/property-images/new-image.png",
                "/uploads/property-images/kept-image.png",
            ],
            price=275000,
            location="Miami, Florida",
            property_type="House",
            bedrooms=4,
            status="available",
        )

        with patch(
            "backend.services.property_services.delete_uploaded_property_image"
        ) as delete_image:
            update_property(self.session, property_item.id, update, seller.id)
            delete_image.assert_called_once_with(
                "/uploads/property-images/old-image.png"
            )

            delete_property(self.session, property_item.id, seller.id)
            self.assertEqual(
                {call.args[0] for call in delete_image.call_args_list[1:]},
                {
                    "/uploads/property-images/new-image.png",
                    "/uploads/property-images/kept-image.png",
                },
            )

    def test_deleting_account_cleans_up_its_uploaded_property_images(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)
        property_item.image_urls = ["/uploads/property-images/account-image.png"]
        self.session.commit()

        with patch(
            "backend.services.user_service.delete_uploaded_property_image"
        ) as delete_image:
            delete_current_user(self.session, seller.id)

        delete_image.assert_called_once_with(
            "/uploads/property-images/account-image.png"
        )

    def test_shared_uploaded_image_is_kept_until_last_property_is_deleted(self):
        seller = self.create_test_user()
        shared_image = "/uploads/property-images/shared-image.png"
        first_property = self.create_test_property(seller.id)
        first_property.image_urls = [shared_image]
        second_property = create_property(
            self.session,
            PropertyCreate(
                title="Second Shared Image Home",
                image_urls=[shared_image],
                price=300000,
                location="Orlando, Florida",
                property_type="House",
                bedrooms=3,
            ),
            seller.id,
        )
        self.session.commit()

        with patch(
            "backend.services.property_services.delete_uploaded_property_image"
        ) as delete_image:
            delete_property(self.session, first_property.id, seller.id)
            delete_image.assert_not_called()

            delete_property(self.session, second_property.id, seller.id)
            delete_image.assert_called_once_with(shared_image)

    def test_seller_can_reply_to_and_accept_an_inquiry(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)

        inquiry = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "Is this property still available?",
        )

        replied = reply_to_inquiry(
            self.session,
            inquiry.id,
            seller.id,
            "Yes, it is available.",
        )
        accepted = update_inquiry_status(
            self.session,
            inquiry.id,
            seller.id,
            "accepted",
        )
        accepted_retry = update_inquiry_status(
            self.session,
            inquiry.id,
            seller.id,
            "accepted",
        )

        self.assertEqual(replied.reply, "Yes, it is available.")
        self.assertEqual(accepted.status, "accepted")
        self.assertEqual(accepted_retry.id, accepted.id)

        with self.assertRaises(HTTPException) as reopen_error:
            update_inquiry_status(
                self.session,
                inquiry.id,
                seller.id,
                "pending",
            )

        self.assertEqual(reopen_error.exception.status_code, 400)
        self.assertEqual(
            reopen_error.exception.detail,
            "Invalid inquiry status",
        )

    def test_buyer_cannot_reply_to_or_accept_an_inquiry(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        inquiry = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "Is this property still available?",
        )

        with self.assertRaises(HTTPException) as reply_error:
            reply_to_inquiry(
                self.session,
                inquiry.id,
                buyer.id,
                "I should not be able to reply.",
            )

        with self.assertRaises(HTTPException) as status_error:
            update_inquiry_status(
                self.session,
                inquiry.id,
                buyer.id,
                "accepted",
            )

        self.assertEqual(reply_error.exception.status_code, 403)
        self.assertEqual(status_error.exception.status_code, 403)

    def test_invalid_inquiry_status_is_rejected(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        inquiry = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "Is this property still available?",
        )

        with self.assertRaises(HTTPException) as raised:
            update_inquiry_status(
                self.session,
                inquiry.id,
                seller.id,
                "deleted",
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_rejected_inquiry_is_closed_to_status_changes_and_replies(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        inquiry = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "Is a viewing available?",
        )
        rejected = update_inquiry_status(
            self.session,
            inquiry.id,
            seller.id,
            "rejected",
        )

        with self.assertRaises(HTTPException) as update_error:
            update_inquiry_status(
                self.session,
                inquiry.id,
                seller.id,
                "accepted",
            )
        with self.assertRaises(HTTPException) as reply_error:
            reply_to_inquiry(
                self.session,
                inquiry.id,
                seller.id,
                "This should not be sent.",
            )

        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(update_error.exception.status_code, 400)
        self.assertEqual(reply_error.exception.status_code, 400)
        self.assertIsNone(rejected.reply)

    def test_only_buyer_can_cancel_a_pending_inquiry(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        inquiry = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "I would like a viewing.",
        )

        with self.assertRaises(HTTPException) as seller_error:
            cancel_inquiry(self.session, inquiry.id, seller.id)

        cancelled = cancel_inquiry(self.session, inquiry.id, buyer.id)

        self.assertEqual(seller_error.exception.status_code, 403)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertIsNotNone(cancelled.created_at)
        self.assertIsNotNone(cancelled.updated_at)

        repeated_cancel = cancel_inquiry(self.session, inquiry.id, buyer.id)
        with self.assertRaises(HTTPException) as update_error:
            update_inquiry_status(
                self.session, inquiry.id, seller.id, "accepted"
            )
        with self.assertRaises(HTTPException) as reply_error:
            reply_to_inquiry(
                self.session, inquiry.id, seller.id, "Too late."
            )

        self.assertEqual(repeated_cancel.id, cancelled.id)
        self.assertEqual(repeated_cancel.status, "cancelled")
        self.assertEqual(update_error.exception.status_code, 400)
        self.assertEqual(reply_error.exception.status_code, 400)

    def test_duplicate_pending_inquiry_is_rejected(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        first = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "My first message.",
        )

        with self.assertRaises(HTTPException) as duplicate_error:
            create_inquiry(
                self.session,
                property_item.id,
                buyer.id,
                "My accidental duplicate message.",
            )

        self.assertEqual(duplicate_error.exception.status_code, 409)
        self.assertEqual(
            duplicate_error.exception.detail,
            "You already have a pending inquiry for this property",
        )
        self.assertEqual(
            self.session.scalars(select(InquiryDB)).all(),
            [first],
        )

        cancel_inquiry(self.session, first.id, buyer.id)
        second = create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "A new inquiry after cancellation.",
        )
        self.assertEqual(second.status, "pending")

    def test_owner_cannot_inquire_about_their_own_property(self):
        seller = self.create_test_user()
        property_item = self.create_test_property(seller.id)

        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                property_item.id,
                seller.id,
                "Can I inquire about my own listing?",
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_unavailable_property_rejects_new_inquiry(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        property_item.status = "unavailable"
        self.session.commit()

        with self.assertRaises(HTTPException) as raised:
            create_inquiry(
                self.session,
                property_item.id,
                buyer.id,
                "Please let me know when this becomes available.",
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(
            raised.exception.detail,
            "This property is not available for inquiries",
        )

    def test_deleting_property_cleans_up_favorites_and_inquiries(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        create_favorite(self.session, property_item.id, buyer.id)
        create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "I am interested in this property.",
        )

        delete_property(
            self.session,
            property_item.id,
            seller.id,
        )

        self.assertEqual(self.session.scalars(select(FavoriteDB)).all(), [])
        self.assertEqual(self.session.scalars(select(InquiryDB)).all(), [])

    def test_deleting_account_cleans_up_related_marketplace_data(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        create_favorite(self.session, property_item.id, buyer.id)
        create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "I am interested in this property.",
        )

        delete_current_user(self.session, seller.id)

        self.assertIsNone(self.session.get(UserDB, seller.id))
        self.assertIsNotNone(self.session.get(UserDB, buyer.id))
        self.assertEqual(self.session.scalars(select(PropertyDB)).all(), [])
        self.assertEqual(self.session.scalars(select(FavoriteDB)).all(), [])
        self.assertEqual(self.session.scalars(select(InquiryDB)).all(), [])

    def test_deleting_buyer_keeps_listing_and_removes_buyer_activity(self):
        seller = self.create_test_user()
        buyer = self.create_buyer()
        property_item = self.create_test_property(seller.id)
        create_favorite(self.session, property_item.id, buyer.id)
        create_inquiry(
            self.session,
            property_item.id,
            buyer.id,
            "I am interested in this property.",
        )

        delete_current_user(self.session, buyer.id)

        self.assertIsNone(self.session.get(UserDB, buyer.id))
        self.assertIsNotNone(self.session.get(UserDB, seller.id))
        self.assertIsNotNone(self.session.get(PropertyDB, property_item.id))
        self.assertEqual(self.session.scalars(select(FavoriteDB)).all(), [])
        self.assertEqual(self.session.scalars(select(InquiryDB)).all(), [])


if __name__ == "__main__":
    unittest.main()
