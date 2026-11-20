"""Prometheus metrics, PII-safe structured logging, rate limiting and request size limits."""

import contextlib
import json
import logging
import re
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.config import get_settings
from app.llm import client as llm_client

REQUEST_LATENCY = Histogram(
    "trustledger_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
REQUESTS = Counter(
    "trustledger_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
ERRORS = Counter("trustledger_http_errors_total", "HTTP 5xx responses", ["route"])
DECISIONS = Counter("trustledger_decisions_total", "Credit decisions", ["band", "approved"])
LLM_CALLS = Counter("trustledger_llm_calls_total", "LLM calls", ["kind", "ok"])
LLM_TOKENS = Counter("trustledger_llm_tokens_total", "LLM tokens", ["kind", "type"])
RATE_LIMITED = Counter("trustledger_rate_limited_total", "Requests rejected by the rate limiter")


def _llm_usage(kind: str, prompt: int, completion: int, ok: bool) -> None:
    LLM_CALLS.labels(kind, str(ok).lower()).inc()
    if prompt:
        LLM_TOKENS.labels(kind, "prompt").inc(prompt)
    if completion:
        LLM_TOKENS.labels(kind, "completion").inc(completion)


llm_client.usage_hook = _llm_usage


def record_decision(band: str, approved: bool) -> None:
    DECISIONS.labels(band, str(approved).lower()).inc()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---- PII-safe logging ------------------------------------------------------------------

_PII_PATTERNS = [
    (re.compile(r"(?:\+?880|0)1[3-9]\d{8}"), "<PHONE>"),
    (re.compile(r"\b\d{10}(?:\d{3}|\d{7})?\b"), "<ID>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"Bearer\s+\S+"), "Bearer <redacted>"),
]


def scrub(text: str) -> str:
    for pattern, repl in _PII_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _scrub_arg(value: Any) -> Any:
    return scrub(value) if isinstance(value, str) else value


_factory_installed = False


def install_log_filter() -> None:
    """Scrub every log record at creation time, whichever logger or handler emits it."""
    global _factory_installed
    if _factory_installed:
        return
    base_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = base_factory(*args, **kwargs)
        with contextlib.suppress(Exception):  # never break logging
            # Scrub the template and each argument but keep record.args: formatters such as
            # uvicorn's AccessFormatter unpack it, and fail on None.
            if isinstance(record.msg, str):
                record.msg = scrub(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(_scrub_arg(a) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _scrub_arg(v) for k, v in record.args.items()}
        return record

    logging.setLogRecordFactory(factory)
    _factory_installed = True


# ---- rate limiting and size limits ---------------------------------------------------------


class RateLimiter:
    """Fixed one-minute window per client (API key, else borrower token, else IP)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        window = int((now or time.time()) // 60)
        with self._lock:
            start, count = self._windows.get(key, (window, 0))
            if start != window:
                start, count = window, 0
            count += 1
            self._windows[key] = (start, count)
            if len(self._windows) > 50_000:  # bound memory
                self._windows = {k: v for k, v in self._windows.items() if v[0] == window}
        return count <= self.per_minute, max(0, self.per_minute - count)


def client_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return "key:" + api_key[-12:]
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return "tok:" + auth[-16:]
    return "ip:" + (request.client.host if request.client else "unknown")


EXEMPT_PATHS = {"/health", "/metrics", "/version"}


class GuardMiddleware(BaseHTTPMiddleware):
    """Body-size limit, per-client rate limit and Prometheus request metrics."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        s = get_settings()
        self.limiter = RateLimiter(s.RATE_LIMIT_PER_MINUTE)
        self.max_body = s.MAX_BODY_BYTES
        self.max_upload = s.MAX_UPLOAD_BYTES

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        length = int(request.headers.get("content-length") or 0)
        limit = self.max_upload if path.startswith("/documents") else self.max_body
        if length > limit:
            return JSONResponse(
                {"error": "PAYLOAD_TOO_LARGE", "detail": f"Body exceeds {limit} bytes"}, 413
            )
        if path not in EXEMPT_PATHS and request.method != "OPTIONS":
            ok, remaining = self.limiter.allow(client_key(request))
            request.state.rate_limit_remaining = remaining
            if not ok:
                RATE_LIMITED.inc()
                return JSONResponse(
                    {"error": "RATE_LIMITED", "detail": "Too many requests, try again in a minute"},
                    429,
                    headers={"Retry-After": "60"},
                )
        start = time.perf_counter()
        response = await call_next(request)
        route: Any = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        REQUEST_LATENCY.labels(request.method, route_path).observe(time.perf_counter() - start)
        REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
        if response.status_code >= 500:
            ERRORS.labels(route_path).inc()
        return response


def json_log(payload: dict[str, Any]) -> str:
    return scrub(json.dumps(payload, ensure_ascii=False))
