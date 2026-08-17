"""Concalls module — Service and Router."""

from __future__ import annotations
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.concalls.models import ConcallEvent, Transcript, TranscriptSegment


async def get_company_concalls(db: AsyncSession, company_id: uuid.UUID, limit: int = 20) -> list[ConcallEvent]:
    result = await db.execute(
        select(ConcallEvent)
        .where(ConcallEvent.company_id == company_id)
        .options(selectinload(ConcallEvent.transcripts))
        .order_by(desc(ConcallEvent.scheduled_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_concall_by_id(db: AsyncSession, concall_id: uuid.UUID) -> ConcallEvent | None:
    result = await db.execute(
        select(ConcallEvent)
        .where(ConcallEvent.id == concall_id)
        .options(selectinload(ConcallEvent.transcripts).selectinload(Transcript.segments))
    )
    return result.scalar_one_or_none()


async def get_upcoming_concalls(db: AsyncSession, limit: int = 20) -> list[ConcallEvent]:
    from datetime import datetime, timezone
    result = await db.execute(
        select(ConcallEvent)
        .where(ConcallEvent.status == "scheduled", ConcallEvent.scheduled_at >= datetime.now(timezone.utc))
        .order_by(ConcallEvent.scheduled_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_concalls(db: AsyncSession, limit: int = 20) -> list[ConcallEvent]:
    result = await db.execute(
        select(ConcallEvent)
        .where(ConcallEvent.status == "completed")
        .order_by(desc(ConcallEvent.scheduled_at))
        .limit(limit)
    )
    return list(result.scalars().all())
