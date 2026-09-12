"""Authentication flow tests for HabitaRD's current auth implementation."""

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from backend.auth.login_throttle import (
    clear_login_failures,
    login_retry_after,
    record_login_failure,
    reset_login_throttle,
)
from backend.auth.security import verify_password
from backend.auth.token import create_access_token, decode_access_token, verify_access_token
from backend.db_models.base import Base
from backend.db_models.user import UserDB
from backend.models import UserCreate
from backend.services.email_verification_service import verify_email
from backend.services.password_reset_service import request_password_reset, reset_password
from backend.services.user_service import (
    change_password,
    create_user,
    delete_current_user,
    login_user,
)


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.verification_tokens = []
        self.verification_patcher = patch(
            "backend.services.email_verification_service._send",
            side_effect=lambda _recipient, token: self.verification_tokens.append(token),
        )
        self.verification_patcher.start()

    def tearDown(self):
        self.verification_patcher.stop()
        self.session.close()
        self.engine.dispose()

    def make_user(self, email="test@example.com", password="password-123"):
        return create_user(
            self.session,
            UserCreate(name="Test User", email=email, password=password),
        )

    def test_registration_creates_user_with_normalized_email(self):
        user = create_user(
            self.session,
            UserCreate(
                name="Jane Smith",
                email="  JANE.SMITH@EXAMPLE.COM  ",
                password="secure-password-123",
            ),
        )
        self.assertEqual(user.email, "jane.smith@example.com")
        self.assertEqual(user.name, "Jane Smith")
        self.assertTrue(verify_password("secure-password-123", user.password))
        self.assertFalse(user.email_verified)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        self.make_user("test@example.com")
        with self.assertRaises(HTTPException) as raised:
            self.make_user("TEST@EXAMPLE.COM")
        self.assertEqual(raised.exception.status_code, 400)

    def test_registration_validates_email_and_password(self):
        for invalid_email in ("notanemail", "no@domain", "@example.com", "test@.com"):
            with self.subTest(email=invalid_email), self.assertRaises(ValueError):
                UserCreate(name="Test User", email=invalid_email, password="password-123")

        for invalid_password in ("", "123", "short"):
            with self.subTest(password=invalid_password), self.assertRaises(ValueError):
                UserCreate(name="Test User", email="test@example.com", password=invalid_password)

        with self.assertRaises(ValueError):
            UserCreate(name="Test User", email="test@example.com", password="a" * 73)
        with self.assertRaises(ValueError):
            UserCreate(name="Test User", email="test@example.com", password="😀" * 19)

    def test_login_returns_access_token(self):
        user = self.make_user()
        result = login_user(self.session, "TEST@EXAMPLE.COM", "password-123")
        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(verify_access_token(result["access_token"]), str(user.id))
        payload = decode_access_token(result["access_token"])
        self.assertEqual(payload["gen"], user.token_generation)

    def test_login_rejects_wrong_or_unknown_credentials(self):
        self.make_user()
        for email, password in (
            ("test@example.com", "wrong-password"),
            ("missing@example.com", "password-123"),
        ):
            with self.subTest(email=email), self.assertRaises(HTTPException) as raised:
                login_user(self.session, email, password)
            self.assertEqual(raised.exception.status_code, 401)
            self.assertEqual(raised.exception.detail, "Invalid email or password")

    def test_login_performs_dummy_password_check_for_unknown_email(self):
        with patch(
            "backend.services.user_service.verify_password",
            return_value=False,
        ) as password_check:
            with self.assertRaises(HTTPException):
                login_user(self.session, "missing@example.com", "password")
        password_check.assert_called_once()

    def test_token_includes_required_claims(self):
        token = create_access_token({"sub": "123", "gen": 1})
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "123")
        for claim in ("iss", "aud", "iat", "exp", "jti", "token_type"):
            self.assertIn(claim, payload)

    def test_password_change_rotates_token_generation(self):
        user = self.make_user(password="original-password")
        old_token = login_user(
            self.session, "test@example.com", "original-password"
        )["access_token"]
        old_generation = user.token_generation

        result = change_password(
            self.session,
            user.id,
            "original-password",
            "new-password-123",
        )
        self.session.refresh(user)

        self.assertEqual(user.token_generation, old_generation + 1)
        self.assertEqual(decode_access_token(old_token)["gen"], old_generation)
        self.assertEqual(
            decode_access_token(result["access_token"])["gen"],
            user.token_generation,
        )
        self.assertTrue(verify_password("new-password-123", user.password))

    def test_account_deletion_requires_correct_password(self):
        user = self.make_user(password="secure-password")
        with self.assertRaises(HTTPException) as raised:
            delete_current_user(
                self.session,
                user.id,
                current_password="wrong-password",
            )
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIsNotNone(self.session.get(UserDB, user.id))

        delete_current_user(
            self.session,
            user.id,
            current_password="secure-password",
        )
        self.assertIsNone(self.session.get(UserDB, user.id))

    def test_password_reset_is_single_use_and_rotates_sessions(self):
        user = self.make_user(password="old-password-123")
        original_generation = user.token_generation
        sent_tokens = []

        with patch(
            "backend.services.password_reset_service.send_password_reset_email",
            side_effect=lambda _recipient, token: sent_tokens.append(token),
        ):
            response = request_password_reset(self.session, user.email)

        self.assertIn("message", response)
        self.assertEqual(len(sent_tokens), 1)
        token = sent_tokens[0]

        reset_result = reset_password(
            self.session,
            token,
            "new-password-456",
        )
        self.session.refresh(user)
        self.assertEqual(user.token_generation, original_generation + 1)
        self.assertIn("access_token", reset_result)
        self.assertTrue(verify_password("new-password-456", user.password))

        with self.assertRaises(HTTPException) as raised:
            reset_password(self.session, token, "another-password-789")
        self.assertEqual(raised.exception.status_code, 400)

    def test_email_verification_is_single_use(self):
        user = self.make_user("verify@example.com")
        self.assertEqual(len(self.verification_tokens), 1)
        token = self.verification_tokens[0]

        result = verify_email(self.session, token)
        self.session.refresh(user)
        self.assertTrue(user.email_verified)
        self.assertEqual(result["message"], "Email verified successfully")

        with self.assertRaises(HTTPException) as raised:
            verify_email(self.session, token)
        self.assertEqual(raised.exception.status_code, 400)


class LoginThrottleTests(unittest.TestCase):
    def setUp(self):
        reset_login_throttle()

    def tearDown(self):
        reset_login_throttle()

    def test_throttle_blocks_pair_after_five_failures(self):
        email = "user@example.com"
        address = "127.0.0.1"
        self.assertIsNone(login_retry_after(address, email))
        for _ in range(5):
            record_login_failure(address, email)
        self.assertIsNotNone(login_retry_after(address, email))

    def test_successful_login_clear_removes_pair_and_account_failure_state(self):
        email = "user@example.com"
        address = "127.0.0.1"
        for _ in range(5):
            record_login_failure(address, email)
        self.assertIsNotNone(login_retry_after(address, email))
        clear_login_failures(address, email)
        self.assertIsNone(login_retry_after(address, email))

    def test_failures_for_one_account_do_not_immediately_block_another(self):
        address = "127.0.0.1"
        for _ in range(5):
            record_login_failure(address, "first@example.com")
        self.assertIsNotNone(login_retry_after(address, "first@example.com"))
        self.assertIsNone(login_retry_after(address, "second@example.com"))


if __name__ == "__main__":
    unittest.main()
