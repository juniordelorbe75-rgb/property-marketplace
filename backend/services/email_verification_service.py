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

from backend.db_models.email_verification import EmailVerificationTokenDB
from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback

logger = logging.getLogger(__name__)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _send(recipient, token):
    url = f"{os.getenv('FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')}/verify-email?token={quote(token, safe='')}"
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        logger.warning("Local email verification link for %s: %s", recipient, url)
        return
    message = EmailMessage()
    message["Subject"] = "Verify your Property Marketplace email"
    message["From"] = os.getenv("SMTP_FROM", "no-reply@property-marketplace.local")
    message["To"] = recipient
    message.set_content(f"Verify your email within 24 hours:\n\n{url}")
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as smtp:
        if os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}:
            smtp.starttls()
        if os.getenv("SMTP_USERNAME"):
            smtp.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(message)


def issue_email_verification(db, user):
    if user.email_verified:
        return {"message": "Email is already verified"}
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    db.execute(update(EmailVerificationTokenDB).where(
        EmailVerificationTokenDB.user_id == user.id,
        EmailVerificationTokenDB.used_at.is_(None),
    ).values(used_at=now))
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
    record.used_at = now
    commit_or_rollback(db)
    return {"message": "Email verified successfully"}
