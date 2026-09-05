import logging
import os
from pathlib import Path
import tempfile
from urllib.parse import quote, urlsplit

UPLOAD_URL_PREFIX = "/uploads/property-images/"
UPLOAD_DIRECTORY = Path(__file__).resolve().parent / "uploads" / "property-images"
OBJECT_KEY_PREFIX = "property-images/"
logger = logging.getLogger(__name__)


def image_storage_mode(settings=None) -> str:
    settings = os.environ if settings is None else settings
    mode = settings.get("PROPERTY_IMAGE_STORAGE", "local").strip().lower()
    if mode not in {"local", "s3"}:
        raise RuntimeError("PROPERTY_IMAGE_STORAGE must be local or s3")
    return mode


def validate_object_storage_settings(settings=None) -> None:
    settings = os.environ if settings is None else settings
    if image_storage_mode(settings) != "s3":
        return
    required = (
        "OBJECT_STORAGE_BUCKET", "OBJECT_STORAGE_ACCESS_KEY_ID",
        "OBJECT_STORAGE_SECRET_ACCESS_KEY", "OBJECT_STORAGE_PUBLIC_BASE_URL",
    )
    missing = [name for name in required if not settings.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"Missing object storage settings: {', '.join(missing)}")
    public_url = urlsplit(settings["OBJECT_STORAGE_PUBLIC_BASE_URL"].strip())
    if public_url.scheme != "https" or not public_url.netloc or public_url.query or public_url.fragment:
        raise RuntimeError("OBJECT_STORAGE_PUBLIC_BASE_URL must be an HTTPS URL")
    endpoint = settings.get("OBJECT_STORAGE_ENDPOINT_URL", "").strip()
    if endpoint:
        parsed_endpoint = urlsplit(endpoint)
        if parsed_endpoint.scheme != "https" or not parsed_endpoint.netloc or parsed_endpoint.query or parsed_endpoint.fragment:
            raise RuntimeError("OBJECT_STORAGE_ENDPOINT_URL must be an HTTPS URL")


def _s3_client(settings):
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("boto3 is required for S3 property image storage") from error
    options = {
        "aws_access_key_id": settings["OBJECT_STORAGE_ACCESS_KEY_ID"].strip(),
        "aws_secret_access_key": settings["OBJECT_STORAGE_SECRET_ACCESS_KEY"].strip(),
    }
    endpoint = settings.get("OBJECT_STORAGE_ENDPOINT_URL", "").strip()
    region = settings.get("OBJECT_STORAGE_REGION", "").strip()
    if endpoint:
        options["endpoint_url"] = endpoint
    if region:
        options["region_name"] = region
    return boto3.client("s3", **options)


def property_image_url(image_name: str, settings=None) -> str:
    settings = os.environ if settings is None else settings
    if image_storage_mode(settings) == "local":
        return f"{UPLOAD_URL_PREFIX}{image_name}"
    base_url = settings["OBJECT_STORAGE_PUBLIC_BASE_URL"].strip().rstrip("/")
    return f"{base_url}/{OBJECT_KEY_PREFIX}{quote(image_name)}"


def store_property_image(image_name: str, image_data: bytes, content_type: str, *, directory: Path | None = None, settings=None, client=None) -> str:
    settings = os.environ if settings is None else settings
    if image_storage_mode(settings) == "s3":
        validate_object_storage_settings(settings)
        (client or _s3_client(settings)).put_object(
            Bucket=settings["OBJECT_STORAGE_BUCKET"].strip(),
            Key=f"{OBJECT_KEY_PREFIX}{image_name}", Body=image_data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        return property_image_url(image_name, settings)
    directory = UPLOAD_DIRECTORY if directory is None else directory
    directory.mkdir(parents=True, exist_ok=True)
    final_path = directory / image_name
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=directory, prefix=".upload-", suffix=".tmp", delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(image_data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, final_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return property_image_url(image_name, settings)


def _image_name_from_url(image_url: str, settings) -> str | None:
    if image_url.startswith(UPLOAD_URL_PREFIX):
        image_name = image_url.removeprefix(UPLOAD_URL_PREFIX)
    elif image_storage_mode(settings) == "s3":
        prefix = settings["OBJECT_STORAGE_PUBLIC_BASE_URL"].strip().rstrip("/") + f"/{OBJECT_KEY_PREFIX}"
        if not image_url.startswith(prefix):
            return None
        image_name = image_url.removeprefix(prefix)
    else:
        return None
    if not image_name or Path(image_name).name != image_name:
        return None
    return image_name


def delete_uploaded_property_image(image_url: str, *, directory: Path | None = None, settings=None, client=None) -> bool:
    settings = os.environ if settings is None else settings
    image_name = _image_name_from_url(image_url, settings)
    if image_name is None:
        return False
    if image_storage_mode(settings) == "s3" and not image_url.startswith(UPLOAD_URL_PREFIX):
        try:
            (client or _s3_client(settings)).delete_object(
                Bucket=settings["OBJECT_STORAGE_BUCKET"].strip(),
                Key=f"{OBJECT_KEY_PREFIX}{image_name}",
            )
        except Exception as error:
            logger.warning("Could not delete uploaded property image %s: %s", image_url, error)
            return False
        return True
    directory = UPLOAD_DIRECTORY if directory is None else directory
    upload_directory = directory.resolve()
    image_path = (upload_directory / image_name).resolve()
    if image_path.parent != upload_directory:
        return False
    try:
        image_path.unlink()
    except FileNotFoundError:
        return False
    except OSError as error:
        logger.warning("Could not delete uploaded property image %s: %s", image_url, error)
        return False
    return True
