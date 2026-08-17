"""Financials module — Schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class MetricValue(BaseModel):
    metric_code: str
    metric_name: str
    value: Decimal
    unit: Optional[str] = None
    currency: str = "INR"
    source_page: Optional[int] = None
    version_number: int = 1
    model_config = {"from_attributes": True}


class PeriodFinancials(BaseModel):
    period_type: str
    period_start: date
    period_end: date
    fiscal_year: int
    fiscal_quarter: Optional[int] = None
    standalone_or_consolidated: str = "standalone"
    statement_type: str
    publication_timestamp: Optional[datetime] = None
    metrics: list[MetricValue] = []


class FinancialsResponse(BaseModel):
    company_id: UUID
    company_name: str
    periods: list[PeriodFinancials] = []
