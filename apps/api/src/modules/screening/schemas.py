"""Screening module — Pydantic schemas for screener requests/responses."""

from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Optional


class ScreenerFilter(BaseModel):
    """A single filter condition."""
    field: str = Field(..., description="Metric code or company attribute to filter on")
    operator: str = Field(..., description="Comparison operator: gt, gte, lt, lte, eq, between, in")
    value: Decimal | float | str | None = None
    value2: Decimal | float | None = None  # For 'between' operator
    values: list[str] | None = None  # For 'in' operator


class ScreenerRequest(BaseModel):
    """Request to execute a stock screen."""
    filters: list[ScreenerFilter] = Field(default_factory=list)
    sort_by: str = Field(default="market_cap", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    period_type: str = Field(default="quarterly", pattern="^(quarterly|annual)$")
    consolidated: str = Field(default="standalone", pattern="^(standalone|consolidated)$")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ScreenerCompanyResult(BaseModel):
    """A single company result from screening."""
    company_id: UUID
    company_name: str
    slug: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    isin: Optional[str] = None
    symbol: Optional[str] = None
    exchange_code: Optional[str] = None
    latest_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    metrics: dict[str, Decimal | None] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class ScreenerResponse(BaseModel):
    """Response from screening execution."""
    results: list[ScreenerCompanyResult]
    total_count: int
    filters_applied: list[ScreenerFilter]
    period_type: str
    consolidated: str
    execution_time_ms: int = 0


class SavedScreenRequest(BaseModel):
    """Save a screen configuration."""
    name: str = Field(max_length=200)
    description: Optional[str] = None
    filters: list[ScreenerFilter]
    sort_by: str = "market_cap"
    sort_order: str = "desc"


class SavedScreenResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    filter_expression: dict
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# Whitelist of allowed screening fields — never accept raw SQL
ALLOWED_SCREEN_FIELDS = {
    # Company attributes
    "sector", "industry", "market_cap",
    # P&L metrics
    "revenue", "total_income", "ebitda", "ebit", "pbt", "pat", "eps",
    "raw_materials", "employee_cost", "other_expenses", "depreciation",
    "interest", "tax", "other_income",
    # Derived / calculated
    "revenue_growth_yoy", "pat_growth_yoy", "ebitda_margin",
    "pat_margin", "operating_margin",
    # Balance sheet (when available)
    "total_assets", "total_debt", "net_worth", "debt_to_equity",
    # Cash flow (when available)
    "operating_cashflow", "capex", "free_cashflow",
    # Ratios (when available)
    "roe", "roce", "pe_ratio",
}

ALLOWED_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "between", "in"}
