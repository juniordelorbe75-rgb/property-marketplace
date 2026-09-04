from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_id
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


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "/",
    response_model=UserResponse
)
def register_user(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    client_address = request.client.host if request.client else "unknown"
    retry_after = consume_rate_limit(
        "registration", client_address, limit=5, window_seconds=15 * 60
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
    client_address = request.client.host if request.client else "unknown"
    retry_after = login_retry_after(client_address, user_json.email)
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
            record_login_failure(client_address, user_json.email)
        raise

    clear_login_failures(client_address, user_json.email)
    return result


@router.post("/password-reset/request")
def request_password_reset_link(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_address = request.client.host if request.client else "unknown"
    retry_after = consume_rate_limit(
        "password-reset-request", client_address, limit=5, window_seconds=15 * 60
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
    client_address = request.client.host if request.client else "unknown"
    retry_after = consume_rate_limit(
        "password-reset-confirm", client_address, limit=10, window_seconds=15 * 60
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
    client_address = request.client.host if request.client else "unknown"
    retry_after = consume_rate_limit("email-verification", client_address, limit=3, window_seconds=15 * 60)
    if retry_after is not None:
        raise HTTPException(429, retry_after_detail("Too many verification requests.", retry_after), headers={"Retry-After": str(retry_after)})
    return issue_email_verification(db, get_user_by_id(db, current_user_id))


@router.post("/email-verification/confirm")
def confirm_email_verification(payload: EmailVerificationConfirmation, db: Session = Depends(get_db)):
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
    response_model=UserResponse
)
def update_me(
    user_data: UserUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return update_current_user(
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
