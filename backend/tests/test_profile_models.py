import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from backend.models import UserCreate, UserUpdate


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


if __name__ == "__main__":
    unittest.main()
