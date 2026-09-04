import hashlib
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select, update

from backend.auth.security import hash_password, verify_password
from backend.auth.token import create_access_token
from backend.db_models.password_reset import PasswordResetTokenDB
from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback


logger = logging.getLogger(__name__)
RESET_TOKEN_LIFETIME_MINUTES = 30
GENERIC_REQUEST_MESSAGE = (
    "If an account exists for that email, password reset instructions have been sent."
)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _reset_url(token: str) -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
    return f"{frontend_url}/reset-password?token={quote(token, safe='')}"


def send_password_reset_email(recipient: str, token: str) -> None:
    reset_url = _reset_url(token)
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if not smtp_host:
        logger.warning("Local password reset link for %s: %s", recipient, reset_url)
        return

    message = EmailMessage()
    message["Subject"] = "Reset your Property Marketplace password"
    message["From"] = os.getenv("SMTP_FROM", "no-reply@property-marketplace.local")
    message["To"] = recipient
    message.set_content(
        "Use the link below within 30 minutes to reset your password. "
        "If you did not request this, you can ignore this email.\n\n"
        f"{reset_url}"
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    with smtplib.SMTP(smtp_host, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def request_password_reset(db, email: str) -> dict:
    user = db.scalar(select(UserDB).where(UserDB.email == email.strip().lower()))
    if user is None:
        return {"message": GENERIC_REQUEST_MESSAGE}

    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    db.execute(
        update(PasswordResetTokenDB)
        .where(
            PasswordResetTokenDB.user_id == user.id,
            PasswordResetTokenDB.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.add(PasswordResetTokenDB(
        user_id=user.id,
        token_hash=_token_hash(raw_token),
        created_at=now,
        expires_at=now + timedelta(minutes=RESET_TOKEN_LIFETIME_MINUTES),
    ))
    commit_or_rollback(db)

    try:
        send_password_reset_email(user.email, raw_token)
    except Exception:
        logger.exception("Password reset email delivery failed for user_id=%s", user.id)

    return {"message": GENERIC_REQUEST_MESSAGE}


def reset_password(db, token: str, new_password: str) -> dict:
    now = datetime.now(timezone.utc)
    reset_record = db.scalar(
        select(PasswordResetTokenDB)
        .where(PasswordResetTokenDB.token_hash == _token_hash(token))
        .with_for_update()
    )
    if (
        reset_record is None
        or reset_record.used_at is not None
        or _utc(reset_record.expires_at) <= now
    ):
        raise HTTPException(status_code=400, detail="This password reset link is invalid or expired")

    user = db.scalar(select(UserDB).where(UserDB.id == reset_record.user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or expired")
    if user.has_password and verify_password(new_password, user.password):
        raise HTTPException(status_code=400, detail="Choose a password you have not already used")

    user.password = hash_password(new_password)
    user.has_password = True
    user.token_generation += 1
    db.execute(
        update(PasswordResetTokenDB)
        .where(
            PasswordResetTokenDB.user_id == user.id,
            PasswordResetTokenDB.used_at.is_(None),
        )
        .values(used_at=now)
    )
    commit_or_rollback(db)

    return {
        "message": "Password reset successfully",
        "access_token": create_access_token({"sub": str(user.id), "gen": user.token_generation}),
        "token_type": "bearer",
    }
