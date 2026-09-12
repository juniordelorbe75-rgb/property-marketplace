from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.db_models.base import Base


class AccountSecurityDB(Base):
    __tablename__ = "account_security"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    verified_phone: Mapped[str] = mapped_column(String(25), default="", server_default="")
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_phone: Mapped[str | None] = mapped_column(String(25))
    phone_verification_sid: Mapped[str | None] = mapped_column(String(34))
    phone_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_window_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_send_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    phone_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sms_mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sms_mfa_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_mfa_window_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_mfa_send_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mfa_secret: Mapped[str | None] = mapped_column(Text)
    mfa_pending_secret: Mapped[str | None] = mapped_column(Text)
    mfa_pending_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_pending_generation: Mapped[int | None] = mapped_column(Integer)
    mfa_setup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_setup_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mfa_last_counter: Mapped[int] = mapped_column(Integer, default=-1, server_default="-1")
    mfa_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mfa_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_hashes: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")


class LoginChallengeDB(Base):
    __tablename__ = "login_challenges"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    generation: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verification_sid: Mapped[str | None] = mapped_column(String(34))
    phone_number: Mapped[str | None] = mapped_column(String(25))


class SellerPhoneVerificationDB(Base):
    __tablename__ = "seller_phone_verifications"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(25), index=True)
    verification_sid: Mapped[str] = mapped_column(String(34))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
