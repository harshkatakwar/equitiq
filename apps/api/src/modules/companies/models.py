"""Companies module — Company, Security, Exchange, IdentifierHistory models."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Boolean, Integer, Date, DateTime, ForeignKey, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base, TimestampMixin, UUIDMixin


class Exchange(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "exchanges"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="IN")


class Company(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_companies_sector", "sector"),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), index=True)
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    headquarters: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    securities: Mapped[list[Security]] = relationship(back_populates="company", lazy="selectin")


class Security(UUIDMixin, Base):
    __tablename__ = "securities"
    __table_args__ = (
        Index("ix_securities_symbol_trgm", "symbol", postgresql_using="gin",
              postgresql_ops={"symbol": "gin_trgm_ops"}),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    exchange_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    listing_date: Mapped[date | None] = mapped_column(Date)
    delisting_date: Mapped[date | None] = mapped_column(Date)

    company: Mapped[Company] = relationship(back_populates="securities")
    exchange: Mapped[Exchange] = relationship(lazy="selectin")
    prices: Mapped[list["MarketPrice"]] = relationship(back_populates="security", lazy="noload")


class IdentifierHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "identifier_history"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)  # name, symbol, isin
    old_value: Mapped[str | None] = mapped_column(String(300))
    new_value: Mapped[str | None] = mapped_column(String(300))
    effective_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(100))
