import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db_models.base import Base


class ListingSourceDB(Base):
    __tablename__ = "listing_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    license_name: Mapped[str] = mapped_column(String(150), nullable=False)
    license_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    attribution: Mapped[str] = mapped_column(String(300), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    permission_document_url: Mapped[str | None] = mapped_column(String(2000))
    permission_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permission_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[int | None] = mapped_column(Integer)
    stale_after_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48, server_default="48")
    last_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    listings: Mapped[list["ExternalListingDB"]] = relationship(back_populates="source")
    audit_events: Mapped[list["ListingFeedAuditDB"]] = relationship(back_populates="source")


class ExternalListingDB(Base):
    __tablename__ = "external_listings"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_external_listing_source_identity"),
        Index("ix_external_listing_public_search", "is_public", "status", "country_code", "province"),
        Index("ix_external_listing_updated", "source_updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("listing_sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    listing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    sector: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    property_type: Mapped[str] = mapped_column(String(100), nullable=False)
    bedrooms: Mapped[int | None] = mapped_column()
    bathrooms: Mapped[float | None] = mapped_column(Float)
    area_sqm: Mapped[float | None] = mapped_column(Float)
    images_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    amenities_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    source: Mapped[ListingSourceDB] = relationship(back_populates="listings")

    @property
    def image_urls(self) -> list[str]:
        try:
            values = json.loads(self.images_json)
        except (TypeError, json.JSONDecodeError):
            return []
        return [value for value in values if isinstance(value, str)]

    @property
    def amenities(self) -> list[str]:
        try:
            values = json.loads(self.amenities_json)
        except (TypeError, json.JSONDecodeError):
            return []
        return [value for value in values if isinstance(value, str)]


class ListingFeedAuditDB(Base):
    __tablename__ = "listing_feed_audit"
    __table_args__ = (Index("ix_listing_feed_audit_source_created", "source_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("listing_sources.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(Integer)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source: Mapped[ListingSourceDB] = relationship(back_populates="audit_events")
