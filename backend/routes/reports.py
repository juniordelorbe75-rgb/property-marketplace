from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin_user_id, get_current_user_id
from backend.db import get_db
from backend.models import (
    AdminAccess,
    AdminListingReport,
    ListingReport,
    ListingReportPage,
    ListingSafetyHold,
    MyListingReportPage,
)
from backend.services.report_service import (
    create_listing_report,
    get_my_listing_report_page,
    get_listing_report_page,
    moderate_listing_report,
    set_listing_safety_hold,
)


class ListingReportCreate(BaseModel):
    reason: Literal[
        "suspected_scam",
        "misleading_information",
        "duplicate_listing",
        "already_unavailable",
        "inappropriate_content",
        "other",
    ]
    details: str = Field(default="", max_length=1000)

    @field_validator("details")
    @classmethod
    def strip_details(cls, value: str) -> str:
        return value.strip()


class ListingReportUpdate(BaseModel):
    status: Literal["submitted", "reviewing", "resolved", "dismissed"]
    moderator_note: str = Field(default="", max_length=1000)

    @field_validator("moderator_note")
    @classmethod
    def strip_moderator_note(cls, value: str) -> str:
        return value.strip()


class ListingSafetyHoldUpdate(BaseModel):
    held: bool


router = APIRouter(prefix="/reports", tags=["Safety Reports"])


@router.get("/mine", response_model=MyListingReportPage)
def get_my_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_my_listing_report_page(
        session,
        current_user_id,
        page,
        page_size,
    )


@router.get("/admin/access", response_model=AdminAccess)
def get_admin_access(
    _admin_user_id: int = Depends(get_current_admin_user_id),
):
    return {"is_admin": True}


@router.get("/admin", response_model=ListingReportPage)
def get_admin_reports(
    status: Literal["submitted", "reviewing", "resolved", "dismissed"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    return get_listing_report_page(session, status, page, page_size)


@router.patch("/admin/{report_id}/listing-hold", response_model=ListingSafetyHold)
def update_listing_safety_hold(
    report_id: int,
    hold_data: ListingSafetyHoldUpdate,
    safety_version: int = Header(ge=1, alias="X-Listing-Safety-Version"),
    admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    return set_listing_safety_hold(
        session=session,
        report_id=report_id,
        held=hold_data.held,
        reviewer_id=admin_user_id,
        expected_safety_version=safety_version,
    )


@router.patch("/admin/{report_id}", response_model=AdminListingReport)
def update_admin_report(
    report_id: int,
    report_data: ListingReportUpdate,
    report_version: int = Header(ge=1, alias="X-Report-Version"),
    admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    return moderate_listing_report(
        session=session,
        report_id=report_id,
        status=report_data.status,
        moderator_note=report_data.moderator_note,
        reviewer_id=admin_user_id,
        expected_version=report_version,
    )


@router.post("/properties/{property_id}", response_model=ListingReport)
def report_property(
    property_id: int,
    report_data: ListingReportCreate,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return create_listing_report(
        session=session,
        property_id=property_id,
        reporter_id=current_user_id,
        reason=report_data.reason,
        details=report_data.details,
        creation_key=str(idempotency_key),
    )
