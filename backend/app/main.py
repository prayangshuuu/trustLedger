"""TrustLedger FastAPI application factory, middleware, exception handlers, and routing."""

import json
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.routers import (
    bhorsha_router,
    consent_router,
    documents_router,
    fairness_router,
    features_router,
    health_router,
    score_router,
)
from app.core.features import AllFeaturesMissingError
from app.privacy.consent import ConsentMissingError

logger = logging.getLogger("trustledger.api")


class RequestLoggingAndIDMiddleware(BaseHTTPMiddleware):
    """Middleware attaching X-Request-ID and emitting structured JSON access logs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        # Structured JSON log entry
        log_payload = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        logger.info(json.dumps(log_payload))

        return response


def create_app() -> FastAPI:
    """Create and configure the TrustLedger FastAPI application."""
    application = FastAPI(
        title="TrustLedger API",
        description=(
            "Fair, private, explainable alternative credit scoring for individuals without a bank history in Bangladesh.\n\n"
            "Features:\n"
            "- **Fairness-calibrated scoring**: XGBoost + demographic parity thresholds\n"
            "- **Explainability**: SHAP TreeExplainer attributions with native Bangla translations and actionable tips\n"
            "- **Privacy by design**: Mandatory source consent, Presidio PII scrubbing, zero raw SMS persistence, cascading deletion\n"
            "- **Inclusion reporting**: Quantifiable Inclusion Lift vs legacy collateral/salary-slip banking rules"
        ),
        version="0.1.0",
        openapi_tags=[
            {"name": "System", "description": "Service health checks and version introspection"},
            {
                "name": "Privacy & Consent",
                "description": "Granular data consent and Right-to-be-Forgotten",
            },
            {
                "name": "Scoring & Decisions",
                "description": "Alternative scoring engine and SHAP explanation breakdowns",
            },
            {
                "name": "Fairness & Inclusion",
                "description": "Demographic parity audits and bank rule inclusion lift",
            },
        ],
    )

    # 1. CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request Correlation & Logging Middleware
    application.add_middleware(RequestLoggingAndIDMiddleware)

    # 3. Exception Handlers
    @application.exception_handler(ConsentMissingError)
    async def consent_missing_handler(request: Request, exc: ConsentMissingError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "CONSENT_MISSING",
                "detail": str(exc),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else {},
        )

    @application.exception_handler(AllFeaturesMissingError)
    async def all_features_missing_handler(
        request: Request, exc: AllFeaturesMissingError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "ALL_FEATURES_MISSING",
                "detail": str(exc),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else {},
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "detail": "Invalid request payload schema",
                "errors": exc.errors(),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else {},
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP_{exc.status_code}",
                "detail": exc.detail,
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id} if req_id else {},
        )

    # 4. Mount Routers
    application.include_router(health_router)
    application.include_router(consent_router)
    application.include_router(bhorsha_router)
    application.include_router(documents_router)
    application.include_router(features_router)
    application.include_router(score_router)
    application.include_router(fairness_router)

    return application


app: FastAPI = create_app()
