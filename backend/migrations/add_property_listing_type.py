from sqlalchemy import inspect, text

from backend.db import engine


def add_property_listing_type():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }
        if "listing_type" in columns:
            print("Property listing type column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN listing_type VARCHAR(20) NOT NULL DEFAULT 'sale'
                """
            )
        )
        print("Property listing type column applied")


if __name__ == "__main__":
    add_property_listing_type()
