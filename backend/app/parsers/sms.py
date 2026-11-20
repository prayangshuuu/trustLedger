"""Bangladeshi MFS and banking SMS parser.

Implements two-stage parsing:
1. High-throughput deterministic regex parser for bKash, Nagad, Rocket, Upay, bank, and utility bills.
2. PII-redacted LLM fallback (DeepSeek) for unseen, complex, or conversational formats.

Follows PLAN_CONTEXT.md §6: Raw SMS text is NEVER stored in database or persistent logs.
"""

import csv
import hashlib
import io
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.llm.client import get_llm_client
from app.privacy.redaction import redact_pii

logger = logging.getLogger("trustledger.sms")

# Conversion table for Bengali digits ০-৯ to standard Arabic numerals 0-9
BANGLA_DIGITS_TABLE = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

PROMPT_FILE_PATH = Path(__file__).resolve().parent / "prompts" / "sms_parser.md"

TransactionType = Literal[
    "income", "bill", "recharge", "remittance", "savings", "transfer", "other"
]
TransactionDirection = Literal["in", "out"]


class Transaction(BaseModel):
    """Structured financial transaction extracted from SMS."""

    date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Transaction execution date and time",
    )
    amount_bdt: float = Field(..., ge=0.0, description="Transaction amount in BDT")
    direction: TransactionDirection = Field(
        ..., description="'in' for credits/receipts, 'out' for debits/payments"
    )
    type: TransactionType = Field(
        ...,
        description="Transaction category: income | bill | recharge | remittance | savings | transfer | other",
    )
    counterparty: str | None = Field(
        default=None, description="Sender, merchant, biller, or receiver name/institution"
    )
    txn_id: str | None = Field(default=None, description="Unique MFS/Bank transaction identifier")
    raw_hash: str = Field(
        ..., description="SHA-256 fingerprint of the raw message for deduplication"
    )
    confidence: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Extraction confidence score (0.0 - 1.0)"
    )


@lru_cache(maxsize=1)
def load_sms_parser_prompt() -> str:
    """Load XML-structured SMS parser system prompt."""
    if PROMPT_FILE_PATH.exists():
        return PROMPT_FILE_PATH.read_text(encoding="utf-8")
    return (
        "<system_prompt>\n"
        "<role>You are an expert financial transaction extraction system for Bangladeshi SMS.</role>\n"
        "</system_prompt>"
    )


def normalize_bangla_digits(text: str) -> str:
    """Translate Bengali digits to standard ASCII digits."""
    return text.translate(BANGLA_DIGITS_TABLE)


def compute_raw_hash(text: str) -> str:
    """Compute deterministic SHA-256 fingerprint of raw text without persisting content."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def extract_amount(text: str) -> float | None:
    """Extract numeric amount from text handling commas and decimal points."""
    m = re.search(r"(?:Tk|BDT|টাকা|পরিমাণ)\s*[:.]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:Tk|BDT|টাকা)", text, re.IGNORECASE)
    if m:
        raw_num = m.group(1).replace(",", "")
        try:
            return float(raw_num)
        except ValueError:
            return None
    return None


def extract_trx_id(text: str) -> str | None:
    """Extract MFS or banking TrxID."""
    m = re.search(
        r"(?:TrxID|TxnID|Trx\s*Id|ট্রানজেকশন\s*আইডি)\s*[:.\s]*([A-Za-z0-9]+)", text, re.IGNORECASE
    )
    return m.group(1) if m else None


def extract_date(text: str) -> datetime:
    """Extract date from text with fallback to current UTC timestamp."""
    # Pattern: DD/MM/YYYY or DD-MM-YYYY, optional HH:MM
    m = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\b", text
    )
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        raw_year = int(m.group(3))
        year = raw_year + 2000 if raw_year < 100 else raw_year
        hour = int(m.group(4) or 12)
        minute = int(m.group(5) or 0)
        try:
            return datetime(year, month, day, hour, minute, tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def parse_regex_stage(text: str, raw_hash: str) -> Transaction | None:
    """Stage 1: High-speed regex parsing for known Bangladeshi MFS and banking SMS formats."""
    norm_text = normalize_bangla_digits(text)
    lower = norm_text.lower()

    # Check for failed transactions -> classify as other/failed
    if any(k in lower for k in ("failed", "unsuccessful", "declined", "canceled", "বাতিল", "ব্যর্থ")):
        amount = extract_amount(norm_text) or 0.0
        return Transaction(
            date=extract_date(norm_text),
            amount_bdt=amount,
            direction="out",
            type="other",
            counterparty="Failed Transaction",
            txn_id=extract_trx_id(norm_text),
            raw_hash=raw_hash,
        )

    parsed_amount = extract_amount(norm_text)
    if parsed_amount is None:
        return None
    amount = parsed_amount

    txn_id = extract_trx_id(norm_text)
    txn_date = extract_date(norm_text)

    # 1. Remittance
    if any(
        k in lower for k in ("remittance", "western union", "moneygram", "রেমিট্যান্স", "প্রবাসী আয়")
    ):
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="in",
            type="remittance",
            counterparty="Foreign Remittance",
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 2. Mobile Recharge (must precede fee checks to prevent "recharge" matching "charge")
    if any(k in lower for k in ("recharge", "airtime", "রিচার্জ", "টপ আপ")):
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="out",
            type="recharge",
            counterparty="Mobile Airtime",
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 3. Utility Bills
    bill_keywords = (
        "desco",
        "dpdc",
        "wasa",
        "titas",
        "nesco",
        "breb",
        "btcl",
        "carnival",
        "electricity",
        "bill",
        "pay bill",
        "পল্লী বিদ্যুৎ",
        "বিল পরিশোধ",
        "গ্যাস বিল",
        "বিদ্যুৎ বিল",
        "পানির বিল",
    )
    if any(k in lower for k in bill_keywords):
        counterparty = "Utility Biller"
        for kw in ("desco", "dpdc", "wasa", "titas", "nesco", "breb", "btcl", "carnival"):
            if kw in lower:
                counterparty = kw.upper()
                break
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="out",
            type="bill",
            counterparty=counterparty,
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 4. Salary / Income
    salary_keywords = ("salary", "payroll", "বেতন", "মজুরি", "উপবৃত্তি")
    if any(k in lower for k in salary_keywords):
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="in",
            type="income",
            counterparty="Employer / Payroll",
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 5. DPS / Savings
    if any(k in lower for k in ("dps", "savings", "সঞ্চয়", "ডিপিএস")):
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="out",
            type="savings",
            counterparty="Savings / DPS",
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 6. Service fee / adjustments / other debits
    if any(k in lower for k in ("fee deduction", "service fee", "annual sms", "চার্জ", "ফি কর্তন")):
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="out",
            type="other",
            counterparty="Service Fee / Bank",
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 7. Cash In / Money Received (Inflow)
    if any(
        k in lower
        for k in (
            "received tk",
            "cash in",
            "deposit",
            "টাকা জমা",
            "টাকা পেয়েছেন",
            "জমা হয়েছে",
            "ক্রেডিট",
            "credited",
            "ক্যাশ ইন",
        )
    ):
        counterparty = "Agent / Sender"
        from_m = re.search(
            r"from\s+([A-Za-z0-9_\s]+?)(?:\.|\s+ref|\s+fee|\s+balance|\s+trxid)",
            norm_text,
            re.IGNORECASE,
        )
        if from_m:
            counterparty = from_m.group(1).strip()
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="in",
            type="income" if "salary" in lower else "transfer",
            counterparty=counterparty,
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    # 8. Send Money / Payment / Cash Out (Outflow)
    if any(
        k in lower
        for k in (
            "send money",
            "payment tk",
            "payment of tk",
            "cash out",
            "টাকা পাঠানো",
            "পেমেন্ট",
            "ক্যাশ আউট",
        )
    ):
        counterparty = "Receiver / Merchant"
        to_m = re.search(
            r"to\s+([A-Za-z0-9_\s]+?)(?:\.|\s+fee|\s+balance|\s+trxid)", norm_text, re.IGNORECASE
        )
        if to_m:
            counterparty = to_m.group(1).strip()
        return Transaction(
            date=txn_date,
            amount_bdt=amount,
            direction="out",
            type="transfer",
            counterparty=counterparty,
            txn_id=txn_id,
            raw_hash=raw_hash,
        )

    return None


def parse_llm_stage(text: str, raw_hash: str) -> Transaction:
    """Stage 2: Fallback to LLM parser after scrubbing PII with Presidio."""
    # Strict compliance check: Redact PII before LLM invocation
    anonymized_text = redact_pii(text)

    llm = get_llm_client()
    system_prompt = load_sms_parser_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Parse this SMS:\n{anonymized_text}"},
    ]

    try:
        raw_res = llm.chat(messages=messages, schema=Transaction)
        if isinstance(raw_res, Transaction):
            res_dict = raw_res.model_dump()
            res_dict["raw_hash"] = raw_hash
            res_dict["confidence"] = 0.85
            return Transaction.model_validate(res_dict)
        if isinstance(raw_res, dict):
            raw_res["raw_hash"] = raw_hash
            raw_res["confidence"] = 0.85
            return Transaction.model_validate(raw_res)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "LLM SMS extraction failed (%s); falling back to low-confidence heuristic", e
        )

    # Low-confidence fallback if LLM completion is unparseable or failed
    return Transaction(
        date=extract_date(text),
        amount_bdt=extract_amount(text) or 0.0,
        direction="out",
        type="other",
        counterparty=None,
        txn_id=extract_trx_id(text),
        raw_hash=raw_hash,
        confidence=0.35,
    )


def extract_messages_from_export(content: str | bytes, filename: str | None = None) -> list[str]:
    """Extract raw SMS message strings from .txt, .csv, Android backup .xml, or raw pasted text."""
    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = content

    lower_fn = (filename or "").lower()
    trimmed = text.strip()
    if not trimmed:
        return []

    # 1. Android SMS backup XML (<smses><sms ... body="..."/></smses>)
    if lower_fn.endswith(".xml") or trimmed.startswith("<?xml") or "<smses" in trimmed:
        messages: list[str] = []
        try:
            root = ET.fromstring(trimmed)
            for el in root.iter("sms"):
                body = el.attrib.get("body") or el.attrib.get("msg") or el.text
                if body and body.strip():
                    messages.append(body.strip())
            if messages:
                return messages
        except Exception:  # noqa: BLE001
            xml_matches = re.findall(r'body="([^"]+)"', trimmed)
            if xml_matches:
                cleaned = [
                    m.replace("&amp;", "&")
                    .replace("&quot;", '"')
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                    for m in xml_matches
                    if m.strip()
                ]
                if cleaned:
                    return cleaned

    # 2. CSV file (either explicit .csv extension or first line has standard CSV message header)
    first_line = trimmed.split("\n", 1)[0].lower() if trimmed else ""
    is_csv_header = "," in first_line and any(
        c in first_line for c in ("body", "message", "sms", "text", "content")
    )
    if lower_fn.endswith(".csv") or is_csv_header:
        try:
            reader = csv.reader(io.StringIO(trimmed))
            rows = list(reader)
            if rows and len(rows) > 1:
                header = [h.strip().lower() for h in rows[0]]
                body_col = -1
                for candidate in ("body", "message", "sms", "text", "content"):
                    if candidate in header:
                        body_col = header.index(candidate)
                        break
                if body_col != -1:
                    msgs = [
                        r[body_col].strip()
                        for r in rows[1:]
                        if len(r) > body_col and r[body_col].strip()
                    ]
                    if msgs:
                        return msgs
                if lower_fn.endswith(".csv"):
                    candidates: list[str] = []
                    for row in rows:
                        if row:
                            longest = max(row, key=len).strip()
                            if len(longest) > 15:
                                candidates.append(longest)
                    if candidates:
                        return candidates
        except Exception:  # noqa: BLE001, S110
            pass

    # 3. Plain text / Pasted text
    return [line.strip() for line in trimmed.splitlines() if line.strip()]


def parse_sms(raw_text: str, use_llm_fallback: bool = True) -> Transaction:
    """Parse single SMS string into a structured Transaction.

    Stage 1 regex runs first. If unrecognized and fallback is enabled, invokes Stage 2 LLM.
    """
    raw_hash = compute_raw_hash(raw_text)

    parsed = parse_regex_stage(raw_text, raw_hash)
    if parsed is not None:
        return parsed

    if use_llm_fallback:
        return parse_llm_stage(raw_text, raw_hash)

    return Transaction(
        date=extract_date(raw_text),
        amount_bdt=extract_amount(raw_text) or 0.0,
        direction="out",
        type="other",
        counterparty=None,
        txn_id=extract_trx_id(raw_text),
        raw_hash=raw_hash,
    )


def parse_sms_batch(sms_list: list[str], use_llm_fallback: bool = True) -> list[Transaction]:
    """Parse a list of SMS messages with deduplication by TrxID and raw_hash."""
    transactions: list[Transaction] = []
    seen_ids: set[str] = set()

    for raw_sms in sms_list:
        if not raw_sms or not raw_sms.strip():
            continue
        trx = parse_sms(raw_sms, use_llm_fallback=use_llm_fallback)
        dedupe_key = trx.txn_id if trx.txn_id else trx.raw_hash
        if dedupe_key not in seen_ids:
            seen_ids.add(dedupe_key)
            transactions.append(trx)

    transactions.sort(key=lambda t: t.date)
    return transactions
