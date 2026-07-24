"""Object storage abstraction.

Prefers a MinIO / S3-compatible backend when configured and reachable, and
transparently falls back to the local filesystem otherwise. This keeps local
dev friction-free while making the eventual move to real S3 / R2 config-only.
"""
from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

from app.config import settings

logger = logging.getLogger("autotracker.storage")


class StorageBackend:
    """Common interface implemented by both backends."""

    name = "base"

    def save(self, data: bytes, *, key: str | None = None, content_type: str) -> str:
        raise NotImplementedError

    def load(self, key: str) -> bytes:
        raise NotImplementedError

    def stream(self, key: str) -> BinaryIO:
        return io.BytesIO(self.load(key))

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def presigned_url(self, key: str, expires_seconds: int = 300) -> str | None:
        return None


def _new_key(original_ext: str = "") -> str:
    ext = f".{original_ext.lstrip('.')}" if original_ext else ""
    return f"{uuid.uuid4().hex}{ext}"


class LocalStorage(StorageBackend):
    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal — keys are always flat uuid names.
        safe = key.replace("..", "").lstrip("/")
        return self.root / safe

    def save(self, data: bytes, *, key: str | None = None, content_type: str) -> str:
        key = key or _new_key()
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError:  # pragma: no cover
            logger.warning("failed to delete local object %s", key)


class MinioStorage(StorageBackend):
    name = "minio"

    def __init__(self) -> None:
        from minio import Minio  # local import: optional dependency

        self.bucket = settings.s3_bucket
        self.client = Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
            region=settings.s3_region,
        )
        # Ping + ensure bucket. Raises if the endpoint is unreachable.
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def save(self, data: bytes, *, key: str | None = None, content_type: str) -> str:
        key = key or _new_key()
        self.client.put_object(
            self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
        )
        return key

    def load(self, key: str) -> bytes:
        resp = self.client.get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)

    def presigned_url(self, key: str, expires_seconds: int = 300) -> str | None:
        try:
            return self.client.presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expires_seconds)
            )
        except Exception:  # pragma: no cover
            return None


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return a lazily-initialised singleton, falling back to local on failure."""
    global _backend
    if _backend is not None:
        return _backend

    if settings.storage_backend == "minio":
        try:
            _backend = MinioStorage()
            logger.info("storage backend: minio (%s/%s)", settings.s3_endpoint, settings.s3_bucket)
            return _backend
        except Exception as exc:  # noqa: BLE001
            logger.warning("MinIO unavailable (%s); falling back to local storage", exc)

    root = settings.local_storage_dir
    try:
        _backend = LocalStorage(root)
    except OSError as exc:
        # Read-only filesystem (serverless). /tmp is writable but per-instance
        # and ephemeral — uploads survive only until the container is recycled.
        import tempfile

        root = os.path.join(tempfile.gettempdir(), "autotracker-storage")
        logger.warning(
            "local storage dir %s not writable (%s); falling back to %s — "
            "configure S3-compatible storage for durable uploads",
            settings.local_storage_dir,
            exc,
            root,
        )
        _backend = LocalStorage(root)
    logger.info("storage backend: local (%s)", root)
    return _backend


def reset_storage() -> None:
    """Testing helper — drop the cached backend."""
    global _backend
    _backend = None


def guess_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename or "")
    return ext.lstrip(".").lower()
