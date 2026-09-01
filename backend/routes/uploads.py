from base64 import b64decode
from binascii import Error as Base64Error
from io import BytesIO
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from PIL import Image, UnidentifiedImageError

from backend.auth.dependencies import get_current_user_id
from backend.db import get_db
from backend.models import PropertyImageUpload, PropertyImageUploadResponse
from backend.repositories import property_repository
from sqlalchemy.orm import Session


router = APIRouter(prefix="/uploads", tags=["Uploads"])
UPLOAD_DIRECTORY = Path(__file__).resolve().parents[1] / "uploads" / "property-images"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_FORMATS = {
    "image/jpeg": (".jpg", b"\xff\xd8\xff", "JPEG"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n", "PNG"),
    "image/webp": (".webp", b"RIFF", "WEBP"),
}
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_EDGE = 12_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


@router.post("/property-images", response_model=PropertyImageUploadResponse)
def upload_property_image(
    upload: PropertyImageUpload,
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        image_data = b64decode(upload.data, validate=True)
    except (Base64Error, ValueError) as error:
        raise HTTPException(status_code=400, detail="Image data is invalid") from error

    if not image_data or len(image_data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image must be no larger than 5 MB",
        )

    extension, signature, expected_format = IMAGE_FORMATS[upload.content_type]
    valid_signature = image_data.startswith(signature)
    if upload.content_type == "image/webp":
        valid_signature = valid_signature and image_data[8:12] == b"WEBP"
    if not valid_signature:
        raise HTTPException(
            status_code=400,
            detail="File contents do not match the selected image type",
        )

    try:
        with Image.open(BytesIO(image_data)) as image:
            width, height = image.size
            if (
                width <= 0
                or height <= 0
                or width > MAX_IMAGE_EDGE
                or height > MAX_IMAGE_EDGE
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Image dimensions are too large",
                )
            if image.format != expected_format:
                raise HTTPException(
                    status_code=400,
                    detail="Decoded image type does not match the selected type",
                )
            image.verify()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail="Image is corrupt or cannot be decoded",
        ) from error

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    image_name = f"{current_user_id}_{uuid4().hex}{extension}"
    final_path = UPLOAD_DIRECTORY / image_name
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=UPLOAD_DIRECTORY,
            prefix=".upload-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(image_data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, final_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return {"image_url": f"/uploads/property-images/{image_name}"}


@router.delete("/property-images/{image_name}", status_code=204)
def delete_unused_property_image(
    image_name: str,
    current_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_db),
):
    if Path(image_name).name != image_name or not image_name.startswith(
        f"{current_user_id}_"
    ):
        raise HTTPException(status_code=403, detail="You do not own this upload")

    image_url = f"/uploads/property-images/{image_name}"
    if property_repository.is_image_url_in_use(session, image_url):
        raise HTTPException(
            status_code=409,
            detail="This upload is attached to a property",
        )

    image_path = UPLOAD_DIRECTORY / image_name
    try:
        image_path.unlink()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Upload not found") from error

    return Response(status_code=204)
