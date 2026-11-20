"""API routers exports."""

from app.api.routers.apply import router as apply_router
from app.api.routers.bhorsha import router as bhorsha_router
from app.api.routers.consent import router as consent_router
from app.api.routers.demo import router as demo_router
from app.api.routers.documents import router as documents_router
from app.api.routers.fairness import router as fairness_router
from app.api.routers.features import router as features_router
from app.api.routers.health import router as health_router
from app.api.routers.loans import router as loans_router
from app.api.routers.score import router as score_router

__all__ = [
    "apply_router",
    "bhorsha_router",
    "consent_router",
    "demo_router",
    "documents_router",
    "fairness_router",
    "features_router",
    "health_router",
    "loans_router",
    "score_router",
]
