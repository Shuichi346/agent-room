import base64
from io import BytesIO

from PIL import Image

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096
MIME_BY_FORMAT = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def validate_image(data: bytes, filename: str) -> tuple[str, tuple[int, int]]:
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("image is larger than 10 MB")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            image_format = image.format
            width, height = image.size
    except Exception as exc:
        raise ValueError(f"{filename or 'image'} is not a valid image") from exc

    if image_format not in MIME_BY_FORMAT:
        raise ValueError("image must be PNG, JPEG, or WebP")
    if max(width, height) > MAX_IMAGE_DIMENSION:
        raise ValueError("image dimensions must be 4096 px or smaller")
    return MIME_BY_FORMAT[image_format], (width, height)


def to_data_url(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"

