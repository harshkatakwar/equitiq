"""Administration module — Admin API routes."""

from __future__ import annotations
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.modules.identity.dependencies import require_admin
from src.modules.identity.models import User
from src.modules.ingestion.models import IngestionJob
from src.modules.licensing.models import DataLicence

router = APIRouter()


class IngestionJobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    pipeline_stage: Optional[str] = None
    attempts: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class LicenceResponse(BaseModel):
    id: uuid.UUID
    provider: str
    dataset: str
    licence_type: str
    display_allowed: bool = False
    export_allowed: bool = False
    contract_expiry: Optional[str] = None
    model_config = {"from_attributes": True}


@router.get("/ingestion/jobs", response_model=list[IngestionJobResponse])
async def list_ingestion_jobs(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(IngestionJob).order_by(desc(IngestionJob.created_at)).limit(limit)
    if status:
        q = q.where(IngestionJob.status == status)
    result = await db.execute(q)
    return [IngestionJobResponse.model_validate(j) for j in result.scalars().all()]


@router.post("/documents/{doc_id}/reprocess", status_code=202)
async def reprocess_document(doc_id: uuid.UUID, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    job = IngestionJob(
        job_type="reprocess_document",
        document_version_id=doc_id,
        status="pending",
        pipeline_stage="DISCOVERED",
    )
    db.add(job)
    await db.flush()
    return {"job_id": str(job.id), "status": "pending"}


@router.get("/licences", response_model=list[LicenceResponse])
async def list_licences(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataLicence))
    return [LicenceResponse(
        id=l.id, provider=l.provider, dataset=l.dataset, licence_type=l.licence_type,
        display_allowed=l.display_allowed, export_allowed=l.export_allowed,
        contract_expiry=str(l.contract_expiry) if l.contract_expiry else None,
    ) for l in result.scalars().all()]
