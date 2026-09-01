from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def commit_or_rollback(session: Session) -> None:
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
