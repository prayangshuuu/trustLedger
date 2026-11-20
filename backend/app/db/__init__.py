"""Database package exposing models, base, session, and table initialization."""

from app.db.base import Base
from app.db.models import (
    Application,
    AuditLog,
    Consent,
    DecisionRecord,
    DocumentRecord,
    FeatureSnapshot,
    KnowledgeChunk,
    Repayment,
    User,
)
from app.db.session import (
    create_app_engine,
    get_db,
    get_engine,
    get_session_factory,
    init_db,
    normalize_db_url,
)

__all__ = [
    "Application",
    "AuditLog",
    "Base",
    "Consent",
    "DecisionRecord",
    "DocumentRecord",
    "FeatureSnapshot",
    "KnowledgeChunk",
    "Repayment",
    "User",
    "create_app_engine",
    "get_db",
    "get_engine",
    "get_session_factory",
    "init_db",
    "normalize_db_url",
]
