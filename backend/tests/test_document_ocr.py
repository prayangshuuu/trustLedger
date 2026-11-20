"""Unit and integration tests for document OCR extraction, storage retention, and API endpoints."""

import io
from datetime import UTC, datetime

from app.db.base import Base
from app.db.models import DocumentRecord, User
from app.db.session import create_app_engine, get_db
from app.main import create_app
from app.parsers.ocr import (
    detect_document_type,
    normalize_image,
    store_document_blob,
)
from app.privacy.consent import grant_consent
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from evals.ocr.evaluate import run_evaluation


def create_dummy_image(text: str = "Test Bill") -> bytes:
    """Generate minimal valid JPEG bytes for testing."""
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_image_normalization() -> None:
    """Verify normalize_image downscales large images, balances contrast, and returns JPEG bytes."""
    # Create large image (2000x2400)
    large_img = Image.new("RGB", (2000, 2400), color=(150, 150, 150))
    buf = io.BytesIO()
    large_img.save(buf, format="JPEG")

    norm_bytes = normalize_image(buf.getvalue(), max_dim=1600)
    assert len(norm_bytes) > 0

    with Image.open(io.BytesIO(norm_bytes)) as out_img:
        w, h = out_img.size
        assert max(w, h) <= 1600
        assert out_img.format == "JPEG"


def test_document_type_detection() -> None:
    """Verify heuristic classification maps file names and content to standard types."""
    dummy = create_dummy_image()
    assert detect_document_type(dummy, "desco_bill_oct.jpg") == "utility_bill"
    assert detect_document_type(dummy, "pos_receipt_shwapno.jpg") == "receipt"
    assert detect_document_type(dummy, "shop_khata_page_01.jpg") == "khata_page"
    assert detect_document_type(dummy, "unknown_scan.png") == "utility_bill"


def test_document_storage_and_30_day_expiry() -> None:
    """Verify encrypted blob storage and strict 30-day expiration window."""
    dummy_bytes = create_dummy_image("DESCO")
    storage_key, expires_at = store_document_blob(dummy_bytes, "user-storage-1", "utility_bill")

    assert "user-storage-1" in storage_key
    assert storage_key.endswith(".enc")

    # Expiry must be ~30 days in the future
    now = datetime.now(UTC)
    delta_days = (expires_at - now).total_seconds() / 86400.0
    assert 29.0 <= delta_days <= 31.0


def test_post_documents_endpoint_success_and_consent() -> None:
    """Verify POST /documents extracts fields, persists metadata to DB, and enforces consent."""
    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = TestingSessionLocal()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        # 1. Seed user without consent
        user = User(
            id="user-ocr-1",
            phone_hash="ocrhash1",
            gender="F",
            region="urban",
            division="Dhaka",
        )
        db_session.add(user)
        db_session.commit()

        dummy_img = create_dummy_image("DPDC Bill")
        files = {"file": ("dpdc_bill.jpg", dummy_img, "image/jpeg")}
        data = {"user_id": "user-ocr-1", "document_type": "utility_bill"}

        # Attempt upload without consent -> 403 Forbidden
        resp_no_consent = client.post("/documents", data=data, files=files)
        assert resp_no_consent.status_code == 403
        assert "CONSENT_MISSING" in resp_no_consent.json()["error"]

        # 2. Grant 'bills' consent
        grant_consent(db_session, "user-ocr-1", "bills")

        # Retry upload with consent -> 201 Created
        files = {"file": ("dpdc_bill.jpg", dummy_img, "image/jpeg")}
        resp_success = client.post("/documents", data=data, files=files)
        assert resp_success.status_code == 201
        res_data = resp_success.json()

        assert res_data["user_id"] == "user-ocr-1"
        assert res_data["document_type"] == "utility_bill"
        assert "storage_key" in res_data
        assert "extracted_fields" in res_data
        assert res_data["confidence"] >= 0.80
        assert res_data["needs_review"] is False

        # Verify DB persistence: metadata saved, but no image binary stored
        db_record = db_session.query(DocumentRecord).filter_by(user_id="user-ocr-1").first()
        assert db_record is not None
        assert db_record.document_type == "utility_bill"
        assert "raw_bytes" not in db_record.__dict__
        assert "image" not in db_record.__dict__
        assert db_record.extracted_fields["amount_bdt"] > 0
    finally:
        db_session.close()


def test_ocr_evaluation_script_runs() -> None:
    """Verify evaluation benchmark executes and reports field-level F1 >= 0.85."""
    f1 = run_evaluation()
    assert f1 >= 0.85, f"Expected field-level F1 >= 0.85, got {f1:.4f}"
