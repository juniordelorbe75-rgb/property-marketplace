from sqlalchemy import inspect, text

from backend.db import engine


def add_property_amenities():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }
        if "amenities_json" in columns:
            print("Property amenities column already exists")
            return
        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN amenities_json TEXT NOT NULL DEFAULT '[]'
                """
            )
        )
        print("Property amenities column applied")


if __name__ == "__main__":
    add_property_amenities()
