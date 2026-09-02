from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models import PropertyCreate, PropertyUpdate
from backend.image_storage import delete_uploaded_property_image
from backend.repositories import property_repository, user_repository


def get_all_properties(
    session: Session,
    limit: int | None = None,
    offset: int = 0,
):
    return property_repository.get_all_properties(
        session,
        limit=limit,
        offset=offset,
    )


def get_property_by_id(
    session: Session,
    property_id: int
):
    property = property_repository.get_property_by_id(
        session,
        property_id
    )

    if property is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )

    return property


def search_properties(
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
    sort_by: str = "newest",
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    if (
        (min_price is not None or max_price is not None or sort_by.startswith("price_"))
        and currency is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Choose a currency before filtering or sorting by price",
        )
    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=400,
            detail="Minimum price cannot be greater than maximum price"
        )

    return property_repository.search_properties(
        session=session,
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
        sort_by=sort_by,
        status=status,
        limit=limit,
        offset=offset,
    )


def get_property_engagement(session: Session, current_user_id: int):
    return property_repository.get_property_engagement(session, current_user_id)


def update_property(
    session: Session,
    property_id: int,
    updated_property: PropertyUpdate,
    current_user_id: int,
    expected_version: int | None = None,
):
    property = property_repository.get_property_for_update(
        session,
        property_id
    )

    if property is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )

    if property.owner_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this property"
        )

    if expected_version is not None and property.version != expected_version:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "This listing changed after you opened it. "
                "Cancel editing and reopen it before saving again."
            ),
        )

    if property.safety_hold and updated_property.status == "available":
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "This listing is temporarily unavailable during a safety review. "
                "You can edit its details, but it cannot be marked available yet."
            ),
        )

    previous_image_urls = set(property.image_urls)
    updated = property_repository.update_property(
        session,
        property_id,
        updated_property
    )
    for removed_image_url in previous_image_urls - set(updated.image_urls):
        if not property_repository.is_image_url_in_use(session, removed_image_url):
            delete_uploaded_property_image(removed_image_url)
    return updated


def delete_property(
        session: Session,
        property_id: int,
        current_user_id: int,
        expected_version: int | None = None,
):
    property = property_repository.get_property_for_update(
        session,
        property_id
    )

    if property is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )

    if property.owner_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this property"
        )

    if expected_version is not None and property.version != expected_version:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "This listing changed after you opened it. "
                "Reload the current listing before deleting it."
            ),
        )

    image_urls = property.image_urls
    deleted = property_repository.delete_property(
        session,
        property_id
    )
    for image_url in image_urls:
        if not property_repository.is_image_url_in_use(session, image_url):
            delete_uploaded_property_image(image_url)
    return deleted


def create_property(
        session: Session,
        property_data: PropertyCreate,
        current_user_id: int,
        creation_key: str | None = None,
):
    current_user = user_repository.get_user_by_id(
        session,
        current_user_id
    )

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="User account no longer exists"
        )

    if creation_key:
        existing = property_repository.get_property_by_creation_key(
            session, current_user_id, creation_key
        )
        if existing is not None:
            return existing

    try:
        return property_repository.create_property(
            session,
            property_data,
            current_user_id,
            creation_key=creation_key,
        )
    except IntegrityError:
        if not creation_key:
            raise
        existing = property_repository.get_property_by_creation_key(
            session, current_user_id, creation_key
        )
        if existing is None:
            raise
        return existing

def get_my_properties(
    session: Session,
    current_user_id: int
):
    return property_repository.get_my_properties(
        session,
        current_user_id
    )


def get_seller_dashboard_stats(session: Session, current_user_id: int):
    return property_repository.get_seller_dashboard_stats(
        session,
        current_user_id,
    )
