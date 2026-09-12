import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_verified_user_id
from backend.config import email_verification_required
from backend.db_models.base import Base
from backend.db_models.user import UserDB


class VerifiedEmailGateTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.user = UserDB(
            name="Verification User",
            email="verification-gate@example.com",
            password="test-hash",
            email_verified=False,
            role="buyer",
        )
        self.session.add(self.user)
        self.session.commit()
        self.session.refresh(self.user)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_development_does_not_require_verification_by_default(self):
        with patch.dict(
            os.environ,
            {"APP_ENV": "development", "REQUIRE_EMAIL_VERIFICATION": ""},
            clear=False,
        ):
            self.assertFalse(email_verification_required())
            self.assertEqual(
                get_current_verified_user_id(self.user.id, self.session),
                self.user.id,
            )

    def test_production_requires_verification_by_default(self):
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "REQUIRE_EMAIL_VERIFICATION": ""},
            clear=False,
        ):
            self.assertTrue(email_verification_required())
            with self.assertRaises(HTTPException) as raised:
                get_current_verified_user_id(self.user.id, self.session)

        self.assertEqual(raised.exception.status_code, 403)
        self.assertIn("Verify your email", raised.exception.detail)

    def test_development_can_opt_into_production_verification_behavior(self):
        with patch.dict(
            os.environ,
            {"APP_ENV": "development", "REQUIRE_EMAIL_VERIFICATION": "true"},
            clear=False,
        ):
            with self.assertRaises(HTTPException) as raised:
                get_current_verified_user_id(self.user.id, self.session)

        self.assertEqual(raised.exception.status_code, 403)

    def test_verified_user_passes_when_gate_is_enabled(self):
        self.user.email_verified = True
        self.session.commit()

        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "REQUIRE_EMAIL_VERIFICATION": "true"},
            clear=False,
        ):
            self.assertEqual(
                get_current_verified_user_id(self.user.id, self.session),
                self.user.id,
            )


if __name__ == "__main__":
    unittest.main()
