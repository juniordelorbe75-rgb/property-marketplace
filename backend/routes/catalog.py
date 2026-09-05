from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin_user_id
from backend.db import get_db
from backend.db_models.external_listing import ExternalListingDB, ListingFeedAuditDB, ListingSourceDB
from backend.models import ExternalProperty
from backend.integrations.reppingdr_sync import sync_reppingdr
from backend.repositories.external_listing_repository import (
    count_public_external_listings,
    get_public_external_listings,
    set_source_approval,
    withdraw_stale_listings,
)


router = APIRouter(prefix="/catalog", tags=["Catalog"])


class SourceCreate(BaseModel):
    source_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=2, max_length=150)
    country_code: str = Field(min_length=2, max_length=2)
    license_name: str = Field(min_length=2, max_length=150)
    license_url: str = Field(max_length=1000)
    attribution: str = Field(min_length=2, max_length=300)
    stale_after_hours: int = Field(default=48, ge=1, le=720)

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.upper()

    @field_validator("license_url")
    @classmethod
    def require_https(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("License URL must be HTTPS")
        return value


class SourceApprovalUpdate(BaseModel):
    status: Literal["approved", "revoked"]
    permission_document_url: str | None = Field(default=None, max_length=2000)
    permission_expires_at: datetime | None = None
    stale_after_hours: int | None = Field(default=None, ge=1, le=720)

    @field_validator("permission_document_url")
    @classmethod
    def require_https(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Permission document URL must be HTTPS")
        return value


class SourceResponse(BaseModel):
    id: int
    source_key: str
    name: str
    country_code: str
    license_name: str
    license_url: str
    attribution: str
    approved: bool
    approval_status: str
    permission_document_url: str | None
    permission_approved_at: datetime | None
    permission_expires_at: datetime | None
    approved_by_id: int | None
    stale_after_hours: int
    last_retrieved_at: datetime | None

    model_config = {"from_attributes": True}


class SourceOversightResponse(SourceResponse):
    total_listings: int
    public_listings: int
    latest_event_type: str | None
    latest_event_at: datetime | None


class AuditResponse(BaseModel):
    id: int
    source_id: int
    event_type: str
    actor_user_id: int | None
    details_json: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/external", response_model=list[ExternalProperty])
def public_external_catalog(
    response: Response,
    location: str | None = Query(default=None, max_length=200),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, pattern=r"^[A-Z]{3}$"),
    property_type: str | None = Query(default=None, max_length=100),
    listing_type: str | None = Query(default=None, pattern=r"^(sale|rent)$"),
    bedrooms: int | None = Query(default=None, ge=0, le=100),
    bathrooms: float | None = Query(default=None, ge=0, le=100),
    min_area_sqm: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    filters = dict(
        location=location, min_price=min_price, max_price=max_price, currency=currency,
        property_type=property_type, listing_type=listing_type, bedrooms=bedrooms,
        bathrooms=bathrooms, min_area_sqm=min_area_sqm,
    )
    response.headers["X-Total-Count"] = str(count_public_external_listings(session, **filters))
    return [ExternalProperty.from_db(item) for item in get_public_external_listings(session, limit, offset, **filters)]


@router.get("/admin/sources", response_model=list[SourceOversightResponse])
def admin_sources(
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    sources = session.scalars(select(ListingSourceDB).order_by(ListingSourceDB.name)).all()
    result = []
    for source in sources:
        total_listings = session.scalar(
            select(func.count(ExternalListingDB.id)).where(ExternalListingDB.source_id == source.id)
        ) or 0
        public_listings = session.scalar(
            select(func.count(ExternalListingDB.id)).where(
                ExternalListingDB.source_id == source.id,
                ExternalListingDB.is_public.is_(True),
                ExternalListingDB.status == "active",
            )
        ) or 0
        latest_event = session.scalar(
            select(ListingFeedAuditDB)
            .where(ListingFeedAuditDB.source_id == source.id)
            .order_by(ListingFeedAuditDB.created_at.desc(), ListingFeedAuditDB.id.desc())
            .limit(1)
        )
        result.append({
            **SourceResponse.model_validate(source).model_dump(),
            "total_listings": total_listings,
            "public_listings": public_listings,
            "latest_event_type": latest_event.event_type if latest_event else None,
            "latest_event_at": latest_event.created_at if latest_event else None,
        })
    return result


@router.post("/admin/sources", response_model=SourceResponse, status_code=201)
def create_source(
    data: SourceCreate,
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    if session.scalar(select(ListingSourceDB).where(ListingSourceDB.source_key == data.source_key)):
        raise HTTPException(status_code=409, detail="A source with this key already exists")
    source = ListingSourceDB(**data.model_dump(), approved=False, approval_status="pending")
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


@router.patch("/admin/sources/{source_id}/approval", response_model=SourceResponse)
def update_source_approval(
    source_id: int,
    data: SourceApprovalUpdate,
    admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    source = session.get(ListingSourceDB, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Listing source not found")
    try:
        return set_source_approval(
            session, source,
            approved=data.status == "approved",
            actor_user_id=admin_user_id,
            permission_document_url=data.permission_document_url,
            permission_expires_at=data.permission_expires_at,
            stale_after_hours=data.stale_after_hours,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/admin/withdraw-stale")
def admin_withdraw_stale(
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    return {"withdrawn": withdraw_stale_listings(session)}


@router.post("/admin/sources/{source_id}/sync/reppingdr")
def admin_sync_reppingdr(
    source_id: int,
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    source = session.get(ListingSourceDB, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Listing source not found")
    try:
        return sync_reppingdr(session, source)
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/admin/audit", response_model=list[AuditResponse])
def admin_audit(
    source_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    _admin_user_id: int = Depends(get_current_admin_user_id),
    session: Session = Depends(get_db),
):
    statement = select(ListingFeedAuditDB)
    if source_id is not None:
        statement = statement.where(ListingFeedAuditDB.source_id == source_id)
    return session.scalars(statement.order_by(ListingFeedAuditDB.created_at.desc()).limit(limit)).all()
