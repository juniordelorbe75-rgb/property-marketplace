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
