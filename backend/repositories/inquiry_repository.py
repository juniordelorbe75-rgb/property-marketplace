from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.db_models.inquiry import InquiryDB, InquiryMessageDB
from backend.repositories.transaction import commit_or_rollback


def get_inquiries_by_buyer(
    session: Session,
    buyer_id: int
):
    statement = (
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(
            InquiryDB.buyer_id == buyer_id
        )
        .order_by(
            InquiryDB.created_at.desc(),
            InquiryDB.id.desc(),
        )
    )

    inquiries = session.scalars(statement).all()
    annotate_unread_counts(inquiries, buyer_id)
    return inquiries


def get_inquiries_by_seller(
    session: Session,
    seller_id: int
):
    statement = (
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(
            InquiryDB.seller_id == seller_id
        )
        .order_by(
            InquiryDB.created_at.desc(),
            InquiryDB.id.desc(),
        )
    )

    inquiries = session.scalars(statement).all()
    annotate_unread_counts(inquiries, seller_id)
    return inquiries


def get_inquiry_page(
    session: Session,
    participant_field,
    user_id: int,
    *,
    status: str | None = None,
    property_id: int | None = None,
    page: int = 1,
    page_size: int = 6,
):
    base_filters = [participant_field == user_id]
    if property_id is not None:
        base_filters.append(InquiryDB.property_id == property_id)

    count_rows = session.execute(
        select(InquiryDB.status, func.count(InquiryDB.id))
        .where(*base_filters)
        .group_by(InquiryDB.status)
    ).all()
    counts = {
        "all": 0,
        "pending": 0,
        "accepted": 0,
        "rejected": 0,
        "cancelled": 0,
    }
    for inquiry_status, count in count_rows:
        if inquiry_status in counts:
            counts[inquiry_status] = count
            counts["all"] += count

    total = counts[status] if status else counts["all"]
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    item_filters = list(base_filters)
    if status:
        item_filters.append(InquiryDB.status == status)

    statement = (
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(*item_filters)
        .order_by(InquiryDB.updated_at.desc(), InquiryDB.id.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    )
    items = session.scalars(statement).all()
    annotate_unread_counts(items, user_id)
    return {
        "items": items,
        "total": total,
        "page": current_page,
        "page_size": page_size,
        "total_pages": total_pages,
        "counts": counts,
    }


def get_inquiry_page_by_buyer(session: Session, buyer_id: int, **filters):
    return get_inquiry_page(session, InquiryDB.buyer_id, buyer_id, **filters)


def get_inquiry_page_by_seller(session: Session, seller_id: int, **filters):
    return get_inquiry_page(session, InquiryDB.seller_id, seller_id, **filters)


def get_inquiry_by_id(
    session: Session,
    inquiry_id: int
):
    statement = (
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(
            InquiryDB.id == inquiry_id
        )
    )

    return session.scalar(statement)


def get_inquiry_for_update(
    session: Session,
    inquiry_id: int,
):
    statement = (
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(InquiryDB.id == inquiry_id)
        .with_for_update()
    )
    return session.scalar(statement)


def get_pending_inquiry(
    session: Session,
    property_id: int,
    buyer_id: int,
):
    statement = select(InquiryDB).where(
        InquiryDB.property_id == property_id,
        InquiryDB.buyer_id == buyer_id,
        InquiryDB.status == "pending",
    )
    return session.scalar(statement)


def get_inquiry_by_creation_key(
    session: Session,
    buyer_id: int,
    creation_key: str,
):
    return session.scalar(
        select(InquiryDB)
        .options(
            selectinload(InquiryDB.property),
            selectinload(InquiryDB.buyer),
            selectinload(InquiryDB.seller),
            selectinload(InquiryDB.messages),
        )
        .where(
            InquiryDB.buyer_id == buyer_id,
            InquiryDB.creation_key == creation_key,
        )
    )


def create_inquiry(
    session: Session,
    property_id: int,
    buyer_id: int,
    seller_id: int,
    message: str,
    creation_key: str | None = None,
):
    new_inquiry = InquiryDB(
        property_id=property_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        message=message,
        creation_key=creation_key,
    )

    session.add(new_inquiry)
    commit_or_rollback(session)
    session.refresh(new_inquiry)

    return new_inquiry


def update_inquiry_status(
    session: Session,
    inquiry: InquiryDB,
    status: str
):
    inquiry.status = status

    commit_or_rollback(session)
    session.refresh(inquiry)

    return inquiry

def reply_to_inquiry(
    session: Session,
    inquiry: InquiryDB,
    reply: str
):
    inquiry.reply = reply
    inquiry.seller_last_read_at = func.now()

    commit_or_rollback(session)
    session.refresh(inquiry)

    return inquiry


def add_inquiry_message(
    session: Session,
    inquiry: InquiryDB,
    sender_id: int,
    body: str,
    creation_key: str | None = None,
):
    message = InquiryMessageDB(
        inquiry_id=inquiry.id,
        sender_id=sender_id,
        body=body,
        creation_key=creation_key,
        created_at=datetime.now(timezone.utc),
    )
    session.add(message)
    read_at = datetime.now(timezone.utc)
    if sender_id == inquiry.buyer_id:
        inquiry.buyer_last_read_at = read_at
    else:
        inquiry.seller_last_read_at = read_at
    inquiry.updated_at = func.now()
    commit_or_rollback(session)
    session.refresh(inquiry)
    return inquiry


def get_message_by_creation_key(
    session: Session,
    sender_id: int,
    creation_key: str,
):
    return session.scalar(
        select(InquiryMessageDB).where(
            InquiryMessageDB.sender_id == sender_id,
            InquiryMessageDB.creation_key == creation_key,
        )
    )


def get_inquiries_for_participant(
    session: Session,
    inquiry_ids: list[int],
    user_id: int,
):
    return session.scalars(
        select(InquiryDB)
        .where(
            InquiryDB.id.in_(inquiry_ids),
            or_(InquiryDB.buyer_id == user_id, InquiryDB.seller_id == user_id),
        )
        .with_for_update()
    ).all()


def get_inquiry_unread_count(session: Session, user_id: int) -> int:
    unread_initial_inquiries = session.scalar(
        select(func.count(InquiryDB.id)).where(
            InquiryDB.seller_id == user_id,
            InquiryDB.seller_last_read_at.is_(None),
        )
    ) or 0
    unread_legacy_replies = session.scalar(
        select(func.count(InquiryDB.id)).where(
            InquiryDB.buyer_id == user_id,
            InquiryDB.reply.is_not(None),
            InquiryDB.buyer_last_read_at.is_(None),
        )
    ) or 0
    unread_thread_messages = session.scalar(
        select(func.count(InquiryMessageDB.id))
        .join(InquiryDB, InquiryDB.id == InquiryMessageDB.inquiry_id)
        .where(
            InquiryMessageDB.sender_id != user_id,
            or_(
                and_(
                    InquiryDB.buyer_id == user_id,
                    or_(
                        InquiryDB.buyer_last_read_at.is_(None),
                        InquiryMessageDB.created_at > InquiryDB.buyer_last_read_at,
                    ),
                ),
                and_(
                    InquiryDB.seller_id == user_id,
                    or_(
                        InquiryDB.seller_last_read_at.is_(None),
                        InquiryMessageDB.created_at > InquiryDB.seller_last_read_at,
                    ),
                ),
            ),
        )
    ) or 0
    return unread_initial_inquiries + unread_legacy_replies + unread_thread_messages


def mark_inquiries_read(
    session: Session,
    inquiries: list[InquiryDB],
    user_id: int,
    read_through_by_id: dict[int, datetime],
) -> None:
    now = datetime.now(timezone.utc)
    for inquiry in inquiries:
        read_at = min(_as_utc(read_through_by_id[inquiry.id]), now)
        if inquiry.buyer_id == user_id:
            if (
                inquiry.buyer_last_read_at is None
                or read_at > _as_utc(inquiry.buyer_last_read_at)
            ):
                inquiry.buyer_last_read_at = read_at
        else:
            if (
                inquiry.seller_last_read_at is None
                or read_at > _as_utc(inquiry.seller_last_read_at)
            ):
                inquiry.seller_last_read_at = read_at
    commit_or_rollback(session)


def annotate_unread_counts(inquiries, user_id: int) -> None:
    for inquiry in inquiries:
        last_read = (
            inquiry.buyer_last_read_at
            if inquiry.buyer_id == user_id
            else inquiry.seller_last_read_at
        )
        unread_count = 0
        if inquiry.seller_id == user_id and last_read is None:
            unread_count += 1
        if inquiry.buyer_id == user_id and inquiry.reply and last_read is None:
            unread_count += 1
        unread_count += sum(
            1
            for message in inquiry.messages
            if message.sender_id != user_id
            and (last_read is None or _as_utc(message.created_at) > _as_utc(last_read))
        )
        inquiry.unread_count = unread_count


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
