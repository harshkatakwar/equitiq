"""Documents module — API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database import get_db
from src.shared import not_found
from src.modules.documents.service import get_company_documents
from src.modules.documents.schemas import DocumentResponse, DocumentVersionResponse

router = APIRouter()


@router.get("/companies/{company_id}/documents", response_model=list[DocumentResponse])
async def company_documents(
    company_id: UUID,
    doc_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    docs = await get_company_documents(db, company_id, doc_type, limit)
    return [
        DocumentResponse(
            id=d.id,
            title=d.title,
            document_type=d.document_type,
            filing_type=d.filing.filing_type if d.filing else None,
            filing_date=d.filing.filing_date if d.filing else None,
            versions=[
                DocumentVersionResponse(
                    id=v.id, version_number=v.version_number,
                    source_url=v.source_url, publication_timestamp=v.publication_timestamp,
                    mime_type=v.mime_type, processing_status=v.processing_status,
                    page_count=v.page_count,
                ) for v in (d.versions or [])
            ],
            created_at=d.created_at,
        ) for d in docs
    ]
