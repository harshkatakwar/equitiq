"""Shared utilities — pagination, errors, formatting."""

from __future__ import annotations
import uuid
import re
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel
from fastapi import HTTPException, status


T = TypeVar("T")


# ─── Pagination ────────────────────────────────────────────────
class PaginationParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = 20


class PaginationMeta(BaseModel):
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: Optional[int] = None


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta


# ─── Errors ────────────────────────────────────────────────────
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: Optional[str] = None


def not_found(resource: str = "Resource") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": f"{resource} not found"},
    )


def forbidden(message: str = "Access denied") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "FORBIDDEN", "message": message},
    )


def bad_request(message: str, details: list[dict] | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "BAD_REQUEST", "message": message, "details": details or []},
    )


def limit_exceeded(feature: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "LIMIT_EXCEEDED", "message": f"Usage limit exceeded for {feature}"},
    )


# ─── Indian Number Formatting ─────────────────────────────────
def format_indian_number(value: float | int, currency: str = "INR") -> str:
    """Format number in Indian numbering system (lakhs, crores)."""
    if value is None:
        return "—"

    abs_val = abs(float(value))
    sign = "-" if value < 0 else ""

    if abs_val >= 1e7:  # Crores
        crore_val = abs_val / 1e7
        if crore_val >= 100:
            formatted = f"{crore_val:,.0f}"
        else:
            formatted = f"{crore_val:,.2f}"
        suffix = " Cr"
    elif abs_val >= 1e5:  # Lakhs
        lakh_val = abs_val / 1e5
        formatted = f"{lakh_val:,.2f}"
        suffix = " L"
    else:
        # Indian comma placement: 1,25,000
        int_part = int(abs_val)
        dec_part = abs_val - int_part
        s = str(int_part)
        if len(s) > 3:
            last3 = s[-3:]
            rest = s[:-3]
            groups = []
            while rest:
                groups.insert(0, rest[-2:] if len(rest) >= 2 else rest)
                rest = rest[:-2]
            formatted = ",".join(groups) + "," + last3
        else:
            formatted = s
        if dec_part > 0:
            formatted += f".{int(dec_part * 100):02d}"
        suffix = ""

    prefix = "₹" if currency == "INR" else ""
    return f"{sign}{prefix}{formatted}{suffix}"


def format_international_number(value: float | int) -> str:
    """Format in international style (millions, billions)."""
    if value is None:
        return "—"

    abs_val = abs(float(value))
    sign = "-" if value < 0 else ""

    if abs_val >= 1e9:
        return f"{sign}{abs_val / 1e9:,.2f}B"
    elif abs_val >= 1e6:
        return f"{sign}{abs_val / 1e6:,.2f}M"
    elif abs_val >= 1e3:
        return f"{sign}{abs_val / 1e3:,.2f}K"
    return f"{sign}{abs_val:,.2f}"


def parse_indian_number(text: str) -> float | None:
    """Parse Indian-formatted numbers like ₹1,25,000 or 2,350 Cr."""
    if not text:
        return None
    cleaned = text.strip().replace("₹", "").replace(",", "").strip()
    match = re.match(r"^(-?\d+\.?\d*)\s*(Cr|Crore|L|Lakh|K|M|B)?\.?$", cleaned, re.IGNORECASE)
    if not match:
        return None
    val = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    multipliers = {"cr": 1e7, "crore": 1e7, "l": 1e5, "lakh": 1e5, "k": 1e3, "m": 1e6, "b": 1e9}
    return val * multipliers.get(suffix, 1)
