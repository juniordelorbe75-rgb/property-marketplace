from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

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


def get_report_page(
    session: Session,
    status: str | None,
    page: int,
    page_size: int,
):
    filters = [] if status is None else [ListingReportDB.status == status]
    total = session.scalar(
        select(func.count(ListingReportDB.id)).where(*filters)
    ) or 0
    items = session.scalars(
        select(ListingReportDB)
        .options(
            selectinload(ListingReportDB.reporter),
            selectinload(ListingReportDB.reviewer),
            selectinload(ListingReportDB.listing),
        )
        .where(*filters)
        .order_by(ListingReportDB.created_at.desc(), ListingReportDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    grouped_counts = dict(
        session.execute(
            select(ListingReportDB.status, func.count(ListingReportDB.id))
            .group_by(ListingReportDB.status)
        ).all()
    )
    counts = {
        "all": sum(grouped_counts.values()),
        "submitted": grouped_counts.get("submitted", 0),
        "reviewing": grouped_counts.get("reviewing", 0),
        "resolved": grouped_counts.get("resolved", 0),
        "dismissed": grouped_counts.get("dismissed", 0),
    }
    return items, total, counts


def get_report_page_by_reporter(
    session: Session,
    reporter_id: int,
    page: int,
    page_size: int,
):
    reporter_filter = ListingReportDB.reporter_id == reporter_id
    total = session.scalar(
        select(func.count(ListingReportDB.id)).where(reporter_filter)
    ) or 0
    items = session.scalars(
        select(ListingReportDB)
        .where(reporter_filter)
        .order_by(ListingReportDB.created_at.desc(), ListingReportDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


def get_report_for_update(session: Session, report_id: int):
    return session.scalar(
        select(ListingReportDB)
        .options(
            selectinload(ListingReportDB.reporter),
            selectinload(ListingReportDB.reviewer),
            selectinload(ListingReportDB.listing),
        )
        .where(ListingReportDB.id == report_id)
        .with_for_update()
    )


def update_report(
    session: Session,
    report: ListingReportDB,
    status: str,
    moderator_note: str,
    reviewer_id: int,
):
    report.status = status
    report.moderator_note = moderator_note
    report.reviewed_by_id = reviewer_id
    report.reviewed_at = datetime.now(timezone.utc)
    report.version += 1
    commit_or_rollback(session)
    session.refresh(report)
    session.expire(report, ["reviewer"])
    return report
