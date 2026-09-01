import logging
from pathlib import Path


UPLOAD_URL_PREFIX = "/uploads/property-images/"
UPLOAD_DIRECTORY = Path(__file__).resolve().parent / "uploads" / "property-images"
logger = logging.getLogger(__name__)


def delete_uploaded_property_image(image_url: str) -> bool:
    if not image_url.startswith(UPLOAD_URL_PREFIX):
        return False

    filename = image_url.removeprefix(UPLOAD_URL_PREFIX)
    if not filename or Path(filename).name != filename:
        return False

    upload_directory = UPLOAD_DIRECTORY.resolve()
    image_path = (upload_directory / filename).resolve()
    if image_path.parent != upload_directory:
        return False

    try:
        image_path.unlink()
    except FileNotFoundError:
        return False
    except OSError as error:
        logger.warning(
            "Could not delete uploaded property image %s: %s",
            image_url,
            error,
        )
        return False

    return True
