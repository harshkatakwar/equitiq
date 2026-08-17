"""Unit tests for ResearchOS core functionality."""

# pyrefly: ignore [missing-import]
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone


# ─── Indian Number Formatting Tests ───────────────────────────
class TestIndianNumberFormatting:
    def test_format_crores(self):
        from src.shared import format_indian_number
        result = format_indian_number(25000000)
        assert "₹" in result
        assert "Cr" in result

    def test_format_lakhs(self):
        from src.shared import format_indian_number
        result = format_indian_number(500000)
        assert "₹" in result
        assert "L" in result

    def test_format_small_number(self):
        from src.shared import format_indian_number
        result = format_indian_number(125000)
        assert "₹" in result
        assert "1,25,000" in result

    def test_format_negative(self):
        from src.shared import format_indian_number
        result = format_indian_number(-5000000)
        assert "-" in result

    def test_format_none(self):
        from src.shared import format_indian_number
        assert format_indian_number(None) == "—"

    def test_parse_crore(self):
        from src.shared import parse_indian_number
        assert parse_indian_number("₹2,350 Cr") == 23500000000.0

    def test_parse_lakh(self):
        from src.shared import parse_indian_number
        assert parse_indian_number("5.5 L") == 550000.0

    def test_parse_plain(self):
        from src.shared import parse_indian_number
        result = parse_indian_number("1,25,000")
        assert result == 125000.0

    def test_parse_empty(self):
        from src.shared import parse_indian_number
        assert parse_indian_number("") is None
        assert parse_indian_number(None) is None


# ─── International Formatting Tests ──────────────────────────
class TestInternationalFormatting:
    def test_format_billions(self):
        from src.shared import format_international_number
        result = format_international_number(5000000000)
        assert "B" in result

    def test_format_millions(self):
        from src.shared import format_international_number
        result = format_international_number(2500000)
        assert "M" in result

    def test_format_thousands(self):
        from src.shared import format_international_number
        result = format_international_number(5000)
        assert "K" in result


# ─── Password Hashing Tests ─────────────────────────────────
class TestPasswordHashing:
    def test_hash_and_verify(self):
        from src.modules.identity.service import hash_password, verify_password
        hashed = hash_password("test_password_123")
        assert hashed != "test_password_123"
        assert verify_password("test_password_123", hashed)
        assert not verify_password("wrong_password", hashed)


# ─── JWT Token Tests ─────────────────────────────────────────
class TestJWT:
    def test_create_and_decode(self):
        import uuid
        from src.modules.identity.service import create_access_token, decode_access_token
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_decode_invalid(self):
        from src.modules.identity.service import decode_access_token
        assert decode_access_token("invalid.token.here") is None


# ─── AI Provider Tests ───────────────────────────────────────
class TestMockAIProvider:
    @pytest.mark.asyncio
    async def test_classify_announcement(self):
        from src.modules.ai_research.providers import MockAIProvider
        provider = MockAIProvider()
        result = await provider.classify_announcement("New order win worth ₹500 Cr", ["order_win", "dividend"])
        assert result.category == "order_win"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_generate_concall_summary(self):
        from src.modules.ai_research.providers import MockAIProvider
        provider = MockAIProvider()
        segments = [{"id": "seg-1", "text": "Revenue grew 20%", "speaker": "CEO"}]
        result = await provider.generate_concall_summary(segments, "Test Corp")
        assert len(result.sections) > 0
        assert "Test Corp" in result.sections[0].content
        assert result.model == "mock-v1"

    @pytest.mark.asyncio
    async def test_answer_without_context(self):
        from src.modules.ai_research.providers import MockAIProvider
        provider = MockAIProvider()
        result = await provider.answer_document_question("What was revenue?", [], [])
        assert "could not find" in result.answer.lower() or "not" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_create_embeddings(self):
        from src.modules.ai_research.providers import MockAIProvider
        provider = MockAIProvider()
        embeddings = await provider.create_embeddings(["hello world", "test text"])
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536
        # Deterministic — same input gives same output
        embeddings2 = await provider.create_embeddings(["hello world"])
        assert embeddings[0] == embeddings2[0]


# ─── Error Utilities Tests ───────────────────────────────────
class TestErrors:
    def test_not_found(self):
        from src.shared import not_found
        exc = not_found("Company")
        assert exc.status_code == 404

    def test_forbidden(self):
        from src.shared import forbidden
        exc = forbidden()
        assert exc.status_code == 403

    def test_limit_exceeded(self):
        from src.shared import limit_exceeded
        exc = limit_exceeded("watchlists")
        assert exc.status_code == 429


# ─── Config Tests ────────────────────────────────────────────
class TestConfig:
    def test_settings_load(self):
        from src.config import get_settings
        settings = get_settings()
        assert settings.app_name == "ResearchOS"
        assert settings.data_mode in ["demo", "official", "licensed"]

    def test_cors_origins(self):
        from src.config import get_settings
        settings = get_settings()
        origins = settings.cors_origin_list
        assert isinstance(origins, list)
        assert len(origins) > 0
