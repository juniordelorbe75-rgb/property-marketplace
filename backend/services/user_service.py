from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.models import UserCreate
from backend.image_storage import delete_uploaded_property_image
from backend.auth.security import hash_password, verify_password
from backend.repositories import property_repository, user_repository
from backend.auth.token import create_access_token
from backend.db_models.user import UserDB


def get_all_users(db):
    return user_repository.get_all_users(db)


def get_user_by_email(db, email: str):
    return user_repository.get_user_by_email(
        db,
        email
    )


def get_user_by_id(db, user_id: int):

    user = user_repository.get_user_by_id(
        db,
        user_id
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


def login_user(
    db,
    email: str,
    password: str
):
    user = user_repository.get_user_by_email(
        db,
        email.strip().lower()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_correct = verify_password(
        password,
        user.password
    )

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "gen": user.token_generation,
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def create_user(
    db,
    user_data: UserCreate
):
    email = user_data.email.strip().lower()

    email_exists = user_repository.get_user_by_email(
        db,
        email
    )

    if email_exists:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = UserDB(
        name=user_data.name.strip(),
        email=email,
        password=hash_password(user_data.password),
        role="buyer"
    )

    try:
        return user_repository.create_user(
            db,
            new_user
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


def update_current_user(
    db,
    user_id: int,
    name: str,
    email: str
):
    user = user_repository.get_user_by_id(
        db,
        user_id
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    email = email.strip().lower()
    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email cannot be empty"
        )

    existing_user = user_repository.get_user_by_email(
        db,
        email
    )

    if existing_user and existing_user.id != user_id:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user.name = name
    user.email = email

    try:
        return user_repository.update_user(
            db,
            user
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


def change_password(
    db,
    user_id: int,
    current_password: str,
    new_password: str
):
    user = user_repository.get_user_by_id(
        db,
        user_id
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not verify_password(
        current_password,
        user.password
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters"
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    user.password = hash_password(new_password)
    user.token_generation += 1

    user_repository.update_user(
        db,
        user
    )

    return {
        "message": "Password changed successfully",
        "access_token": create_access_token({
            "sub": str(user.id),
            "gen": user.token_generation,
        }),
        "token_type": "bearer",
    }


def delete_current_user(
    db,
    user_id: int,
    current_password: str | None = None,
):
    user = user_repository.get_user_by_id(
        db,
        user_id
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if current_password is not None and not verify_password(current_password, user.password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    uploaded_image_urls = [
        image_url
        for property_item in property_repository.get_my_properties(db, user_id)
        for image_url in property_item.image_urls
    ]

    user_repository.delete_user(
        db,
        user
    )

    for image_url in uploaded_image_urls:
        if not property_repository.is_image_url_in_use(db, image_url):
            delete_uploaded_property_image(image_url)

    return {
        "message": "Account deleted successfully"
    }
