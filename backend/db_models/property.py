import json
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db_models.base import Base


class PropertyDB(Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_created_id", "created_at", "id"),
        Index("ix_properties_price_id", "price", "id"),
        Index("ix_properties_currency_price_id", "currency", "price", "id"),
        Index(
            "ix_properties_status_listing_created",
            "status",
            "listing_type",
            "created_at",
        ),
        Index("ix_properties_owner_created", "owner_id", "created_at"),
        Index(
            "uq_properties_owner_creation_key",
            "owner_id",
            "creation_key",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    creation_key: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1",
    )

    description: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        default="",
        server_default=""
    )

    image_url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        default="",
        server_default=""
    )

    images_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )

    amenities_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        server_default="USD",
    )

    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    property_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    bedrooms: Mapped[int] = mapped_column(
        nullable=False
    )

    listing_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="sale",
        server_default="sale",
    )

    bathrooms: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        server_default="1"
    )

    square_feet: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["UserDB"] = relationship(
        "UserDB",
        back_populates="properties"
    )

    favorites: Mapped[list["FavoriteDB"]] = relationship(
        "FavoriteDB",
        back_populates="property",
        cascade="all, delete-orphan"
    )

    inquiries: Mapped[list["InquiryDB"]] = relationship(
        "InquiryDB",
        back_populates="property",
        cascade="all, delete-orphan"
    )

    @property
    def owner_name(self) -> str:
        return self.owner.name

    @property
    def image_urls(self) -> list[str]:
        try:
            images = json.loads(self.images_json or "[]")
        except (TypeError, json.JSONDecodeError):
            images = []

        valid_images = [image for image in images if isinstance(image, str) and image]
        if not valid_images and self.image_url:
            return [self.image_url]
        return valid_images

    @image_urls.setter
    def image_urls(self, images: list[str]) -> None:
        cleaned_images = list(dict.fromkeys(image for image in images if image))
        self.images_json = json.dumps(cleaned_images)
        self.image_url = cleaned_images[0] if cleaned_images else ""

    @property
    def amenities(self) -> list[str]:
        try:
            amenities = json.loads(self.amenities_json or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        return [item for item in amenities if isinstance(item, str)]

    @amenities.setter
    def amenities(self, values: list[str]) -> None:
        self.amenities_json = json.dumps(list(dict.fromkeys(values)))
