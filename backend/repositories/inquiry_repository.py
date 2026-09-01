from sqlalchemy import func, select
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

    return session.scalars(statement).all()


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

    return session.scalars(statement).all()


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
    return {
        "items": session.scalars(statement).all(),
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
    )
    session.add(message)
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
