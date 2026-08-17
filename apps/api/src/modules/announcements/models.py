"""Announcements module — Models, Schemas, Service, Router."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base, TimestampMixin, UUIDMixin


class AnnouncementCategory(UUIDMixin, Base):
    __tablename__ = "announcement_categories"
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))


class Announcement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "announcements"
    __table_args__ = (Index("ix_announcements_company_date", "company_id", "published_at"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("announcement_categories.id"))
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    exchange: Mapped[str | None] = mapped_column(String(10))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_material: Mapped[bool] = mapped_column(Boolean, default=False)
    materiality_reason: Mapped[str | None] = mapped_column(Text)
    materiality_confidence: Mapped[Decimal | None] = mapped_column(default=None)
    provider: Mapped[str | None] = mapped_column(String(100))

    category: Mapped[AnnouncementCategory | None] = relationship(lazy="selectin")


class AnnouncementIdea(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "announcement_ideas"

    announcement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("announcements.id"), nullable=False)
    idea_type: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(default=None)
    analyst_correction: Mapped[str | None] = mapped_column(String(50))
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
