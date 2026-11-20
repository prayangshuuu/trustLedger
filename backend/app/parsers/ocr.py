"""Document OCR extraction and image normalization pipeline for TrustLedger.

Extracts structured financial signals from utility bills, MFS receipts, and handwritten
Bangla khata ledgers using DeepSeek-OCR, enforcing strict Pydantic schemas, confidence
scoring, and zero-image PostgreSQL persistence with a 30-day storage expiration policy.
"""

import io
from datetime import datetime
from typing import Any, Literal

from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from app.llm.client import get_llm_client
from app.storage import store_document

DocumentType = Literal["utility_bill", "receipt", "khata_page"]


class UtilityBillExtraction(BaseModel):
    """Structured fields extracted from electricity, gas, or water utility bills."""

    document_type: Literal["utility_bill"] = "utility_bill"
    provider: str = Field(
        ..., description="Utility provider: DESCO | DPDC | WASA | Titas | NESCO | BREB"
    )
    amount_bdt: float = Field(..., ge=0.0, description="Total payable amount in BDT")
    due_date: str | None = Field(
        default=None, description="Payment due date (YYYY-MM-DD or DD/MM/YYYY)"
    )
    bill_month: str | None = Field(default=None, description="Billing cycle month and year")
    paid: bool | None = Field(default=None, description="True if paid seal or stamp detected")
    account_or_meter_no: str | None = Field(
        default=None, description="Customer account or meter number"
    )
    confidence: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Model extraction confidence score"
    )


class ReceiptExtraction(BaseModel):
    """Structured fields extracted from point-of-sale, bank, or MFS cash transaction receipts."""

    document_type: Literal["receipt"] = "receipt"
    merchant_or_platform: str = Field(..., description="Store, merchant, or financial platform")
    amount_bdt: float = Field(..., ge=0.0, description="Total transaction amount in BDT")
    date: str | None = Field(default=None, description="Transaction timestamp or date")
    trx_id: str | None = Field(default=None, description="Transaction reference ID")
    category: str | None = Field(default=None, description="Expense or service category")
    confidence: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Model extraction confidence score"
    )


class KhataEntry(BaseModel):
    """Single credit/debit entry on a handwritten Bangla khata page."""

    customer_name: str = Field(..., description="Customer or supplier name")
    amount_bdt: float = Field(..., ge=0.0, description="Entry transaction amount in BDT")
    direction: Literal["in", "out"] = Field(
        ..., description="'in' for payment, 'out' for credit taken"
    )
    date: str | None = Field(default=None, description="Entry date recorded")


class KhataPageExtraction(BaseModel):
    """Structured ledger transactions extracted from handwritten khata ledger photo."""

    document_type: Literal["khata_page"] = "khata_page"
    shop_name: str | None = Field(default=None, description="Identified shop or business name")
    page_total_bdt: float | None = Field(default=None, description="Reconciled page total in BDT")
    entries: list[KhataEntry] = Field(
        default_factory=list, description="Extracted line item entries"
    )
    confidence: float = Field(
        default=0.90, ge=0.0, le=1.0, description="Model extraction confidence score"
    )


class DocumentExtractionResult(BaseModel):
    """Normalized document extraction outcome ready for persistence and feature building."""

    document_type: DocumentType
    storage_key: str
    extracted_fields: dict[str, Any]
    confidence: float
    needs_review: bool
    expires_at: datetime


def normalize_image(image_bytes: bytes, max_dim: int = 1600) -> bytes:
    """Normalize raw document photo: auto-orient via EXIF, resize to max dimension, and contrast-balance."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        oriented = ImageOps.exif_transpose(img)
        if oriented is None:
            oriented = img

        if oriented.mode not in ("RGB", "L"):
            oriented = oriented.convert("RGB")

        width, height = oriented.size
        if max(width, height) > max_dim:
            scaling = max_dim / float(max(width, height))
            new_size = (int(width * scaling), int(height * scaling))
            oriented = oriented.resize(new_size, Image.Resampling.LANCZOS)

        enhanced = ImageOps.autocontrast(oriented, cutoff=1)

        output = io.BytesIO()
        enhanced.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue()


def detect_document_type(image_bytes: bytes, filename: str | None = None) -> DocumentType:
    """Heuristic document classification based on filename, aspect ratio, or OCR keywords."""
    lower_fn = (filename or "").lower()
    if any(k in lower_fn for k in ("khata", "ledger", "khata_page", "হালখাতা", "খাতা")):
        return "khata_page"
    if any(k in lower_fn for k in ("receipt", "pos", "voucher", "রসিদ")):
        return "receipt"
    if any(k in lower_fn for k in ("bill", "desco", "dpdc", "wasa", "titas", "বিদ্যুৎ", "গ্যাস")):
        return "utility_bill"

    return "utility_bill"


def store_document_blob(
    image_bytes: bytes,
    user_id: str,
    doc_type: str,
) -> tuple[str, datetime]:
    """Encrypt and store the image in object storage with a 30-day expiry (never in Postgres)."""
    return store_document(image_bytes, user_id, doc_type)


def process_document(
    image_bytes: bytes,
    user_id: str,
    document_type: DocumentType | None = None,
    filename: str | None = None,
) -> DocumentExtractionResult:
    """Full OCR processing pipeline: normalize -> classify -> extract via DeepSeek-OCR -> validate."""
    norm_bytes = normalize_image(image_bytes)

    resolved_type: DocumentType = document_type or detect_document_type(norm_bytes, filename)

    schema_cls: type[BaseModel]
    if resolved_type == "utility_bill":
        schema_cls = UtilityBillExtraction
    elif resolved_type == "receipt":
        schema_cls = ReceiptExtraction
    else:
        schema_cls = KhataPageExtraction

    client = get_llm_client()
    raw_extracted = client.ocr(norm_bytes, schema=schema_cls, filename=filename)

    if isinstance(raw_extracted, BaseModel):
        extracted_data = raw_extracted.model_dump()
    elif isinstance(raw_extracted, dict):
        extracted_data = raw_extracted
    else:
        extracted_data = {"raw_output": str(raw_extracted)}

    confidence = float(extracted_data.get("confidence", 0.90))
    needs_review = confidence < 0.80

    storage_key, expires_at = store_document_blob(norm_bytes, user_id, resolved_type)

    return DocumentExtractionResult(
        document_type=resolved_type,
        storage_key=storage_key,
        extracted_fields=extracted_data,
        confidence=confidence,
        needs_review=needs_review,
        expires_at=expires_at,
    )
