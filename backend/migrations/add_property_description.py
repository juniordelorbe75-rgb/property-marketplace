from sqlalchemy import inspect, text

from backend.db import engine


def migrate():
    existing_columns = {
        column["name"]
        for column in inspect(engine).get_columns("properties")
    }

    if "description" in existing_columns:
        print("Property description column already exists")
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE properties
                ADD COLUMN description VARCHAR(2000) NOT NULL DEFAULT ''
                """
            )
        )

    print("Property description column applied")


if __name__ == "__main__":
    migrate()
