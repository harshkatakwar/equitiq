"""Financials module — Service for financial data retrieval."""

from __future__ import annotations
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.financials.models import FinancialPeriod, FinancialStatement, FinancialFact, StandardMetric


async def get_company_financials(
    db: AsyncSession,
    company_id: uuid.UUID,
    period_type: str = "quarterly",
    statement_type: str = "pnl",
    standalone_or_consolidated: str = "standalone",
    limit: int = 12,
) -> list[FinancialPeriod]:
    """Get financial periods with statements and current facts for a company."""
    result = await db.execute(
        select(FinancialPeriod)
        .where(
            FinancialPeriod.company_id == company_id,
            FinancialPeriod.period_type == period_type,
            FinancialPeriod.standalone_or_consolidated == standalone_or_consolidated,
        )
        .options(
            selectinload(FinancialPeriod.statements)
            .selectinload(FinancialStatement.facts)
            .selectinload(FinancialFact.standard_metric)
        )
        .order_by(FinancialPeriod.period_end.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_standard_metrics(db: AsyncSession, statement_type: str | None = None) -> list[StandardMetric]:
    q = select(StandardMetric).order_by(StandardMetric.display_order)
    if statement_type:
        q = q.where(StandardMetric.statement_type == statement_type)
    result = await db.execute(q)
    return list(result.scalars().all())
