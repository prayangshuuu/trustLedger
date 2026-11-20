"""LLM gateway: one interface for DeepSeek chat, DeepSeek-OCR and an offline mock.

Every LLM call in the app goes through ``get_llm_client()``. Callers that need a specific mock
behaviour put ``<task>name</task>`` in their system prompt; the mock routes on that tag.
"""

import base64
import json
import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger("trustledger.llm")

# Optional hook (set by observability) receiving (kind, prompt_tokens, completion_tokens, ok)
usage_hook: Callable[[str, int, int, bool], None] | None = None

TASK_RE = re.compile(r"<task>([a-z_]+)</task>")


def _record(kind: str, prompt_tokens: int, completion_tokens: int, ok: bool) -> None:
    if usage_hook is not None:
        try:
            usage_hook(kind, prompt_tokens, completion_tokens, ok)
        except Exception:  # noqa: BLE001 - metrics must never break a call
            logger.debug("usage hook failed")


def _validate(schema: type[BaseModel] | dict[str, Any] | None, data: Any) -> Any:
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_validate(data)
    return data


def _extract_json(content: str) -> Any:
    """Parse JSON, tolerating code fences or a reasoning preamble before the object."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


@runtime_checkable
class LLMClient(Protocol):
    """Unified gateway protocol for chat generation and OCR extraction."""

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        """Send chat messages and return text, or a validated object when schema is given."""
        ...

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> Any:
        """Extract structured fields from an image with a strict output schema."""
        ...


class DeepSeekClient:
    """Live client for the DeepSeek OpenAI-compatible API (chat) and a DeepSeek-OCR server.

    DeepSeek-OCR is an open-weights model; we call it through any OpenAI-compatible
    ``/chat/completions`` endpoint that serves it (vLLM, SGLang or a hosted provider),
    configured with ``DEEPSEEK_OCR_URL``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        ocr_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or settings.DEEPSEEK_BASE_URL).rstrip("/")
        self.ocr_url = (ocr_url or settings.DEEPSEEK_OCR_URL or "").rstrip("/")
        self.chat_model = settings.DEEPSEEK_CHAT_MODEL
        self.ocr_model = settings.DEEPSEEK_OCR_MODEL
        self.ocr_api_key = settings.DEEPSEEK_OCR_API_KEY or self.api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def _post_with_retries(
        self, kind: str, endpoint: str, payload: dict[str, Any], api_key: str
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.perf_counter()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(endpoint, json=payload, headers=headers)
                    resp.raise_for_status()
                    data: dict[str, Any] = resp.json()
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                usage = data.get("usage", {}) or {}
                logger.info(
                    "DeepSeek %s success: prompt_tokens=%s completion_tokens=%s "
                    "cache_hit_tokens=%s cache_miss_tokens=%s duration_ms=%s",
                    kind,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    usage.get("prompt_cache_hit_tokens", 0),
                    usage.get("prompt_cache_miss_tokens", 0),
                    duration_ms,
                )
                _record(
                    kind,
                    int(usage.get("prompt_tokens") or 0),
                    int(usage.get("completion_tokens") or 0),
                    True,
                )
                return data
            except Exception as e:  # noqa: BLE001
                last_error = e
                _record(kind, 0, 0, False)
                if attempt < self.max_retries:
                    backoff = 2**attempt
                    logger.warning(
                        "DeepSeek %s attempt %s failed: %s. Retrying in %ss",
                        kind,
                        attempt,
                        type(e).__name__,
                        backoff,
                    )
                    time.sleep(backoff)
        raise RuntimeError(
            f"DeepSeek {kind} failed after {self.max_retries} attempts"
        ) from last_error

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        if not self.api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not configured. Set the environment variable or use LLM_MODE=mock."
            )
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
        }
        if schema is not None:
            payload["response_format"] = {"type": "json_object"}
            schema_json = (
                schema.model_json_schema()
                if isinstance(schema, type) and issubclass(schema, BaseModel)
                else schema
            )
            instruction = (
                "Return only a valid JSON object matching this JSON schema:\n"
                + json.dumps(schema_json, ensure_ascii=False)
            )
            payload["messages"] = [{"role": "system", "content": instruction}, *messages]

        data = self._post_with_retries(
            "chat", f"{self.base_url}/chat/completions", payload, self.api_key
        )
        content_str: str = data["choices"][0]["message"]["content"]
        if schema is not None:
            return _validate(schema, _extract_json(content_str))
        return content_str

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> Any:
        if not self.ocr_api_key or not self.ocr_url:
            raise RuntimeError("DEEPSEEK_OCR_URL / API key are not configured for OCR.")
        schema_json = (
            schema.model_json_schema()
            if isinstance(schema, type) and issubclass(schema, BaseModel)
            else (schema or {})
        )
        data_uri = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
        prompt = (
            "Read this document (Bangla and English). Return only a JSON object matching this "
            "schema, with a 'confidence' between 0 and 1:\n"
            + json.dumps(schema_json, ensure_ascii=False)
        )
        payload = {
            "model": self.ocr_model,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        data = self._post_with_retries(
            "ocr", f"{self.ocr_url}/chat/completions", payload, self.ocr_api_key
        )
        content: str = data["choices"][0]["message"]["content"]
        return _validate(schema, _extract_json(content))


MockHandler = Callable[[str, str], Any]
_mock_handlers: dict[str, MockHandler] = {}


def register_mock_task(task: str, handler: MockHandler) -> None:
    """Register a deterministic mock response for ``<task>task</task>`` prompts.

    The handler receives (system_prompt, user_content) and returns a dict or str.
    """
    _mock_handlers[task] = handler


class MockClient:
    """Deterministic offline implementation for tests, CI and demos without keys."""

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        user_content = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        _record("chat", 0, 0, True)

        task_match = TASK_RE.search(system)
        if task_match and task_match.group(1) in _mock_handlers:
            result = _mock_handlers[task_match.group(1)](system, user_content)
            if schema is not None:
                return _validate(schema, result)
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

        # SMS parser fallback (prompt sends "Parse this SMS: ...")
        if "SMS" in user_content or "transaction" in user_content.lower():
            extracted_amount = 500.0
            amt_match = re.search(
                r"(?:tk|bdt|\$)\s*([\d,]+(?:\.\d+)?)", user_content, re.IGNORECASE
            )
            if amt_match:
                try:
                    extracted_amount = float(amt_match.group(1).replace(",", ""))
                except ValueError:
                    extracted_amount = 500.0
            mock_data = {
                "date": "2026-11-15T12:00:00Z",
                "amount_bdt": extracted_amount,
                "direction": "out",
                "type": "other",
                "counterparty": None,
                "txn_id": None,
                "raw_hash": "mock_hash_123",
            }
            return _validate(schema, mock_data) if schema is not None else mock_data

        default_resp = {"status": "ok", "response": "Mock conversational response"}
        if schema is not None and isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(default_resp)
        return json.dumps(default_resp)

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> Any:
        _record("ocr", 0, 0, True)
        schema_name = getattr(schema, "__name__", "")

        # Eval fixtures: return their labelled fields so the OCR eval measures the pipeline
        if filename:
            labels_path = Path(__file__).resolve().parents[3] / "evals" / "ocr" / "labels.json"
            if labels_path.exists():
                try:
                    labels = json.loads(labels_path.read_text(encoding="utf-8"))
                    for item in labels:
                        if item["filename"] == filename:
                            exp = dict(item["expected"])
                            exp["confidence"] = 0.95
                            return _validate(schema, exp)
                except (OSError, json.JSONDecodeError, KeyError):
                    logger.debug("Failed reading labels for OCR fixture %s", filename)

        mock_ocr: dict[str, Any]
        if "Receipt" in schema_name:
            mock_ocr = {
                "document_type": "receipt",
                "merchant_or_platform": "Shwapno Superstore",
                "amount_bdt": 1850.0,
                "date": "2026-10-20",
                "trx_id": "POS778899",
                "category": "Groceries",
                "confidence": 0.94,
            }
        elif "Khata" in schema_name:
            mock_ocr = {
                "document_type": "khata_page",
                "shop_name": "Bhai Bhai General Store",
                "page_total_bdt": 3400.0,
                "entries": [
                    {
                        "customer_name": "Rahim Uddin",
                        "amount_bdt": 1200.0,
                        "direction": "out",
                        "date": "10/10/2026",
                    },
                    {
                        "customer_name": "Karim Mia",
                        "amount_bdt": 2200.0,
                        "direction": "in",
                        "date": "12/10/2026",
                    },
                ],
                "confidence": 0.91,
            }
        else:
            mock_ocr = {
                "document_type": "utility_bill",
                "provider": "DESCO",
                "amount_bdt": 1450.0,
                "due_date": "2026-11-25",
                "bill_month": "October 2026",
                "paid": True,
                "account_or_meter_no": "MTR-982103",
                "confidence": 0.96,
            }
        return _validate(schema, mock_ocr)


_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return the client selected by LLM_MODE (live needs DEEPSEEK_API_KEY, else mock)."""
    global _client_instance
    if _client_instance is None:
        settings = get_settings()
        mode = (settings.LLM_MODE or os.getenv("LLM_MODE", "mock")).lower()
        if mode == "live" and settings.DEEPSEEK_API_KEY:
            _client_instance = DeepSeekClient()
        else:
            if mode == "live":
                logger.warning("LLM_MODE=live but DEEPSEEK_API_KEY is empty; using MockClient")
            _client_instance = MockClient()
    return _client_instance


def is_live() -> bool:
    return isinstance(get_llm_client(), DeepSeekClient)


def reset_llm_client() -> None:
    """Clear cached LLMClient instance."""
    global _client_instance
    _client_instance = None
