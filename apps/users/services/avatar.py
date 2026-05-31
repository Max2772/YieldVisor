from __future__ import annotations

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_AVATAR_SIZE = 512
JPEG_QUALITY = 85


def process_avatar(uploaded_file) -> ContentFile:
    """Resize and normalize uploaded avatar to a square JPEG."""
    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.load()
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported image format.") from exc

    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.convert("RGBA").split()[-1]
        background.paste(image.convert("RGBA"), mask=alpha)
        image = background
    else:
        image = image.convert("RGB")

    image.thumbnail((MAX_AVATAR_SIZE, MAX_AVATAR_SIZE), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buffer.seek(0)
    return ContentFile(buffer.read(), name="avatar.jpg")
