"""Market data module — MarketPrice, CorporateAction models."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Numeric, BigInteger, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database import Base, TimestampMixin, UUIDMixin


class MarketPrice(UUIDMixin, Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        Index("ix_market_prices_security_date", "security_id", "date", unique=True),
    )

    security_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("securities.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    source: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()")
    )

    security: Mapped["Security"] = relationship(back_populates="prices")


class CorporateAction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "corporate_actions"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ex_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    details: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(100))
