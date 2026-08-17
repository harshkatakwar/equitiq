"""Subscriptions module — Plan, Subscription, Entitlement, UsageLedger models and service."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import String, Boolean, Integer, Date, DateTime, ForeignKey, Text, Numeric, text, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base, TimestampMixin, UUIDMixin


# ─── Models ───────────────────────────────────────────────────
class Plan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_monthly: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_annual: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    entitlements: Mapped[list[Entitlement]] = relationship(back_populates="plan", lazy="selectin")


class Entitlement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "entitlements"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    limit_value: Mapped[int | None] = mapped_column(Integer)  # NULL = unlimited
    period: Mapped[str | None] = mapped_column(String(10))  # month, year, NULL for absolute

    plan: Mapped[Plan] = relationship(back_populates="entitlements")


class Subscription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    payment_provider: Mapped[str | None] = mapped_column(String(50))
    external_subscription_id: Mapped[str | None] = mapped_column(String(200))
    current_period_start: Mapped[date | None] = mapped_column(Date)
    current_period_end: Mapped[date | None] = mapped_column(Date)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship(lazy="selectin")


class UsageLedger(UUIDMixin, Base):
    __tablename__ = "usage_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 use, -1 refund
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    operation_type: Mapped[str] = mapped_column(String(20), default="use")  # use, refund, reset, override
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reference_type: Mapped[str | None] = mapped_column(String(50))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))


# ─── Schemas ──────────────────────────────────────────────────
class PlanResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = None
    price_annual: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    plan: PlanResponse
    status: str
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None
    model_config = {"from_attributes": True}


class UsageItem(BaseModel):
    feature_key: str
    used: int
    limit: Optional[int] = None
    remaining: Optional[int] = None
    period: Optional[str] = None


class UsageResponse(BaseModel):
    items: list[UsageItem] = []
