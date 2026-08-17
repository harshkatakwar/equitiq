"""Subscriptions module — API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User
from src.modules.subscriptions.service import get_user_subscription, get_usage_summary
from src.modules.subscriptions.models import SubscriptionResponse, PlanResponse, UsageResponse, UsageItem

router = APIRouter()


@router.get("", response_model=SubscriptionResponse | None)
async def current_subscription(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub = await get_user_subscription(db, user.id)
    if not sub:
        return None
    return SubscriptionResponse(
        id=sub.id,
        plan=PlanResponse.model_validate(sub.plan),
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
    )


@router.get("/usage", response_model=UsageResponse)
async def usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = await get_usage_summary(db, user.id)
    return UsageResponse(items=[UsageItem(**i) for i in items])
