"""Concalls module — ConcallEvent, Transcript, TranscriptSegment models."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Interval, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from src.database import Base, TimestampMixin, UUIDMixin


class ConcallEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "concall_events"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), default="earnings_call")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    financial_period_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_periods.id"))
    recording_url: Mapped[str | None] = mapped_column(String(2000))
    presentation_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    source: Mapped[str | None] = mapped_column(String(100))

    transcripts: Mapped[list[Transcript]] = relationship(back_populates="concall_event", lazy="selectin")


class Transcript(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "transcripts"

    concall_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("concall_events.id"), nullable=False)
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    source_type: Mapped[str] = mapped_column(String(30), default="official")
    language: Mapped[str] = mapped_column(String(10), default="en")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    concall_event: Mapped[ConcallEvent] = relationship(back_populates="transcripts")
    segments: Mapped[list[TranscriptSegment]] = relationship(back_populates="transcript", lazy="selectin",
                                                              order_by="TranscriptSegment.sequence")


class TranscriptSegment(UUIDMixin, Base):
    __tablename__ = "transcript_segments"

    transcript_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transcripts.id"), nullable=False)
    speaker_name: Mapped[str | None] = mapped_column(String(200))
    speaker_role: Mapped[str | None] = mapped_column(String(200))
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    timestamp_start: Mapped[str | None] = mapped_column(String(20))
    timestamp_end: Mapped[str | None] = mapped_column(String(20))
    segment_type: Mapped[str] = mapped_column(String(30), default="prepared_remarks")
    text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(default=None)
    source_reference: Mapped[str | None] = mapped_column(String(200))
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    transcript: Mapped[Transcript] = relationship(back_populates="segments")
