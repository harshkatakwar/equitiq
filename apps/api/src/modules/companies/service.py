"""Companies module — Search and retrieval service."""

from __future__ import annotations
import uuid
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.companies.models import Company, Security, Exchange


async def search_companies(
    db: AsyncSession,
    query: str,
    sector: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Company], int]:
    """Search companies using pg_trgm fuzzy matching on name and symbol."""
    base_q = select(Company).where(Company.is_active == True)

    if query:
        # Combine name similarity + symbol exact/prefix + ISIN exact
        similarity = func.similarity(Company.name, query)
        base_q = base_q.outerjoin(Security, Security.company_id == Company.id)
        base_q = base_q.where(
            or_(
                func.similarity(Company.name, query) > 0.1,
                Security.symbol.ilike(f"{query}%"),
                Company.isin == query.upper(),
            )
        ).order_by(desc(similarity))
    else:
        base_q = base_q.order_by(Company.name)

    if sector:
        base_q = base_q.where(Company.sector == sector)

    # Count
    count_q = select(func.count()).select_from(base_q.distinct(Company.id).subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    # Results
    results_q = base_q.distinct(Company.id).limit(limit).offset(offset)
    result = await db.execute(results_q)
    companies = list(result.scalars().all())

    # Load securities
    if companies:
        company_ids = [c.id for c in companies]
        sec_q = select(Security).where(Security.company_id.in_(company_ids)).options(selectinload(Security.exchange))
        sec_result = await db.execute(sec_q)
        secs = sec_result.scalars().all()
        sec_map: dict[uuid.UUID, list[Security]] = {}
        for s in secs:
            sec_map.setdefault(s.company_id, []).append(s)
        for c in companies:
            c.securities = sec_map.get(c.id, [])

    return companies, total


async def get_company_by_id(db: AsyncSession, company_id: uuid.UUID) -> Company | None:
    result = await db.execute(
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.securities))
    )
    return result.scalar_one_or_none()


async def get_company_by_slug(db: AsyncSession, slug: str) -> Company | None:
    result = await db.execute(
        select(Company)
        .where(Company.slug == slug)
        .options(selectinload(Company.securities))
    )
    return result.scalar_one_or_none()


async def get_all_sectors(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Company.sector).where(Company.sector.isnot(None)).distinct().order_by(Company.sector)
    )
    return [r[0] for r in result.all()]
