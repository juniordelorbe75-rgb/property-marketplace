from sqlalchemy import inspect, text

from backend.db import engine


def add_property_bathrooms():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }

        if "bathrooms" in columns:
            print("Property bathrooms column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN bathrooms INTEGER NOT NULL DEFAULT 1
                """
            )
        )
        print("Property bathrooms column applied")


if __name__ == "__main__":
    add_property_bathrooms()
