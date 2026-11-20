"""Document upload and OCR extraction router."""

from typing import cast

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.db.models import DocumentRecord, User
from app.parsers.ocr import (
    DocumentType,
    process_document,
)
from app.privacy.consent import ConsentMissingError, has_consent
from app.schemas.documents import DocumentUploadResponse

router = APIRouter(tags=["Documents & OCR"])

MAX_IMAGE_BYTES = 8_000_000


def sniff_image_type(data: bytes) -> str | None:
    """Identify an image by its magic bytes (the client-sent content type is not trusted)."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document and Extract Fields via OCR",
)
def upload_document(
    db: DbSession,
    user_id: str = Form(..., description="Applicant User UUID"),
    document_type: str | None = Form(
        None, description="Optional document type override (utility_bill | receipt | khata_page)"
    ),
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP)"),  # noqa: B008
    _api_key: ApiKeyAuth = None,
) -> DocumentUploadResponse:
    """Normalize uploaded document, perform DeepSeek-OCR extraction, and save encrypted blob with 30-day TTL.

    Images are NEVER stored in PostgreSQL. Consent for 'ocr' or 'bills' is strictly required.
    """
    # 1. Verify user exists
    user = db.scalars(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant user '{user_id}' not found.",
        )

    # 2. Check active consent
    if not (has_consent(db, user_id, "ocr") or has_consent(db, user_id, "bills")):
        raise ConsentMissingError(
            f"Applicant '{user_id}' lacks active consent for document OCR processing (ocr or bills)."
        )

    # 3. Read the image (bounded) and check it really is a JPEG, PNG or WebP
    image_bytes = file.file.read(MAX_IMAGE_BYTES + 1)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file payload is empty.",
        )
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image larger than 8 MB")
    if sniff_image_type(image_bytes) is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG or WebP images are accepted"
        )

    # 4. Execute OCR processing pipeline
    doc_type_val = (
        cast(DocumentType, document_type)
        if document_type in ("utility_bill", "receipt", "khata_page")
        else None
    )
    result = process_document(
        image_bytes=image_bytes,
        user_id=user_id,
        document_type=doc_type_val,
        filename=file.filename,
    )

    # 5. Persist metadata and extracted fields in DB (zero image bytes stored)
    doc_record = DocumentRecord(
        user_id=user.id,
        document_type=result.document_type,
        storage_key=result.storage_key,
        extracted_fields=result.extracted_fields,
        confidence=result.confidence,
        needs_review=result.needs_review,
        expires_at=result.expires_at,
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return DocumentUploadResponse(
        id=doc_record.id,
        user_id=doc_record.user_id,
        document_type=doc_record.document_type,
        storage_key=doc_record.storage_key,
        extracted_fields=doc_record.extracted_fields,
        confidence=doc_record.confidence,
        needs_review=doc_record.needs_review,
        expires_at=doc_record.expires_at,
        created_at=doc_record.created_at,
    )
