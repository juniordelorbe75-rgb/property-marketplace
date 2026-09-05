import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import delete, select

from backend.auth.security import hash_password, verify_password
from backend.auth.token import create_access_token
from backend.db_models.password_reset import PasswordResetTokenDB
from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback
from backend.services.smtp_delivery import deliver_email


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
    message = EmailMessage()
    message["Subject"] = "Restablezca su contraseña de HabitaRD"
    message["From"] = os.getenv("SMTP_FROM", "no-reply@property-marketplace.local")
    message["To"] = recipient
    message.set_content(
        "Use el siguiente enlace durante los próximos 30 minutos para restablecer su contraseña. "
        "Si usted no solicitó este cambio, puede ignorar este correo.\n\n"
        f"{reset_url}"
    )

    if not deliver_email(message):
        logger.warning("Local password reset link for %s: %s", recipient, reset_url)


def request_password_reset(db, email: str) -> dict:
    user = db.scalar(select(UserDB).where(UserDB.email == email.strip().lower()))
    if user is None:
        return {"message": GENERIC_REQUEST_MESSAGE}

    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    # A new request supersedes every earlier link for this account. Removing
    # hashes instead of retaining consumed rows keeps recovery state bounded.
    db.execute(
        delete(PasswordResetTokenDB).where(
            PasswordResetTokenDB.user_id == user.id
        )
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
        delete(PasswordResetTokenDB).where(
            PasswordResetTokenDB.user_id == user.id
        )
    )
    commit_or_rollback(db)

    return {
        "message": "Password reset successfully",
        "access_token": create_access_token({"sub": str(user.id), "gen": user.token_generation}),
        "token_type": "bearer",
    }
