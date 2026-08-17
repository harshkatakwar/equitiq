"""Gemini AI Provider implementation."""

from __future__ import annotations
import json
from google import genai
from google.genai import types

from src.config import get_settings
from src.modules.ai_research.providers import (
    AIProvider,
    ClassificationResult,
    SummaryResult,
    SummarySection,
    AnswerResult,
)


class GeminiAIProvider(AIProvider):
    """AI provider implementation using Google Gemini."""

    def __init__(self):
        settings = get_settings()
        if not settings.ai_provider_api_key:
            raise ValueError("ai_provider_api_key is required for Gemini provider")
        
        self.client = genai.Client(api_key=settings.ai_provider_api_key)
        self.model = settings.ai_default_model
        self.embedding_model = settings.ai_embedding_model

    async def classify_announcement(self, text: str, categories: list[str]) -> ClassificationResult:
        prompt = f"""
        Classify the following corporate announcement into ONE of these categories: {', '.join(categories)}.
        Respond ONLY with a JSON object containing:
        - "category": the chosen category
        - "confidence": a float between 0 and 1
        - "explanation": a short reason for the choice

        Announcement text:
        {text}
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        result_dict = json.loads(response.text)
        return ClassificationResult(**result_dict)

    async def generate_concall_summary(self, transcript_segments: list[dict], company_name: str) -> SummaryResult:
        # Prepare the transcript text
        transcript_text = "\n".join([f"{seg['speaker']}: {seg['text']}" for seg in transcript_segments])
        
        prompt = f"""
        Summarize the following earnings conference call transcript for {company_name}.
        Structure the summary into sections like "Executive Summary", "Financial Performance", "Management Guidance", "Analyst Q&A".
        For each section, extract key factual claims.
        
        Respond ONLY with a JSON object matching this schema:
        {{
            "sections": [
                {{
                    "title": "Section Title",
                    "content": "Section text paragraph.",
                    "claims": [
                        {{
                            "claim": "Specific factual claim extracted",
                            "claim_type": "reported_metric" | "management_guidance" | "other",
                            "confidence": 0.95
                        }}
                    ]
                }}
            ]
        }}

        Transcript:
        {transcript_text[:30000]}  # limit length for now
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        result_dict = json.loads(response.text)
        
        sections = [SummarySection(**sec) for sec in result_dict.get("sections", [])]
        
        return SummaryResult(
            sections=sections,
            model=self.model,
            prompt_version="v1",
            input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        )

    async def generate_annual_report_summary(self, sections: list[dict], company_name: str) -> SummaryResult:
        # Simplified implementation for now
        return SummaryResult(
            sections=[SummarySection(title="Overview", content=f"Gemini summary for {company_name}", claims=[])],
            model=self.model,
            prompt_version="v1",
        )

    async def generate_company_overview(self, context: dict, company_name: str) -> SummaryResult:
        # Simplified implementation for now
        return SummaryResult(
            sections=[SummarySection(title="Overview", content=f"Gemini overview for {company_name}", claims=[])],
            model=self.model,
            prompt_version="v1",
        )

    async def answer_document_question(
        self, question: str, context_chunks: list[dict], conversation_history: list[dict]
    ) -> AnswerResult:
        context_text = "\n\n".join([f"Source [{i}]: {chunk['text']}" for i, chunk in enumerate(context_chunks)])
        
        prompt = f"""
        Answer the following question based ONLY on the provided context chunks.
        If the answer cannot be found in the context, say "I cannot answer this based on the provided documents."
        Cite your sources using the chunk index like [0], [1].
        
        Context:
        {context_text}
        
        Question: {question}
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        
        # Simple citation extraction for this example
        citations = []
        for i, chunk in enumerate(context_chunks):
            if f"[{i}]" in response.text:
                citations.append({
                    "source_type": chunk.get("source_type", "document_section"),
                    "source_id": chunk.get("id", "gemini-generated"),
                    "text": chunk.get("text", "")[:100],
                    "confidence": 0.9,
                })

        return AnswerResult(
            answer=response.text,
            citations=citations,
            tokens_used=(response.usage_metadata.total_token_count if response.usage_metadata else 0),
            model=self.model,
        )

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Map the model name because text-embedding-004 needs models/ prefix usually or specific call structure in new SDK
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=texts,
        )
        
        # In the new SDK, response.embeddings is a list of embeddings
        return [emb.values for emb in response.embeddings]
