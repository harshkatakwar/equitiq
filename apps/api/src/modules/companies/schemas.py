"""Companies module — Pydantic schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


class SecurityResponse(BaseModel):
    id: UUID
    symbol: str
    exchange_code: str | None = None
    is_primary: bool
    model_config = {"from_attributes": True}


class CompanySearchResult(BaseModel):
    id: UUID
    name: str
    slug: str
    isin: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    symbols: list[SecurityResponse] = []
    latest_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class CompanyDetail(BaseModel):
    id: UUID
    name: str
    slug: str
    isin: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    securities: list[SecurityResponse] = []
    latest_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CompanySearchRequest(BaseModel):
    q: str
    sector: Optional[str] = None
    limit: int = 20
    offset: int = 0
