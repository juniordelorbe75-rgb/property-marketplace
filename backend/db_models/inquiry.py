import builtins
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db_models.base import Base


class InquiryDB(Base):
    __tablename__ = "inquiries"
    __table_args__ = (
        Index("ix_inquiries_buyer_updated", "buyer_id", "updated_at"),
        Index("ix_inquiries_buyer_status_updated", "buyer_id", "status", "updated_at"),
        Index("ix_inquiries_seller_status_updated", "seller_id", "status", "updated_at"),
        Index("ix_inquiries_property_id", "property_id"),
        Index(
            "uq_inquiries_buyer_creation_key",
            "buyer_id",
            "creation_key",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"),
        nullable=False
    )

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    reply: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending"
    )

    creation_key: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    property: Mapped["PropertyDB"] = relationship(
        "PropertyDB",
        back_populates="inquiries"
    )

    buyer: Mapped["UserDB"] = relationship(
        "UserDB",
        foreign_keys=[buyer_id],
        back_populates="sent_inquiries"
    )

    seller: Mapped["UserDB"] = relationship(
        "UserDB",
        foreign_keys=[seller_id],
        back_populates="received_inquiries"
    )

    messages: Mapped[list["InquiryMessageDB"]] = relationship(
        "InquiryMessageDB",
        back_populates="inquiry",
        cascade="all, delete-orphan",
        order_by="InquiryMessageDB.created_at, InquiryMessageDB.id",
    )

    @builtins.property
    def property_title(self) -> str:
        return self.property.title

    @builtins.property
    def buyer_name(self) -> str:
        return self.buyer.name

    @builtins.property
    def seller_name(self) -> str:
        return self.seller.name

    @builtins.property
    def conversation_messages(self) -> list[dict]:
        conversation = [
            {
                "id": None,
                "sender_id": self.buyer_id,
                "sender_role": "buyer",
                "sender_name": self.buyer_name,
                "body": self.message,
                "created_at": self.created_at,
            }
        ]
        if self.reply:
            conversation.append(
                {
                    "id": None,
                    "sender_id": self.seller_id,
                    "sender_role": "seller",
                    "sender_name": self.seller_name,
                    "body": self.reply,
                    "created_at": self.updated_at,
                }
            )
        conversation.extend(
                {
                    "id": item.id,
                    "sender_id": item.sender_id,
                    "sender_role": "buyer" if item.sender_id == self.buyer_id else "seller",
                    "sender_name": self.buyer_name if item.sender_id == self.buyer_id else self.seller_name,
                    "body": item.body,
                    "created_at": item.created_at,
                }
                for item in self.messages
            )
        return conversation


class InquiryMessageDB(Base):
    __tablename__ = "inquiry_messages"
    __table_args__ = (
        Index("ix_inquiry_messages_inquiry_created", "inquiry_id", "created_at"),
        Index(
            "uq_inquiry_messages_sender_creation_key",
            "sender_id",
            "creation_key",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id"),
        nullable=False,
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    creation_key: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    inquiry: Mapped["InquiryDB"] = relationship(
        "InquiryDB",
        back_populates="messages",
    )
