"""
Image uploads (restaurant logos and menu item photos), stored on the server's
disk and served from /api/v1/uploads. In production the folder is a Docker
volume so files survive a redeploy.

Safety: the file type is decided from the file's own first bytes, never from
the name or the Content-Type the browser claims, the size is capped, and the
stored name is generated here (nothing from the user ends up in a path).
"""
import os
import secrets
from typing import Optional

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_BYTES = 2 * 1024 * 1024  # the web app shrinks images to a few tens of KB first
PUBLIC_PREFIX = "/api/v1/uploads"
FOLDERS = ("logos", "menu", "categories")


def upload_root() -> str:
    root = os.path.abspath(settings.UPLOAD_DIR)
    for folder in FOLDERS:
        os.makedirs(os.path.join(root, folder), exist_ok=True)
    return root


def _image_extension(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


async def save_image(file: UploadFile, folder: str, owner_id: str) -> str:
    """Store the image under `folder` and return the public path to save in the database."""
    if folder not in FOLDERS:
        raise ValueError(folder)
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="That image is too large. Please use one under 2 MB.")
    extension = _image_extension(data)
    if not extension:
        raise HTTPException(status_code=400, detail="Please upload a PNG, JPG or WebP image")

    name = f"{owner_id}-{secrets.token_hex(8)}.{extension}"
    with open(os.path.join(upload_root(), folder, name), "wb") as handle:
        handle.write(data)
    return f"{PUBLIC_PREFIX}/{folder}/{name}"


async def save_logo(file: UploadFile, restaurant_id: str) -> str:
    return await save_image(file, "logos", restaurant_id)


def delete_uploaded(public_path: Optional[str]) -> None:
    """Remove a file we stored earlier. Ignores anything that is not ours (e.g. an external URL)."""
    if not public_path:
        return
    for folder in FOLDERS:
        prefix = f"{PUBLIC_PREFIX}/{folder}/"
        if public_path.startswith(prefix):
            path = os.path.join(upload_root(), folder, os.path.basename(public_path))
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return
