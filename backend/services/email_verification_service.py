import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import delete, select

from backend.db_models.email_verification import EmailVerificationTokenDB
from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback
from backend.services.smtp_delivery import deliver_email

logger = logging.getLogger(__name__)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _send(recipient, token):
    url = f"{os.getenv('FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')}/verify-email?token={quote(token, safe='')}"
    message = EmailMessage()
    message["Subject"] = "Verifique su correo electrónico de HabitaRD"
    message["From"] = os.getenv("SMTP_FROM", "no-reply@property-marketplace.local")
    message["To"] = recipient
    message.set_content(f"Verifique su correo electrónico durante las próximas 24 horas:\n\n{url}")
    if not deliver_email(message):
        logger.warning("Local email verification link for %s: %s", recipient, url)


def issue_email_verification(db, user):
    if user.email_verified:
        return {"message": "Email is already verified"}
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    # Keep only the newest verification link for an account and avoid retaining
    # obsolete token hashes indefinitely.
    db.execute(delete(EmailVerificationTokenDB).where(
        EmailVerificationTokenDB.user_id == user.id,
    ))
    db.add(EmailVerificationTokenDB(user_id=user.id, token_hash=_hash(token), expires_at=now + timedelta(hours=24)))
    commit_or_rollback(db)
    try:
        _send(user.email, token)
    except Exception:
        logger.exception("Email verification delivery failed for user_id=%s", user.id)
    return {"message": "Verification instructions have been sent"}


def verify_email(db, token):
    now = datetime.now(timezone.utc)
    record = db.scalar(select(EmailVerificationTokenDB).where(
        EmailVerificationTokenDB.token_hash == _hash(token)
    ).with_for_update())
    expires = record.expires_at if record and record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc) if record else now
    if not record or record.used_at is not None or expires <= now:
        raise HTTPException(400, "This verification link is invalid or expired")
    user = db.get(UserDB, record.user_id)
    if not user:
        raise HTTPException(400, "This verification link is invalid or expired")
    user.email_verified = True
    db.execute(delete(EmailVerificationTokenDB).where(
        EmailVerificationTokenDB.user_id == user.id,
    ))
    commit_or_rollback(db)
    return {"message": "Email verified successfully"}
