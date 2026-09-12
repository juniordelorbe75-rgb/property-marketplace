import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select

from backend.db_models.account_security import SellerPhoneVerificationDB
from backend.repositories.transaction import commit_or_rollback
from backend.services.phone_delivery import check_phone_code, send_phone_code, sms_configured


def utcnow():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def request_seller_phone_verification(db, phone):
    if not sms_configured():
        raise HTTPException(503, "La validación de teléfonos de vendedores todavía no está configurada.")
    now = utcnow()
    db.execute(delete(SellerPhoneVerificationDB).where(SellerPhoneVerificationDB.expires_at <= now))
    raw = secrets.token_urlsafe(32)
    sid = send_phone_code(phone)
    db.add(SellerPhoneVerificationDB(
        token_hash=_hash(raw),
        phone_number=phone,
        verification_sid=sid,
        expires_at=now + timedelta(minutes=10),
    ))
    commit_or_rollback(db)
    return {"challenge_token": raw, "expires_in": 600, "message": "Código enviado por SMS."}


def confirm_seller_phone_verification(db, raw, code):
    challenge = db.scalar(
        select(SellerPhoneVerificationDB)
        .where(SellerPhoneVerificationDB.token_hash == _hash(raw))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        challenge is None
        or utc(challenge.expires_at) <= utcnow()
        or challenge.verified_at is not None
        or challenge.attempts >= 5
    ):
        raise HTTPException(400, "La validación del teléfono venció. Solicite un nuevo código.")
    challenge.attempts += 1
    if not check_phone_code(challenge.verification_sid, challenge.phone_number, code.strip()):
        commit_or_rollback(db)
        raise HTTPException(400, "El código SMS no es válido o ha vencido.")
    challenge.verified_at = utcnow()
    challenge.expires_at = utcnow() + timedelta(minutes=15)
    commit_or_rollback(db)
    return {"phone_verification_token": raw, "message": "Teléfono validado."}


def consume_seller_phone_verification(db, raw, phone):
    if not raw:
        raise HTTPException(400, "Valide el teléfono del vendedor antes de crear la cuenta.")
    challenge = db.scalar(
        select(SellerPhoneVerificationDB)
        .where(SellerPhoneVerificationDB.token_hash == _hash(raw))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        challenge is None
        or challenge.phone_number != phone
        or challenge.verified_at is None
        or utc(challenge.expires_at) <= utcnow()
    ):
        raise HTTPException(400, "La validación del teléfono no corresponde a este número o ya venció.")
    db.delete(challenge)
