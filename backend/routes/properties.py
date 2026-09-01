from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session
from typing import Literal
from uuid import UUID

from backend.auth.dependencies import get_current_user_id
from backend.db import get_db
from backend.repositories import property_repository
from backend.services.property_services import (
    get_all_properties,
    get_property_by_id,
    search_properties,
    create_property,
    update_property,
    delete_property,
    get_my_properties,
    get_seller_dashboard_stats,
    get_property_engagement,
)
from backend.models import (
    Amenity,
    Property,
    PropertyCreate,
    PropertyUpdate,
    SellerDashboardStats,
    PropertyEngagement,
)


router = APIRouter(
    prefix="/properties",
    tags=["Properties"]
)


@router.get("/", response_model=list[Property])
def get_properties(
    response: Response,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db)
):
    response.headers["X-Total-Count"] = str(
        property_repository.count_all_properties(session)
    )
    return get_all_properties(session, limit=limit, offset=offset)


@router.get("/my", response_model=list[Property])
def get_my_properties_route(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return get_my_properties(
        session,
        current_user_id
    )


@router.get("/search", response_model=list[Property])
def search_properties_route(
    response: Response,
    reference: str | None = Query(default=None, pattern=r"^PM-\d{6,}$"),
    location: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    currency: Literal["USD", "DOP"] | None = None,
    property_type: Literal[
        "House", "Villa", "Apartment", "Condo"
    ] | None = None,
    listing_type: Literal["sale", "rent"] | None = None,
    amenity: Amenity | None = None,
    bedrooms: int | None = Query(default=None, ge=0, le=100),
    bathrooms: int | None = Query(default=None, ge=0, le=100),
    min_square_feet: int | None = Query(
        default=None,
        ge=0,
        le=10000000,
    ),
    sort_by: Literal["newest", "price_low", "price_high"] = "newest",
    status: Literal["available", "unavailable"] | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db)
):
    filters = dict(
        session=session,
        reference=reference,
        location=location,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        property_type=property_type,
        listing_type=listing_type,
        amenity=amenity,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_square_feet=min_square_feet,
        sort_by=sort_by,
        status=status,
    )
    results = search_properties(**filters, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(
        property_repository.count_search_properties(
            **{key: value for key, value in filters.items() if key != "sort_by"}
        )
    )
    return results


@router.get("/{property_id}", response_model=Property)
def get_property(
    property_id: int,
    session: Session = Depends(get_db)
):
    return get_property_by_id(
        session,
        property_id
    )


@router.put("/{property_id}", response_model=Property)
def update_property_route(
    property_id: int,
    updated_property: PropertyUpdate,
    property_version: int | None = Header(
        default=None,
        alias="X-Property-Version",
        ge=1,
    ),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return update_property(
        session,
        property_id,
        updated_property,
        current_user_id,
        expected_version=property_version,
    )


@router.delete("/{property_id}", response_model=Property)
def delete_property_route(
    property_id: int,
    property_version: int = Header(
        alias="X-Property-Version",
        ge=1,
    ),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return delete_property(
        session,
        property_id,
        current_user_id,
        expected_version=property_version,
    )


@router.post("/", response_model=Property)
def create_new_property(
    property_data: PropertyCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return create_property(
        session,
        property_data,
        current_user_id,
        creation_key=str(idempotency_key) if idempotency_key else None,
    )


@router.get("/my/stats", response_model=SellerDashboardStats)
def get_my_property_stats(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_seller_dashboard_stats(session, current_user_id)


@router.get("/my/engagement", response_model=list[PropertyEngagement])
def get_my_property_engagement(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_property_engagement(session, current_user_id)
