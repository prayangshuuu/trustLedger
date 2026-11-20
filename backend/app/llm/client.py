"""LLM gateway abstraction supporting DeepSeek live API and deterministic mock mode."""

import json
import logging
import os
import time
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger("trustledger.llm")


@runtime_checkable
class LLMClient(Protocol):
    """Unified gateway protocol for chat generation and OCR extraction."""

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        """Send chat messages and return completion, optionally constrained by Pydantic schema."""
        ...

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
    ) -> Any:
        """Perform multimodal OCR extraction from image bytes with strict JSON output schema."""
        ...


class DeepSeekClient:
    """Live implementation calling DeepSeek API with retry, backoff, and JSON schema mode."""

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
        self.ocr_url = ocr_url or settings.DEEPSEEK_OCR_URL
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        if not self.api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not configured. Please set the environment variable or use LLM_MODE=mock."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
        }

        if schema is not None:
            payload["response_format"] = {"type": "json_object"}
            system_instruction = "Return a valid JSON object matching the requested schema."
            payload["messages"] = [
                {"role": "system", "content": system_instruction},
                *messages,
            ]

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.perf_counter()
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(endpoint, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                usage = data.get("usage", {})
                logger.info(
                    "DeepSeek chat success: prompt_tokens=%s completion_tokens=%s duration_ms=%s",
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    duration_ms,
                )

                content_str = data["choices"][0]["message"]["content"]
                if schema is not None:
                    parsed_json = json.loads(content_str)
                    if isinstance(schema, type) and issubclass(schema, BaseModel):
                        return schema.model_validate(parsed_json)
                    return parsed_json
                return content_str

            except Exception as e:  # noqa: BLE001  # noqa: BLE001
                last_error = e
                backoff = 2**attempt
                logger.warning(
                    "DeepSeek chat attempt %s failed: %s. Retrying in %ss...",
                    attempt,
                    e,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(
            f"DeepSeek chat failed after {self.max_retries} attempts"
        ) from last_error

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
    ) -> Any:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured for OCR service.")

        # DeepSeek multimodal / OCR endpoint
        endpoint = self.ocr_url or f"{self.base_url}/ocr"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("document.jpg", image_bytes, "image/jpeg")}

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(endpoint, files=files, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                if schema is not None:
                    if isinstance(schema, type) and issubclass(schema, BaseModel):
                        return schema.model_validate(data)
                    return data
                return data

            except Exception as e:
                time.sleep(2**attempt)
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"DeepSeek OCR failed after {self.max_retries} attempts: {e}"
                    ) from e


class MockClient:
    """Deterministic offline mock implementation for tests and local development."""

    def chat(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Any:
        user_content = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )

        # 1. SMS parsing fallback response
        if "SMS" in user_content or "transaction" in user_content.lower():
            mock_data = {
                "date": "2026-11-15T12:00:00Z",
                "amount_bdt": 500.0,
                "direction": "out",
                "type": "recharge",
                "counterparty": "Grameenphone",
                "txn_id": "MOCKTXN123",
                "raw_hash": "mock_hash_123",
            }
            if schema and isinstance(schema, type) and issubclass(schema, BaseModel):
                return schema.model_validate(mock_data)
            return mock_data

        # 2. Generic default response
        default_resp = {"status": "ok", "response": "Mock conversational response"}
        if schema and isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(default_resp)
        return json.dumps(default_resp)

    def ocr(
        self,
        image_bytes: bytes,
        schema: type[BaseModel] | dict[str, Any] | None = None,
    ) -> Any:
        mock_ocr = {
            "document_type": "utility_bill",
            "provider": "DESCO",
            "amount_bdt": 1450.0,
            "due_date": "2026-11-25",
            "bill_month": "October 2026",
            "paid": True,
            "confidence": 0.96,
        }
        if schema and isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(mock_ocr)
        return mock_ocr


_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return LLM client instance selected by LLM_MODE environment setting."""
    global _client_instance
    if _client_instance is None:
        settings = get_settings()
        mode = (settings.LLM_MODE or os.getenv("LLM_MODE", "mock")).lower()
        if mode == "live" and settings.DEEPSEEK_API_KEY:
            _client_instance = DeepSeekClient()
        else:
            _client_instance = MockClient()
    return _client_instance


def reset_llm_client() -> None:
    """Clear cached LLMClient instance."""
    global _client_instance
    _client_instance = None
