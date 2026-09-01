from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db_models.base import Base


class FavoriteDB(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "property_id",
            name="uq_favorites_user_property",
        ),
        Index("ix_favorites_property_id", "property_id"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id"),
        nullable=False
    )

    user: Mapped["UserDB"] = relationship(
        "UserDB",
        back_populates="favorites"
    )

    property: Mapped["PropertyDB"] = relationship(
        "PropertyDB",
        back_populates = "favorites"
    )
