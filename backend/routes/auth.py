import os
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.auth.social import PROVIDERS, begin_flow, consume_flow, create_login_code, consume_login_code, fetch_profile, provider_options
from backend.auth.dependencies import get_current_user_id, oauth2_scheme
from backend.auth.token import create_access_token, decode_access_token
from backend.db import get_db
from backend.db_models.social_identity import SocialIdentityDB
from backend.db_models.user import UserDB
from backend.db_models.revoked_token import RevokedTokenDB
from backend.repositories.transaction import commit_or_rollback

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    _user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    db.execute(delete(RevokedTokenDB).where(RevokedTokenDB.expires_at <= datetime.now(timezone.utc)))
    db.add(RevokedTokenDB(jti=payload["jti"], expires_at=expires_at))
    commit_or_rollback(db)
    return Response(status_code=204)


class CodeExchange(BaseModel):
    code: str = Field(min_length=20, max_length=200)


def _safe_return_to(value):
    return value if value.startswith("/") and not value.startswith("//") else "/"


@router.get("/providers")
def providers():
    return {"providers": provider_options()}


@router.get("/{provider}/start")
def start(provider: str, return_to: str = "/"):
    url, state = begin_flow(provider, _safe_return_to(return_to))
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(
        "oauth_state", state, max_age=600, httponly=True, samesite="lax",
        secure=redirect_uri_is_secure(), path="/auth/",
    )
    return response


def redirect_uri_is_secure():
    return os.getenv("OAUTH_REDIRECT_BASE_URL", "http://127.0.0.1:8000").startswith("https://")


@router.get("/{provider}/callback")
def callback(request: Request, provider: str, state: str = "", code: str = "", error: str = "", db: Session = Depends(get_db)):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown sign-in provider")
    cookie_state = request.cookies.get("oauth_state", "")
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(400, "The sign-in request did not originate in this browser")
    return_to = consume_flow(provider, state)
    frontend = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
    if error or not code:
        response = RedirectResponse(f"{frontend}/auth/callback?{urlencode({'error': 'Sign-in was cancelled or denied'})}", status_code=302)
        response.delete_cookie("oauth_state", path="/auth/")
        return response

    subject, email, name = fetch_profile(provider, code)
    identity = db.scalar(select(SocialIdentityDB).where(SocialIdentityDB.provider == provider, SocialIdentityDB.provider_user_id == subject))
    if identity:
        user = identity.user
    else:
        user = db.scalar(select(UserDB).where(UserDB.email == email))
        if user is None:
            user = UserDB(name=name, email=email, password=hash_password(secrets.token_urlsafe(48)), has_password=False, email_verified=True, role="buyer")
            db.add(user)
            db.flush()
        else:
            user.email_verified = True
        db.add(SocialIdentityDB(user_id=user.id, provider=provider, provider_user_id=subject))
        try:
            commit_or_rollback(db)
        except IntegrityError as exc:
            raise HTTPException(409, "This social account is already linked") from exc
        db.refresh(user)

    login_code = create_login_code(user.id)
    response = RedirectResponse(f"{frontend}/auth/callback?{urlencode({'code': login_code, 'return_to': return_to})}", status_code=302)
    response.delete_cookie("oauth_state", path="/auth/")
    return response


@router.post("/exchange")
def exchange(payload: CodeExchange, db: Session = Depends(get_db)):
    user = db.get(UserDB, consume_login_code(payload.code))
    if user is None:
        raise HTTPException(400, "The account no longer exists")
    return {"access_token": create_access_token({"sub": str(user.id), "gen": user.token_generation}), "token_type": "bearer"}
