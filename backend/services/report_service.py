from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db_models.report import ListingReportDB
from backend.repositories import property_repository, report_repository


def create_listing_report(
    session: Session,
    property_id: int,
    reporter_id: int,
    reason: str,
    details: str,
    creation_key: str,
):
    replay = report_repository.get_by_reporter_and_creation_key(
        session,
        reporter_id,
        creation_key,
    )
    if replay is not None:
        return replay

    existing = report_repository.get_by_reporter_and_listing(
        session,
        reporter_id,
        property_id,
    )
    if existing is not None:
        return existing

    property_item = property_repository.get_property_by_id(session, property_id)
    if property_item is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if property_item.owner_id == reporter_id:
        raise HTTPException(status_code=400, detail="You cannot report your own property")

    report = ListingReportDB(
        reporter_id=reporter_id,
        property_id=property_item.id,
        listing_id=property_item.id,
        listing_title=property_item.title,
        listing_owner_id=property_item.owner_id,
        listing_owner_name=property_item.owner.name,
        reason=reason,
        details=details,
        creation_key=creation_key,
    )

    try:
        return report_repository.create_report(session, report)
    except IntegrityError:
        replay = report_repository.get_by_reporter_and_creation_key(
            session,
            reporter_id,
            creation_key,
        )
        if replay is not None:
            return replay
        existing = report_repository.get_by_reporter_and_listing(
            session,
            reporter_id,
            property_id,
        )
        if existing is not None:
            return existing
        raise


def get_listing_report_page(
    session: Session,
    status: str | None,
    page: int,
    page_size: int,
):
    items, total, counts = report_repository.get_report_page(
        session,
        status,
        page,
        page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "counts": counts,
    }


def moderate_listing_report(
    session: Session,
    report_id: int,
    status: str,
    moderator_note: str,
    reviewer_id: int,
    expected_version: int,
):
    report = report_repository.get_report_for_update(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Safety report not found")

    if report.version != expected_version:
        exact_retry = (
            report.version == expected_version + 1
            and report.status == status
            and report.moderator_note == moderator_note
            and report.reviewed_by_id == reviewer_id
        )
        if exact_retry:
            return report
        raise HTTPException(
            status_code=409,
            detail="This report changed in another review session. Refresh before continuing.",
        )

    allowed_statuses = {
        "submitted": {"submitted", "reviewing", "resolved", "dismissed"},
        "reviewing": {"reviewing", "resolved", "dismissed"},
        "resolved": {"resolved"},
        "dismissed": {"dismissed"},
    }
    if status not in allowed_statuses.get(report.status, set()):
        raise HTTPException(
            status_code=400,
            detail="This safety report cannot be moved to the requested status",
        )
    if status in {"resolved", "dismissed"} and len(moderator_note) < 3:
        raise HTTPException(
            status_code=400,
            detail="Add a short review note before closing this report",
        )

    return report_repository.update_report(
        session,
        report,
        status,
        moderator_note,
        reviewer_id,
    )
