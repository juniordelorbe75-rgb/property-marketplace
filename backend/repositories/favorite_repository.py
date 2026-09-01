from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db_models.favorite import FavoriteDB
from backend.repositories.transaction import commit_or_rollback


def get_all_favorites(
    session: Session
):
    statement = select(FavoriteDB)

    return session.scalars(statement).all()


def get_favorites_by_user(
    session: Session,
    user_id: int
):
    statement = (
        select(FavoriteDB)
        .options(
            selectinload(FavoriteDB.property)
        )
        .where(
            FavoriteDB.user_id == user_id
        )
        .order_by(FavoriteDB.id.desc())
    )

    return session.scalars(statement).all()


def get_favorite_by_user_and_property(
    session: Session,
    user_id: int,
    property_id: int,
):
    statement = select(FavoriteDB).where(
        FavoriteDB.user_id == user_id,
        FavoriteDB.property_id == property_id,
    )
    return session.scalar(statement)

def create_favorite(
    session: Session,
    user_id: int,
    property_id: int
):
    new_favorite = FavoriteDB(
        user_id=user_id,
        property_id=property_id
    )

    session.add(new_favorite)
    commit_or_rollback(session)
    session.refresh(new_favorite)

    return new_favorite


def delete_favorite(
    session: Session,
    user_id: int,
    property_id: int
):
    statement = select(FavoriteDB).where(
        FavoriteDB.user_id == user_id,
        FavoriteDB.property_id == property_id
    )

    favorite = session.scalar(statement)

    if favorite is None:
        return None

    session.delete(favorite)
    commit_or_rollback(session)

    return favorite
