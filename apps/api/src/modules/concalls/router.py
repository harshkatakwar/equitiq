"""Concalls module — API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database import get_db
from src.shared import not_found
from src.modules.concalls.service import get_company_concalls, get_concall_by_id, get_upcoming_concalls, get_recent_concalls
from src.modules.concalls.schemas import ConcallEventResponse, TranscriptResponse, TranscriptSegmentResponse

router = APIRouter()


@router.get("/companies/{company_id}/concalls", response_model=list[ConcallEventResponse])
async def company_concalls(company_id: UUID, limit: int = Query(20), db: AsyncSession = Depends(get_db)):
    events = await get_company_concalls(db, company_id, limit)
    return [
        ConcallEventResponse(
            id=e.id, company_id=e.company_id, title=e.title,
            event_type=e.event_type, scheduled_at=e.scheduled_at,
            status=e.status, recording_url=e.recording_url,
            has_transcript=bool(e.transcripts), created_at=e.created_at,
        ) for e in events
    ]


@router.get("/concalls/{concall_id}", response_model=ConcallEventResponse)
async def get_concall(concall_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await get_concall_by_id(db, concall_id)
    if not event:
        raise not_found("Concall event")
    return ConcallEventResponse(
        id=event.id, company_id=event.company_id, title=event.title,
        event_type=event.event_type, scheduled_at=event.scheduled_at,
        status=event.status, recording_url=event.recording_url,
        has_transcript=bool(event.transcripts), created_at=event.created_at,
    )


@router.get("/concalls/{concall_id}/transcript", response_model=TranscriptResponse | None)
async def get_transcript(concall_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await get_concall_by_id(db, concall_id)
    if not event or not event.transcripts:
        raise not_found("Transcript")
    t = event.transcripts[0]
    return TranscriptResponse(
        id=t.id, source_type=t.source_type, language=t.language, is_verified=t.is_verified,
        segments=[
            TranscriptSegmentResponse(
                id=s.id, speaker_name=s.speaker_name, speaker_role=s.speaker_role,
                sequence=s.sequence, segment_type=s.segment_type, text=s.text, confidence=s.confidence,
            ) for s in (t.segments or [])
        ],
    )


@router.get("/concall-calendar/upcoming", response_model=list[ConcallEventResponse])
async def upcoming(limit: int = Query(20), db: AsyncSession = Depends(get_db)):
    events = await get_upcoming_concalls(db, limit)
    return [ConcallEventResponse(
        id=e.id, company_id=e.company_id, title=e.title, event_type=e.event_type,
        scheduled_at=e.scheduled_at, status=e.status, created_at=e.created_at,
    ) for e in events]


@router.get("/concall-calendar/recent", response_model=list[ConcallEventResponse])
async def recent(limit: int = Query(20), db: AsyncSession = Depends(get_db)):
    events = await get_recent_concalls(db, limit)
    return [ConcallEventResponse(
        id=e.id, company_id=e.company_id, title=e.title, event_type=e.event_type,
        scheduled_at=e.scheduled_at, status=e.status, has_transcript=bool(e.transcripts),
        created_at=e.created_at,
    ) for e in events]
