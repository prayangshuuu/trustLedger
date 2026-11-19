"""TrustLedger FastAPI application factory and entry point."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the TrustLedger FastAPI application instance."""
    application = FastAPI(
        title="TrustLedger API",
        description="Alternative Credit Scoring and Financial Inclusion Platform for Bangladesh",
        version="0.1.0",
    )

    @application.get("/health", summary="Health Check")
    async def health() -> dict[str, str]:
        """Return application health status."""
        return {"status": "ok", "app": "trustledger"}

    return application


app: FastAPI = create_app()
