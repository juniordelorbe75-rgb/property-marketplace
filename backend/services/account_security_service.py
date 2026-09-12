import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import delete, or_, select

from backend.auth.security import verify_password
from backend.auth.token import create_access_token
from backend.db_models.account_security import AccountSecurityDB, LoginChallengeDB
from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback
from backend.services.phone_delivery import check_phone_code, send_phone_code, sms_configured


def utcnow():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def _cipher():
    try:
        return Fernet(os.getenv("MFA_ENCRYPTION_KEY", "").encode())
    except (ValueError, TypeError):
        raise HTTPException(503, "La verificación en dos pasos todavía no está configurada.") from None


def mfa_configured():
    try:
        _cipher()
        return True
    except HTTPException:
        return False


def _secret(encrypted):
    try:
        return _cipher().decrypt(encrypted.encode()).decode()
    except (InvalidToken, ValueError, AttributeError):
        raise HTTPException(503, "No pudimos validar el segundo paso. Contacte al soporte.") from None


def _locked(db, user_id, create=True):
    user = db.scalar(select(UserDB).where(UserDB.id == user_id).with_for_update().execution_options(populate_existing=True))
    if user is None:
        raise HTTPException(401, "User account no longer exists")
    security = db.scalar(select(AccountSecurityDB).where(AccountSecurityDB.user_id == user_id).execution_options(populate_existing=True))
    if security is None and create:
        security = AccountSecurityDB(user_id=user_id)
        db.add(security)
        db.flush()
    return user, security


def _password(user, password):
    if not user.has_password:
        raise HTTPException(400, "Primero cree una contraseña en Mi cuenta.")
    if not verify_password(password, user.password):
        raise HTTPException(400, "Current password is incorrect")


def _access(user):
    return {"access_token": create_access_token({"sub": str(user.id), "gen": user.token_generation}), "token_type": "bearer"}


def _unblocked(security):
    if security.mfa_blocked_until and utc(security.mfa_blocked_until) > utcnow():
        raise HTTPException(429, "Demasiados códigos incorrectos. Espere cinco minutos.", headers={"Retry-After": "300"})


def _bad_code(db, security):
    security.mfa_failures += 1
    if security.mfa_failures >= 5:
        security.mfa_blocked_until = utcnow() + timedelta(minutes=5)
        security.mfa_failures = 0
    commit_or_rollback(db)
    raise HTTPException(400, "El código no es válido, ya fue utilizado o ha vencido.")


def _matching_counter(encrypted, code, last=-1):
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    totp = pyotp.TOTP(_secret(encrypted))
    current = int(utcnow().timestamp()) // 30
    for counter in (current, current - 1, current + 1):
        if counter > last and secrets.compare_digest(totp.at(counter * 30), code):
            return counter
    return None


def _recovery_hash(user_id, code):
    normalized = code.replace("-", "").replace(" ", "").lower()
    return hmac.new(os.environ["MFA_ENCRYPTION_KEY"].encode(), f"recovery:{user_id}:{normalized}".encode(), hashlib.sha256).hexdigest()


def _new_recovery_codes(security):
    raw = [secrets.token_hex(10) for _ in range(10)]
    security.recovery_hashes = json.dumps([_recovery_hash(security.user_id, value) for value in raw])
    return ["-".join(value[index:index + 5] for index in range(0, 20, 5)) for value in raw]


def _consume_code(db, security, code):
    _unblocked(security)
    counter = _matching_counter(security.mfa_secret, code.strip(), security.mfa_last_counter)
    if counter is not None:
        security.mfa_last_counter = counter
    else:
        hashes = json.loads(security.recovery_hashes)
        candidate = _recovery_hash(security.user_id, code)
        matched = next((value for value in hashes if hmac.compare_digest(value, candidate)), None)
        if matched is None:
            _bad_code(db, security)
        hashes.remove(matched)
        security.recovery_hashes = json.dumps(hashes)
    security.mfa_failures = 0
    security.mfa_blocked_until = None


def security_status(db, user_id):
    user = db.get(UserDB, user_id)
    security = db.get(AccountSecurityDB, user_id)
    phone = (
        security.verified_phone
        if security and security.sms_mfa_enabled and security.verified_phone
        else user.seller_phone if user.account_type == "seller"
        else security.verified_phone if security
        else ""
    )
    pending = security.pending_phone if security and security.phone_expires_at and utc(security.phone_expires_at) > utcnow() else None
    return {
        "email_verified": user.email_verified,
        "phone_number": phone,
        "phone_verified": bool(phone and security and security.verified_phone == phone and security.phone_verified_at),
        "pending_phone": pending,
        "sms_available": sms_configured(),
        "mfa_available": sms_configured() or mfa_configured(),
        "mfa_enabled": bool(security and (security.sms_mfa_enabled or security.mfa_secret)),
        "mfa_method": "sms" if security and security.sms_mfa_enabled else ("authenticator" if security and security.mfa_secret else None),
        "has_password": user.has_password,
    }


def begin_phone_verification(db, user_id, phone):
    if not sms_configured():
        raise HTTPException(503, "La verificación por SMS todavía no está configurada.")
    user, security = _locked(db, user_id)
    if user.account_type == "seller" and phone != user.seller_phone:
        raise HTTPException(400, "Actualice primero el teléfono de vendedor en Editar perfil.")
    now = utcnow()
    if security.phone_sent_at and utc(security.phone_sent_at) > now - timedelta(seconds=60):
        raise HTTPException(429, "Espere un minuto antes de solicitar otro SMS.", headers={"Retry-After": "60"})
    if not security.phone_window_at or utc(security.phone_window_at) <= now - timedelta(hours=1):
        security.phone_window_at, security.phone_send_count = now, 0
    if security.phone_send_count >= 5:
        raise HTTPException(429, "Alcanzó el límite de SMS. Intente de nuevo en una hora.")
    security.phone_sent_at = now
    security.phone_send_count += 1
    security.pending_phone = security.phone_verification_sid = None
    try:
        sid = send_phone_code(phone)
    except HTTPException:
        commit_or_rollback(db)
        raise
    security.pending_phone = phone
    security.phone_verification_sid = sid
    security.phone_expires_at = now + timedelta(minutes=10)
    security.phone_attempts = 0
    commit_or_rollback(db)
    return {"message": "Código enviado por SMS.", "pending_phone": phone}


def confirm_phone_verification(db, user_id, code):
    user, security = _locked(db, user_id)
    if not security.pending_phone or not security.phone_expires_at or utc(security.phone_expires_at) <= utcnow() or security.phone_attempts >= 5:
        raise HTTPException(400, "Solicite un nuevo código de verificación por SMS.")
    if user.account_type == "seller" and security.pending_phone != user.seller_phone:
        raise HTTPException(400, "El teléfono cambió. Solicite un código para el número actual.")
    security.phone_attempts += 1
    try:
        approved = check_phone_code(security.phone_verification_sid, security.pending_phone, code)
    except HTTPException:
        commit_or_rollback(db)
        raise
    if not approved:
        commit_or_rollback(db)
        raise HTTPException(400, "El código SMS no es válido o ha vencido.")
    security.verified_phone = security.pending_phone
    security.phone_verified_at = utcnow()
    security.pending_phone = security.phone_verification_sid = None
    commit_or_rollback(db)
    return {"message": "Teléfono verificado."}


def enable_sms_mfa(db, user_id, password, code):
    """Approve the pending phone verification and make it the login factor."""
    if not sms_configured():
        raise HTTPException(503, "La verificación por SMS todavía no está configurada.")
    user, security = _locked(db, user_id)
    _password(user, password)
    if security.sms_mfa_enabled:
        raise HTTPException(409, "La verificación en dos pasos por SMS ya está activa.")
    if (
        not security.pending_phone
        or not security.phone_verification_sid
        or not security.phone_expires_at
        or utc(security.phone_expires_at) <= utcnow()
        or security.phone_attempts >= 5
    ):
        raise HTTPException(400, "Solicite un nuevo código de verificación por SMS.")
    if user.account_type == "seller" and security.pending_phone != user.seller_phone:
        raise HTTPException(400, "El teléfono cambió. Solicite un código para el número actual.")
    security.phone_attempts += 1
    try:
        approved = check_phone_code(security.phone_verification_sid, security.pending_phone, code.strip())
    except HTTPException:
        commit_or_rollback(db)
        raise
    if not approved:
        commit_or_rollback(db)
        raise HTTPException(400, "El código SMS no es válido o ha vencido.")
    security.verified_phone = security.pending_phone
    security.phone_verified_at = utcnow()
    security.pending_phone = security.phone_verification_sid = None
    security.phone_expires_at = None
    security.phone_attempts = 0
    security.sms_mfa_enabled = True
    # A user cannot accidentally be asked for two different second factors.
    security.mfa_secret = security.mfa_pending_secret = None
    security.recovery_hashes = "[]"
    user.token_generation += 1
    commit_or_rollback(db)
    return {**_access(user), "message": "Verificación en dos pasos por SMS activada."}


def begin_sms_mfa_disable(db, user_id):
    user, security = _locked(db, user_id)
    if not security.sms_mfa_enabled or not security.verified_phone:
        raise HTTPException(400, "La verificación en dos pasos por SMS no está activa.")
    now = utcnow()
    if security.phone_sent_at and utc(security.phone_sent_at) > now - timedelta(seconds=60):
        raise HTTPException(429, "Espere un minuto antes de solicitar otro SMS.", headers={"Retry-After": "60"})
    if not security.phone_window_at or utc(security.phone_window_at) <= now - timedelta(hours=1):
        security.phone_window_at, security.phone_send_count = now, 0
    if security.phone_send_count >= 5:
        raise HTTPException(429, "Alcanzó el límite de SMS. Intente de nuevo en una hora.")
    security.phone_sent_at = now
    security.phone_send_count += 1
    security.pending_phone = security.verified_phone
    security.phone_verification_sid = send_phone_code(security.verified_phone)
    security.phone_expires_at = now + timedelta(minutes=10)
    security.phone_attempts = 0
    commit_or_rollback(db)
    return {"message": "Código enviado por SMS.", "pending_phone": security.verified_phone}


def disable_sms_mfa(db, user_id, password, code):
    user, security = _locked(db, user_id)
    _password(user, password)
    if not security.sms_mfa_enabled:
        raise HTTPException(400, "La verificación en dos pasos por SMS no está activa.")
    if (
        security.pending_phone != security.verified_phone
        or not security.phone_verification_sid
        or not security.phone_expires_at
        or utc(security.phone_expires_at) <= utcnow()
        or security.phone_attempts >= 5
    ):
        raise HTTPException(400, "Solicite un nuevo código antes de desactivar la protección.")
    security.phone_attempts += 1
    if not check_phone_code(security.phone_verification_sid, security.verified_phone, code.strip()):
        commit_or_rollback(db)
        raise HTTPException(400, "El código SMS no es válido o ha vencido.")
    security.sms_mfa_enabled = False
    security.pending_phone = security.phone_verification_sid = None
    security.phone_expires_at = None
    security.phone_attempts = 0
    user.token_generation += 1
    commit_or_rollback(db)
    return {**_access(user), "message": "Verificación en dos pasos por SMS desactivada."}


def begin_mfa_setup(db, user_id, password):
    cipher = _cipher()
    user, security = _locked(db, user_id)
    _password(user, password)
    if security.mfa_secret:
        raise HTTPException(409, "La verificación en dos pasos ya está activa.")
    _unblocked(security)
    if security.mfa_setup_at and utc(security.mfa_setup_at) > utcnow() - timedelta(seconds=60):
        raise HTTPException(429, "Espere un minuto antes de iniciar otra configuración.")
    secret = pyotp.random_base32()
    security.mfa_pending_secret = cipher.encrypt(secret.encode()).decode()
    security.mfa_pending_expires_at = utcnow() + timedelta(minutes=10)
    security.mfa_pending_generation = user.token_generation
    security.mfa_setup_at = utcnow()
    security.mfa_setup_attempts = 0
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="HabitaRD")
    image = qrcode.make(uri)
    output = BytesIO()
    image.save(output, format="PNG")
    commit_or_rollback(db)
    return {"setup_key": secret, "qr_code": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()}


def enable_mfa(db, user_id, code):
    user, security = _locked(db, user_id)
    _unblocked(security)
    if security.mfa_secret or not security.mfa_pending_secret or security.mfa_pending_generation != user.token_generation or utc(security.mfa_pending_expires_at) <= utcnow() or security.mfa_setup_attempts >= 5:
        raise HTTPException(400, "La configuración venció. Inicie la configuración nuevamente.")
    security.mfa_setup_attempts += 1
    counter = _matching_counter(security.mfa_pending_secret, code)
    if counter is None:
        _bad_code(db, security)
    security.mfa_secret = security.mfa_pending_secret
    security.mfa_pending_secret = None
    security.mfa_last_counter = counter
    security.mfa_failures = 0
    codes = _new_recovery_codes(security)
    user.token_generation += 1
    commit_or_rollback(db)
    return {**_access(user), "recovery_codes": codes, "message": "Verificación en dos pasos activada."}


def manage_mfa(db, user_id, password, code, disable=False):
    user, security = _locked(db, user_id)
    _password(user, password)
    if not security.mfa_secret:
        raise HTTPException(400, "La verificación en dos pasos no está activa.")
    _consume_code(db, security, code)
    if disable:
        security.mfa_secret = security.mfa_pending_secret = None
        security.recovery_hashes = "[]"
        codes = []
    else:
        codes = _new_recovery_codes(security)
    user.token_generation += 1
    commit_or_rollback(db)
    return {**_access(user), "recovery_codes": codes, "message": "Verificación en dos pasos desactivada." if disable else "Códigos de recuperación renovados."}


def finish_primary_auth(db, user):
    generation = user.token_generation
    user, security = _locked(db, user.id, create=False)
    if generation != user.token_generation:
        raise HTTPException(401, "This session is no longer valid. Please log in again.")
    if not security or not (security.sms_mfa_enabled or security.mfa_secret):
        return _access(user)
    _unblocked(security)
    raw = secrets.token_urlsafe(32)
    now = utcnow()
    verification_sid = phone_number = None
    if security.sms_mfa_enabled:
        if not security.verified_phone or not sms_configured():
            raise HTTPException(503, "No pudimos enviar el segundo paso por SMS. Contacte al soporte.")
        if security.sms_mfa_sent_at and utc(security.sms_mfa_sent_at) > now - timedelta(seconds=30):
            raise HTTPException(429, "Espere unos segundos antes de solicitar otro código.", headers={"Retry-After": "30"})
        if not security.sms_mfa_window_at or utc(security.sms_mfa_window_at) <= now - timedelta(hours=1):
            security.sms_mfa_window_at, security.sms_mfa_send_count = now, 0
        if security.sms_mfa_send_count >= 5:
            raise HTTPException(429, "Alcanzó el límite de códigos SMS. Intente de nuevo en una hora.")
        verification_sid = send_phone_code(security.verified_phone)
        phone_number = security.verified_phone
        security.sms_mfa_sent_at = now
        security.sms_mfa_send_count += 1
    db.execute(delete(LoginChallengeDB).where(or_(LoginChallengeDB.user_id == user.id, LoginChallengeDB.expires_at <= now)))
    db.add(LoginChallengeDB(
        token_hash=hashlib.sha256(raw.encode()).hexdigest(), user_id=user.id,
        generation=user.token_generation, expires_at=now + timedelta(minutes=5),
        verification_sid=verification_sid, phone_number=phone_number,
    ))
    commit_or_rollback(db)
    hint = f"•••• {phone_number[-4:]}" if phone_number else None
    return {"mfa_required": True, "mfa_method": "sms" if verification_sid else "authenticator", "challenge_token": raw, "expires_in": 300, "phone_hint": hint}


def complete_mfa_login(db, raw, code):
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    challenge = db.get(LoginChallengeDB, token_hash)
    if challenge is None:
        raise HTTPException(400, "La solicitud de acceso venció. Inicie sesión nuevamente.")
    user, security = _locked(db, challenge.user_id)
    challenge = db.scalar(select(LoginChallengeDB).where(LoginChallengeDB.token_hash == token_hash).with_for_update().execution_options(populate_existing=True))
    if (
        not challenge
        or utc(challenge.expires_at) <= utcnow()
        or challenge.generation != user.token_generation
        or challenge.attempts >= 5
        or not (security.sms_mfa_enabled or security.mfa_secret)
    ):
        raise HTTPException(400, "La solicitud de acceso venció. Inicie sesión nuevamente.")
    challenge.attempts += 1
    if challenge.verification_sid:
        if not security.sms_mfa_enabled or challenge.phone_number != security.verified_phone:
            raise HTTPException(400, "La solicitud de acceso venció. Inicie sesión nuevamente.")
        if not check_phone_code(challenge.verification_sid, challenge.phone_number, code.strip()):
            if challenge.attempts >= 5:
                db.delete(challenge)
            commit_or_rollback(db)
            raise HTTPException(400, "El código SMS no es válido o ha vencido.")
    else:
        _consume_code(db, security, code)
    db.delete(challenge)
    commit_or_rollback(db)
    return _access(user)
