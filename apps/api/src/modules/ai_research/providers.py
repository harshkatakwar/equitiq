"""AI Research module — Provider abstraction and mock implementation."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from decimal import Decimal
import hashlib
import json


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    explanation: str


class SummarySection(BaseModel):
    title: str
    content: str
    claims: list[dict] = []


class SummaryResult(BaseModel):
    sections: list[SummarySection]
    model: str
    prompt_version: str
    input_tokens: int = 0
    output_tokens: int = 0


class AnswerResult(BaseModel):
    answer: str
    citations: list[dict] = []
    tokens_used: int = 0
    model: str = ""


class AIProvider(ABC):
    """Abstract AI provider interface — all AI operations go through this."""

    @abstractmethod
    async def classify_announcement(self, text: str, categories: list[str]) -> ClassificationResult:
        ...

    @abstractmethod
    async def generate_concall_summary(self, transcript_segments: list[dict], company_name: str) -> SummaryResult:
        ...

    @abstractmethod
    async def generate_annual_report_summary(self, sections: list[dict], company_name: str) -> SummaryResult:
        ...

    @abstractmethod
    async def generate_company_overview(self, context: dict, company_name: str) -> SummaryResult:
        ...

    @abstractmethod
    async def answer_document_question(
        self, question: str, context_chunks: list[dict], conversation_history: list[dict]
    ) -> AnswerResult:
        ...

    @abstractmethod
    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        ...


class MockAIProvider(AIProvider):
    """Deterministic mock provider for demo mode and testing."""

    async def classify_announcement(self, text: str, categories: list[str]) -> ClassificationResult:
        # Deterministic classification based on text content
        text_lower = text.lower()
        if "order" in text_lower or "contract" in text_lower:
            return ClassificationResult(category="order_win", confidence=0.92, explanation="Text mentions order/contract wins")
        if "dividend" in text_lower:
            return ClassificationResult(category="dividend", confidence=0.95, explanation="Dividend announcement detected")
        if "acquisition" in text_lower:
            return ClassificationResult(category="acquisition", confidence=0.88, explanation="Acquisition mentioned")
        return ClassificationResult(category="other_material", confidence=0.75, explanation="General material announcement")

    async def generate_concall_summary(self, transcript_segments: list[dict], company_name: str) -> SummaryResult:
        sections = [
            SummarySection(
                title="Executive Summary",
                content=f"Demo content — not an exchange filing. {company_name} reported strong quarterly performance with key operational improvements across segments.",
                claims=[
                    {"claim": f"{company_name} reported strong quarterly performance", "claim_type": "reported_metric",
                     "citation_ids": [transcript_segments[0]["id"] if transcript_segments else "demo"], "confidence": 0.92}
                ],
            ),
            SummarySection(
                title="Reported Performance",
                content=f"Demo content — not an exchange filing. Revenue growth was driven by volume expansion and improved realization. Operating margins expanded due to cost optimization.",
                claims=[
                    {"claim": "Revenue growth was driven by volume expansion", "claim_type": "reported_metric",
                     "citation_ids": [transcript_segments[1]["id"] if len(transcript_segments) > 1 else "demo"], "confidence": 0.89}
                ],
            ),
            SummarySection(
                title="Management Guidance",
                content=f"Demo content — not an exchange filing. Management guided for continued growth momentum in the coming quarters with stable margins.",
                claims=[
                    {"claim": "Management guided for continued growth momentum", "claim_type": "management_guidance",
                     "citation_ids": [transcript_segments[2]["id"] if len(transcript_segments) > 2 else "demo"], "confidence": 0.85}
                ],
            ),
            SummarySection(
                title="Risks and Concerns",
                content="Demo content — not an exchange filing. Key risks include input cost volatility, regulatory changes, and competitive intensity.",
                claims=[],
            ),
            SummarySection(
                title="Analyst Q&A Highlights",
                content="Demo content — not an exchange filing. Analysts focused on margin sustainability, capital allocation plans, and market share trends.",
                claims=[],
            ),
        ]
        return SummaryResult(sections=sections, model="mock-v1", prompt_version="v1", input_tokens=5000, output_tokens=1500)

    async def generate_annual_report_summary(self, sections: list[dict], company_name: str) -> SummaryResult:
        return SummaryResult(
            sections=[
                SummarySection(title="Business Overview", content=f"Demo content — not an exchange filing. {company_name} overview.", claims=[]),
                SummarySection(title="Financial Trends", content="Demo content — not an exchange filing. Positive trends observed.", claims=[]),
            ],
            model="mock-v1", prompt_version="v1", input_tokens=8000, output_tokens=2000,
        )

    async def generate_company_overview(self, context: dict, company_name: str) -> SummaryResult:
        return SummaryResult(
            sections=[
                SummarySection(title="Company Operations", content=f"Demo content — not an exchange filing. {company_name} operations overview.", claims=[]),
            ],
            model="mock-v1", prompt_version="v1", input_tokens=3000, output_tokens=1000,
        )

    async def answer_document_question(
        self, question: str, context_chunks: list[dict], conversation_history: list[dict]
    ) -> AnswerResult:
        if not context_chunks:
            return AnswerResult(
                answer="I could not find sufficient evidence in the selected sources to answer this question.",
                citations=[], tokens_used=100, model="mock-v1",
            )
        first_chunk = context_chunks[0]
        return AnswerResult(
            answer=f"Demo content — not an exchange filing. Based on the available documents: {first_chunk.get('text', '')[:200]}...",
            citations=[{"source_type": first_chunk.get("source_type", "document_section"),
                        "source_id": first_chunk.get("id", "demo"),
                        "text": first_chunk.get("text", "")[:100], "confidence": 0.88}],
            tokens_used=500, model="mock-v1",
        )

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic hash-based embeddings."""
        embeddings = []
        for text in texts:
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Create a 1536-dim vector from hash
            embedding = []
            for i in range(1536):
                byte_idx = i % len(hash_bytes)
                embedding.append((hash_bytes[byte_idx] - 128) / 128.0)
            embeddings.append(embedding)
        return embeddings


def get_ai_provider() -> AIProvider:
    """Factory to get the configured AI provider."""
    from src.config import get_settings
    settings = get_settings()
    if settings.ai_provider == "mock":
        return MockAIProvider()
    elif settings.ai_provider == "gemini":
        from src.modules.ai_research.gemini_provider import GeminiAIProvider
        return GeminiAIProvider()
    
    # Fallback to mock for unknown providers or unconfigured keys
    return MockAIProvider()
