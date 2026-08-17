"""Companies module — API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database import get_db
from src.shared import not_found
from src.modules.companies.service import search_companies, get_company_by_id, get_company_by_slug, get_all_sectors
from src.modules.companies.schemas import CompanySearchResult, CompanyDetail, SecurityResponse
from src.modules.market_data.service import get_latest_price

router = APIRouter()


@router.get("/search", response_model=list[CompanySearchResult])
async def search(
    q: str = Query("", description="Search query"),
    sector: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    companies, total = await search_companies(db, q, sector, limit, offset)
    results = []
    for c in companies:
        price_data = await get_latest_price(db, c.id)
        results.append(CompanySearchResult(
            id=c.id,
            name=c.name,
            slug=c.slug,
            isin=c.isin,
            sector=c.sector,
            industry=c.industry,
            symbols=[
                SecurityResponse(
                    id=s.id, symbol=s.symbol,
                    exchange_code=s.exchange.code if s.exchange else None,
                    is_primary=s.is_primary
                ) for s in (c.securities or [])
            ],
            latest_price=price_data.get("close") if price_data else None,
            market_cap=price_data.get("market_cap") if price_data else None,
        ))
    return results


@router.get("/sectors", response_model=list[str])
async def sectors(db: AsyncSession = Depends(get_db)):
    return await get_all_sectors(db)


@router.get("/{company_id}", response_model=CompanyDetail)
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    company = await get_company_by_id(db, company_id)
    if not company:
        raise not_found("Company")
    price_data = await get_latest_price(db, company.id)
    return CompanyDetail(
        id=company.id,
        name=company.name,
        slug=company.slug,
        isin=company.isin,
        sector=company.sector,
        industry=company.industry,
        description=company.description,
        founded_year=company.founded_year,
        headquarters=company.headquarters,
        website=company.website,
        securities=[
            SecurityResponse(
                id=s.id, symbol=s.symbol,
                exchange_code=s.exchange.code if s.exchange else None,
                is_primary=s.is_primary
            ) for s in (company.securities or [])
        ],
        latest_price=price_data.get("close") if price_data else None,
        market_cap=price_data.get("market_cap") if price_data else None,
        created_at=company.created_at,
    )
