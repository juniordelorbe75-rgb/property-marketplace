import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from backend.db_models.base import Base
from backend.db_models.user import UserDB
from backend.db_models.property import PropertyDB
from backend.db_models.inquiry import InquiryDB, InquiryMessageDB
from backend.db_models.favorite import FavoriteDB
from backend.db_models.report import ListingReportDB
from backend.db_models.social_identity import SocialIdentityDB

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    hide_parameters=True,
)

Base.metadata.create_all(bind=engine)


def ensure_schema_safety():
    with engine.begin() as connection:
        user_columns = {
            column["name"]
            for column in inspect(connection).get_columns("users")
        }
        if "token_generation" not in user_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN token_generation INTEGER NOT NULL DEFAULT 1
                    """
                )
            )

        if "has_password" not in user_columns:
            connection.execute(text(
                "ALTER TABLE users ADD COLUMN has_password BOOLEAN NOT NULL DEFAULT TRUE"
            ))

        user_profile_columns = (
            ("first_name", "VARCHAR(100) NOT NULL DEFAULT ''"),
            ("middle_name", "VARCHAR(100) NOT NULL DEFAULT ''"),
            ("last_name", "VARCHAR(100) NOT NULL DEFAULT ''"),
            ("date_of_birth", "DATE"),
            ("bio", "VARCHAR(1000) NOT NULL DEFAULT ''"),
            ("public_profile_enabled", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("public_name_mode", "VARCHAR(20) NOT NULL DEFAULT 'first_name'"),
            ("public_bio_visible", "BOOLEAN NOT NULL DEFAULT FALSE"),
        )
        for column_name, column_definition in user_profile_columns:
            if column_name not in user_columns:
                connection.execute(text(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"
                ))

        property_columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }

        if "description" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN description VARCHAR(2000) NOT NULL DEFAULT ''
                    """
                )
            )

        if "image_url" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN image_url VARCHAR(2000) NOT NULL DEFAULT ''
                    """
                )
            )

        if "images_json" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN images_json TEXT NOT NULL DEFAULT '[]'
                    """
                )
            )

        if "bathrooms" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN bathrooms INTEGER NOT NULL DEFAULT 1
                    """
                )
            )

        if "listing_type" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN listing_type VARCHAR(20) NOT NULL DEFAULT 'sale'
                    """
                )
            )

        if "currency" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'USD'
                    """
                )
            )

        if "amenities_json" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN amenities_json TEXT NOT NULL DEFAULT '[]'
                    """
                )
            )

        if "square_feet" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN square_feet INTEGER NOT NULL DEFAULT 0
                    """
                )
            )

        if "created_at" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN created_at TIMESTAMP WITH TIME ZONE
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """
                )
            )

        if "updated_at" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE properties
                    SET updated_at = created_at
                    """
                )
            )

        if "creation_key" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN creation_key VARCHAR(36)
                    """
                )
            )

        if "version" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN version INTEGER NOT NULL DEFAULT 1
                    """
                )
            )

        if "safety_hold" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN safety_hold BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
            )

        if "safety_version" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN safety_version INTEGER NOT NULL DEFAULT 1
                    """
                )
            )

        if "safety_report_id" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN safety_report_id INTEGER
                    """
                )
            )

        if "safety_updated_by_id" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN safety_updated_by_id INTEGER
                    """
                )
            )

        if "safety_updated_at" not in property_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE properties
                    ADD COLUMN safety_updated_at TIMESTAMP WITH TIME ZONE
                    """
                )
            )

        inquiry_columns = {
            column["name"]
            for column in inspect(connection).get_columns("inquiries")
        }

        if "created_at" not in inquiry_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiries
                    ADD COLUMN created_at TIMESTAMP WITH TIME ZONE
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """
                )
            )

        if "updated_at" not in inquiry_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiries
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """
                )
            )

        if "creation_key" not in inquiry_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiries
                    ADD COLUMN creation_key VARCHAR(36)
                    """
                )
            )

        if "buyer_last_read_at" not in inquiry_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiries
                    ADD COLUMN buyer_last_read_at TIMESTAMP WITH TIME ZONE
                    """
                )
            )

        if "seller_last_read_at" not in inquiry_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiries
                    ADD COLUMN seller_last_read_at TIMESTAMP WITH TIME ZONE
                    """
                )
            )

        inquiry_message_columns = {
            column["name"]
            for column in inspect(connection).get_columns("inquiry_messages")
        }
        if "creation_key" not in inquiry_message_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE inquiry_messages
                    ADD COLUMN creation_key VARCHAR(36)
                    """
                )
            )

        report_columns = {
            column["name"]
            for column in inspect(connection).get_columns("listing_reports")
        }
        if "moderator_note" not in report_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE listing_reports
                    ADD COLUMN moderator_note TEXT NOT NULL DEFAULT ''
                    """
                )
            )
        if "reviewed_by_id" not in report_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE listing_reports
                    ADD COLUMN reviewed_by_id INTEGER
                    REFERENCES users(id) ON DELETE SET NULL
                    """
                )
            )
        if "reviewed_at" not in report_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE listing_reports
                    ADD COLUMN reviewed_at TIMESTAMP WITH TIME ZONE
                    """
                )
            )
        if "version" not in report_columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE listing_reports
                    ADD COLUMN version INTEGER NOT NULL DEFAULT 1
                    """
                )
            )

        duplicate_favorite = connection.execute(
            text(
                """
                SELECT user_id, property_id
                FROM favorites
                GROUP BY user_id, property_id
                HAVING COUNT(*) > 1
                LIMIT 1
                """
            )
        ).first()

        if duplicate_favorite is not None:
            raise RuntimeError(
                "Cannot enforce favorite uniqueness because duplicate "
                "favorite records already exist"
            )

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                uq_favorites_user_property
                ON favorites (user_id, property_id)
                """
            )
        )

        performance_indexes = (
            "CREATE INDEX IF NOT EXISTS ix_properties_created_id "
            "ON properties (created_at, id)",
            "CREATE INDEX IF NOT EXISTS ix_properties_price_id "
            "ON properties (price, id)",
            "CREATE INDEX IF NOT EXISTS ix_properties_currency_price_id "
            "ON properties (currency, price, id)",
            "CREATE INDEX IF NOT EXISTS ix_properties_status_listing_created "
            "ON properties (status, listing_type, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_properties_owner_created "
            "ON properties (owner_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_properties_safety_created "
            "ON properties (safety_hold, created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_properties_owner_creation_key "
            "ON properties (owner_id, creation_key)",
            "CREATE INDEX IF NOT EXISTS ix_inquiries_buyer_updated "
            "ON inquiries (buyer_id, updated_at)",
            "CREATE INDEX IF NOT EXISTS ix_inquiries_buyer_status_updated "
            "ON inquiries (buyer_id, status, updated_at)",
            "CREATE INDEX IF NOT EXISTS ix_inquiries_seller_status_updated "
            "ON inquiries (seller_id, status, updated_at)",
            "CREATE INDEX IF NOT EXISTS ix_inquiries_property_id "
            "ON inquiries (property_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_inquiries_buyer_creation_key "
            "ON inquiries (buyer_id, creation_key)",
            "CREATE INDEX IF NOT EXISTS ix_inquiry_messages_inquiry_created "
            "ON inquiry_messages (inquiry_id, created_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "uq_inquiry_messages_sender_creation_key "
            "ON inquiry_messages (sender_id, creation_key)",
            "CREATE INDEX IF NOT EXISTS ix_favorites_property_id "
            "ON favorites (property_id)",
            "CREATE INDEX IF NOT EXISTS ix_listing_reports_status_created "
            "ON listing_reports (status, created_at)",
        )
        for index_statement in performance_indexes:
            connection.execute(text(index_statement))

        duplicate_pending_inquiry = connection.execute(
            text(
                """
                SELECT buyer_id, property_id
                FROM inquiries
                WHERE status = 'pending'
                GROUP BY buyer_id, property_id
                HAVING COUNT(*) > 1
                LIMIT 1
                """
            )
        ).first()

        if duplicate_pending_inquiry is not None:
            raise RuntimeError(
                "Cannot enforce pending inquiry uniqueness because duplicate "
                "pending inquiry records already exist"
            )

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                uq_inquiries_pending_buyer_property
                ON inquiries (buyer_id, property_id)
                WHERE status = 'pending'
                """
            )
        )


ensure_schema_safety()


def get_db():
    with Session(engine) as session:
        yield session
