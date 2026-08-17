"""Documents module — Service."""

from __future__ import annotations
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.documents.models import Document, DocumentVersion, Filing


async def get_company_documents(
    db: AsyncSession, company_id: uuid.UUID, doc_type: str | None = None, limit: int = 20
) -> list[Document]:
    q = (
        select(Document)
        .where(Document.company_id == company_id)
        .options(selectinload(Document.versions), selectinload(Document.filing))
        .order_by(desc(Document.created_at))
        .limit(limit)
    )
    if doc_type:
        q = q.where(Document.document_type == doc_type)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_document_by_id(db: AsyncSession, doc_id: uuid.UUID) -> Document | None:
    result = await db.execute(
        select(Document)
        .where(Document.id == doc_id)
        .options(selectinload(Document.versions), selectinload(Document.filing))
    )
    return result.scalar_one_or_none()
