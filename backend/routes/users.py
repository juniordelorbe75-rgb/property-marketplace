from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_id
from backend.auth.login_throttle import (
    clear_login_failures,
    login_retry_after,
    record_login_failure,
)
from backend.models import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    PublicProfile,
    PasswordChange,
    AccountDeletionConfirmation,
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
    db: Session = Depends(get_db)
):
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
            detail="Too many login attempts. Please try again later.",
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
