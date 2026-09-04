from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.models import UserCreate
from backend.image_storage import delete_uploaded_property_image
from backend.auth.security import hash_password, verify_password
from backend.repositories import property_repository, user_repository
from backend.auth.token import create_access_token
from backend.db_models.user import UserDB
from backend.services.email_verification_service import issue_email_verification


# Unknown accounts still perform one normal bcrypt verification so login timing
# does not disclose whether an email address is registered.
DUMMY_PASSWORD_HASH = hash_password("timing-only-password-that-is-never-accepted")


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


def get_public_profile(db, user_id: int):
    user = user_repository.get_user_by_id(db, user_id)
    if user is None or not user.public_profile_enabled:
        raise HTTPException(status_code=404, detail="Public profile not available")

    return {
        "id": user.id,
        "display_name": user.public_display_name,
        "bio": user.bio if user.public_bio_visible and user.bio else None,
    }


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
        verify_password(password, DUMMY_PASSWORD_HASH)
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
        first_name=user_data.first_name or "",
        middle_name=user_data.middle_name,
        last_name=user_data.last_name or "",
        date_of_birth=user_data.date_of_birth,
        bio=user_data.bio,
        email=email,
        password=hash_password(user_data.password),
        role="buyer"
    )

    try:
        created_user = user_repository.create_user(
            db,
            new_user
        )
        issue_email_verification(db, created_user)
        return created_user
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


def update_current_user(
    db,
    user_id: int,
    name: str | None,
    email: str,
    first_name: str | None = None,
    middle_name: str = "",
    last_name: str | None = None,
    date_of_birth=None,
    bio: str = "",
    public_profile_enabled: bool = False,
    public_name_mode: str = "first_name",
    public_bio_visible: bool = False,
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

    email = email.strip().lower()
    name = name.strip() if name else ""

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

    email_changed = email != user.email
    if email_changed:
        if not current_password:
            raise HTTPException(
                status_code=400,
                detail="Current password is required to change your email",
            )
        if not verify_password(current_password, user.password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect",
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
    if first_name is not None or last_name is not None:
        user.first_name = first_name or ""
        user.middle_name = middle_name
        user.last_name = last_name or ""
        user.date_of_birth = date_of_birth
        user.bio = bio
        user.public_profile_enabled = public_profile_enabled
        user.public_name_mode = public_name_mode
        user.public_bio_visible = public_bio_visible
    user.email = email
    if email_changed:
        user.email_verified = False

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

    had_password = user.has_password
    if had_password:
        if not current_password or not verify_password(current_password, user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters"
        )

    if current_password and current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    user.password = hash_password(new_password)
    user.has_password = True
    user.token_generation += 1

    user_repository.update_user(
        db,
        user
    )

    return {
        "message": "Password changed successfully" if had_password else "Password created successfully",
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

    if not user.has_password:
        raise HTTPException(
            status_code=400,
            detail="Create an account password before deleting your account",
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
