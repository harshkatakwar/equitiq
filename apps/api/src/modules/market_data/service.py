"""Market data module — Service for price retrieval."""

from __future__ import annotations
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.market_data.models import MarketPrice
from src.modules.companies.models import Security


async def get_latest_price(db: AsyncSession, company_id: uuid.UUID) -> dict | None:
    """Get latest EOD price for a company's primary security."""
    result = await db.execute(
        select(MarketPrice)
        .join(Security, Security.id == MarketPrice.security_id)
        .where(Security.company_id == company_id, Security.is_primary == True)
        .order_by(desc(MarketPrice.date))
        .limit(1)
    )
    price = result.scalar_one_or_none()
    if not price:
        return None
    return {
        "date": price.date,
        "open": price.open,
        "high": price.high,
        "low": price.low,
        "close": price.close,
        "volume": price.volume,
        "market_cap": price.market_cap,
    }


async def get_price_history(db: AsyncSession, company_id: uuid.UUID, limit: int = 252) -> list[dict]:
    result = await db.execute(
        select(MarketPrice)
        .join(Security, Security.id == MarketPrice.security_id)
        .where(Security.company_id == company_id, Security.is_primary == True)
        .order_by(desc(MarketPrice.date))
        .limit(limit)
    )
    prices = result.scalars().all()
    return [
        {"date": p.date, "open": p.open, "high": p.high, "low": p.low,
         "close": p.close, "volume": p.volume, "market_cap": p.market_cap}
        for p in reversed(prices)
    ]
