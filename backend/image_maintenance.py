import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db_models.property import PropertyDB
from backend.image_storage import UPLOAD_DIRECTORY, UPLOAD_URL_PREFIX


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def cleanup_orphaned_uploads(
    session: Session,
    *,
    directory: Path = UPLOAD_DIRECTORY,
    older_than: timedelta = timedelta(hours=24),
    delete: bool = False,
    now: datetime | None = None,
) -> dict[str, list[str]]:
    now = now or datetime.now(timezone.utc)
    cutoff_timestamp = (now - older_than).timestamp()
    directory.mkdir(parents=True, exist_ok=True)

    referenced_urls = {
        image_url
        for property_item in session.scalars(select(PropertyDB)).all()
        for image_url in property_item.image_urls
    }
    candidates: list[Path] = []

    for path in directory.iterdir():
        if not path.is_file() or path.stat().st_mtime > cutoff_timestamp:
            continue

        is_stale_temporary_file = (
            path.name.startswith(".upload-") and path.suffix == ".tmp"
        )
        is_unreferenced_image = (
            path.suffix.lower() in IMAGE_EXTENSIONS
            and f"{UPLOAD_URL_PREFIX}{path.name}" not in referenced_urls
        )
        if is_stale_temporary_file or is_unreferenced_image:
            candidates.append(path)

    deleted: list[str] = []
    if delete:
        for path in candidates:
            try:
                path.unlink()
                deleted.append(path.name)
            except FileNotFoundError:
                continue

    return {
        "candidates": sorted(path.name for path in candidates),
        "deleted": sorted(deleted),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Report or remove old property uploads not referenced by the database."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete candidates. Without this flag, the command is a dry run.",
    )
    parser.add_argument(
        "--older-than-hours",
        type=float,
        default=24,
        help="Only inspect files at least this many hours old (default: 24).",
    )
    args = parser.parse_args()
    if args.older_than_hours < 1:
        parser.error("--older-than-hours must be at least 1")

    from backend.db import engine

    with Session(engine) as session:
        result = cleanup_orphaned_uploads(
            session,
            older_than=timedelta(hours=args.older_than_hours),
            delete=args.delete,
        )

    action = "Deleted" if args.delete else "Would delete"
    print(f"{action} {len(result['deleted'] if args.delete else result['candidates'])} file(s).")
    for filename in result["deleted"] if args.delete else result["candidates"]:
        print(filename)


if __name__ == "__main__":
    main()
