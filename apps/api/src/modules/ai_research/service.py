"""AI Research module — Service for AI operations with citation verification."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.ai_research.models import AIArtifact, AIClaim, SourceCitation, ChatConversation, ChatMessage
from src.modules.ai_research.providers import get_ai_provider, SummaryResult
from src.modules.concalls.models import ConcallEvent, Transcript, TranscriptSegment
from src.modules.subscriptions.service import check_and_record_usage


async def generate_concall_summary(
    db: AsyncSession, user_id: uuid.UUID, concall_id: uuid.UUID, idempotency_key: str | None = None
) -> AIArtifact:
    """Generate an AI concall summary with citation verification."""
    # Check usage limits
    allowed = await check_and_record_usage(
        db, user_id, "concall.summaries",
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        reference_id=concall_id, reference_type="concall_summary",
    )
    if not allowed:
        from src.shared import limit_exceeded
        raise limit_exceeded("concall.summaries")

    # Get concall with transcript
    result = await db.execute(
        select(ConcallEvent)
        .where(ConcallEvent.id == concall_id)
        .options(selectinload(ConcallEvent.transcripts).selectinload(Transcript.segments))
    )
    event = result.scalar_one_or_none()
    if not event or not event.transcripts:
        from src.shared import not_found
        raise not_found("Concall transcript")

    transcript = event.transcripts[0]
    segments = [
        {"id": str(s.id), "speaker": s.speaker_name, "role": s.speaker_role,
         "type": s.segment_type, "text": s.text, "sequence": s.sequence}
        for s in (transcript.segments or [])
    ]

    # Get company name
    from src.modules.companies.service import get_company_by_id
    company = await get_company_by_id(db, event.company_id)
    company_name = company.name if company else "Unknown"

    # Generate summary via AI provider
    provider = get_ai_provider()
    summary: SummaryResult = await provider.generate_concall_summary(segments, company_name)

    # Create AI artifact
    artifact = AIArtifact(
        company_id=event.company_id,
        artifact_type="concall_summary",
        status="processing",
        generation_timestamp=datetime.now(timezone.utc),
        data_cutoff_date=date.today(),
        model_name=summary.model,
        prompt_version=summary.prompt_version,
        input_tokens=summary.input_tokens,
        output_tokens=summary.output_tokens,
        content={"sections": [s.model_dump() for s in summary.sections]},
        source_document_version_ids=[transcript.document_version_id] if transcript.document_version_id else [],
        created_by=user_id,
    )
    db.add(artifact)
    await db.flush()

    # Create claims and citations
    total_claims = 0
    unsupported_claims = 0

    for section in summary.sections:
        for claim_data in section.claims:
            total_claims += 1
            claim = AIClaim(
                ai_artifact_id=artifact.id,
                claim_text=claim_data["claim"],
                claim_type=claim_data.get("claim_type", "general"),
                section=section.title,
                confidence=claim_data.get("confidence", 0.8),
                verification_status="pending",
            )
            db.add(claim)
            await db.flush()

            # Create citations
            citation_ids = claim_data.get("citation_ids", [])
            verified = False
            for cid in citation_ids:
                # Verify the source segment exists
                seg_result = await db.execute(
                    select(TranscriptSegment).where(TranscriptSegment.id == uuid.UUID(cid))
                ) if cid != "demo" else None

                segment = seg_result.scalar_one_or_none() if seg_result else None

                citation = SourceCitation(
                    ai_claim_id=claim.id,
                    source_type="transcript_segment",
                    source_id=uuid.UUID(cid) if cid != "demo" else None,
                    source_text=segment.text[:200] if segment else "Demo reference",
                    page_or_sequence=segment.sequence if segment else 0,
                    confidence=claim_data.get("confidence", 0.8),
                )
                db.add(citation)
                if segment:
                    verified = True

            claim.verification_status = "verified" if verified else "unsupported"
            claim.verified_at = datetime.now(timezone.utc)
            if not verified:
                unsupported_claims += 1

    artifact.total_claim_count = total_claims
    artifact.unsupported_claim_count = unsupported_claims

    # Check threshold — reject if > 30% unsupported
    if total_claims > 0 and (unsupported_claims / total_claims) > 0.3:
        artifact.status = "rejected"
    else:
        artifact.status = "published"

    await db.flush()
    return artifact


async def get_ai_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> AIArtifact | None:
    result = await db.execute(
        select(AIArtifact)
        .where(AIArtifact.id == artifact_id)
        .options(selectinload(AIArtifact.claims).selectinload(AIClaim.citations))
    )
    return result.scalar_one_or_none()


async def document_chat(
    db: AsyncSession, user_id: uuid.UUID, company_id: uuid.UUID,
    question: str, document_scope: list[uuid.UUID] | None = None,
    conversation_id: uuid.UUID | None = None,
) -> dict:
    """Answer a document question with RAG and citations."""
    # Check usage
    allowed = await check_and_record_usage(
        db, user_id, "document_chat.questions",
        idempotency_key=str(uuid.uuid4()),
    )
    if not allowed:
        from src.shared import limit_exceeded
        raise limit_exceeded("document_chat.questions")

    # Get or create conversation
    if conversation_id:
        conv_result = await db.execute(
            select(ChatConversation)
            .where(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id)
            .options(selectinload(ChatConversation.messages))
        )
        conversation = conv_result.scalar_one_or_none()
    else:
        conversation = ChatConversation(
            user_id=user_id, company_id=company_id,
            title=question[:100], document_scope=document_scope,
        )
        db.add(conversation)
        await db.flush()

    if not conversation:
        from src.shared import not_found
        raise not_found("Conversation")

    # Save user message
    user_msg = ChatMessage(conversation_id=conversation.id, role="user", content=question)
    db.add(user_msg)

    # Retrieve context — company-scoped, tenant-authorized
    from src.modules.documents.models import DocumentSection
    context_q = (
        select(DocumentSection)
        .join(DocumentSection.document_version)
        .where(DocumentSection.content.isnot(None))
    )
    # Company filtering via document version → document → company
    from src.modules.documents.models import DocumentVersion, Document
    context_q = (
        select(DocumentSection)
        .join(DocumentVersion, DocumentSection.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Document.company_id == company_id, DocumentSection.content.isnot(None))
        .limit(5)
    )
    ctx_result = await db.execute(context_q)
    sections = ctx_result.scalars().all()

    context_chunks = [
        {"id": str(s.id), "source_type": "document_section", "text": s.content or "",
         "title": s.title, "page": s.page_start}
        for s in sections
    ]

    # Also add transcript segments if available
    from src.modules.concalls.models import TranscriptSegment
    ts_q = (
        select(TranscriptSegment)
        .join(Transcript, TranscriptSegment.transcript_id == Transcript.id)
        .join(ConcallEvent, Transcript.concall_event_id == ConcallEvent.id)
        .where(ConcallEvent.company_id == company_id, TranscriptSegment.text.isnot(None))
        .limit(5)
    )
    ts_result = await db.execute(ts_q)
    for seg in ts_result.scalars().all():
        context_chunks.append({
            "id": str(seg.id), "source_type": "transcript_segment",
            "text": seg.text or "", "title": f"Transcript - {seg.speaker_name}",
        })

    # Get conversation history
    history = [{"role": m.role, "content": m.content} for m in (conversation.messages or [])]

    # Generate answer via AI provider
    provider = get_ai_provider()
    answer = await provider.answer_document_question(question, context_chunks, history)

    # Save assistant message
    assistant_msg = ChatMessage(
        conversation_id=conversation.id, role="assistant",
        content=answer.answer, citations=answer.citations,
        tokens_used=answer.tokens_used,
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "conversation_id": str(conversation.id),
        "answer": answer.answer,
        "citations": answer.citations,
        "tokens_used": answer.tokens_used,
    }
