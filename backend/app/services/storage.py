import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


def _audio_dir() -> Path:
    path = Path(settings.STORAGE_DIR) / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(file: UploadFile, meeting_id: uuid.UUID) -> str:
    """Saves an uploaded audio/video file to local disk and returns a storage URL.

    Swap this function's body for an S3 `put_object` call later; callers only
    ever see the returned URL string, so no other code needs to change.
    """
    suffix = Path(file.filename or "").suffix or ".bin"
    dest = _audio_dir() / f"{meeting_id}{suffix}"

    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    return f"local://{dest}"


def resolve_local_path(storage_url: str | None) -> Path:
    """Turns a `local://...` URL back into a filesystem Path for processing."""
    if not storage_url:
        raise ValueError("storage_url cannot be None or empty")
    if not storage_url.startswith("local://"):
        raise ValueError(f"Unsupported storage backend for URL: {storage_url}")
    return Path(storage_url.removeprefix("local://"))

