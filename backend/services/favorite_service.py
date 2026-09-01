from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.repositories import (
    favorite_repository,
    property_repository
)


def get_my_favorites(
    session: Session,
    current_user_id: int
):
    return favorite_repository.get_favorites_by_user(
        session,
        current_user_id
    )


def get_favorite_status(
    session: Session,
    property_id: int,
    current_user_id: int,
):
    favorite = favorite_repository.get_favorite_by_user_and_property(
        session,
        current_user_id,
        property_id,
    )
    return {"is_favorite": favorite is not None}


def create_favorite(
    session: Session,
    property_id: int,
    current_user_id: int
):
    property_item = property_repository.get_property_by_id(
        session,
        property_id
    )

    if property_item is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )

    if property_item.owner_id == current_user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot favorite your own property"
        )

    existing_favorite = favorite_repository.get_favorite_by_user_and_property(
        session,
        current_user_id,
        property_id,
    )

    if existing_favorite is not None:
        raise HTTPException(
            status_code=400,
            detail="Property already favorited"
        )

    try:
        return favorite_repository.create_favorite(
            session,
            current_user_id,
            property_id
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Property already favorited"
        )


def delete_favorite(
    session: Session,
    property_id: int,
    current_user_id: int
):
    deleted_favorite = favorite_repository.delete_favorite(
        session,
        current_user_id,
        property_id
    )

    if deleted_favorite is None:
        raise HTTPException(
            status_code=404,
            detail="Favorite not found"
        )

    return deleted_favorite
