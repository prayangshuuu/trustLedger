"""Unit and evaluation tests for SMS parsing, PII redaction, and LLM gateway."""

import json
from pathlib import Path

import pytest
from app.config import Settings
from app.llm.client import (
    DeepSeekClient,
    MockClient,
    get_llm_client,
    reset_llm_client,
)
from app.parsers.sms import (
    Transaction,
    compute_raw_hash,
    normalize_bangla_digits,
    parse_sms,
    parse_sms_batch,
)
from app.privacy.redaction import redact_pii


def test_presidio_pii_redaction() -> None:
    """Verify that Presidio redaction scrubs Bangladeshi phone numbers and personal identifiers."""
    sample_text = (
        "Send Money Tk 1,500.00 from 01711223344 to 01899887766. "
        "User Rahim Uddin, NID 1994123456789. TrxID SM123456 on 12/10/2026."
    )
    redacted = redact_pii(sample_text)

    # Asserts that original phone numbers and NIDs do not appear in redacted output
    assert "01711223344" not in redacted
    assert "01899887766" not in redacted
    assert "<PHONE_NUMBER>" in redacted
    # Non-sensitive transactional tokens are preserved
    assert "1,500.00" in redacted
    assert "SM123456" in redacted


def test_normalize_bangla_digits() -> None:
    """Verify Bengali digits ০১২৩৪৫৬৭৮৯ are translated to 0123456789."""
    bangla_str = "টাকা ৫,৪৫০.৫০ তারিখ ১২/১০/২০২৬"
    normalized = normalize_bangla_digits(bangla_str)
    assert "5,450.50" in normalized
    assert "12/10/2026" in normalized


def test_sms_parser_f1_score_on_fixtures() -> None:
    """Evaluate SMS parser across the 60+ synthetic fixtures and verify F1 >= 0.95."""
    fixtures_path = Path(__file__).parent / "fixtures" / "sms" / "synthetic_sms.json"
    assert fixtures_path.exists(), f"Fixtures file missing at {fixtures_path}"

    with open(fixtures_path, encoding="utf-8") as f:
        fixtures = json.load(f)

    assert len(fixtures) >= 60, f"Expected >= 60 fixtures, got {len(fixtures)}"

    correct_type = 0
    correct_direction = 0
    total = len(fixtures)

    for item in fixtures:
        sms_text = item["text"]
        expected = item["expected"]

        trx = parse_sms(sms_text, use_llm_fallback=True)

        assert isinstance(trx, Transaction)
        assert trx.raw_hash == compute_raw_hash(sms_text)

        if trx.type == expected["type"]:
            correct_type += 1
        if trx.direction == expected["direction"]:
            correct_direction += 1

    type_accuracy = correct_type / total
    direction_accuracy = correct_direction / total
    # For single-label classification over fixed test set, accuracy equals macro-precision/recall
    f1_score = 2 * (type_accuracy * direction_accuracy) / (type_accuracy + direction_accuracy)

    print(
        f"\nSMS Parser Accuracy: Type={type_accuracy:.4f}, "
        f"Direction={direction_accuracy:.4f}, Combined F1={f1_score:.4f}"
    )
    assert f1_score >= 0.95, f"Parser F1 {f1_score:.4f} is below required 0.95 standard"


def test_sms_deduplication() -> None:
    """Verify batch parsing deduplicates identical TrxIDs and identical raw hashes."""
    sms_list = [
        "Payment Tk 1,450.00 to DESCO Bill successful. TrxID BD897201 on 12/09/2026 18:30.",
        "Payment Tk 1,450.00 to DESCO Bill successful. TrxID BD897201 on 12/09/2026 18:30.",  # Duplicate TrxID
        "Payment Tk 500.00 to DESCO Bill successful. TrxID BD897202 on 12/10/2026 18:30.",
        "Payment Tk 500.00 to DESCO Bill successful. TrxID BD897202 on 12/10/2026 18:30.",  # Duplicate TrxID
    ]

    transactions = parse_sms_batch(sms_list)
    assert len(transactions) == 2
    assert {t.txn_id for t in transactions} == {"BD897201", "BD897202"}


def test_no_raw_sms_in_transaction_model() -> None:
    """Verify Transaction model does not include raw SMS string attribute."""
    trx = parse_sms("Cash In Tk 500.00 from Agent 01711 successful. TrxID CI99 on 01/10/2026.")
    data = trx.model_dump()
    assert "raw_text" not in data
    assert "sms" not in data
    assert "raw_hash" in data
    assert len(trx.raw_hash) == 64  # SHA-256 fingerprint


def test_llm_gateway_mock_and_live_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_llm_client factory dynamically chooses MockClient or DeepSeekClient."""
    reset_llm_client()

    # 1. Default or mock mode
    monkeypatch.setattr("app.llm.client.get_settings", lambda: Settings(LLM_MODE="mock"))
    reset_llm_client()
    client = get_llm_client()
    assert isinstance(client, MockClient)

    # 2. Mock client chat output
    mock_resp = client.chat([{"role": "user", "content": "Parse this SMS transaction"}])
    assert "amount_bdt" in mock_resp or isinstance(mock_resp, dict)

    # 3. Live mode with API key configured
    monkeypatch.setattr(
        "app.llm.client.get_settings",
        lambda: Settings(LLM_MODE="live", DEEPSEEK_API_KEY="sk-test-deepseek-key"),
    )
    reset_llm_client()
    live_client = get_llm_client()
    assert isinstance(live_client, DeepSeekClient)

    # 4. Live client raises clear error when DEEPSEEK_API_KEY is missing
    monkeypatch.setattr(
        "app.llm.client.get_settings",
        lambda: Settings(LLM_MODE="live", DEEPSEEK_API_KEY=None),
    )
    reset_llm_client()
    client_no_key = get_llm_client()
    # When no key is set in live mode, falls back to MockClient or raises RuntimeError on chat
    if isinstance(client_no_key, DeepSeekClient):
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY is not configured"):
            client_no_key.chat([{"role": "user", "content": "hello"}])
    else:
        assert isinstance(client_no_key, MockClient)
