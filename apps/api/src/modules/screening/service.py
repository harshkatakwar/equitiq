"""Screening module — Server-side screening service.

All filtering uses parameterized queries against a whitelist of allowed fields.
No raw SQL injection is possible through the screening API.
"""

from __future__ import annotations
import uuid
import time
from decimal import Decimal
from sqlalchemy import select, func, desc, asc, and_, or_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.companies.models import Company, Security
from src.modules.financials.models import FinancialPeriod, FinancialStatement, FinancialFact, StandardMetric
from src.modules.market_data.models import MarketPrice
from src.modules.screening.schemas import (
    ScreenerFilter, ScreenerRequest, ScreenerCompanyResult, ScreenerResponse,
    ALLOWED_SCREEN_FIELDS, ALLOWED_OPERATORS,
)


# Company-level attributes that don't need metric joins
COMPANY_ATTRS = {"sector", "industry"}
PRICE_ATTRS = {"market_cap", "latest_price"}

# Map metric codes to their standard_metric codes in the DB
METRIC_CODES = ALLOWED_SCREEN_FIELDS - COMPANY_ATTRS - PRICE_ATTRS - {
    "revenue_growth_yoy", "pat_growth_yoy", "ebitda_margin", "pat_margin",
    "operating_margin", "debt_to_equity", "roe", "roce", "pe_ratio",
}


async def execute_screen(
    db: AsyncSession,
    request: ScreenerRequest,
) -> ScreenerResponse:
    """Execute a stock screen with validated filters."""
    start_time = time.monotonic()

    # Validate all filters
    for f in request.filters:
        if f.field not in ALLOWED_SCREEN_FIELDS:
            from src.shared import bad_request
            raise bad_request(f"Unknown screening field: {f.field}")
        if f.operator not in ALLOWED_OPERATORS:
            from src.shared import bad_request
            raise bad_request(f"Unknown operator: {f.operator}")

    # Step 1: Get all active companies with their latest financials
    companies_q = (
        select(Company)
        .where(Company.is_active == True)
        .options(selectinload(Company.securities))
    )

    # Apply company-level filters
    for f in request.filters:
        if f.field == "sector" and f.operator == "eq":
            companies_q = companies_q.where(Company.sector == str(f.value))
        elif f.field == "sector" and f.operator == "in" and f.values:
            companies_q = companies_q.where(Company.sector.in_(f.values))
        elif f.field == "industry" and f.operator == "eq":
            companies_q = companies_q.where(Company.industry == str(f.value))
        elif f.field == "industry" and f.operator == "in" and f.values:
            companies_q = companies_q.where(Company.industry.in_(f.values))

    result = await db.execute(companies_q)
    companies = list(result.scalars().all())

    if not companies:
        elapsed = int((time.monotonic() - start_time) * 1000)
        return ScreenerResponse(
            results=[], total_count=0, filters_applied=request.filters,
            period_type=request.period_type, consolidated=request.consolidated,
            execution_time_ms=elapsed,
        )

    # Step 2: Get latest financial facts for each company
    company_ids = [c.id for c in companies]

    # Get latest period for each company
    latest_periods = await _get_latest_periods(
        db, company_ids, request.period_type, request.consolidated
    )

    # Get metric values for those periods
    metric_values = await _get_metric_values(db, company_ids, latest_periods)

    # Get latest prices
    price_data = await _get_latest_prices(db, company_ids)

    # Step 3: Build result set with metrics
    results: list[ScreenerCompanyResult] = []
    for company in companies:
        cid = company.id
        metrics = metric_values.get(cid, {})
        prices = price_data.get(cid, {})

        # Calculate derived metrics
        revenue = metrics.get("revenue")
        ebitda = metrics.get("ebitda")
        pat = metrics.get("pat")
        ebit = metrics.get("ebit")

        if revenue and revenue != 0:
            metrics["ebitda_margin"] = round((ebitda / revenue * 100), 2) if ebitda else None
            metrics["pat_margin"] = round((pat / revenue * 100), 2) if pat else None
            metrics["operating_margin"] = round((ebit / revenue * 100), 2) if ebit else None

        metrics["market_cap"] = prices.get("market_cap")
        metrics["latest_price"] = prices.get("close")

        # Apply metric-level filters
        if not _passes_metric_filters(metrics, request.filters):
            continue

        primary_security = next((s for s in (company.securities or []) if s.is_primary), None)
        fallback_security = (company.securities or [None])[0] if company.securities else None
        sec = primary_security or fallback_security

        results.append(ScreenerCompanyResult(
            company_id=cid,
            company_name=company.name,
            slug=company.slug,
            sector=company.sector,
            industry=company.industry,
            isin=company.isin,
            symbol=sec.symbol if sec else None,
            exchange_code=sec.exchange.code if sec and hasattr(sec, 'exchange') and sec.exchange else None,
            latest_price=prices.get("close"),
            market_cap=prices.get("market_cap"),
            metrics={k: v for k, v in metrics.items() if v is not None},
        ))

    # Sort
    sort_field = request.sort_by
    reverse = request.sort_order == "desc"
    results.sort(
        key=lambda r: (
            r.metrics.get(sort_field) if sort_field in r.metrics
            else getattr(r, sort_field, None) or Decimal(0)
        ) or Decimal(0),
        reverse=reverse,
    )

    total_count = len(results)
    page = results[request.offset:request.offset + request.limit]

    elapsed = int((time.monotonic() - start_time) * 1000)
    return ScreenerResponse(
        results=page, total_count=total_count,
        filters_applied=request.filters,
        period_type=request.period_type, consolidated=request.consolidated,
        execution_time_ms=elapsed,
    )


def _passes_metric_filters(metrics: dict, filters: list[ScreenerFilter]) -> bool:
    """Check if a company's metrics pass all non-company-attribute filters."""
    for f in filters:
        if f.field in COMPANY_ATTRS:
            continue  # Already handled at SQL level
        val = metrics.get(f.field)
        if val is None:
            # Missing value behavior: exclude from results if filter requires it
            if f.operator in ("gt", "gte", "lt", "lte", "between"):
                return False
            continue

        val = Decimal(str(val))
        if f.operator == "gt" and not (val > Decimal(str(f.value))):
            return False
        elif f.operator == "gte" and not (val >= Decimal(str(f.value))):
            return False
        elif f.operator == "lt" and not (val < Decimal(str(f.value))):
            return False
        elif f.operator == "lte" and not (val <= Decimal(str(f.value))):
            return False
        elif f.operator == "eq" and not (val == Decimal(str(f.value))):
            return False
        elif f.operator == "between":
            if f.value2 is None:
                return False
            if not (Decimal(str(f.value)) <= val <= Decimal(str(f.value2))):
                return False

    return True


async def _get_latest_periods(
    db: AsyncSession, company_ids: list[uuid.UUID],
    period_type: str, consolidated: str,
) -> dict[uuid.UUID, uuid.UUID]:
    """Get the latest financial period ID for each company."""
    # Subquery for max period_end per company
    subq = (
        select(
            FinancialPeriod.company_id,
            func.max(FinancialPeriod.period_end).label("max_end"),
        )
        .where(
            FinancialPeriod.company_id.in_(company_ids),
            FinancialPeriod.period_type == period_type,
            FinancialPeriod.standalone_or_consolidated == consolidated,
        )
        .group_by(FinancialPeriod.company_id)
        .subquery()
    )

    q = (
        select(FinancialPeriod)
        .join(subq, and_(
            FinancialPeriod.company_id == subq.c.company_id,
            FinancialPeriod.period_end == subq.c.max_end,
        ))
        .where(
            FinancialPeriod.period_type == period_type,
            FinancialPeriod.standalone_or_consolidated == consolidated,
        )
    )
    result = await db.execute(q)
    periods = result.scalars().all()
    return {p.company_id: p.id for p in periods}


async def _get_metric_values(
    db: AsyncSession, company_ids: list[uuid.UUID],
    period_map: dict[uuid.UUID, uuid.UUID],
) -> dict[uuid.UUID, dict[str, Decimal]]:
    """Get latest metric values for companies from their latest periods."""
    period_ids = list(period_map.values())
    if not period_ids:
        return {}

    q = (
        select(FinancialFact)
        .join(StandardMetric, FinancialFact.standard_metric_id == StandardMetric.id)
        .join(FinancialStatement, FinancialFact.financial_statement_id == FinancialStatement.id)
        .where(
            FinancialFact.company_id.in_(company_ids),
            FinancialStatement.financial_period_id.in_(period_ids),
            FinancialFact.known_until.is_(None),  # Current version only
        )
        .options(selectinload(FinancialFact.standard_metric))
    )
    result = await db.execute(q)
    facts = result.scalars().all()

    metrics: dict[uuid.UUID, dict[str, Decimal]] = {}
    for fact in facts:
        cid = fact.company_id
        if cid not in metrics:
            metrics[cid] = {}
        metrics[cid][fact.standard_metric.code] = fact.value

    return metrics


async def _get_latest_prices(
    db: AsyncSession, company_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict]:
    """Get latest price for each company."""
    # For each company, get the most recent price via their primary security
    prices = {}
    for cid in company_ids:
        from src.modules.market_data.service import get_latest_price
        price = await get_latest_price(db, cid)
        if price:
            prices[cid] = price
    return prices
