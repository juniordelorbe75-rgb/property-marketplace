from sqlalchemy import inspect, text

from backend.db import engine


def add_property_created_at():
    with engine.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("properties")
        }

        if "created_at" in columns:
            print("Property creation timestamp column already exists")
            return

        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE
                NOT NULL DEFAULT CURRENT_TIMESTAMP
                """
            )
        )
        print("Property creation timestamp column applied")


if __name__ == "__main__":
    add_property_created_at()
