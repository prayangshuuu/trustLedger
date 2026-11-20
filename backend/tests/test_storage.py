"""Encrypted object storage: encryption at rest, 30-day expiry purge and delete-my-data."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.db.base import Base
from app.db.models import DocumentRecord, User
from app.db.session import create_app_engine
from app.privacy.deletion import delete_user_data
from app.storage import LocalStore, decrypt, get_store, store_document
from sqlalchemy.orm import sessionmaker


def test_blob_is_encrypted_and_round_trips() -> None:
    data = b"\xff\xd8 fake jpeg bytes DESCO bill 1450"
    key, expires_at = store_document(data, "user-enc", "utility_bill")
    stored = get_store().get(key)
    assert b"DESCO" not in stored
    assert decrypt(stored) == data
    assert timedelta(days=29) < expires_at - datetime.now(UTC) <= timedelta(days=30)


def test_purge_expired_removes_only_expired(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    now = datetime.now(UTC)
    store.put("u/a.enc", b"old", now - timedelta(seconds=1))
    store.put("u/b.enc", b"new", now + timedelta(days=30))
    assert store.purge_expired(now) == 1
    assert not (tmp_path / "u/a.enc").exists()
    assert (tmp_path / "u/b.enc").exists()


def test_delete_me_removes_document_blobs() -> None:
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(phone_hash="h-del", gender="F", region="urban", division="Dhaka")
    session.add(user)
    session.flush()
    key, exp = store_document(b"image", user.id, "receipt")
    session.add(
        DocumentRecord(
            user_id=user.id,
            document_type="receipt",
            storage_key=key,
            extracted_fields={},
            confidence=0.9,
            expires_at=exp,
        )
    )
    session.commit()
    assert delete_user_data(session, user.id) is True
    root = get_store().root  # type: ignore[attr-defined]
    assert not (root / user.id).exists()
