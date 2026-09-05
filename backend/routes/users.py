import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_id
from backend.auth.token import create_access_token
from backend.auth.login_throttle import (
    clear_login_failures,
    login_retry_after,
    record_login_failure,
)
from backend.auth.request_throttle import consume_rate_limit, retry_after_detail
from backend.models import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdateResponse,
    UserUpdate,
    PublicProfile,
    PasswordChange,
    AccountDeletionConfirmation,
    PasswordResetRequest,
    PasswordResetConfirmation,
    EmailVerificationConfirmation,
)
from backend.services.user_service import (
    create_user,
    login_user,
    get_user_by_id,
    get_public_profile,
    update_current_user,
    change_password,
    delete_current_user,
)
from backend.services.password_reset_service import request_password_reset, reset_password
from backend.services.email_verification_service import issue_email_verification, verify_email

from backend.db import get_db
from backend.request_identity import client_address, parse_trusted_proxy_networks


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)
TRUSTED_PROXY_NETWORKS = parse_trusted_proxy_networks(os.getenv("TRUSTED_PROXY_IPS"))


def _anonymous_rate_limit_key(value: str) -> str:
    """Keep normalized account identifiers out of process-local throttle keys."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _combined_retry_after(*limits: tuple[str, str, int, int]) -> int | None:
    waits = [
        wait
        for action, subject, limit, window_seconds in limits
        if (wait := consume_rate_limit(
            action,
            subject,
            limit=limit,
            window_seconds=window_seconds,
        )) is not None
    ]
    return max(waits, default=None)


@router.post(
    "/",
    response_model=UserResponse
)
def register_user(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = consume_rate_limit(
        "registration", request_address, limit=5, window_seconds=15 * 60
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=retry_after_detail(
                "Too many accounts were created from this address.", retry_after
            ),
            headers={"Retry-After": str(retry_after)},
        )
    return create_user(
        db,
        user
    )


@router.post("/login")
def login(
    user_json: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = login_retry_after(request_address, user_json.email)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=retry_after_detail("Too many login attempts.", retry_after),
            headers={"Retry-After": str(retry_after)},
        )

    try:
        result = login_user(
            db,
            user_json.email,
            user_json.password
        )
    except HTTPException as error:
        if error.status_code == 401:
            record_login_failure(request_address, user_json.email)
        raise

    clear_login_failures(request_address, user_json.email)
    return result


@router.post("/password-reset/request")
def request_password_reset_link(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = _combined_retry_after(
        ("password-reset-request-client", request_address, 5, 15 * 60),
        (
            "password-reset-request-account",
            _anonymous_rate_limit_key(payload.email),
            3,
            15 * 60,
        ),
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=retry_after_detail("Too many password reset requests.", retry_after),
            headers={"Retry-After": str(retry_after)},
        )
    return request_password_reset(db, payload.email)


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirmation,
    request: Request,
    db: Session = Depends(get_db),
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = consume_rate_limit(
        "password-reset-confirm", request_address, limit=10, window_seconds=15 * 60
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=retry_after_detail("Too many password reset attempts.", retry_after),
            headers={"Retry-After": str(retry_after)},
        )
    return reset_password(db, payload.token, payload.new_password)


@router.post("/email-verification/request")
def resend_email_verification(
    request: Request,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = _combined_retry_after(
        ("email-verification-client", request_address, 3, 15 * 60),
        ("email-verification-account", str(current_user_id), 3, 15 * 60),
    )
    if retry_after is not None:
        raise HTTPException(429, retry_after_detail("Too many verification requests.", retry_after), headers={"Retry-After": str(retry_after)})
    return issue_email_verification(db, get_user_by_id(db, current_user_id))


@router.post("/email-verification/confirm")
def confirm_email_verification(
    payload: EmailVerificationConfirmation,
    request: Request,
    db: Session = Depends(get_db),
):
    request_address = client_address(request, TRUSTED_PROXY_NETWORKS)
    retry_after = consume_rate_limit(
        "email-verification-confirm", request_address, limit=20, window_seconds=15 * 60
    )
    if retry_after is not None:
        raise HTTPException(
            429,
            retry_after_detail("Too many verification attempts.", retry_after),
            headers={"Retry-After": str(retry_after)},
        )
    return verify_email(db, payload.token)


@router.get(
    "/me",
    response_model=UserResponse
)
def get_current_user(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return get_user_by_id(
        db,
        current_user_id
    )


@router.put(
    "/me",
    response_model=UserUpdateResponse,
    response_model_exclude_none=True,
)
def update_me(
    user_data: UserUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    updated_user, email_changed = update_current_user(
        db=db,
        user_id=current_user_id,
        name=user_data.name,
        first_name=user_data.first_name,
        middle_name=user_data.middle_name,
        last_name=user_data.last_name,
        date_of_birth=user_data.date_of_birth,
        bio=user_data.bio,
        public_profile_enabled=user_data.public_profile_enabled,
        public_name_mode=user_data.public_name_mode,
        public_bio_visible=user_data.public_bio_visible,
        email=user_data.email,
        current_password=user_data.current_password,
    )
    response = UserUpdateResponse.model_validate(updated_user).model_dump()
    if email_changed:
        response.update({
            "access_token": create_access_token({
                "sub": str(updated_user.id),
                "gen": updated_user.token_generation,
            }),
            "token_type": "bearer",
        })
    return response


@router.get("/{user_id}/profile", response_model=PublicProfile)
def view_public_profile(user_id: int, db: Session = Depends(get_db)):
    return get_public_profile(db, user_id)


@router.patch("/me/password")
def change_my_password(
    password_data: PasswordChange,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return change_password(
        db=db,
        user_id=current_user_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )


@router.delete("/me")
def delete_my_account(
    confirmation: AccountDeletionConfirmation,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return delete_current_user(
        db=db,
        user_id=current_user_id,
        current_password=confirmation.current_password,
    )
