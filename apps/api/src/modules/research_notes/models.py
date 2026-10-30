"""Research notebook module — Models for private research notes linked to companies."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Date, text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database import Base, TimestampMixin, UUIDMixin


class ResearchNote(UUIDMixin, TimestampMixin, Base):
    """Private research note linked to a company, owned by a user."""
    __tablename__ = "research_notes"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Thesis
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    investment_thesis: Mapped[str | None] = mapped_column(Text)
    risks: Mapped[str | None] = mapped_column(Text)
    open_questions: Mapped[str | None] = mapped_column(Text)
    catalysts: Mapped[str | None] = mapped_column(Text)
    invalidation_conditions: Mapped[str | None] = mapped_column(Text)

    # Review
    review_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Supporting evidence stored as JSON list
    evidence: Mapped[list | None] = mapped_column(JSONB, default=list)
    # e.g. [{"type": "document", "id": "...", "title": "...", "excerpt": "..."},
    #        {"type": "ai_artifact", "id": "...", "claim": "..."}]

    # Revision history stored as JSON list of diffs
    revision_history: Mapped[list | None] = mapped_column(JSONB, default=list)
    # e.g. [{"revised_at": "...", "fields_changed": ["thesis", "risks"], "summary": "..."}]

    version: Mapped[int] = mapped_column(Integer, default=1)
