"""Concalls module — Schemas, Service, Router."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal

# ─── Schemas ──────────────────────────────────────────────────
class TranscriptSegmentResponse(BaseModel):
    id: UUID
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    sequence: int
    segment_type: str
    text: Optional[str] = None
    confidence: Optional[Decimal] = None
    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    id: UUID
    source_type: str
    language: str
    is_verified: bool
    segments: list[TranscriptSegmentResponse] = []
    model_config = {"from_attributes": True}


class ConcallEventResponse(BaseModel):
    id: UUID
    company_id: UUID
    company_name: Optional[str] = None
    title: str
    event_type: str
    scheduled_at: Optional[datetime] = None
    status: str
    recording_url: Optional[str] = None
    has_transcript: bool = False
    has_ai_summary: bool = False
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
