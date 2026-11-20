"""Encrypted object storage for document images with a 30-day retention window.

Backends: S3-compatible (Cloudflare R2 in production, MinIO locally) when ``R2_ENDPOINT`` is
set, otherwise the local filesystem. Blobs are always encrypted with Fernet (AES-128-CBC +
HMAC) before they leave the process. Postgres never stores image bytes.
"""

import base64
import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from cryptography.fernet import Fernet

from app.config import get_settings

logger = logging.getLogger("trustledger.storage")

RETENTION_DAYS = 30


def _fernet() -> Fernet:
    key = get_settings().STORAGE_ENCRYPTION_KEY
    if not key:
        # Dev-only fallback: a fixed key derived from a constant. Production must set the env var.
        key = base64.urlsafe_b64encode(hashlib.sha256(b"trustledger-dev-only").digest()).decode()
    return Fernet(key.encode())


def encrypt(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt(token: bytes) -> bytes:
    return _fernet().decrypt(token)


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, expires_at: datetime) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def purge_expired(self, now: datetime | None = None) -> int: ...


class LocalStore:
    """Filesystem store; a sidecar .json keeps the expiry for purge_expired()."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, key: str, data: bytes, expires_at: datetime) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.with_suffix(".json").write_text(json.dumps({"expires_at": expires_at.isoformat()}))

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def delete_prefix(self, prefix: str) -> int:
        base = self.root / prefix
        if not base.exists():
            return 0
        count = 0
        for path in sorted(base.rglob("*"), reverse=True):
            if path.is_file():
                count += path.suffix == ".enc"
                path.unlink()
            else:
                path.rmdir()
        base.rmdir()
        return count

    def purge_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        removed = 0
        if not self.root.exists():
            return 0
        for meta in self.root.rglob("*.json"):
            try:
                expires = datetime.fromisoformat(json.loads(meta.read_text())["expires_at"])
            except (ValueError, KeyError, OSError):
                continue
            if expires <= now:
                meta.with_suffix(".enc").unlink(missing_ok=True)
                meta.unlink(missing_ok=True)
                removed += 1
        return removed


class S3Store:
    """R2/MinIO store. Expiry is enforced by a bucket lifecycle rule (see infra/r2-lifecycle.json)
    and also recorded as object metadata so purge_expired() can clean buckets without one."""

    def __init__(self) -> None:
        import boto3

        s = get_settings()
        self.bucket = s.R2_BUCKET
        self.client: Any = boto3.client(
            "s3",
            endpoint_url=s.R2_ENDPOINT,
            aws_access_key_id=s.R2_ACCESS_KEY,
            aws_secret_access_key=s.R2_SECRET_KEY,
            region_name="auto",
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket on first use (MinIO in Docker starts empty). R2 buckets already exist."""
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info("created object storage bucket")
            except ClientError:
                logger.warning("bucket missing and could not be created")

    def put(self, key: str, data: bytes, expires_at: datetime) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            Expires=expires_at,
            Metadata={"expires-at": expires_at.isoformat()},
        )

    def get(self, key: str) -> bytes:
        body: bytes = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return body

    def _keys(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys

    def delete_prefix(self, prefix: str) -> int:
        keys = self._keys(prefix)
        for key in keys:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        return len(keys)

    def purge_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        removed = 0
        for key in self._keys():
            head = self.client.head_object(Bucket=self.bucket, Key=key)
            raw = head.get("Metadata", {}).get("expires-at")
            if raw and datetime.fromisoformat(raw) <= now:
                self.client.delete_object(Bucket=self.bucket, Key=key)
                removed += 1
        return removed


@lru_cache(maxsize=1)
def get_store() -> ObjectStore:
    if get_settings().R2_ENDPOINT:
        return S3Store()
    root = Path(os.getenv("DOCUMENT_STORAGE_DIR", ".storage/documents"))
    return LocalStore(root)


def store_document(image_bytes: bytes, user_id: str, doc_type: str) -> tuple[str, datetime]:
    """Encrypt and store an image. Returns (storage_key, expires_at)."""
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    key = f"{user_id}/{doc_type}/{digest}.enc"
    expires_at = datetime.now(UTC) + timedelta(days=RETENTION_DAYS)
    get_store().put(key, encrypt(image_bytes), expires_at)
    return key, expires_at


def delete_user_documents(user_id: str) -> int:
    """Remove every stored blob for a user (used by DELETE /me)."""
    try:
        return get_store().delete_prefix(f"{user_id}/")
    except Exception:
        logger.exception("blob deletion failed for a user")
        return 0
