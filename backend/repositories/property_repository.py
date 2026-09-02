from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.db_models.property import PropertyDB
from backend.db_models.favorite import FavoriteDB
from backend.db_models.inquiry import InquiryDB
from backend.models import PropertyCreate, PropertyUpdate
from backend.repositories.transaction import commit_or_rollback


def get_all_properties(
    session: Session,
    limit: int | None = None,
    offset: int = 0,
):
    statement = (
        select(PropertyDB)
        .options(
            selectinload(PropertyDB.owner)
        )
        .where(PropertyDB.safety_hold.is_(False))
        .order_by(
            PropertyDB.created_at.desc(),
            PropertyDB.id.desc(),
        )
    )

    if limit is not None:
        statement = statement.offset(offset).limit(limit)

    return session.scalars(statement).all()


def get_my_properties(
    session: Session,
    current_user_id: int
):
    statement = (
        select(PropertyDB)
        .options(
            selectinload(PropertyDB.owner)
        )
        .where(
            PropertyDB.owner_id == current_user_id
        )
        .order_by(
            PropertyDB.created_at.desc(),
            PropertyDB.id.desc(),
        )
    )

    return session.scalars(statement).all()


def count_all_properties(session: Session) -> int:
    return session.scalar(
        select(func.count(PropertyDB.id)).where(PropertyDB.safety_hold.is_(False))
    ) or 0


def get_seller_dashboard_stats(session: Session, current_user_id: int):
    total_listings = session.scalar(
        select(func.count(PropertyDB.id)).where(
            PropertyDB.owner_id == current_user_id
        )
    ) or 0
    available_listings = session.scalar(
        select(func.count(PropertyDB.id)).where(
            PropertyDB.owner_id == current_user_id,
            PropertyDB.status == "available",
            PropertyDB.safety_hold.is_(False),
        )
    ) or 0
    favorites_received = session.scalar(
        select(func.count(FavoriteDB.id))
        .join(PropertyDB, FavoriteDB.property_id == PropertyDB.id)
        .where(PropertyDB.owner_id == current_user_id)
    ) or 0
    inquiries_received = session.scalar(
        select(func.count(InquiryDB.id)).where(
            InquiryDB.seller_id == current_user_id
        )
    ) or 0
    pending_inquiries = session.scalar(
        select(func.count(InquiryDB.id)).where(
            InquiryDB.seller_id == current_user_id,
            InquiryDB.status == "pending",
        )
    ) or 0

    return {
        "total_listings": total_listings,
        "available_listings": available_listings,
        "unavailable_listings": total_listings - available_listings,
        "favorites_received": favorites_received,
        "inquiries_received": inquiries_received,
        "pending_inquiries": pending_inquiries,
    }


def get_property_engagement(session: Session, current_user_id: int):
    favorite_count = (
        select(func.count(FavoriteDB.id))
        .where(FavoriteDB.property_id == PropertyDB.id)
        .correlate(PropertyDB)
        .scalar_subquery()
    )
    inquiry_count = (
        select(func.count(InquiryDB.id))
        .where(InquiryDB.property_id == PropertyDB.id)
        .correlate(PropertyDB)
        .scalar_subquery()
    )
    pending_inquiry_count = (
        select(func.count(InquiryDB.id))
        .where(
            InquiryDB.property_id == PropertyDB.id,
            InquiryDB.status == "pending",
        )
        .correlate(PropertyDB)
        .scalar_subquery()
    )
    rows = session.execute(
        select(
            PropertyDB.id,
            favorite_count.label("favorites"),
            inquiry_count.label("inquiries"),
            pending_inquiry_count.label("pending_inquiries"),
        )
        .where(PropertyDB.owner_id == current_user_id)
        .order_by(PropertyDB.id)
    ).all()

    return [
        {
            "property_id": property_id,
            "favorites": favorites,
            "inquiries": inquiries,
            "pending_inquiries": pending_inquiries,
        }
        for property_id, favorites, inquiries, pending_inquiries in rows
    ]


def get_property_by_id(
    session: Session,
    property_id: int
):
    statement = (
        select(PropertyDB)
        .options(
            selectinload(PropertyDB.owner)
        )
        .where(
            PropertyDB.id == property_id
        )
    )

    return session.scalar(statement)


def get_property_by_creation_key(
    session: Session,
    owner_id: int,
    creation_key: str,
):
    return session.scalar(
        select(PropertyDB)
        .options(selectinload(PropertyDB.owner))
        .where(
            PropertyDB.owner_id == owner_id,
            PropertyDB.creation_key == creation_key,
        )
    )


def get_property_for_update(session: Session, property_id: int):
    return session.scalar(
        select(PropertyDB)
        .options(selectinload(PropertyDB.owner))
        .where(PropertyDB.id == property_id)
        .with_for_update()
    )


def is_image_url_in_use(session: Session, image_url: str) -> bool:
    properties = session.scalars(select(PropertyDB)).all()
    return any(image_url in property_item.image_urls for property_item in properties)


def search_properties(
    session: Session,
    property_id: int | None = None,
    location: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    currency: str | None = None,
    property_type: str | None = None,
    listing_type: str | None = None,
    amenity: str | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    min_square_feet: int | None = None,
    sort_by: str = "newest",
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    statement = _property_filter_statement(
        property_id=property_id,
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
        status=status,
    ).options(selectinload(PropertyDB.owner))

    statement = _sort_property_statement(statement, sort_by)
    if limit is not None:
        statement = statement.offset(offset).limit(limit)

    return session.scalars(statement).all()


def count_search_properties(
    session: Session,
    reference: str | None = None,
    location: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    currency: str | None = None,
    property_type: str | None = None,
    listing_type: str | None = None,
    amenity: str | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    min_square_feet: int | None = None,
    status: str | None = None,
) -> int:
    filtered = _property_filter_statement(
        property_id=int(reference.split("-", 1)[1]) if reference else None,
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
        status=status,
    ).subquery()
    return session.scalar(select(func.count()).select_from(filtered)) or 0


def _property_filter_statement(
    property_id=None,
    location=None,
    min_price=None,
    max_price=None,
    currency=None,
    property_type=None,
    listing_type=None,
    amenity=None,
    bedrooms=None,
    bathrooms=None,
    min_square_feet=None,
    status=None,
):
    statement = select(PropertyDB).where(PropertyDB.safety_hold.is_(False))

    if property_id is not None:
        statement = statement.where(PropertyDB.id == property_id)

    if location:
        statement = statement.where(
            PropertyDB.location.ilike(
                f"%{location}%"
            )
        )

    if min_price is not None:
        statement = statement.where(
            PropertyDB.price >= min_price
        )

    if max_price is not None:
        statement = statement.where(
            PropertyDB.price <= max_price
        )

    if currency:
        statement = statement.where(PropertyDB.currency == currency)

    if property_type:
        statement = statement.where(
            PropertyDB.property_type.ilike(
                f"%{property_type}%"
            )
        )

    if bedrooms is not None:
        statement = statement.where(
            PropertyDB.bedrooms >= bedrooms
        )

    if listing_type:
        statement = statement.where(PropertyDB.listing_type == listing_type)

    if amenity:
        statement = statement.where(
            PropertyDB.amenities_json.contains(f'"{amenity}"')
        )

    if bathrooms is not None:
        statement = statement.where(
            PropertyDB.bathrooms >= bathrooms
        )

    if min_square_feet is not None:
        statement = statement.where(
            PropertyDB.square_feet >= min_square_feet
        )

    if status:
        statement = statement.where(
            PropertyDB.status.ilike(
                f"%{status}%"
            )
        )

    return statement


def _sort_property_statement(statement, sort_by: str):
    if sort_by == "price_low":
        return statement.order_by(
            PropertyDB.price.asc(),
            PropertyDB.id.desc(),
        )
    if sort_by == "price_high":
        return statement.order_by(
            PropertyDB.price.desc(),
            PropertyDB.id.desc(),
        )
    return statement.order_by(
        PropertyDB.created_at.desc(),
        PropertyDB.id.desc(),
    )


def update_property(
    session: Session,
    property_id: int,
    updated_property: PropertyUpdate,
):
    property_item = get_property_by_id(
        session,
        property_id
    )

    if property_item is None:
        return None

    updated_data = updated_property.model_dump()

    for field, value in updated_data.items():
        setattr(
            property_item,
            field,
            value
        )

    property_item.version += 1
    property_item.updated_at = datetime.now(timezone.utc)

    commit_or_rollback(session)
    session.refresh(property_item)

    return property_item


def update_property_safety_hold(
    session: Session,
    property_item: PropertyDB,
    held: bool,
    report_id: int,
    reviewer_id: int,
):
    property_item.safety_hold = held
    property_item.safety_report_id = report_id
    property_item.safety_updated_by_id = reviewer_id
    property_item.safety_updated_at = datetime.now(timezone.utc)
    property_item.safety_version += 1
    commit_or_rollback(session)
    session.refresh(property_item)
    return property_item


def delete_property(
    session: Session,
    property_id: int
):
    property_item = get_property_by_id(
        session,
        property_id
    )

    if property_item is None:
        return None

    session.delete(property_item)
    commit_or_rollback(session)

    return property_item


def create_property(
    session: Session,
    property_data: PropertyCreate,
    owner_id: int,
    creation_key: str | None = None,
):
    new_property = PropertyDB(
        owner_id=owner_id,
        creation_key=creation_key,
        **property_data.model_dump()
    )

    session.add(new_property)
    commit_or_rollback(session)
    session.refresh(new_property)

    return new_property
