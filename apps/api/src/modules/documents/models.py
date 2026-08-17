"""Documents module — Filing, Document, DocumentVersion, DocumentSection models."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text, BigInteger, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from src.database import Base, TimestampMixin, UUIDMixin


class Filing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "filings"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    filing_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    provider: Mapped[str | None] = mapped_column(String(100))

    documents: Mapped[list[Document]] = relationship(back_populates="filing", lazy="selectin")


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    filing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("filings.id"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)

    filing: Mapped[Filing | None] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(back_populates="document", lazy="selectin")


class DocumentVersion(UUIDMixin, Base):
    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    provider: Mapped[str | None] = mapped_column(String(100))
    publication_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieval_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    financial_period_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_periods.id"))
    sha256_checksum: Mapped[str | None] = mapped_column(String(64))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    processing_status: Mapped[str] = mapped_column(String(30), default="DISCOVERED")
    extraction_status: Mapped[str | None] = mapped_column(String(30))
    licence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("data_licences.id"))
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    document: Mapped[Document] = relationship(back_populates="versions")
    sections: Mapped[list[DocumentSection]] = relationship(back_populates="document_version", lazy="noload")


class DocumentSection(UUIDMixin, Base):
    __tablename__ = "document_sections"

    document_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False)
    section_type: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    document_version: Mapped[DocumentVersion] = relationship(back_populates="sections")
