"""AI Research module — API routes."""

from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.shared import not_found
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User
from src.modules.ai_research.service import generate_concall_summary, get_ai_artifact, document_chat

router = APIRouter()


class ConcallSummaryRequest(BaseModel):
    concall_id: uuid.UUID
    idempotency_key: Optional[str] = None


class DocumentChatRequest(BaseModel):
    company_id: uuid.UUID
    question: str
    document_scope: Optional[list[uuid.UUID]] = None
    conversation_id: Optional[uuid.UUID] = None


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    artifact_type: str
    status: str
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    content: Optional[dict] = None
    total_claim_count: Optional[int] = None
    unsupported_claim_count: Optional[int] = None
    claims: list[dict] = []
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[dict] = []
    tokens_used: int = 0


@router.post("/concall-summary", response_model=ArtifactResponse)
async def create_concall_summary(
    body: ConcallSummaryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    artifact = await generate_concall_summary(db, user.id, body.concall_id, body.idempotency_key)
    return ArtifactResponse(
        id=artifact.id, company_id=artifact.company_id,
        artifact_type=artifact.artifact_type, status=artifact.status,
        model_name=artifact.model_name, prompt_version=artifact.prompt_version,
        content=artifact.content,
        total_claim_count=artifact.total_claim_count,
        unsupported_claim_count=artifact.unsupported_claim_count,
        claims=[
            {
                "claim_text": c.claim_text, "claim_type": c.claim_type,
                "confidence": float(c.confidence) if c.confidence else None,
                "verification_status": c.verification_status,
                "citations": [
                    {"source_type": ci.source_type, "source_text": ci.source_text,
                     "page_or_sequence": ci.page_or_sequence, "confidence": float(ci.confidence) if ci.confidence else None}
                    for ci in (c.citations or [])
                ]
            } for c in (artifact.claims or [])
        ],
    )


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    artifact = await get_ai_artifact(db, artifact_id)
    if not artifact:
        raise not_found("AI Artifact")
    return ArtifactResponse(
        id=artifact.id, company_id=artifact.company_id,
        artifact_type=artifact.artifact_type, status=artifact.status,
        model_name=artifact.model_name, prompt_version=artifact.prompt_version,
        content=artifact.content,
        total_claim_count=artifact.total_claim_count,
        unsupported_claim_count=artifact.unsupported_claim_count,
        claims=[
            {
                "claim_text": c.claim_text, "claim_type": c.claim_type,
                "confidence": float(c.confidence) if c.confidence else None,
                "verification_status": c.verification_status,
                "citations": [
                    {"source_type": ci.source_type, "source_text": ci.source_text,
                     "page_or_sequence": ci.page_or_sequence}
                    for ci in (c.citations or [])
                ]
            } for c in (artifact.claims or [])
        ],
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: DocumentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await document_chat(
        db, user.id, body.company_id, body.question,
        body.document_scope, body.conversation_id,
    )
    return ChatResponse(**result)
