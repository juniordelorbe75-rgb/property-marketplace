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

    reporter: Mapped["UserDB"] = relationship("UserDB", back_populates="listing_reports")
    property: Mapped["PropertyDB | None"] = relationship(
        "PropertyDB",
        back_populates="reports",
    )
