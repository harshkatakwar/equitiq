"""Screening module — API router."""

from fastapi import APIRouter

router = APIRouter()

# Placeholders for future screening endpoints
@router.post("/execute")
async def execute_screen():
    return {"data": []}
