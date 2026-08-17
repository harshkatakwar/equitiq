"""Financials module — Financial period, statement, fact, metric models."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Numeric, Text, text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base, TimestampMixin, UUIDMixin


class StandardMetric(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "standard_metrics"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # income, expense, asset, liability, equity, ratio, cashflow
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False)  # currency, percentage, ratio, number
    statement_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pnl, balance_sheet, cashflow, ratio
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class FinancialPeriod(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint("company_id", "period_type", "period_start", "period_end", "standalone_or_consolidated",
                         name="uq_financial_period"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)  # quarterly, annual
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int | None] = mapped_column(Integer)
    standalone_or_consolidated: Mapped[str] = mapped_column(String(15), default="standalone")

    statements: Mapped[list[FinancialStatement]] = relationship(back_populates="period", lazy="selectin")


class FinancialStatement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "financial_statements"

    financial_period_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False)
    statement_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pnl, balance_sheet, cashflow
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    publication_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    period: Mapped[FinancialPeriod] = relationship(back_populates="statements")
    facts: Mapped[list[FinancialFact]] = relationship(back_populates="statement", lazy="selectin")


class FinancialFact(UUIDMixin, Base):
    __tablename__ = "financial_facts"
    __table_args__ = (
        Index("ix_financial_facts_company_metric", "company_id", "standard_metric_id"),
        Index("ix_financial_facts_period", "period_start", "period_end"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    financial_statement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_statements.id"))
    standard_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("standard_metrics.id"), nullable=False)
    original_label: Mapped[str | None] = mapped_column(String(500))
    value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    standalone_or_consolidated: Mapped[str] = mapped_column(String(15), default="standalone")
    publication_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    known_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))
    known_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = current version
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_versions.id"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_location: Mapped[str | None] = mapped_column(String(200))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_financial_fact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_facts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    standard_metric: Mapped[StandardMetric] = relationship(lazy="selectin")
    statement: Mapped[FinancialStatement | None] = relationship(back_populates="facts")
