"""Screening module — API routes for stock screener."""

from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.shared import not_found
from src.modules.identity.dependencies import get_current_user, get_optional_user
from src.modules.identity.models import User
from src.modules.screening.schemas import (
    ScreenerRequest, ScreenerResponse, SavedScreenRequest, SavedScreenResponse,
    ALLOWED_SCREEN_FIELDS,
)
from src.modules.screening.service import execute_screen
from src.modules.screening.models import SavedFilter

router = APIRouter()


@router.post("/execute", response_model=ScreenerResponse)
async def run_screen(body: ScreenerRequest, db: AsyncSession = Depends(get_db)):
    """Execute a stock screen with filters."""
    return await execute_screen(db, body)


@router.get("/fields")
async def available_fields():
    """Return the list of fields available for screening."""
    return {"fields": sorted(ALLOWED_SCREEN_FIELDS)}


@router.get("/presets")
async def preset_screens():
    """Return labeled example screens (not recommendations)."""
    return {
        "presets": [
            {
                "name": "High-margin companies",
                "description": "Companies with EBITDA margin above 25% — illustrative filter, not a recommendation",
                "filters": [{"field": "ebitda_margin", "operator": "gt", "value": 25}],
                "sort_by": "ebitda_margin",
            },
            {
                "name": "Large-cap by market cap",
                "description": "Top companies by market capitalisation — illustrative filter, not a recommendation",
                "filters": [],
                "sort_by": "market_cap",
            },
            {
                "name": "Revenue leaders",
                "description": "Companies with highest quarterly revenue — illustrative filter, not a recommendation",
                "filters": [{"field": "revenue", "operator": "gt", "value": 10000}],
                "sort_by": "revenue",
            },
        ],
        "disclaimer": "These are illustrative filter examples and do not constitute stock recommendations.",
    }


@router.post("/save", response_model=SavedScreenResponse, status_code=201)
async def save_screen(
    body: SavedScreenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a screen configuration for later use."""
    sf = SavedFilter(
        user_id=user.id,
        name=body.name,
        description=body.description,
        filter_expression={
            "filters": [f.model_dump() for f in body.filters],
            "sort_by": body.sort_by,
            "sort_order": body.sort_order,
        },
    )
    db.add(sf)
    await db.flush()
    return SavedScreenResponse(
        id=sf.id, name=sf.name, description=sf.description,
        filter_expression=sf.filter_expression,
        created_at=str(sf.created_at) if sf.created_at else None,
    )


@router.get("/saved", response_model=list[SavedScreenResponse])
async def list_saved_screens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's saved screens."""
    result = await db.execute(
        select(SavedFilter).where(SavedFilter.user_id == user.id).order_by(SavedFilter.created_at.desc())
    )
    screens = result.scalars().all()
    return [SavedScreenResponse(
        id=s.id, name=s.name, description=s.description,
        filter_expression=s.filter_expression,
        created_at=str(s.created_at) if s.created_at else None,
    ) for s in screens]


@router.delete("/saved/{screen_id}", status_code=204)
async def delete_saved_screen(
    screen_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved screen."""
    result = await db.execute(
        select(SavedFilter).where(SavedFilter.id == screen_id, SavedFilter.user_id == user.id)
    )
    sf = result.scalar_one_or_none()
    if not sf:
        raise not_found("Saved screen")
    await db.delete(sf)
