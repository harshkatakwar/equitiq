"""AI Research module — AIArtifact, AIClaim, SourceCitation, ChatConversation models."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, Text, Numeric, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from src.database import Base, TimestampMixin, UUIDMixin


class AIArtifact(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ai_artifacts"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    generation_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_cutoff_date: Mapped[date | None] = mapped_column(Date)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[dict | None] = mapped_column(JSONB)
    source_document_version_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    regeneration_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_artifacts.id"))
    unsupported_claim_count: Mapped[int | None] = mapped_column(Integer)
    total_claim_count: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    claims: Mapped[list[AIClaim]] = relationship(back_populates="artifact", lazy="selectin")


class AIClaim(UUIDMixin, Base):
    __tablename__ = "ai_claims"

    ai_artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_artifacts.id"), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    section: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    artifact: Mapped[AIArtifact] = relationship(back_populates="claims")
    citations: Mapped[list[SourceCitation]] = relationship(back_populates="claim", lazy="selectin")


class SourceCitation(UUIDMixin, Base):
    __tablename__ = "source_citations"

    ai_claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_claims.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_text: Mapped[str | None] = mapped_column(Text)
    page_or_sequence: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    claim: Mapped[AIClaim] = relationship(back_populates="citations")


class ChatConversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    document_scope: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)))

    messages: Mapped[list[ChatMessage]] = relationship(back_populates="conversation", lazy="selectin",
                                                        order_by="ChatMessage.created_at")


class ChatMessage(UUIDMixin, Base):
    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict | None] = mapped_column(JSONB)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")
