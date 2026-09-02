from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db_models.base import Base


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="buyer"
    )

    properties: Mapped[list["PropertyDB"]] = relationship(
        "PropertyDB",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    token_generation: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )

    favorites: Mapped[list["FavoriteDB"]] = relationship(
        "FavoriteDB",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    sent_inquiries: Mapped[list["InquiryDB"]] = relationship(
        "InquiryDB",
        foreign_keys="InquiryDB.buyer_id",
        back_populates="buyer",
        cascade="all, delete-orphan"
    )

    received_inquiries: Mapped[list["InquiryDB"]] = relationship(
        "InquiryDB",
        foreign_keys="InquiryDB.seller_id",
        back_populates="seller",
        cascade="all, delete-orphan"
    )

    listing_reports: Mapped[list["ListingReportDB"]] = relationship(
        "ListingReportDB",
        foreign_keys="ListingReportDB.reporter_id",
        back_populates="reporter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    reviewed_listing_reports: Mapped[list["ListingReportDB"]] = relationship(
        "ListingReportDB",
        foreign_keys="ListingReportDB.reviewed_by_id",
        back_populates="reviewer",
        passive_deletes=True,
    )
