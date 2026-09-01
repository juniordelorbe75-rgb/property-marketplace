from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db_models.report import ListingReportDB
from backend.repositories.transaction import commit_or_rollback


def get_by_reporter_and_listing(
    session: Session,
    reporter_id: int,
    listing_id: int,
):
    return session.scalar(
        select(ListingReportDB).where(
            ListingReportDB.reporter_id == reporter_id,
            ListingReportDB.listing_id == listing_id,
        )
    )


def get_by_reporter_and_creation_key(
    session: Session,
    reporter_id: int,
    creation_key: str,
):
    return session.scalar(
        select(ListingReportDB).where(
            ListingReportDB.reporter_id == reporter_id,
            ListingReportDB.creation_key == creation_key,
        )
    )


def create_report(session: Session, report: ListingReportDB):
    session.add(report)
    commit_or_rollback(session)
    session.refresh(report)
    return report
