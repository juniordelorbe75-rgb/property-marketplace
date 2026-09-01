from sqlalchemy import inspect, text

from backend.db import engine


def add_property_images_json():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }
        if "images_json" in columns:
            print("Property images JSON column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN images_json TEXT NOT NULL DEFAULT '[]'
                """
            )
        )
        print("Property images JSON column applied")


if __name__ == "__main__":
    add_property_images_json()
