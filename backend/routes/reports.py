from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_id
from backend.db import get_db
from backend.models import ListingReport
from backend.services.report_service import create_listing_report


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


router = APIRouter(prefix="/reports", tags=["Safety Reports"])


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
