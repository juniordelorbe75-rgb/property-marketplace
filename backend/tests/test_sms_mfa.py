import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-32-characters-long")

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.auth.security import hash_password
from backend.db_models.account_security import AccountSecurityDB, LoginChallengeDB, SellerPhoneVerificationDB
from backend.db_models.base import Base
from backend.db_models.user import UserDB
from backend.services.account_security_service import (
    begin_phone_verification,
    complete_mfa_login,
    enable_sms_mfa,
    finish_primary_auth,
    security_status,
)
from backend.services.seller_phone_verification_service import (
    confirm_seller_phone_verification,
    consume_seller_phone_verification,
    request_seller_phone_verification,
)


class SmsMfaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = UserDB(
            name="Ada Buyer",
            email="ada@example.com",
            password=hash_password("correct horse battery staple"),
            role="buyer",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @patch("backend.services.account_security_service.sms_configured", return_value=True)
    @patch("backend.services.account_security_service.check_phone_code", return_value=True)
    @patch("backend.services.account_security_service.send_phone_code", return_value="VE" + "a" * 32)
    def test_enrollment_and_login_require_the_sms_code(self, _send, _check, _configured):
        begin_phone_verification(self.db, self.user.id, "+18095550123")
        enabled = enable_sms_mfa(
            self.db, self.user.id, "correct horse battery staple", "123456"
        )

        self.assertIn("access_token", enabled)
        self.assertTrue(security_status(self.db, self.user.id)["mfa_enabled"])
        challenge = finish_primary_auth(self.db, self.user)
        self.assertTrue(challenge["mfa_required"])
        self.assertEqual(challenge["mfa_method"], "sms")
        self.assertEqual(challenge["phone_hint"], "•••• 0123")
        self.assertNotIn("access_token", challenge)

        session = complete_mfa_login(
            self.db, challenge["challenge_token"], "654321"
        )
        self.assertIn("access_token", session)
        self.assertIsNone(
            self.db.scalar(select(LoginChallengeDB).where(LoginChallengeDB.user_id == self.user.id))
        )

    @patch("backend.services.account_security_service.sms_configured", return_value=True)
    @patch("backend.services.account_security_service.check_phone_code", return_value=False)
    @patch("backend.services.account_security_service.send_phone_code", return_value="VE" + "b" * 32)
    def test_wrong_enrollment_code_does_not_enable_mfa(self, _send, _check, _configured):
        begin_phone_verification(self.db, self.user.id, "+18095550123")

        with self.assertRaises(HTTPException) as raised:
            enable_sms_mfa(
                self.db, self.user.id, "correct horse battery staple", "000000"
            )

        self.assertEqual(raised.exception.status_code, 400)
        security = self.db.get(AccountSecurityDB, self.user.id)
        self.assertFalse(security.sms_mfa_enabled)
        self.assertEqual(security.phone_attempts, 1)

    @patch("backend.services.seller_phone_verification_service.sms_configured", return_value=True)
    @patch("backend.services.seller_phone_verification_service.check_phone_code", return_value=True)
    @patch("backend.services.seller_phone_verification_service.send_phone_code", return_value="VE" + "c" * 32)
    def test_seller_phone_proof_is_confirmed_bound_and_single_use(self, _send, _check, _configured):
        challenge = request_seller_phone_verification(self.db, "+18095550123")
        proof = confirm_seller_phone_verification(
            self.db, challenge["challenge_token"], "123456"
        )
        raw = proof["phone_verification_token"]

        with self.assertRaises(HTTPException):
            consume_seller_phone_verification(self.db, raw, "+18295550123")
        consume_seller_phone_verification(self.db, raw, "+18095550123")
        self.db.commit()
        self.assertEqual(self.db.query(SellerPhoneVerificationDB).count(), 0)
        with self.assertRaises(HTTPException):
            consume_seller_phone_verification(self.db, raw, "+18095550123")


if __name__ == "__main__":
    unittest.main()
