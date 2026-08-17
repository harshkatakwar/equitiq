"""Documents module — Schemas and Router."""

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from typing import Optional


class DocumentVersionResponse(BaseModel):
    id: UUID
    version_number: int
    source_url: Optional[str] = None
    publication_timestamp: Optional[datetime] = None
    mime_type: Optional[str] = None
    processing_status: str
    page_count: Optional[int] = None
    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    document_type: str
    filing_type: Optional[str] = None
    filing_date: Optional[date] = None
    versions: list[DocumentVersionResponse] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
