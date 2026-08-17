"""Licensing module — DataLicence model."""

from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Boolean, Date, DateTime, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from src.database import Base, TimestampMixin, UUIDMixin


class DataLicence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_licences"

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    licence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    internal_use_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    display_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    derived_data_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    redistribution_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    export_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    api_delivery_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_training_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    document_retention_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_channels: Mapped[list | None] = mapped_column(ARRAY(String(50)))
    allowed_regions: Mapped[list | None] = mapped_column(ARRAY(String(10)))
    contract_start: Mapped[date | None] = mapped_column(Date)
    contract_expiry: Mapped[date | None] = mapped_column(Date)
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_url: Mapped[str | None] = mapped_column(String(2000))
    notes: Mapped[str | None] = mapped_column(Text)
