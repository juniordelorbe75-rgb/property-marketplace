import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend.models import UserCreate, UserUpdate
from backend.services.user_service import change_password, get_public_profile


class ProfileModelTests(unittest.TestCase):
    def test_structured_registration_builds_display_name(self):
        user = UserCreate(
            first_name=" Ana ",
            middle_name=" María ",
            last_name=" Pérez ",
            date_of_birth="1994-06-15",
            bio="  I help families find a home.  ",
            email="ANA@EXAMPLE.COM",
            password="password123",
        )

        self.assertEqual(user.name, "Ana María Pérez")
        self.assertEqual(user.email, "ana@example.com")
        self.assertEqual(user.bio, "I help families find a home.")

    def test_structured_profile_requires_last_name_and_birth_date(self):
        with self.assertRaises(ValidationError):
            UserUpdate(first_name="Ana", email="ana@example.com")

    def test_birth_date_cannot_be_in_the_future(self):
        with self.assertRaises(ValidationError):
            UserCreate(
                first_name="Ana",
                last_name="Pérez",
                date_of_birth=date.today() + timedelta(days=2),
                email="ana@example.com",
                password="password123",
            )

    def test_public_profile_returns_only_explicitly_shared_fields(self):
        user = SimpleNamespace(
            id=12,
            name="Ana María Pérez",
            first_name="Ana",
            email="private@example.com",
            date_of_birth=date(1994, 6, 15),
            bio="Shared biography",
            public_profile_enabled=True,
            public_name_mode="first_name",
            public_bio_visible=False,
            public_display_name="Ana",
        )
        with patch("backend.services.user_service.user_repository.get_user_by_id", return_value=user):
            profile = get_public_profile(object(), user.id)

        self.assertEqual(profile, {"id": 12, "display_name": "Ana", "bio": None})
        self.assertNotIn("email", profile)
        self.assertNotIn("date_of_birth", profile)

    def test_private_profile_is_not_discoverable(self):
        user = SimpleNamespace(public_profile_enabled=False)
        with patch("backend.services.user_service.user_repository.get_user_by_id", return_value=user):
            with self.assertRaises(HTTPException) as raised:
                get_public_profile(object(), 12)
        self.assertEqual(raised.exception.status_code, 404)

    def test_social_account_can_create_its_first_password(self):
        user = SimpleNamespace(id=12, has_password=False, password="unused", token_generation=1)
        with patch("backend.services.user_service.user_repository.get_user_by_id", return_value=user), patch("backend.services.user_service.user_repository.update_user"):
            result = change_password(object(), user.id, None, "new-password-123")
        self.assertTrue(user.has_password)
        self.assertEqual(user.token_generation, 2)
        self.assertEqual(result["message"], "Password created successfully")

    def test_password_account_still_requires_current_password(self):
        user = SimpleNamespace(id=12, has_password=True, password="stored", token_generation=1)
        with patch("backend.services.user_service.user_repository.get_user_by_id", return_value=user):
            with self.assertRaises(HTTPException) as raised:
                change_password(object(), user.id, None, "new-password-123")
        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
