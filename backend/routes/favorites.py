from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_id
from backend.db import get_db
from backend.models import Favorite, FavoritePropertyResponse, FavoriteStatus
from backend.services.favorite_service import (
    get_my_favorites,
    get_favorite_status,
    create_favorite,
    delete_favorite,
)


router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"]
)


@router.get(
    "/",
    response_model=list[FavoritePropertyResponse]
)
def get_favorites(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return get_my_favorites(
        session,
        current_user_id
    )


@router.post(
    "/{property_id}",
    response_model=Favorite
)
def add_favorite(
    property_id: int,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return create_favorite(
        session,
        property_id,
        current_user_id
    )


@router.delete(
    "/{property_id}",
    response_model=Favorite
)
def remove_favorite(
    property_id: int,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return delete_favorite(
        session,
        property_id,
        current_user_id
    )


@router.get(
    "/{property_id}/status",
    response_model=FavoriteStatus,
)
def get_property_favorite_status(
    property_id: int,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_favorite_status(session, property_id, current_user_id)
