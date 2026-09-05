import logging

from backend.db import apply_schema_updates


def main() -> None:
    apply_schema_updates()
    logging.getLogger(__name__).info("HabitaRD database schema is ready")


if __name__ == "__main__":
    main()
