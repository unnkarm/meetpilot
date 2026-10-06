"""Local-only storage provider. Every stored path stays inside the configured root."""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.app_config import APP_CONFIG


class StorageProvider(ABC):
    @abstractmethod
    def save(self, file: UploadFile, meeting_id: uuid.UUID) -> str:
        raise NotImplementedError

    @abstractmethod
    def get(self, url: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def get_url(self, path: Path) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete(self, url: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, url: str) -> bool:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    @property
    def root(self) -> Path:
        return Path(APP_CONFIG.storage_dir).resolve()

    def get(self, url: str) -> Path:
        if not url.startswith("local://"):
            raise ValueError("Unsupported storage URL")
        raw = Path(url.removeprefix("local://"))
        candidate = (raw if raw.is_absolute() else Path.cwd() / raw).resolve()
        if not candidate.is_relative_to(self.root):
            candidate = (self.root / raw).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Storage path escapes configured root")
        return candidate

    def get_url(self, path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage path escapes configured root")
        return f"local://{path.relative_to(self.root).as_posix()}"

    def save(self, file: UploadFile, meeting_id: uuid.UUID) -> str:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in APP_CONFIG.uploads.audio_extensions:
            raise ValueError(f"Unsupported audio format: {suffix or 'none'}")
        destination = self.root / "audio" / f"{meeting_id}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with destination.open("wb") as output:
                while block := file.file.read(1024 * 1024):
                    total += len(block)
                    if total > APP_CONFIG.uploads.max_audio_bytes:
                        raise ValueError("Audio upload exceeds configured size limit")
                    output.write(block)
            if total == 0:
                raise ValueError("Audio upload is empty")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return self.get_url(destination)

    def delete(self, url: str) -> None:
        self.get(url).unlink(missing_ok=True)

    def exists(self, url: str) -> bool:
        return self.get(url).exists()


def get_storage_provider() -> StorageProvider:
    if APP_CONFIG.storage_provider == "local":
        return LocalStorageProvider()
    raise ValueError(f"Unsupported storage provider: {APP_CONFIG.storage_provider}")


def save_upload(file: UploadFile, meeting_id: uuid.UUID) -> str:
    return get_storage_provider().save(file, meeting_id)


def resolve_local_path(storage_url: str | None) -> Path:
    if not storage_url:
        raise ValueError("Missing storage URL")
    return get_storage_provider().get(storage_url)
