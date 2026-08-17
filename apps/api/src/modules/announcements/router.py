"""Announcements module — Service and Router."""

from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.modules.announcements.models import Announcement, AnnouncementCategory

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────
class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    summary: Optional[str] = None
    category_name: Optional[str] = None
    source_url: Optional[str] = None
    exchange: Optional[str] = None
    published_at: Optional[datetime] = None
    is_material: bool = False
    materiality_reason: Optional[str] = None
    model_config = {"from_attributes": True}


# ─── Service ──────────────────────────────────────────────────
async def get_company_announcements(db: AsyncSession, company_id: uuid.UUID, limit: int = 20) -> list[Announcement]:
    result = await db.execute(
        select(Announcement)
        .where(Announcement.company_id == company_id)
        .options(selectinload(Announcement.category))
        .order_by(desc(Announcement.published_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_announcements_feed(db: AsyncSession, limit: int = 50) -> list[Announcement]:
    result = await db.execute(
        select(Announcement)
        .options(selectinload(Announcement.category))
        .order_by(desc(Announcement.published_at))
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── Routes ───────────────────────────────────────────────────
@router.get("/companies/{company_id}/announcements", response_model=list[AnnouncementResponse])
async def company_announcements(company_id: uuid.UUID, limit: int = Query(20), db: AsyncSession = Depends(get_db)):
    anns = await get_company_announcements(db, company_id, limit)
    return [AnnouncementResponse(
        id=a.id, company_id=a.company_id, title=a.title, summary=a.summary,
        category_name=a.category.name if a.category else None,
        source_url=a.source_url, exchange=a.exchange, published_at=a.published_at,
        is_material=a.is_material, materiality_reason=a.materiality_reason,
    ) for a in anns]


@router.get("/announcements", response_model=list[AnnouncementResponse])
async def announcements_feed(limit: int = Query(50), db: AsyncSession = Depends(get_db)):
    anns = await get_announcements_feed(db, limit)
    return [AnnouncementResponse(
        id=a.id, company_id=a.company_id, title=a.title, summary=a.summary,
        category_name=a.category.name if a.category else None,
        source_url=a.source_url, exchange=a.exchange, published_at=a.published_at,
        is_material=a.is_material, materiality_reason=a.materiality_reason,
    ) for a in anns]
