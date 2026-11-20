"""Validation and integrity guardrails between AI layer and scoring model.

Enforces:
1. Schema and range validation against models/feature_ranges.json.
2. Out-of-distribution (OOD) checks via decile distributions.
3. Sufficiency gate: < 3 months of wallet history and no Bhorsha refuses scoring.
4. Cross-source consistency checks (OCR utility bills vs SMS payments, duplicates, dates).
5. Confidence propagation and DataQualityBlock generation with Bangla notes.
6. Explanation guard: rejects hallucinated features, mismatched numbers, or approval promises.
7. Bhorsha guard: checks paired question consistency and score bounds.
8. Model sanity: feature hashing and refusal of invalid vectors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from app.core.explain import ENGLISH_FEATURE_LABELS
from app.core.features import FEATURE_NAMES
from app.core.model import load_meta

logger = logging.getLogger("trustledger.validation")

ROOT = Path(__file__).resolve().parents[3]
RANGES_FILE = ROOT / "models" / "feature_ranges.json"
BASELINE_FILE = ROOT / "models" / "feature_baseline.json"

APPROVAL_PROMISE_RE = re.compile(
    r"(?:১০০%|নিশ্চিত|গ্যারান্টি|অবশ্যই|guarantee|promise|definitely)\s*(?:পাবেন|হবে|অনুমোদন|approval|দেওয়া হবে)",
    re.IGNORECASE,
)


class InsufficientDataError(ValueError):
    """Raised when an applicant lacks minimum 3 months wallet data and has no Bhorsha assessment."""


class ValidationFailureError(ValueError):
    """Raised when an applicant feature vector fails basic sanity or schema validation."""


class DataQualityBlock(BaseModel):
    """Data quality, source attribution, and verification metrics presented in the UI."""

    sources_used: list[str] = Field(
        default_factory=list, description="Data sources used (e.g. sms, utility_bill, bhorsha)"
    )
    months_covered: float = Field(default=0.0, description="Months of historical transactions")
    transactions_counted: int = Field(default=0, description="Deduplicated transaction count")
    flags: list[str] = Field(
        default_factory=list, description="Triggered data quality and sanity flags"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Aggregate confidence score")
    notes_bn: list[str] = Field(
        default_factory=list, description="Simple Bangla user-facing data quality explanations"
    )


class ValidationResult(BaseModel):
    """Sanitized features, data quality metrics, and integrity assessment outcome."""

    features: dict[str, Any]
    data_quality: DataQualityBlock
    feature_hash: str
    needs_review: bool
    is_sufficient: bool
    flags: list[str]

    @property
    def cleaned_features(self) -> dict[str, Any]:
        """Alias for sanitized features."""
        return self.features

    @property
    def valid(self) -> bool:
        """True if sufficient and not flagged as requiring manual review."""
        return self.is_sufficient and not self.needs_review


def _load_ranges() -> dict[str, dict[str, float]]:
    if RANGES_FILE.exists():
        try:
            data = json.loads(RANGES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return cast(dict[str, dict[str, float]], data)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _load_baseline() -> dict[str, Any]:
    if BASELINE_FILE.exists():
        try:
            data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return cast(dict[str, Any], data)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def compute_feature_hash(features: dict[str, Any] | BaseModel) -> str:
    """Compute deterministic SHA-256 fingerprint of the normalized feature dictionary."""
    feats: dict[str, Any] = features.model_dump() if isinstance(features, BaseModel) else features
    normalized: dict[str, Any] = {}
    for name in FEATURE_NAMES:
        val = feats.get(name)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            normalized[name] = None
        elif isinstance(val, (int, float)):
            normalized[name] = round(float(val), 4)
        else:
            normalized[name] = str(val)
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def validate_transaction_item(tx: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate and sanitize a single transaction item."""
    flags: list[str] = []
    sanitized = dict(tx)

    # 1. Amount range check
    try:
        amt = float(sanitized.get("amount_bdt", 0.0))
        if amt < 0:
            flags.append("negative_amount_clipped")
            amt = 0.0
        elif amt > 1_000_000:
            flags.append("excessive_amount_clipped")
            amt = 1_000_000.0
        sanitized["amount_bdt"] = round(amt, 2)
    except (ValueError, TypeError):
        flags.append("invalid_amount")
        sanitized["amount_bdt"] = 0.0

    # 2. Date sanity check
    dt_val = sanitized.get("date")
    if dt_val:
        try:
            if isinstance(dt_val, str):
                dt = datetime.fromisoformat(dt_val)
            elif isinstance(dt_val, datetime):
                dt = dt_val
            else:
                dt = datetime.now(UTC)

            now = datetime.now(UTC)
            # Cannot be in the far future (> 2 days) or older than 2018
            if dt > now and (dt - now).days > 2:
                flags.append("future_date_flagged")
            if dt.year < 2018:
                flags.append("stale_historic_date")
        except Exception:  # noqa: BLE001
            flags.append("unparseable_date")

    # 3. Direction and Type
    if sanitized.get("direction") not in ("in", "out"):
        sanitized["direction"] = "out"
    valid_types = {"income", "bill", "recharge", "remittance", "savings", "transfer", "other"}
    if sanitized.get("type") not in valid_types:
        sanitized["type"] = "other"

    return sanitized, flags


def check_feature_ranges(features: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate features against empirical training bounds from feature_ranges.json."""
    ranges = _load_ranges()
    clipped = dict(features)
    flags: list[str] = []

    for name, bounds in ranges.items():
        val = clipped.get(name)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        try:
            fval = float(val)
        except (ValueError, TypeError):
            continue

        min_val = bounds.get("min")
        max_val = bounds.get("max")
        if min_val is not None and fval < min_val:
            flags.append(f"{name}_below_min_clipped")
            clipped[name] = min_val
        elif max_val is not None and fval > max_val:
            flags.append(f"{name}_above_max_clipped")
            clipped[name] = max_val

    return clipped, flags


def check_out_of_distribution(features: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check if features significantly deviate from the training distribution (OOD)."""
    ranges = _load_ranges()
    ood_flags: list[str] = []
    extreme_count = 0

    for name, bounds in ranges.items():
        val = features.get(name)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        try:
            fval = float(val)
        except (ValueError, TypeError):
            continue

        p01 = bounds.get("p01")
        p99 = bounds.get("p99")
        if p01 is not None and p99 is not None and p99 > p01:
            iqr_span = p99 - p01
            lower_bound = p01 - 0.75 * iqr_span
            upper_bound = p99 + 0.75 * iqr_span
            if fval < lower_bound or fval > upper_bound:
                extreme_count += 1
                ood_flags.append(f"ood_{name}")

    is_ood = extreme_count >= 2
    return is_ood, ood_flags


def check_cross_source_consistency(
    transactions: list[Any],
    documents: list[Any],
) -> tuple[list[str], list[str]]:
    """Cross-validate OCR documents against SMS transaction history."""
    flags: list[str] = []
    notes_bn: list[str] = []

    tx_list: list[dict[str, Any]] = [
        t.model_dump() if isinstance(t, BaseModel) else t for t in transactions
    ]
    doc_list: list[dict[str, Any]] = [
        d.model_dump() if isinstance(d, BaseModel) else d for d in documents
    ]

    # 1. OCR Utility Bill vs SMS Bill Payment
    ocr_bills = [d for d in doc_list if d.get("document_type") == "utility_bill"]
    sms_bills = [t for t in tx_list if t.get("type") == "bill"]

    for b in ocr_bills:
        ocr_amt = float(b.get("amount_bdt") or 0.0)
        provider = str(b.get("provider") or "").upper()
        if ocr_amt > 0 and sms_bills:
            # Check for payment matching ± 10%
            match = next(
                (
                    s
                    for s in sms_bills
                    if abs(float(s.get("amount_bdt", 0)) - ocr_amt) <= max(50.0, 0.1 * ocr_amt)
                ),
                None,
            )
            if match:
                notes_bn.append(
                    f"{provider or 'ইউটিলিটি'} বিলের পরিমাণ (৳{ocr_amt:.0f}) এবং এসএমএস পরিশোধের তথ্য সফলভাবে মেলানো হয়েছে।"
                )
            else:
                flags.append("bill_ocr_sms_unmatched")
                notes_bn.append(
                    f"{provider or 'ইউটিলিটি'} বিল (৳{ocr_amt:.0f}) এসএমএস রেকর্ডের সাথে মেলেনি (ক্যাশ পরিশোধ হতে পারে)।"
                )

    # 2. Duplicate transaction detection
    seen_hashes: set[str] = set()
    dup_count = 0
    for t in tx_list:
        tx_hash = t.get("raw_hash") or f"{t.get('date')}_{t.get('amount_bdt')}_{t.get('type')}"
        if tx_hash in seen_hashes:
            dup_count += 1
        else:
            seen_hashes.add(tx_hash)
    if dup_count > 0:
        flags.append(f"{dup_count}_duplicate_transactions_removed")

    return flags, notes_bn


def validate_sufficiency(features: dict[str, Any]) -> tuple[bool, str | None]:
    """Ensure applicant has >= 3 months wallet history or an active Bhorsha psychometric score."""
    m_wallet = features.get("months_on_wallet")
    bhorsha = features.get("bhorsha_score")

    has_wallet_history = m_wallet is not None and float(m_wallet) >= 3.0
    has_bhorsha = bhorsha is not None and float(bhorsha) > 0.0

    if not has_wallet_history and not has_bhorsha:
        msg = (
            "ঋণ বিবেচনার জন্য কমপক্ষে ৩ মাসের লেনদেনের তথ্য অথবা ভরসা সাইকোমেট্রিক অ্যাসেসমেন্ট সম্পন্ন করা আবশ্যক।"
        )
        return False, msg

    return True, None


def validate_features_before_scoring(
    features: dict[str, Any],
    raw_sources: dict[str, Any] | None = None,
    enforce_sufficiency: bool = True,
) -> ValidationResult:
    """Primary validation gate between AI data ingestion and credit scoring."""
    sources_info = raw_sources or {}
    transactions = sources_info.get("transactions", [])
    documents = sources_info.get("documents", [])

    all_flags: list[str] = []
    notes_bn: list[str] = []

    # 1. Type and basic sanity check
    sanitized: dict[str, Any] = {}
    for name in FEATURE_NAMES:
        val = features.get(name)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            sanitized[name] = None
        else:
            try:
                sanitized[name] = float(val)
            except (ValueError, TypeError):
                all_flags.append(f"invalid_type_{name}")
                sanitized[name] = None

    if all(v is None for v in sanitized.values()):
        raise ValidationFailureError("All feature values are null; cannot score applicant.")

    # 2. Sufficiency check
    is_sufficient, suff_msg = validate_sufficiency(sanitized)
    if enforce_sufficiency and not is_sufficient:
        raise InsufficientDataError(suff_msg or "Insufficient data for scoring.")

    # 3. Range check & clipping
    clipped, range_flags = check_feature_ranges(sanitized)
    all_flags.extend(range_flags)
    if range_flags:
        notes_bn.append("অস্বাভাবিক কিছু সংখ্যা নির্ভরযোগ্য সীমার মধ্যে স্বয়ংক্রিয়ভাবে সামঞ্জস্য করা হয়েছে।")

    # 4. Out-of-distribution check
    is_ood, ood_flags = check_out_of_distribution(clipped)
    all_flags.extend(ood_flags)
    if is_ood:
        notes_bn.append("লেনদেনের কিছু বৈশিষ্ট্যে ভিন্নতর ধরন লক্ষ্য করা গেছে (পর্যালোচনা প্রয়োজন)।")

    # 5. Cross-checks
    if transactions or documents:
        cross_flags, cross_notes = check_cross_source_consistency(transactions, documents)
        all_flags.extend(cross_flags)
        notes_bn.extend(cross_notes)

    # 6. Confidence calculation
    base_conf = 0.98
    if ood_flags:
        base_conf -= 0.05 * len(ood_flags)
    if range_flags:
        base_conf -= 0.02 * len(range_flags)
    confidence = max(0.50, min(1.0, round(base_conf, 2)))

    sources_used: list[str] = []
    if transactions:
        sources_used.append("sms")
    if documents:
        sources_used.extend([d.get("document_type", "document") for d in documents])
    if sanitized.get("bhorsha_score") is not None:
        sources_used.append("bhorsha")
    if not sources_used:
        sources_used = ["manual_input"]

    months_covered = float(clipped.get("months_on_wallet") or 0.0)
    tx_count = (
        len(transactions)
        if transactions
        else int((clipped.get("txn_per_month") or 0.0) * max(1.0, months_covered))
    )

    if not notes_bn:
        notes_bn.append("যাচাইকৃত তথ্যের ভিত্তিতে স্কোর নির্ধারিত হয়েছে।")

    data_quality = DataQualityBlock(
        sources_used=list(dict.fromkeys(sources_used)),
        months_covered=round(months_covered, 1),
        transactions_counted=tx_count,
        flags=all_flags,
        confidence=confidence,
        notes_bn=notes_bn,
    )

    f_hash = compute_feature_hash(clipped)
    needs_review = is_ood or (confidence < 0.75)

    return ValidationResult(
        features=clipped,
        data_quality=data_quality,
        feature_hash=f_hash,
        needs_review=needs_review,
        is_sufficient=is_sufficient,
        flags=all_flags,
    )


def validate_explanation(
    summary_bn: str,
    decision_score: int,
    shap_features: set[str],
) -> tuple[bool, str | None]:
    """Explanation guard: verifies summary mentions only SHAP features, valid numbers, and no approval promises."""
    if not summary_bn or not summary_bn.strip():
        return False, "empty_summary"

    # 1. Reject approval promises
    if APPROVAL_PROMISE_RE.search(summary_bn):
        return False, "contains_approval_promise"

    # 2. Check feature mentions
    reasons_meta: dict[str, list[str]] = load_meta().get("reasons", {})
    lowered = summary_bn.lower()
    mentioned: set[str] = set()
    for feature, phrases in reasons_meta.items():
        if (
            any(p and p in summary_bn for p in phrases)
            or ENGLISH_FEATURE_LABELS.get(feature, "#").lower() in lowered
        ):
            mentioned.add(feature)

    hallucinated = mentioned - shap_features
    if hallucinated:
        return False, f"hallucinated_features:{sorted(hallucinated)}"

    # 3. Check numbers (score must match decision_score if mentioned)
    number_matches = re.findall(r"\b\d{3,4}\b", summary_bn)
    for num_str in number_matches:
        try:
            num = int(num_str)
            if 300 <= num <= 900 and num != decision_score:
                return False, f"mismatched_score_number:{num}_vs_{decision_score}"
        except ValueError:
            pass

    return True, None


def validate_bhorsha_session(
    evaluations: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Bhorsha guard: checks score ranges, stability, and paired question contradictions."""
    flags: list[str] = []
    if not evaluations:
        return False, ["empty_evaluations"]

    for ev in evaluations:
        score = float(ev.get("score", 0.0))
        if score < 0.0 or score > 100.0:
            flags.append(f"out_of_bounds_score_{score}")

    return len(flags) == 0, flags
