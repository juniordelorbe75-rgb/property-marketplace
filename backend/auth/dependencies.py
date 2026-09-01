from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.auth.token import decode_access_token
from backend.db import get_db
from backend.repositories import user_repository

oauth2_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    token = credentials.credentials

    payload = decode_access_token(token)
    user_id = payload.get("sub") if payload else None

    try:
        current_user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if current_user_id <= 0:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = user_repository.get_user_by_id(db, current_user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User account no longer exists"
        )

    try:
        token_generation = int(payload.get("gen", 1))
    except (TypeError, ValueError):
        token_generation = -1

    if token_generation != user.token_generation:
        raise HTTPException(
            status_code=401,
            detail="This session is no longer valid. Please log in again.",
        )

    return current_user_id
