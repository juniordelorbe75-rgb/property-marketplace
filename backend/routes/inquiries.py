from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from typing import Literal
from uuid import UUID

from backend.auth.dependencies import get_current_user_id
from backend.db import get_db
from backend.models import Inquiry, InquiryPage
from backend.services.inquiry_service import (
    cancel_inquiry,
    create_inquiry,
    get_sent_inquiries,
    get_received_inquiries,
    get_sent_inquiry_page,
    get_received_inquiry_page,
    update_inquiry_status,
    reply_to_inquiry,
    add_inquiry_message,
)


class InquiryCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty")
        return value.strip()

class InquiryStatusUpdate(BaseModel):
    status: Literal["pending", "accepted", "rejected"]

class InquiryReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1000)

    @field_validator("reply")
    @classmethod
    def strip_reply(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reply cannot be empty")
        return value.strip()


class InquiryMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty")
        return value.strip()


router = APIRouter(
    prefix="/inquiries",
    tags=["Inquiries"]
)


@router.post(
    "/{property_id}",
    response_model=Inquiry
)
def send_inquiry(
    property_id: int,
    inquiry_data: InquiryCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return create_inquiry(
        session=session,
        property_id=property_id,
        current_user_id=current_user_id,
        message=inquiry_data.message,
        creation_key=str(idempotency_key) if idempotency_key else None,
    )


@router.get(
    "/sent",
    response_model=list[Inquiry]
)
def get_sent(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return get_sent_inquiries(
        session,
        current_user_id
    )


@router.get(
    "/received",
    response_model=list[Inquiry]
)
def get_received(
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return get_received_inquiries(
        session,
        current_user_id
    )

@router.patch(
    "/{inquiry_id}/status",
    response_model=Inquiry
)
def update_status(
    inquiry_id: int,
    status_data: InquiryStatusUpdate,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return update_inquiry_status(
        session=session,
        inquiry_id=inquiry_id,
        current_user_id=current_user_id,
        status=status_data.status
    )


@router.patch(
    "/{inquiry_id}/reply",
    response_model=Inquiry
)
def reply(
    inquiry_id: int,
    reply_data: InquiryReply,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return reply_to_inquiry(
        session=session,
        inquiry_id=inquiry_id,
        current_user_id=current_user_id,
        reply=reply_data.reply
    )


@router.post("/{inquiry_id}/messages", response_model=Inquiry)
def send_message(
    inquiry_id: int,
    message_data: InquiryMessageCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return add_inquiry_message(
        session=session,
        inquiry_id=inquiry_id,
        current_user_id=current_user_id,
        body=message_data.message,
        creation_key=str(idempotency_key) if idempotency_key else None,
    )


@router.get("/sent/page", response_model=InquiryPage)
def get_sent_page(
    status: Literal["pending", "accepted", "rejected", "cancelled"] | None = None,
    property_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=50),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_sent_inquiry_page(
        session,
        current_user_id,
        status=status,
        property_id=property_id,
        page=page,
        page_size=page_size,
    )


@router.get("/received/page", response_model=InquiryPage)
def get_received_page(
    status: Literal["pending", "accepted", "rejected", "cancelled"] | None = None,
    property_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=50),
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    return get_received_inquiry_page(
        session,
        current_user_id,
        status=status,
        property_id=property_id,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{inquiry_id}/cancel",
    response_model=Inquiry
)
def cancel(
    inquiry_id: int,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db)
):
    return cancel_inquiry(
        session=session,
        inquiry_id=inquiry_id,
        current_user_id=current_user_id,
    )
