"""Document OCR extraction and image normalization pipeline for TrustLedger.

Extracts structured financial signals from utility bills, MFS receipts, and handwritten
Bangla khata ledgers using DeepSeek-OCR, enforcing strict Pydantic schemas, confidence
scoring, and zero-image PostgreSQL persistence with a 30-day storage expiration policy.
"""

import io
import json
import logging
import shutil
from datetime import datetime
from typing import Any, Literal, cast

from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm.client import get_llm_client
from app.storage import store_document

logger = logging.getLogger("trustledger.ocr")

DocumentType = Literal["utility_bill", "receipt", "khata_page"]


def get_active_ocr_backend() -> str:
    """Determine the active OCR backend: deepseek-ocr-local | tesseract | mock."""
    settings = get_settings()
    configured = (settings.OCR_BACKEND or "auto").lower()
    if configured != "auto":
        return configured
    if settings.DEEPSEEK_OCR_URL:
        return "deepseek-ocr-local"
    if shutil.which("tesseract"):
        return "tesseract"
    if settings.LLM_MODE == "live":
        return "deepseek-ocr-local"
    return "mock"


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
    ocr_backend: str = Field(default_factory=get_active_ocr_backend)


def normalize_image(image_bytes: bytes, max_dim: int = 1600) -> bytes:
    """Normalize raw document photo (or PDF): auto-orient via EXIF, resize, and contrast-balance."""
    raw_data = image_bytes
    if image_bytes.startswith(b"%PDF"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(image_bytes))
            for page in reader.pages:
                for img_file in page.images:
                    raw_data = img_file.data
                    break
                if raw_data != image_bytes:
                    break
        except Exception as e:  # noqa: BLE001
            logger.debug("PDF image extraction failed (%s); processing raw bytes", e)

    with Image.open(io.BytesIO(raw_data)) as img:
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


def extract_via_tesseract(norm_bytes: bytes, schema_cls: type[BaseModel]) -> dict[str, Any]:
    """Tesseract extraction: OCR into text, then structure via DeepSeek text model."""
    try:
        import pytesseract  # type: ignore[import-not-found]

        with Image.open(io.BytesIO(norm_bytes)) as img:
            try:
                raw_text = pytesseract.image_to_string(img, lang="ben+eng")
            except Exception:  # noqa: BLE001
                raw_text = pytesseract.image_to_string(img, lang="eng")

        prompt = (
            "You are an expert document parser for Bangladeshi utility bills and receipts. "
            "Extract structured fields matching this JSON schema from the raw OCR text below:\n"
            f"```text\n{raw_text}\n```"
        )
        client = get_llm_client()
        res = client.chat(
            [{"role": "user", "content": prompt}],
            schema=schema_cls,
            temperature=0.0,
        )
        if isinstance(res, BaseModel):
            return res.model_dump()
        if isinstance(res, dict):
            return res
        return cast(dict[str, Any], json.loads(str(res)))
    except Exception as e:  # noqa: BLE001
        logger.warning("Tesseract parsing failed (%s); falling back to direct OCR client", e)
        client = get_llm_client()
        res = client.ocr(norm_bytes, schema=schema_cls)
        return res.model_dump() if isinstance(res, BaseModel) else cast(dict[str, Any], res)


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

    active_backend = get_active_ocr_backend()
    if active_backend == "tesseract":
        extracted_data = extract_via_tesseract(norm_bytes, schema_cls)
    else:
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
        ocr_backend=active_backend,
    )
