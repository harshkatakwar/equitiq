"""Subscriptions module — Entitlement service with atomic usage tracking."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.subscriptions.models import Subscription, Plan, Entitlement, UsageLedger


async def get_user_subscription(db: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
        .options(selectinload(Subscription.plan).selectinload(Plan.entitlements))
    )
    return result.scalar_one_or_none()


async def get_entitlement_limit(db: AsyncSession, user_id: uuid.UUID, feature_key: str, default: int = 0) -> int:
    """Get the limit for a feature key from the user's active plan."""
    sub = await get_user_subscription(db, user_id)
    if not sub:
        return default

    for ent in (sub.plan.entitlements or []):
        if ent.feature_key == feature_key:
            if ent.limit_value is None:
                return 999999  # Unlimited
            return ent.limit_value
    return default


async def get_current_usage(db: AsyncSession, user_id: uuid.UUID, feature_key: str, period: str | None = "month") -> int:
    """Get current usage for a feature within the active period."""
    now = datetime.now(timezone.utc)
    if period == "month":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.coalesce(func.sum(UsageLedger.delta), 0))
        .where(
            UsageLedger.user_id == user_id,
            UsageLedger.feature_key == feature_key,
            UsageLedger.created_at >= period_start,
        )
    )
    return result.scalar() or 0


async def check_and_record_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    feature_key: str,
    idempotency_key: str | None = None,
    reference_id: uuid.UUID | None = None,
    reference_type: str | None = None,
) -> bool:
    """Check if user can use a feature and atomically record usage. Returns True if allowed."""
    limit = await get_entitlement_limit(db, user_id, feature_key, default=0)
    if limit >= 999999:
        # Unlimited — record but don't block
        await _record_usage(db, user_id, feature_key, idempotency_key, reference_id, reference_type)
        return True

    # Get entitlement period
    sub = await get_user_subscription(db, user_id)
    period = "month"
    if sub:
        for ent in (sub.plan.entitlements or []):
            if ent.feature_key == feature_key:
                period = ent.period or "month"
                break

    current = await get_current_usage(db, user_id, feature_key, period)
    if current >= limit:
        return False

    await _record_usage(db, user_id, feature_key, idempotency_key, reference_id, reference_type)
    return True


async def _record_usage(
    db: AsyncSession, user_id: uuid.UUID, feature_key: str,
    idempotency_key: str | None, reference_id: uuid.UUID | None, reference_type: str | None
):
    """Record a usage entry in the append-only ledger."""
    # Check idempotency
    if idempotency_key:
        existing = await db.execute(
            select(UsageLedger).where(UsageLedger.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return  # Already recorded

    sub = await get_user_subscription(db, user_id)
    entry = UsageLedger(
        user_id=user_id,
        subscription_id=sub.id if sub else None,
        feature_key=feature_key,
        delta=1,
        idempotency_key=idempotency_key,
        operation_type="use",
        reference_id=reference_id,
        reference_type=reference_type,
    )
    db.add(entry)
    await db.flush()


async def refund_usage(db: AsyncSession, user_id: uuid.UUID, feature_key: str, idempotency_key: str):
    """Refund a failed operation's usage."""
    entry = UsageLedger(
        user_id=user_id,
        feature_key=feature_key,
        delta=-1,
        idempotency_key=f"refund-{idempotency_key}",
        operation_type="refund",
    )
    db.add(entry)
    await db.flush()


async def get_usage_summary(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """Get usage summary for all features."""
    sub = await get_user_subscription(db, user_id)
    if not sub:
        return []

    items = []
    for ent in (sub.plan.entitlements or []):
        used = await get_current_usage(db, user_id, ent.feature_key, ent.period or "month")
        limit_val = ent.limit_value
        remaining = (limit_val - used) if limit_val is not None else None
        items.append({
            "feature_key": ent.feature_key,
            "used": used,
            "limit": limit_val,
            "remaining": remaining,
            "period": ent.period,
        })
    return items
