"""SQLAlchemy 2 domain entity models for TrustLedger.

Following the core privacy rules:
- Only derived features are stored (no raw SMS table or column).
- All personal applicant records link to users with CASCADE deletion.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

# Portable JSON type: JSONB on Postgres, JSON on SQLite
JsonType = JSON().with_variant(JSONB, "postgresql")

# Embeddings: pgvector on Postgres, JSON list on SQLite (tests and offline dev)
EMBEDDING_DIM = 1024
EmbeddingType = JSON().with_variant(Vector(EMBEDDING_DIM), "postgresql")


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Generate a UUID4 string representation."""
    return str(uuid.uuid4())


class User(Base):
    """User account entity tracking demographic metadata for fairness calibration."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    division: Mapped[str] = mapped_column(String(50), nullable=False)
    # Only used by the legacy bank-rule comparison (Inclusion Lift), never as model inputs
    has_bank_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_salary_slip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships with CASCADE deletion
    consents: Mapped[list["Consent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feature_snapshots: Mapped[list["FeatureSnapshot"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["DecisionRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["DocumentRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Consent(Base):
    """Granular user consent record for data sources."""

    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # sms | bills | recharge | ocr | bhorsha
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    user: Mapped["User"] = relationship(back_populates="consents")


class FeatureSnapshot(Base):
    """Derived feature snapshot. Stores ONLY derived numbers, never raw communications."""

    __tablename__ = "feature_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    features: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    source_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    user: Mapped["User"] = relationship(back_populates="feature_snapshots")


class Application(Base):
    """Credit application submitted by a user."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount_bdt: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    user: Mapped["User"] = relationship(back_populates="applications")
    decisions: Mapped[list["DecisionRecord"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    repayments: Mapped[list["Repayment"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class DecisionRecord(Base):
    """Persisted scoring outcome, SHAP reasons, and demographic fairness audit fields."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    p_repay: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    band: Mapped[str] = mapped_column(String(20), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False)
    tips: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    group: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fairness_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    application: Mapped["Application | None"] = relationship(back_populates="decisions")
    user: Mapped["User | None"] = relationship(back_populates="decisions")


class Repayment(Base):
    """Repayment tracking record for an approved loan application."""

    __tablename__ = "repayments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount_bdt: Mapped[float] = mapped_column(Float, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    on_time: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    application: Mapped["Application"] = relationship(back_populates="repayments")


class AuditLog(Base):
    """Immutable audit trail of compliance, consent, and fairness actions."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")


class DocumentRecord(Base):
    """Extracted document metadata and structured fields (images stored in object storage, never in DB)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    user: Mapped["User"] = relationship(back_populates="documents")


class KnowledgeChunk(Base):
    """RAG knowledge base chunk grounded in central bank circulars and financial guides."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    doc_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    contextual_header: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
