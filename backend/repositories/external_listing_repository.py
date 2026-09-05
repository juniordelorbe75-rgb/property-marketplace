import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.db_models.external_listing import ExternalListingDB, ListingFeedAuditDB, ListingSourceDB
from backend.feed_models import ListingFeedBatch
from backend.repositories.transaction import commit_or_rollback


PUBLIC_STATUSES = {"active"}


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _audit(session: Session, source_id: int, event_type: str, details: dict, actor_user_id: int | None = None):
    session.add(ListingFeedAuditDB(
        source_id=source_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        details_json=json.dumps(details, sort_keys=True),
    ))


def import_feed_batch(
    session: Session,
    batch: ListingFeedBatch,
    *,
    allow_empty_snapshot: bool = False,
) -> dict[str, int]:
    try:
        return _import_feed_batch(
            session,
            batch,
            allow_empty_snapshot=allow_empty_snapshot,
        )
    except Exception:
        session.rollback()
        raise


def _import_feed_batch(
    session: Session,
    batch: ListingFeedBatch,
    *,
    allow_empty_snapshot: bool,
) -> dict[str, int]:
    external_ids = [record.external_id for record in batch.records]
    if len(external_ids) != len(set(external_ids)):
        raise ValueError("Feed snapshot contains duplicate external listing IDs")

    source = session.scalar(select(ListingSourceDB).where(ListingSourceDB.source_key == batch.source.source_key))
    if source is None:
        source = ListingSourceDB(
            **batch.source.model_dump(exclude={"permits_commercial_display"}),
            approved=False,
        )
        session.add(source)
        session.flush()
    else:
        if (
            source.last_retrieved_at is not None
            and _as_utc(batch.retrieved_at) < _as_utc(source.last_retrieved_at)
        ):
            raise ValueError("Feed snapshot is older than the last successful import")
        for field, value in batch.source.model_dump(exclude={"source_key", "permits_commercial_display"}).items():
            setattr(source, field, value)

    source.last_retrieved_at = batch.retrieved_at
    existing = {
        item.external_id: item
        for item in session.scalars(
            select(ExternalListingDB).where(ExternalListingDB.source_id == source.id)
        )
    }
    if existing and not batch.records and not allow_empty_snapshot:
        raise ValueError(
            "Empty feed snapshot requires explicit confirmation before withdrawing existing listings"
        )
    received_ids = set()
    created = updated = withdrawn = 0

    for record in batch.records:
        received_ids.add(record.external_id)
        item = existing.get(record.external_id)
        if item is None:
            item = ExternalListingDB(source_id=source.id, external_id=record.external_id)
            session.add(item)
            created += 1
        else:
            updated += 1
        values = record.model_dump(exclude={"external_id", "image_urls", "amenities"})
        for field, value in values.items():
            setattr(item, "source_updated_at" if field == "updated_at" else field, value)
        item.images_json = json.dumps(record.image_urls)
        item.amenities_json = json.dumps(record.amenities)
        item.retrieved_at = batch.retrieved_at
        permission_current = (
            source.approved
            and source.approval_status == "approved"
            and source.permission_document_url
            and (
                source.permission_expires_at is None
                or _as_utc(source.permission_expires_at) > _as_utc(batch.retrieved_at)
            )
        )
        item.is_public = bool(permission_current and record.status in PUBLIC_STATUSES)

    for external_id, item in existing.items():
        if external_id not in received_ids and item.status != "withdrawn":
            item.status = "withdrawn"
            item.is_public = False
            item.retrieved_at = batch.retrieved_at
            withdrawn += 1

    result = {"created": created, "updated": updated, "withdrawn": withdrawn}
    _audit(session, source.id, "feed_imported", {**result, "retrieved_at": batch.retrieved_at.isoformat()})
    commit_or_rollback(session)
    return result


def set_source_approval(
    session: Session, source: ListingSourceDB, *, approved: bool,
    actor_user_id: int, permission_document_url: str | None = None,
    permission_expires_at: datetime | None = None, stale_after_hours: int | None = None,
) -> ListingSourceDB:
    now = datetime.now(timezone.utc)
    if approved and not permission_document_url:
        raise ValueError("Approval requires a permission document URL")
    if approved and permission_expires_at is not None and _as_utc(permission_expires_at) <= now:
        raise ValueError("Permission expiration must be in the future")
    source.approved = approved
    source.approval_status = "approved" if approved else "revoked"
    source.permission_document_url = permission_document_url if approved else source.permission_document_url
    source.permission_approved_at = now if approved else source.permission_approved_at
    source.permission_expires_at = permission_expires_at if approved else now
    source.approved_by_id = actor_user_id
    if stale_after_hours is not None:
        source.stale_after_hours = stale_after_hours
    if not approved:
        for listing in source.listings:
            listing.is_public = False
    _audit(session, source.id, "source_approved" if approved else "source_revoked", {
        "permission_document_url": source.permission_document_url,
        "permission_expires_at": source.permission_expires_at.isoformat() if source.permission_expires_at else None,
        "stale_after_hours": source.stale_after_hours,
    }, actor_user_id)
    commit_or_rollback(session)
    return source


def withdraw_stale_listings(session: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    withdrawn = 0
    sources = session.scalars(select(ListingSourceDB).options(selectinload(ListingSourceDB.listings))).all()
    for source in sources:
        expires_at = _as_utc(source.permission_expires_at)
        retrieved_at = _as_utc(source.last_retrieved_at)
        comparison_time = _as_utc(now)
        expired = expires_at is not None and expires_at <= comparison_time
        stale = retrieved_at is None or retrieved_at <= comparison_time - timedelta(hours=source.stale_after_hours)
        if not (expired or stale):
            continue
        source_count = 0
        for listing in source.listings:
            if listing.is_public:
                listing.is_public = False
                source_count += 1
        if source_count:
            withdrawn += source_count
            _audit(session, source.id, "listings_unpublished", {
                "count": source_count,
                "reason": "permission_expired" if expired else "feed_stale",
            })
    commit_or_rollback(session)
    return withdrawn


def _public_catalog_statement(
    location=None, min_price=None, max_price=None, currency=None,
    property_type=None, listing_type=None, bedrooms=None, bathrooms=None,
    min_area_sqm=None,
):
    statement = select(ExternalListingDB).where(
        ExternalListingDB.is_public.is_(True), ExternalListingDB.status == "active"
    )
    if location:
        term = f"%{location}%"
        statement = statement.where(
            ExternalListingDB.province.ilike(term)
            | ExternalListingDB.municipality.ilike(term)
            | ExternalListingDB.sector.ilike(term)
        )
    if min_price is not None:
        statement = statement.where(ExternalListingDB.price >= min_price)
    if max_price is not None:
        statement = statement.where(ExternalListingDB.price <= max_price)
    if currency:
        statement = statement.where(ExternalListingDB.currency == currency)
    if property_type:
        statement = statement.where(ExternalListingDB.property_type.ilike(f"%{property_type}%"))
    if listing_type:
        statement = statement.where(ExternalListingDB.listing_type == listing_type)
    if bedrooms is not None:
        statement = statement.where(ExternalListingDB.bedrooms >= bedrooms)
    if bathrooms is not None:
        statement = statement.where(ExternalListingDB.bathrooms >= bathrooms)
    if min_area_sqm is not None:
        statement = statement.where(ExternalListingDB.area_sqm >= min_area_sqm)
    return statement


def get_public_external_listings(session: Session, limit: int = 20, offset: int = 0, **filters):
    statement = (
        _public_catalog_statement(**filters)
        .options(selectinload(ExternalListingDB.source))
        .order_by(ExternalListingDB.source_updated_at.desc(), ExternalListingDB.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return session.scalars(statement).all()


def count_public_external_listings(session: Session, **filters) -> int:
    filtered = _public_catalog_statement(**filters).subquery()
    return session.scalar(select(func.count()).select_from(filtered)) or 0
