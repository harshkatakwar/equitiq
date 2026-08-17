"""Screening module — SavedFilter and FilterExecution models."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database import Base, TimestampMixin, UUIDMixin


class SavedFilter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "saved_filters"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    filter_expression: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_columns: Mapped[list | None] = mapped_column(JSONB)
    sort_config: Mapped[dict | None] = mapped_column(JSONB)


class FilterExecution(UUIDMixin, Base):
    __tablename__ = "filter_executions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    saved_filter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("saved_filters.id"))
    filter_expression: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_count: Mapped[int | None] = mapped_column(Integer)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))
