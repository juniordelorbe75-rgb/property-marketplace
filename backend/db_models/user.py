from datetime import date

from sqlalchemy import Boolean, Date, String
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

    has_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

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

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    middle_name: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    bio: Mapped[str] = mapped_column(String(1000), nullable=False, default="", server_default="")
    public_profile_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    public_name_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="first_name", server_default="first_name")
    public_bio_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

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

    social_identities: Mapped[list["SocialIdentityDB"]] = relationship(
        "SocialIdentityDB",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def public_display_name(self) -> str:
        first_name = self.first_name or self.name.strip().split()[0]
        if self.public_profile_enabled and self.public_name_mode == "full_name":
            return self.name
        return first_name
