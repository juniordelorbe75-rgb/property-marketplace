from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db_models.base import Base


class ListingReportDB(Base):
    __tablename__ = "listing_reports"
    __table_args__ = (
        Index(
            "uq_listing_reports_reporter_listing",
            "reporter_id",
            "listing_id",
            unique=True,
        ),
        Index(
            "uq_listing_reports_reporter_creation_key",
            "reporter_id",
            "creation_key",
            unique=True,
        ),
        Index("ix_listing_reports_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
    )
    listing_id: Mapped[int] = mapped_column(nullable=False)
    listing_title: Mapped[str] = mapped_column(String(255), nullable=False)
    listing_owner_id: Mapped[int] = mapped_column(nullable=False)
    listing_owner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="submitted",
        server_default="submitted",
    )
    moderator_note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )
    creation_key: Mapped[str] = mapped_column(String(36), nullable=False)
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

    reporter: Mapped["UserDB"] = relationship(
        "UserDB",
        foreign_keys=[reporter_id],
        back_populates="listing_reports",
    )
    reviewer: Mapped["UserDB | None"] = relationship(
        "UserDB",
        foreign_keys=[reviewed_by_id],
        back_populates="reviewed_listing_reports",
    )
    listing: Mapped["PropertyDB | None"] = relationship(
        "PropertyDB",
        back_populates="reports",
    )

    @property
    def reporter_name(self) -> str:
        return self.reporter.name

    @property
    def reviewer_name(self) -> str | None:
        return self.reviewer.name if self.reviewer else None

    @property
    def listing_on_safety_hold(self) -> bool | None:
        return self.listing.safety_hold if self.listing else None

    @property
    def listing_safety_version(self) -> int | None:
        return self.listing.safety_version if self.listing else None
