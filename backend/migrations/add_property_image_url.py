from sqlalchemy import inspect, text

from backend.db import engine


def add_property_image_url():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }

        if "image_url" in columns:
            print("Property image URL column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN image_url VARCHAR(2000) NOT NULL DEFAULT ''
                """
            )
        )
        print("Property image URL column applied")


if __name__ == "__main__":
    add_property_image_url()
