from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db_models.user import UserDB
from backend.repositories.transaction import commit_or_rollback


def get_all_users(db: Session):
    statement = select(UserDB)

    return db.scalars(statement).all()


def get_user_by_id(
    db: Session,
    user_id: int
):
    statement = select(UserDB).where(
        UserDB.id == user_id
    )

    return db.scalar(statement)


def get_user_by_email(
    db: Session,
    email: str
):
    statement = select(UserDB).where(
        UserDB.email == email
    )

    return db.scalar(statement)


def create_user(
    db: Session,
    user_data: UserDB
):
    db.add(user_data)

    commit_or_rollback(db)

    db.refresh(user_data)

    return user_data


def update_user(
    db: Session,
    user: UserDB
):
    commit_or_rollback(db)

    db.refresh(user)

    return user


def delete_user(
    db: Session,
    user: UserDB
):
    db.delete(user)

    commit_or_rollback(db)

    return user
