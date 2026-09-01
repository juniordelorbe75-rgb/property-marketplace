from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.repositories import (
    inquiry_repository,
    property_repository,
)


def create_inquiry(
    session: Session,
    property_id: int,
    current_user_id: int,
    message: str,
    creation_key: str | None = None,
):
    if creation_key:
        existing_by_key = inquiry_repository.get_inquiry_by_creation_key(
            session, current_user_id, creation_key
        )
        if existing_by_key is not None:
            return existing_by_key

    property_item = property_repository.get_property_for_update(
        session,
        property_id
    )

    if property_item is None:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )

    seller_id = property_item.owner_id

    if seller_id == current_user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send an inquiry about your own property"
        )

    if property_item.status.lower() != "available":
        raise HTTPException(
            status_code=400,
            detail="This property is not available for inquiries"
        )

    existing_inquiry = inquiry_repository.get_pending_inquiry(
        session=session,
        property_id=property_id,
        buyer_id=current_user_id,
    )

    if existing_inquiry is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending inquiry for this property"
        )

    try:
        return inquiry_repository.create_inquiry(
            session=session,
            property_id=property_id,
            buyer_id=current_user_id,
            seller_id=seller_id,
            message=message,
            creation_key=creation_key,
        )
    except IntegrityError as error:
        if creation_key:
            existing_by_key = inquiry_repository.get_inquiry_by_creation_key(
                session, current_user_id, creation_key
            )
            if existing_by_key is not None:
                return existing_by_key
        raise HTTPException(
            status_code=409,
            detail="You already have a pending inquiry for this property"
        ) from error


def get_sent_inquiries(
    session: Session,
    current_user_id: int
):
    return inquiry_repository.get_inquiries_by_buyer(
        session,
        current_user_id
    )


def get_received_inquiries(
    session: Session,
    current_user_id: int
):
    return inquiry_repository.get_inquiries_by_seller(
        session,
        current_user_id
    )


def update_inquiry_status(
    session: Session,
    inquiry_id: int,
    current_user_id: int,
    status: str
):
    inquiry = inquiry_repository.get_inquiry_for_update(
        session,
        inquiry_id
    )

    if inquiry is None:
        raise HTTPException(
            status_code=404,
            detail="Inquiry not found"
        )

    if inquiry.seller_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update inquiries you received"
        )

    if inquiry.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending inquiries can be updated"
        )

    if status not in [
        "pending",
        "accepted",
        "rejected"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid inquiry status"
        )

    return inquiry_repository.update_inquiry_status(
        session=session,
        inquiry=inquiry,
        status=status
    )


def get_sent_inquiry_page(session: Session, current_user_id: int, **filters):
    return inquiry_repository.get_inquiry_page_by_buyer(
        session, current_user_id, **filters
    )


def get_received_inquiry_page(session: Session, current_user_id: int, **filters):
    return inquiry_repository.get_inquiry_page_by_seller(
        session, current_user_id, **filters
    )


def cancel_inquiry(
    session: Session,
    inquiry_id: int,
    current_user_id: int,
):
    inquiry = inquiry_repository.get_inquiry_for_update(session, inquiry_id)

    if inquiry is None:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if inquiry.buyer_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only cancel inquiries you sent"
        )

    if inquiry.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending inquiries can be cancelled"
        )

    return inquiry_repository.update_inquiry_status(
        session=session,
        inquiry=inquiry,
        status="cancelled"
    )


def reply_to_inquiry(
    session: Session,
    inquiry_id: int,
    current_user_id: int,
    reply: str
):
    inquiry = inquiry_repository.get_inquiry_for_update(
        session,
        inquiry_id
    )

    if inquiry is None:
        raise HTTPException(
            status_code=404,
            detail="Inquiry not found"
        )

    if inquiry.seller_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only reply to inquiries you received"
        )

    if inquiry.status in {"cancelled", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Closed inquiries cannot be replied to"
        )

    if not reply.strip():
        raise HTTPException(
            status_code=400,
            detail="Reply cannot be empty"
        )

    return inquiry_repository.reply_to_inquiry(
        session=session,
        inquiry=inquiry,
        reply=reply
    )


def add_inquiry_message(
    session: Session,
    inquiry_id: int,
    current_user_id: int,
    body: str,
    creation_key: str | None = None,
):
    inquiry = inquiry_repository.get_inquiry_for_update(session, inquiry_id)
    if inquiry is None:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if current_user_id not in {inquiry.buyer_id, inquiry.seller_id}:
        raise HTTPException(
            status_code=403,
            detail="You can only message inquiries you participate in",
        )
    clean_body = body.strip()
    if creation_key:
        existing = inquiry_repository.get_message_by_creation_key(
            session, current_user_id, creation_key
        )
        if existing is not None:
            if existing.inquiry_id != inquiry_id or existing.body != clean_body:
                raise HTTPException(
                    status_code=409,
                    detail="This message retry key was already used for different content",
                )
            return inquiry
    if inquiry.status in {"cancelled", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Closed inquiries cannot receive messages",
        )
    if not clean_body:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        return inquiry_repository.add_inquiry_message(
            session=session,
            inquiry=inquiry,
            sender_id=current_user_id,
            body=clean_body,
            creation_key=creation_key,
        )
    except IntegrityError as error:
        if creation_key:
            existing = inquiry_repository.get_message_by_creation_key(
                session, current_user_id, creation_key
            )
            if (
                existing is not None
                and existing.inquiry_id == inquiry_id
                and existing.body == clean_body
            ):
                return inquiry_repository.get_inquiry_by_id(session, inquiry_id)
        raise HTTPException(
            status_code=409,
            detail="This message could not be safely retried",
        ) from error
