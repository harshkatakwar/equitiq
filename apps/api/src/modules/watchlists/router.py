"""Watchlists module — Models, Service, Router with plan-limit enforcement."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text, text, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base, TimestampMixin, UUIDMixin, get_db
from src.shared import not_found, forbidden, limit_exceeded
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

router = APIRouter()


# ─── Models ───────────────────────────────────────────────────
class Watchlist(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "watchlists"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="watchlists")
    companies: Mapped[list[WatchlistCompany]] = relationship(back_populates="watchlist", lazy="selectin")


class WatchlistCompany(UUIDMixin, Base):
    __tablename__ = "watchlist_companies"

    watchlist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("watchlists.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"))

    watchlist: Mapped[Watchlist] = relationship(back_populates="companies")


# ─── Schemas ──────────────────────────────────────────────────
class WatchlistCreate(BaseModel):
    name: str = Field(max_length=200)
    description: Optional[str] = None


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


class WatchlistCompanyAdd(BaseModel):
    company_id: uuid.UUID
    notes: Optional[str] = None


class WatchlistCompanyResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    display_order: int
    notes: Optional[str] = None
    added_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class WatchlistResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    display_order: int = 0
    company_count: int = 0
    companies: list[WatchlistCompanyResponse] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ─── Service ──────────────────────────────────────────────────
async def get_watchlist_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Watchlist).where(
            Watchlist.user_id == user_id, Watchlist.is_deleted == False
        )
    )
    return result.scalar() or 0


async def get_watchlist_limit(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Get watchlist limit from subscription entitlements."""
    from src.modules.subscriptions.service import get_entitlement_limit
    return await get_entitlement_limit(db, user_id, "watchlists.count", default=2)


# ─── Routes ───────────────────────────────────────────────────
@router.get("", response_model=list[WatchlistResponse])
async def list_watchlists(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.is_deleted == False)
        .order_by(Watchlist.display_order)
    )
    watchlists = result.scalars().all()
    return [WatchlistResponse(
        id=w.id, name=w.name, description=w.description, display_order=w.display_order,
        company_count=len(w.companies or []),
        companies=[WatchlistCompanyResponse.model_validate(c) for c in (w.companies or [])],
        created_at=w.created_at,
    ) for w in watchlists]


@router.post("", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(
    body: WatchlistCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    count = await get_watchlist_count(db, user.id)
    max_allowed = await get_watchlist_limit(db, user.id)
    if count >= max_allowed:
        raise limit_exceeded(f"watchlists (max {max_allowed})")

    watchlist = Watchlist(user_id=user.id, name=body.name, description=body.description, display_order=count)
    db.add(watchlist)
    await db.flush()
    return WatchlistResponse(id=watchlist.id, name=watchlist.name, description=watchlist.description,
                             display_order=watchlist.display_order, company_count=0, created_at=watchlist.created_at)


@router.patch("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: uuid.UUID, body: WatchlistUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise not_found("Watchlist")
    if body.name is not None:
        watchlist.name = body.name
    if body.description is not None:
        watchlist.description = body.description
    await db.flush()
    return WatchlistResponse(id=watchlist.id, name=watchlist.name, description=watchlist.description,
                             display_order=watchlist.display_order,
                             company_count=len(watchlist.companies or []), created_at=watchlist.created_at)


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise not_found("Watchlist")
    watchlist.is_deleted = True
    await db.flush()


@router.post("/{watchlist_id}/companies", response_model=WatchlistCompanyResponse, status_code=201)
async def add_company(
    watchlist_id: uuid.UUID, body: WatchlistCompanyAdd,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        raise not_found("Watchlist")

    # Check companies-per-list limit
    from src.modules.subscriptions.service import get_entitlement_limit
    max_companies = await get_entitlement_limit(db, user.id, "watchlists.companies_per_list", default=50)
    if len(watchlist.companies or []) >= max_companies:
        raise limit_exceeded(f"companies per watchlist (max {max_companies})")

    wc = WatchlistCompany(
        watchlist_id=watchlist_id, company_id=body.company_id,
        notes=body.notes, display_order=len(watchlist.companies or [])
    )
    db.add(wc)
    await db.flush()
    return WatchlistCompanyResponse.model_validate(wc)


@router.delete("/{watchlist_id}/companies/{company_id}", status_code=204)
async def remove_company(
    watchlist_id: uuid.UUID, company_id: uuid.UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WatchlistCompany).join(Watchlist).where(
            WatchlistCompany.watchlist_id == watchlist_id,
            WatchlistCompany.company_id == company_id,
            Watchlist.user_id == user.id,
        )
    )
    wc = result.scalar_one_or_none()
    if not wc:
        raise not_found("Company in watchlist")
    await db.delete(wc)
