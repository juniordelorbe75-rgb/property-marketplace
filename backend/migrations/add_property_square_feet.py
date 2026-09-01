from sqlalchemy import inspect, text

from backend.db import engine


def add_property_square_feet():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }

        if "square_feet" in columns:
            print("Property square feet column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN square_feet INTEGER NOT NULL DEFAULT 0
                """
            )
        )
        print("Property square feet column applied")


if __name__ == "__main__":
    add_property_square_feet()
