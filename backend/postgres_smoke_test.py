"""Small PostgreSQL-only smoke check used by GitHub Actions.

This is intentionally separate from the fast SQLite unit suite. It verifies that
HabitaRD's real PostgreSQL schema/update path can be created and that a minimal
user/listing flow works with the production database dialect.
"""

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.db import apply_schema_updates, engine
from backend.db_models.base import Base
from backend.db_models.property import PropertyDB
from backend.db_models.user import UserDB


def main() -> None:
    apply_schema_updates()

    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        existing_tables = set(inspect(connection).get_table_names())

    missing_tables = set(Base.metadata.tables) - existing_tables
    if missing_tables:
        raise RuntimeError(
            f"PostgreSQL schema is missing required tables: {sorted(missing_tables)}"
        )

    with Session(engine) as session:
        user = UserDB(
            name="PostgreSQL Smoke Seller",
            email="postgres-smoke@example.com",
            password=hash_password("postgres-smoke-password"),
            email_verified=True,
            role="buyer",
        )
        session.add(user)
        session.flush()

        listing = PropertyDB(
            owner_id=user.id,
            title="PostgreSQL Smoke Listing",
            image_url="https://images.example.com/postgres-smoke.jpg",
            images_json='["https://images.example.com/postgres-smoke.jpg"]',
            price=250000,
            currency="USD",
            location="Santiago",
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            listing_type="sale",
            status="available",
        )
        session.add(listing)
        session.commit()

        persisted = session.scalar(
            select(PropertyDB)
            .where(PropertyDB.id == listing.id)
            .with_for_update()
        )
        if persisted is None or persisted.owner_id != user.id:
            raise RuntimeError("PostgreSQL listing round-trip failed")
        if persisted.status != "available" or persisted.currency != "USD":
            raise RuntimeError("PostgreSQL listing values were not preserved")

        session.rollback()


if __name__ == "__main__":
    main()
