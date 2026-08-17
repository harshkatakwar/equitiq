"""Ingestion module — IngestionJob model."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database import Base, TimestampMixin, UUIDMixin


class IngestionJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    pipeline_stage: Mapped[str | None] = mapped_column(String(30))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    unique_key: Mapped[str | None] = mapped_column(String(500), unique=True)
    input_params: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
