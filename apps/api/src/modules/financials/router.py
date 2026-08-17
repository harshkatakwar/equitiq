"""Financials module — API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database import get_db
from src.shared import not_found
from src.modules.companies.service import get_company_by_id
from src.modules.financials.service import get_company_financials
from src.modules.financials.schemas import FinancialsResponse, PeriodFinancials, MetricValue

router = APIRouter()


@router.get("/companies/{company_id}/financials", response_model=FinancialsResponse)
async def company_financials(
    company_id: UUID,
    period_type: str = Query("quarterly", regex="^(quarterly|annual)$"),
    statement_type: str = Query("pnl", regex="^(pnl|balance_sheet|cashflow)$"),
    consolidated: str = Query("standalone", regex="^(standalone|consolidated)$"),
    limit: int = Query(12, ge=1, le=40),
    db: AsyncSession = Depends(get_db),
):
    company = await get_company_by_id(db, company_id)
    if not company:
        raise not_found("Company")

    periods = await get_company_financials(db, company_id, period_type, statement_type, consolidated, limit)

    period_data = []
    for p in periods:
        for stmt in p.statements:
            if stmt.statement_type == statement_type:
                metrics = [
                    MetricValue(
                        metric_code=f.standard_metric.code,
                        metric_name=f.standard_metric.name,
                        value=f.value,
                        unit=f.unit,
                        currency=f.currency,
                        source_page=f.source_page,
                        version_number=f.version_number,
                    )
                    for f in stmt.facts
                    if f.known_until is None  # Only current version
                ]
                period_data.append(PeriodFinancials(
                    period_type=p.period_type,
                    period_start=p.period_start,
                    period_end=p.period_end,
                    fiscal_year=p.fiscal_year,
                    fiscal_quarter=p.fiscal_quarter,
                    standalone_or_consolidated=p.standalone_or_consolidated,
                    statement_type=stmt.statement_type,
                    publication_timestamp=stmt.publication_timestamp,
                    metrics=metrics,
                ))

    return FinancialsResponse(company_id=company.id, company_name=company.name, periods=period_data)
