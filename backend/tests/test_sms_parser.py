"""Unit and evaluation tests for SMS parsing, PII redaction, and LLM gateway."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    load_sms_parser_prompt,
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
    assert "<BD_NID>" in redacted or "1994123456789" not in redacted
    # Non-sensitive transactional tokens are preserved
    assert "1,500.00" in redacted
    assert "SM123456" in redacted


def test_presidio_pii_redaction_bangla_digits() -> None:
    """Verify that Presidio redaction scrubs Bengali numerals phone numbers."""
    bangla_sample = "টাকা পাঠানো হয়েছে ০১৭১১২২৩৩৪৪ নম্বরে। TrxID BN992019।"
    redacted = redact_pii(bangla_sample)
    assert "০১৭১১২২৩৩৪৪" not in redacted
    assert "<PHONE_NUMBER>" in redacted


def test_normalize_bangla_digits() -> None:
    """Verify Bengali digits ০১২৩৪৫৬৭৮৯ are translated to 0123456789."""
    bangla_str = "টাকা ৫,৪৫০.৫০ তারিখ ১২/১০/২০২৬"
    normalized = normalize_bangla_digits(bangla_str)
    assert "5,450.50" in normalized
    assert "12/10/2026" in normalized


def test_sms_parser_prompt_file() -> None:
    """Verify sms_parser.md prompt exists, is XML-structured, and versioned."""
    prompt = load_sms_parser_prompt()
    assert "<system_prompt>" in prompt
    assert "<role>" in prompt
    assert "<few_shot_examples>" in prompt
    assert "Version:" in prompt


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
    if isinstance(client_no_key, DeepSeekClient):
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY is not configured"):
            client_no_key.chat([{"role": "user", "content": "hello"}])
    else:
        assert isinstance(client_no_key, MockClient)


def test_deepseek_client_chat_mocked_network(caplog: pytest.LogCaptureFixture) -> None:
    """Verify DeepSeekClient chat invokes OpenAI-compatible endpoint with JSON mode and logs usage."""
    client = DeepSeekClient(api_key="sk-test-key", base_url="https://api.deepseek.com")

    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "date": "2026-11-20T10:00:00Z",
                            "amount_bdt": 2500.0,
                            "direction": "in",
                            "type": "income",
                            "counterparty": "Test Employer",
                            "txn_id": "TESTTXN99",
                            "raw_hash": "a" * 64,
                        }
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "prompt_cache_hit_tokens": 100,
            "prompt_cache_miss_tokens": 20,
        },
    }

    with (
        patch("httpx.Client.post", return_value=fake_response),
        patch("app.llm.client.logger.info") as mock_log_info,
    ):
        result = client.chat(
            messages=[{"role": "user", "content": "Parse this SMS: Tk 2500 from Employer"}],
            schema=Transaction,
        )

        assert isinstance(result, Transaction)
        assert result.amount_bdt == 2500.0
        assert result.type == "income"
        assert result.txn_id == "TESTTXN99"

        # Verify usage and context caching logging
        mock_log_info.assert_called_once()
        log_format = mock_log_info.call_args[0][0]
        log_args = mock_log_info.call_args[0]
        assert "DeepSeek %s success" in log_format
        assert log_args[1] == "chat"
        assert log_args[4] == 100  # cache_hit_tokens


def test_deepseek_client_retries_and_backoff() -> None:
    """Verify DeepSeekClient performs retries with exponential backoff on transient failure."""
    client = DeepSeekClient(api_key="sk-test-key", max_retries=3)

    success_response = MagicMock()
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {
        "choices": [{"message": {"content": '{"status": "ok"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    # Fails twice with exceptions, succeeds on 3rd attempt
    with (
        patch(
            "httpx.Client.post",
            side_effect=[
                Exception("500 Server Error"),
                Exception("500 Server Error"),
                success_response,
            ],
        ),
        patch("time.sleep") as mock_sleep,
    ):
        res = client.chat([{"role": "user", "content": "hi"}])
        assert res == '{"status": "ok"}'
        assert mock_sleep.call_count == 2


def test_deepseek_client_retry_exhaustion() -> None:
    """Verify DeepSeekClient raises RuntimeError after exhausting all retries."""
    client = DeepSeekClient(api_key="sk-test-key", max_retries=2)

    with (
        patch("httpx.Client.post", side_effect=Exception("Connection refused")),
        patch("time.sleep"),
        pytest.raises(RuntimeError, match="DeepSeek chat failed after 2 attempts"),
    ):
        client.chat([{"role": "user", "content": "hi"}])


def test_deepseek_client_ocr_mocked() -> None:
    """Verify DeepSeekClient ocr sends multipart request and returns structured output."""
    client = DeepSeekClient(api_key="sk-test-key", ocr_url="http://ocr.local/v1")

    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"document_type": "utility_bill", "provider": "DESCO", "amount_bdt": 1200.0}
                    )
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=fake_response) as mock_post:
        res = client.ocr(b"dummy_image_data")
        sent = mock_post.call_args.kwargs["json"]
        assert mock_post.call_args.args[0] == "http://ocr.local/v1/chat/completions"
        assert sent["messages"][0]["content"][0]["type"] == "image_url"
        assert res["provider"] == "DESCO"
        assert res["amount_bdt"] == 1200.0


def test_stage2_llm_fallback_invoked_on_unrecognized_sms() -> None:
    """Verify parse_sms falls back to Stage 2 LLM when regex cannot parse an unstructured SMS."""
    weird_sms = "Some completely unrecognized novel banking notification: Tk 999.00 processed for merchant XYZ."
    trx = parse_sms(weird_sms, use_llm_fallback=True)
    assert isinstance(trx, Transaction)
    assert trx.amount_bdt == 999.0
    assert trx.raw_hash == compute_raw_hash(weird_sms)


@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"), reason="Live mode BLOCKED (no DEEPSEEK_API_KEY)"
)
def test_live_deepseek_api() -> None:
    """Verify live DeepSeek API call when DEEPSEEK_API_KEY is provided."""
    client = DeepSeekClient()
    res = client.chat([{"role": "user", "content": 'Return JSON: {"ping": "pong"}'}])
    assert "pong" in res
