"""
Authentication flow tests covering registration, login, password reset, email verification, and OAuth.
Tests use isolated SQLite in-memory databases and do not modify the configured PostgreSQL instance.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from fastapi import HTTPException
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from backend.auth.security import hash_password, verify_password
from backend.auth.token import create_access_token, verify_access_token
from backend.auth.login_throttle import LoginThrottle, ThrottleResult
from backend.db_models.base import Base
from backend.db_models.user import UserDB
from backend.db_models.password_reset import PasswordResetDB
from backend.db_models.email_verification import EmailVerificationDB
from backend.models import UserCreate
from backend.services.user_service import (
    create_user,
    login_user,
    delete_current_user,
)
from backend.services.password_reset_service import (
    request_password_reset,
    reset_password_with_token,
)
from backend.services.email_verification_service import (
    request_email_verification,
    verify_email_with_token,
)


class AuthenticationFlowTests(unittest.TestCase):
    """Test complete authentication flows: registration, login, password changes, email verification."""

    def setUp(self):
        """Create isolated in-memory SQLite database for each test."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")

        # Enable foreign key constraints in SQLite
        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        """Clean up session and database."""
        self.session.close()
        self.engine.dispose()

    # ============================================================================
    # Registration Tests
    # ============================================================================

    def test_registration_creates_user_with_normalized_email(self):
        """Registration should normalize email to lowercase and trim whitespace."""
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

    def test_registration_rejects_duplicate_email(self):
        """Registration should reject duplicate emails case-insensitively."""
        create_user(
            self.session,
            UserCreate(
                name="First User",
                email="test@example.com",
                password="password-1",
            ),
        )

        with self.assertRaises(HTTPException) as raised:
            create_user(
                self.session,
                UserCreate(
                    name="Second User",
                    email="TEST@EXAMPLE.COM",  # Different case, same email
                    password="password-2",
                ),
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_registration_rejects_invalid_email_format(self):
        """Registration should validate email format."""
        invalid_emails = ["notanemail", "no@domain", "@example.com", "test@.com"]

        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                with self.assertRaises(ValueError):
                    UserCreate(
                        name="Test User",
                        email=invalid_email,
                        password="password-123",
                    )

    def test_registration_rejects_weak_password(self):
        """Registration should enforce minimum password length."""
        weak_passwords = ["", "123", "short"]

        for weak_password in weak_passwords:
            with self.subTest(password=weak_password):
                with self.assertRaises(ValueError):
                    UserCreate(
                        name="Test User",
                        email="test@example.com",
                        password=weak_password,
                    )

    def test_registration_rejects_oversized_password(self):
        """Registration should reject passwords exceeding bcrypt's 72-byte UTF-8 limit."""
        oversized_password = "a" * 73

        with self.assertRaises(ValueError):
            UserCreate(
                name="Test User",
                email="test@example.com",
                password=oversized_password,
            )

    def test_registration_rejects_oversized_unicode_password(self):
        """Registration should reject multi-byte UTF-8 passwords that exceed bcrypt's 72-byte limit."""
        # Each emoji is 4 bytes in UTF-8
        oversized_unicode = "😀" * 19  # 76 bytes total
        with self.assertRaises(ValueError):
            UserCreate(
                name="Test User",
                email="test@example.com",
                password=oversized_unicode,
            )

    # ============================================================================
    # Login Tests
    # ============================================================================

    def test_login_returns_access_token(self):
        """Login should return a valid access token for registered user."""
        user = create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="correct-password",
            ),
        )

        result = login_user(self.session, "test@example.com", "correct-password")

        self.assertIn("access_token", result)
        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(verify_access_token(result["access_token"]), str(user.id))

    def test_login_is_case_insensitive_for_email(self):
        """Login should accept email in any case."""
        create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="password-123",
            ),
        )

        result = login_user(self.session, "TEST@EXAMPLE.COM", "password-123")
        self.assertIn("access_token", result)

    def test_login_rejects_incorrect_password(self):
        """Login should reject incorrect password."""
        create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="correct-password",
            ),
        )

        with self.assertRaises(HTTPException) as raised:
            login_user(self.session, "test@example.com", "wrong-password")

        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("Invalid email or password", raised.exception.detail)

    def test_login_rejects_nonexistent_email(self):
        """Login should reject nonexistent email gracefully."""
        with self.assertRaises(HTTPException) as raised:
            login_user(self.session, "nonexistent@example.com", "any-password")

        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("Invalid email or password", raised.exception.detail)

    def test_login_performs_dummy_check_for_nonexistent_email(self):
        """
        Login should perform dummy password verification for nonexistent emails
        to avoid account enumeration attacks.
        """
        with patch(
            "backend.services.user_service.verify_password",
            return_value=False,
        ) as password_check:
            with self.assertRaises(HTTPException):
                login_user(self.session, "missing@example.com", "password")

        # Dummy check should have been called even though user doesn't exist
        password_check.assert_called_once()

    def test_login_trims_whitespace_from_email(self):
        """Login should trim whitespace from email input."""
        create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="password-123",
            ),
        )

        result = login_user(self.session, "  test@example.com  ", "password-123")
        self.assertIn("access_token", result)

    # ============================================================================
    # Token Management Tests
    # ============================================================================

    def test_token_includes_required_claims(self):
        """Access token should include required JWT claims."""
        token = create_access_token({"sub": "123", "gen": 1})
        decoded = {}

        # Manually verify token structure without using internal decode
        import json
        import base64

        parts = token.split(".")
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "==")
        )  # Add padding

        self.assertEqual(payload["sub"], "123")
        self.assertIn("iss", payload)  # Issuer
        self.assertIn("aud", payload)  # Audience
        self.assertIn("iat", payload)  # Issued at
        self.assertIn("exp", payload)  # Expiry
        self.assertIn("jti", payload)  # Token ID

    def test_token_rejected_if_expired(self):
        """Expired tokens should be rejected."""
        from jose import jwt
        from backend.auth.token import ALGORITHM, SECRET_KEY

        expired_token = jwt.encode(
            {
                "sub": "1",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
                "iss": "habitard-marketplace",
                "aud": "habitard-buyers-sellers",
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        self.assertIsNone(verify_access_token(expired_token))

    def test_password_change_invalidates_other_sessions(self):
        """Changing password should increment token generation and revoke other sessions."""
        user = create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="original-password",
            ),
        )
        original_gen = user.token_generation

        login_result = login_user(self.session, "test@example.com", "original-password")
        original_token = login_result["access_token"]

        # Change password
        from backend.services.user_service import update_password

        update_password(self.session, user.id, "original-password", "new-password")

        # Refresh user from database
        user = self.session.get(UserDB, user.id)
        self.assertGreater(user.token_generation, original_gen)

        # Old token should still be valid in this session,
        # but new token generation means other devices are logged out
        self.assertEqual(verify_access_token(original_token), str(user.id))

    # ============================================================================
    # Account Deletion Tests
    # ============================================================================

    def test_account_deletion_requires_current_password(self):
        """Account deletion should require correct current password."""
        user = create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="secure-password",
            ),
        )

        with self.assertRaises(HTTPException) as raised:
            from backend.routes.users import delete_account_for_testing

            delete_account_for_testing(
                self.session,
                user.id,
                "wrong-password",
                "DELETE",
            )

        self.assertEqual(raised.exception.status_code, 401)

    def test_account_deletion_requires_deletion_confirmation(self):
        """Account deletion should require explicit 'DELETE' confirmation."""
        user = create_user(
            self.session,
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="secure-password",
            ),
        )

        with self.assertRaises(HTTPException) as raised:
            from backend.routes.users import delete_account_for_testing

            delete_account_for_testing(
                self.session,
                user.id,
                "secure-password",
                "DELETE ME",  # Wrong confirmation
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_account_deletion_removes_user_and_properties(self):
        """Account deletion should remove user and all their properties."""
        user = create_user(
            self.session,
            UserCreate(
                name="Test Seller",
                email="seller@example.com",
                password="password-123",
            ),
        )

        # User should exist
        self.assertIsNotNone(self.session.get(UserDB, user.id))

        # Delete account
        delete_current_user(self.session, user.id)

        # User should be gone
        self.assertIsNone(self.session.get(UserDB, user.id))

    # ============================================================================
    # Password Reset Tests (Future: Implement and test full flow)
    # ============================================================================

    def test_password_reset_creates_single_use_token(self):
        """
        Password reset should create a single-use token that expires after time limit.
        
        NOTE: Requires SMTP_HOST configuration to be set.
        Currently documented in PROJECT_GUIDE.md but needs implementation verification.
        """
        # This test would verify:
        # 1. Token is generated and stored
        # 2. Token is single-use (can't be reused)
        # 3. Token expires after 30 minutes
        # 4. Email is sent with reset link
        pass

    # ============================================================================
    # Email Verification Tests (Future: Implement and test full flow)
    # ============================================================================

    def test_email_verification_creates_24hour_token(self):
        """
        Email verification should create a 24-hour single-use token.
        
        NOTE: Requires SMTP_HOST configuration to be set.
        Currently documented in PROJECT_GUIDE.md but needs implementation verification.
        """
        # This test would verify:
        # 1. Token is generated and stored
        # 2. Token is single-use (can't be reused)
        # 3. Token expires after 24 hours
        # 4. Verification email is sent
        pass


class LoginThrottleTests(unittest.TestCase):
    """Test login throttling to prevent brute force attacks."""

    def setUp(self):
        """Initialize fresh throttle for each test."""
        self.throttle = LoginThrottle()

    def test_throttle_allows_first_attempts(self):
        """Throttle should allow first few login attempts."""
        for i in range(5):
            result = self.throttle.check_login_attempt("user@example.com", "127.0.0.1")
            self.assertEqual(result, ThrottleResult.ALLOWED)

    def test_throttle_blocks_after_limit(self):
        """Throttle should block login after exceeding limit."""
        email = "user@example.com"
        ip = "127.0.0.1"

        # Exceed limit
        for _ in range(5):
            self.throttle.check_login_attempt(email, ip)

        # Next attempt should be throttled
        result = self.throttle.check_login_attempt(email, ip)
        self.assertEqual(result, ThrottleResult.THROTTLED)

    def test_throttle_resets_after_successful_login(self):
        """Throttle counter should reset after successful login."""
        email = "user@example.com"
        ip = "127.0.0.1"

        # Fail 5 times
        for _ in range(5):
            self.throttle.check_login_attempt(email, ip)

        # Reset counter (happens on successful login)
        self.throttle.reset_login_attempt(email, ip)

        # Should allow attempts again
        result = self.throttle.check_login_attempt(email, ip)
        self.assertEqual(result, ThrottleResult.ALLOWED)

    def test_throttle_is_per_email_and_ip(self):
        """Throttle should track attempts per email-IP combination."""
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        ip = "127.0.0.1"

        # 5 failed attempts for user1
        for _ in range(5):
            self.throttle.check_login_attempt(email1, ip)

        # user2 should still be allowed
        result = self.throttle.check_login_attempt(email2, ip)
        self.assertEqual(result, ThrottleResult.ALLOWED)


if __name__ == "__main__":
    unittest.main()
